"""The RL environment: turn the head, listen, and declare.

The interface mirrors Gymnasium (``reset`` returns ``(obs, info)``; ``step``
returns ``(obs, reward, terminated, truncated, info)``) without depending on
it.

State (all small integers, so tabular methods work directly):
    - ``bucket``: current time-difference bucket, 0 = far left ... n-1 = far right
    - ``prev_bucket``: the bucket before the last turn, or ``n_buckets`` if there
      has been no turn yet
    - ``last_turn``: 0 = none yet, 1 = turned left, 2 = turned right

A single reading cannot tell a source in front from one behind (both give a
delay near zero); the previous bucket and the turn direction together can.

Actions:
    - 0 = turn left (counterclockwise) one head step
    - 1 = turn right (clockwise) one head step
    - 2 = declare that the source is straight ahead

Reward: ``step_reward`` for every step, plus ``correct_reward`` or
``wrong_reward`` on a declaration. A declaration is correct when the source is
within half a head step of where the head is facing. The episode ends at the
declaration, or is truncated after ``max_steps``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sim.acoustics import HeadConfig, RoomConfig, SourceConfig, TdoaTable, build_tdoa_table
from sim.tdoa import bucketize

TURN_LEFT, TURN_RIGHT, DECLARE = 0, 1, 2
NO_TURN, TURNED_LEFT, TURNED_RIGHT = 0, 1, 2


@dataclass(frozen=True)
class EnvConfig:
    room: RoomConfig = field(default_factory=RoomConfig)
    head: HeadConfig = field(default_factory=HeadConfig)
    source: SourceConfig = field(default_factory=SourceConfig)
    n_buckets: int = 9
    step_reward: float = -1.0
    correct_reward: float = 20.0
    wrong_reward: float = -20.0
    max_steps: int = 50


def angle_diff(a: float, b: float) -> float:
    """Signed difference a - b in degrees, wrapped to (-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


class SoundLocalizationEnv:
    n_actions = 3

    def __init__(self, config: EnvConfig = EnvConfig(), table: TdoaTable | None = None, cache_dir="default"):
        self.config = config
        if table is None:
            kwargs = {} if cache_dir == "default" else {"cache_dir": cache_dir}
            table = build_tdoa_table(config.room, config.head, config.source, **kwargs)
        self.table = table
        self.rng = np.random.default_rng()
        self._head_idx = 0
        self._source_idx = 0
        self._bucket = 0
        self._prev_bucket = config.n_buckets
        self._last_turn = NO_TURN
        self._steps = 0

    # Sizes of each state component, for building Q-tables.
    @property
    def state_shape(self) -> tuple[int, int, int]:
        n = self.config.n_buckets
        return (n, n + 1, 3)

    @property
    def n_states(self) -> int:
        a, b, c = self.state_shape
        return a * b * c

    def state_index(self, obs: tuple[int, int, int]) -> int:
        """Flatten an observation into a single index in ``range(n_states)``."""
        return int(np.ravel_multi_index(obs, self.state_shape))

    @property
    def head_angle(self) -> float:
        return float(self.table.head_angles[self._head_idx])

    @property
    def source_angle(self) -> float:
        return float(self.table.source_angles[self._source_idx])

    def _read_bucket(self) -> int:
        tau = self.table.tau[self._head_idx, self._source_idx]
        return bucketize(tau, self.table.max_tau, self.config.n_buckets)

    def _obs(self) -> tuple[int, int, int]:
        return (self._bucket, self._prev_bucket, self._last_turn)

    def _info(self) -> dict:
        return {
            "head_angle": self.head_angle,
            "source_angle": self.source_angle,
            "angle_error": angle_diff(self.source_angle, self.head_angle),
            "steps": self._steps,
        }

    def reset(self, seed: int | None = None, options: dict | None = None):
        """Start an episode with a random head angle and source angle.

        ``options`` may set ``head_angle`` and/or ``source_angle`` (degrees,
        snapped to the nearest grid angle) for reproducible test cases.
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        options = options or {}
        self._head_idx = self._nearest(self.table.head_angles, options.get("head_angle"))
        self._source_idx = self._nearest(self.table.source_angles, options.get("source_angle"))
        self._bucket = self._read_bucket()
        self._prev_bucket = self.config.n_buckets
        self._last_turn = NO_TURN
        self._steps = 0
        return self._obs(), self._info()

    def _nearest(self, grid: np.ndarray, angle: float | None) -> int:
        if angle is None:
            return int(self.rng.integers(len(grid)))
        return int(np.argmin([abs(angle_diff(g, angle)) for g in grid]))

    def step(self, action: int):
        if action not in (TURN_LEFT, TURN_RIGHT, DECLARE):
            raise ValueError(f"invalid action {action}")
        cfg = self.config
        self._steps += 1
        reward = cfg.step_reward
        terminated = False
        info_extra = {}

        if action == DECLARE:
            correct = abs(angle_diff(self.source_angle, self.head_angle)) <= cfg.head.step_deg / 2
            reward += cfg.correct_reward if correct else cfg.wrong_reward
            terminated = True
            info_extra["correct"] = correct
        else:
            n = len(self.table.head_angles)
            # Left is counterclockwise (increasing angle); right is clockwise.
            self._head_idx = (self._head_idx + (1 if action == TURN_LEFT else -1)) % n
            self._prev_bucket = self._bucket
            self._bucket = self._read_bucket()
            self._last_turn = TURNED_LEFT if action == TURN_LEFT else TURNED_RIGHT

        truncated = not terminated and self._steps >= cfg.max_steps
        return self._obs(), reward, terminated, truncated, {**self._info(), **info_extra}
