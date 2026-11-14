"""Calibration spike: what does reverberation do to ITD (and ILD) estimates?

Throwaway exploratory code, not project code. Run from the repo root:

    .venv/bin/python spikes/reverb_itd/spike.py

Writes results.npz, timing.json and PNG figures next to this file.

Conventions (match sim/acoustics.py and sim/tdoa.py):
  * Head faces +x (0 deg). Left mic at +y, right mic at -y.
  * Source azimuth phi is measured counterclockwise from the facing direction,
    so phi = +90 deg is straight left.
  * ITD = t_left - t_right (sim.tdoa.gcc_phat). A source on the LEFT reaches the
    left mic first, so ITD is NEGATIVE on the left:  ITD = -(b/c) * sin(phi).
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pyroomacoustics as pra
from scipy.signal import fftconvolve

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from sim.tdoa import gcc_phat  # noqa: E402  (reuse the project's estimator)

OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- setup
FS = 48_000
C = pra.constants.get("c")
ROOM_DIM = [6.0, 5.0, 3.0]
HEAD = np.array([2.6, 2.2, 1.2])  # slightly off-center
B = 0.18  # mic spacing (m)
SRC_DIST = 1.75  # m
BURST_MS = 50
WINDOW_MS = 100  # listening window: burst + 50 ms of tail
N_BURSTS = 50
AZ = np.arange(40) * 9.0  # source azimuths, deg
RT60S = [0.0, 0.2, 0.4, 0.7]  # targets; 0.0 = anechoic
SNRS = [None, 20.0, 10.0, 0.0]  # dB; None = no mic noise
MAX_TAU = B / C
GCC_INTERP = 16

rng = np.random.default_rng(138)
burst_len = int(FS * BURST_MS / 1000)
win_len = int(FS * WINDOW_MS / 1000)

mics = np.stack([HEAD + [0, B / 2, 0], HEAD - [0, B / 2, 0]], axis=1)  # (3, 2): left, right


def src_pos(phi_deg: float) -> np.ndarray:
    a = np.deg2rad(phi_deg)
    return HEAD + SRC_DIST * np.array([np.cos(a), np.sin(a), 0.0])


def make_room(rt60: float, sources) -> pra.ShoeBox:
    if rt60 == 0.0:
        room = pra.ShoeBox(ROOM_DIM, fs=FS, max_order=0)
    else:
        e_abs, max_order = pra.inverse_sabine(rt60, ROOM_DIM)
        room = pra.ShoeBox(ROOM_DIM, fs=FS, materials=pra.Material(e_abs), max_order=max_order)
    for s in sources:
        room.add_source(s)
    room.add_microphone_array(mics)
    return room


# Expected ITDs: far-field formula and exact geometric (near-field) delay.
itd_formula = -(B / C) * np.sin(np.deg2rad(AZ))
itd_geom = np.array(
    [(np.linalg.norm(src_pos(p) - mics[:, 0]) - np.linalg.norm(src_pos(p) - mics[:, 1])) / C for p in AZ]
)

itd = np.full((len(RT60S), len(SNRS), len(AZ), N_BURSTS), np.nan)
ild = np.full_like(itd, np.nan)
timing = {"per_cell_rir_s": {}, "batched_rir_all40_s": {}, "per_burst_s": {}, "measured_rt60_s": {}}

for ri, rt60 in enumerate(RT60S):
    # Per-cell RIR cost (one room per cell, as sim/acoustics.py does): time 3 cells.
    ts = []
    for p in AZ[:3]:
        r = make_room(rt60, [src_pos(p)])
        t0 = time.perf_counter()
        r.compute_rir()
        ts.append(time.perf_counter() - t0)
    timing["per_cell_rir_s"][rt60] = float(np.mean(ts))

    # All 40 sources in one room: RIRs for every source-mic pair in one call.
    room = make_room(rt60, [src_pos(p) for p in AZ])
    t0 = time.perf_counter()
    room.compute_rir()
    timing["batched_rir_all40_s"][rt60] = time.perf_counter() - t0
    if rt60 > 0:
        timing["measured_rt60_s"][rt60] = float(np.mean(room.measure_rt60()))

    burst_times = []
    for ai in range(len(AZ)):
        h_l, h_r = room.rir[0][ai], room.rir[1][ai]
        for k in range(N_BURSTS):
            t0 = time.perf_counter()
            s = rng.standard_normal(burst_len)
            # pad/truncate each channel to the listening window (anechoic RIRs are short)
            clean = np.stack(
                [np.pad(y, (0, max(0, win_len - len(y))))[:win_len] for y in (fftconvolve(s, h_l), fftconvolve(s, h_r))]
            )
            p_sig = np.mean(clean**2)
            for si, snr in enumerate(SNRS):
                x = clean
                if snr is not None:
                    sigma = np.sqrt(p_sig / 10 ** (snr / 10))
                    x = clean + sigma * rng.standard_normal(clean.shape)
                itd[ri, si, ai, k] = gcc_phat(x[0], x[1], FS, MAX_TAU, interp=GCC_INTERP)
                ild[ri, si, ai, k] = 10 * np.log10(np.sum(x[0] ** 2) / np.sum(x[1] ** 2))
            burst_times.append((time.perf_counter() - t0) / len(SNRS))
    timing["per_burst_s"][rt60] = float(np.mean(burst_times))
    print(
        f"RT60 target {rt60}: per-cell RIR {timing['per_cell_rir_s'][rt60]*1e3:.1f} ms, "
        f"batched 40 {timing['batched_rir_all40_s'][rt60]:.2f} s, "
        f"per burst {timing['per_burst_s'][rt60]*1e3:.2f} ms",
        flush=True,
    )

# Extrapolate to a full 40 head x 40 source table with 200 readings per cell.
n_cells, n_read = 1600, 200
timing["full_table_estimate_s"] = {
    rt: timing["per_cell_rir_s"][rt] * n_cells + timing["per_burst_s"][rt] * n_cells * n_read for rt in RT60S
}
cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
timing["machine"] = f"{cpu}, {platform.platform()}, python {platform.python_version()}, pyroomacoustics {pra.__version__}"

np.savez(
    OUT / "results.npz",
    itd=itd, ild=ild, az=AZ, rt60s=RT60S, snrs=np.array([np.nan if s is None else s for s in SNRS]),
    itd_formula=itd_formula, itd_geom=itd_geom, fs=FS, max_tau=MAX_TAU,
)
(OUT / "timing.json").write_text(json.dumps(timing, indent=2, default=str))
print(json.dumps(timing, indent=2, default=str))
