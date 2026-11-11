"""Room acoustics: simulate what the head's two microphones hear.

pyroomacoustics does the physics. Given a room, a sound source and microphone
positions, it computes each microphone's impulse response (direct path plus
wall reflections, if enabled) and convolves the source signal with it.

Simulating on every agent step would be slow, so ``build_tdoa_table``
simulates every (head angle, source angle) pair once, estimates the time
difference between the two microphones for each, and caches the table on disk.
During training a turn is then just a table lookup.

Angles are in degrees, measured counterclockwise from the room's +x axis. The
head faces along its angle; its left microphone is 90 degrees counterclockwise
from the facing direction and its right microphone 90 degrees clockwise.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pyroomacoustics as pra

from sim.tdoa import gcc_phat

SPEED_OF_SOUND = pra.constants.get("c")  # m/s


@dataclass(frozen=True)
class RoomConfig:
    """A rectangular room. ``max_order=0`` disables reflections (no echoes)."""

    dims: tuple[float, ...] = (8.0, 8.0)  # meters; 2D for now
    fs: int = 16000  # sample rate, Hz
    max_order: int = 0  # reflection order; raise it to add echoes
    absorption: float = 0.3  # fraction of energy absorbed per wall bounce (used when max_order > 0)


@dataclass(frozen=True)
class HeadConfig:
    """The rotating head: two microphones, one on each side."""

    mic_spacing: float = 0.15  # meters between the two microphones
    n_angles: int = 24  # discrete head angles around the circle (24 -> 15 degree steps)

    @property
    def step_deg(self) -> float:
        return 360.0 / self.n_angles

    @property
    def max_tau(self) -> float:
        """Largest physically possible delay between the microphones, in seconds."""
        return self.mic_spacing / SPEED_OF_SOUND


@dataclass(frozen=True)
class SourceConfig:
    """A stationary source playing repeated short bursts of static."""

    distance: float = 2.0  # meters from the head
    n_angles: int = 72  # discrete source angles around the circle (72 -> 5 degree steps)
    burst_ms: float = 50.0
    gap_ms: float = 50.0
    n_bursts: int = 3
    seed: int = 0  # seed for the static, so the table is reproducible


def static_bursts(source: SourceConfig, fs: int) -> np.ndarray:
    """White-noise bursts separated by silence."""
    rng = np.random.default_rng(source.seed)
    burst = int(fs * source.burst_ms / 1000)
    gap = int(fs * source.gap_ms / 1000)
    pieces = []
    for _ in range(source.n_bursts):
        pieces.append(rng.standard_normal(burst))
        pieces.append(np.zeros(gap))
    return np.concatenate(pieces)


def _unit(angle_deg: float) -> np.ndarray:
    a = np.deg2rad(angle_deg)
    return np.array([np.cos(a), np.sin(a)])


def mic_positions(center: np.ndarray, head_angle_deg: float, spacing: float) -> np.ndarray:
    """Left and right microphone positions as columns of a (2, 2) array."""
    left = center + (spacing / 2) * _unit(head_angle_deg + 90)
    right = center + (spacing / 2) * _unit(head_angle_deg - 90)
    return np.stack([left, right], axis=1)


def simulate_mics(
    head_angle_deg: float,
    source_angle_deg: float,
    room: RoomConfig = RoomConfig(),
    head: HeadConfig = HeadConfig(),
    source: SourceConfig = SourceConfig(),
    signal: np.ndarray | None = None,
) -> np.ndarray:
    """Simulate both microphone recordings. Returns an array of shape (2, n_samples): left, right."""
    if len(room.dims) != 2:
        raise NotImplementedError("Only 2D rooms are supported so far.")
    center = np.asarray(room.dims, dtype=float) / 2
    if signal is None:
        signal = static_bursts(source, room.fs)

    kwargs = {"fs": room.fs, "max_order": room.max_order}
    if room.max_order > 0:
        kwargs["materials"] = pra.Material(room.absorption)
    sim_room = pra.ShoeBox(list(room.dims), **kwargs)
    sim_room.add_source(center + source.distance * _unit(source_angle_deg), signal=signal)
    sim_room.add_microphone_array(mic_positions(center, head_angle_deg, head.mic_spacing))
    sim_room.simulate()
    return sim_room.mic_array.signals


@dataclass
class TdoaTable:
    """Estimated delay ``tau`` (seconds) for every (head angle, source angle) pair."""

    head_angles: np.ndarray  # degrees, shape (n_head,)
    source_angles: np.ndarray  # degrees, shape (n_source,)
    tau: np.ndarray  # seconds, shape (n_head, n_source)
    max_tau: float
    config: dict = field(default_factory=dict)

    def save(self, path: Path) -> None:
        np.savez(
            path,
            head_angles=self.head_angles,
            source_angles=self.source_angles,
            tau=self.tau,
            max_tau=self.max_tau,
            config=json.dumps(self.config),
        )

    @classmethod
    def load(cls, path: Path) -> "TdoaTable":
        data = np.load(path)
        return cls(
            head_angles=data["head_angles"],
            source_angles=data["source_angles"],
            tau=data["tau"],
            max_tau=float(data["max_tau"]),
            config=json.loads(str(data["config"])),
        )


def _config_dict(room: RoomConfig, head: HeadConfig, source: SourceConfig) -> dict:
    return {
        "room": asdict(room),
        "head": {**asdict(head)},
        "source": asdict(source),
        "pyroomacoustics": pra.__version__,
    }


def build_tdoa_table(
    room: RoomConfig = RoomConfig(),
    head: HeadConfig = HeadConfig(),
    source: SourceConfig = SourceConfig(),
    cache_dir: Path | str | None = Path(".cache/tdoa"),
    verbose: bool = False,
) -> TdoaTable:
    """Simulate every (head angle, source angle) pair and estimate its delay.

    Results are cached in ``cache_dir`` under a hash of the configuration, so a
    given setup is only simulated once. Pass ``cache_dir=None`` to skip caching.
    """
    config = _config_dict(room, head, source)
    cache_path = None
    if cache_dir is not None:
        key = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]
        cache_path = Path(cache_dir) / f"tdoa-{key}.npz"
        if cache_path.exists():
            return TdoaTable.load(cache_path)

    head_angles = np.arange(head.n_angles) * head.step_deg
    source_angles = np.arange(source.n_angles) * (360.0 / source.n_angles)
    signal = static_bursts(source, room.fs)
    tau = np.zeros((len(head_angles), len(source_angles)))
    for i, h in enumerate(head_angles):
        if verbose:
            print(f"head angle {h:6.1f} ({i + 1}/{len(head_angles)})", flush=True)
        for j, s in enumerate(source_angles):
            left, right = simulate_mics(h, s, room, head, source, signal=signal)
            tau[i, j] = gcc_phat(left, right, room.fs, head.max_tau)

    table = TdoaTable(head_angles, source_angles, tau, head.max_tau, config)
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        table.save(cache_path)
    return table
