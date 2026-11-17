"""KEMAR vs. two point mics: what does a dummy head change for the agent?

Same geometry as spikes/reverb_itd (6x5x3 m room, head at (2.6, 2.2, 1.2),
source 1.75 m away, 40 azimuths at 9 deg, 48 kHz, 50 ms white-noise bursts).
Convention here follows spec.md §4.1: ITD = t_right - t_left, + = source on left.
"""
import json
import sys
import time

import numpy as np
import pyroomacoustics as pra
import types; sys.modules.setdefault("sounddevice", types.ModuleType("sounddevice"))
import slab
from pyroomacoustics.directivities import MeasuredDirectivityFile, Rotation3D
from scipy.signal import fftconvolve

FS = 48_000
C = 343.0
ROOM = [6.0, 5.0, 3.0]
HEAD = np.array([2.6, 2.2, 1.2])
DIST = 1.75
AZ = np.arange(40) * 9.0
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
BURST = int(0.05 * FS)
WIN = int(0.10 * FS)
MAX_TAU = 1.0e-3  # head ITDs reach ~0.7 ms, so widen the search
rng = np.random.default_rng(138)


def kemar_reader(path, fs):
    """file_reader_callback: MIT KEMAR (normal pinna) from the slab package."""
    h = slab.HRTF.kemar()
    ir = np.stack([np.asarray(f.data).T for f in h.data])  # (n_src, 2, taps)
    fs_file = int(h.samplerate)
    from scipy.signal import resample_poly
    from math import gcd
    g = gcd(fs, fs_file)
    ir = resample_poly(ir, fs // g, fs_file // g, axis=-1)
    src = np.asarray(h.sources.vertical_polar)  # az deg (ccw), el deg, dist m
    src_sph = np.stack([np.deg2rad(src[:, 0]), np.deg2rad(90 - src[:, 1]), src[:, 2]])
    rec = np.array([[0, 0], [0.0875, -0.0875], [0, 0]], dtype=float)
    return ir, fs, src_sph, rec, None, ["left", "right"]


def gcc_phat(x_l, x_r, fs, max_tau, interp=16):
    """Returns t_right - t_left (s); largest positive peak (spec §4.4)."""
    n = len(x_l) + len(x_r)
    spec = np.fft.rfft(x_r, n=n) * np.conj(np.fft.rfft(x_l, n=n))
    spec /= np.abs(spec) + 1e-12
    cc = np.fft.irfft(spec, n=interp * n)
    m = int(interp * fs * max_tau)
    cc = np.concatenate((cc[-m:], cc[: m + 1]))
    return (int(np.argmax(cc)) - m) / (interp * fs)


def band_ild(x_l, x_r, edges):
    X_l = np.abs(np.fft.rfft(x_l)) ** 2
    X_r = np.abs(np.fft.rfft(x_r)) ** 2
    f = np.fft.rfftfreq(len(x_l), 1 / FS)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = (f >= lo) & (f < hi)
        out.append(10 * np.log10(X_l[s].sum() / X_r[s].sum()))
    return np.array(out)


def band_level(x, edges):
    X = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / FS)
    return np.array([10 * np.log10(X[(f >= lo) & (f < hi)].sum()) for lo, hi in zip(edges[:-1], edges[1:])])


EDGES = np.geomspace(300, 16000, 13)  # 12 log-spaced bands


def src_pos(a):
    a = np.deg2rad(a)
    return HEAD + DIST * np.array([np.cos(a), np.sin(a), 0.0])


def build(model, rt60, hrtf=None, heading_deg=0.0):
    if rt60 == 0:
        room = pra.ShoeBox(ROOM, fs=FS, max_order=0, air_absorption=False)
    else:
        e, mo = pra.inverse_sabine(rt60, ROOM)
        room = pra.ShoeBox(ROOM, fs=FS, materials=pra.Material(e), max_order=mo)
    for a in AZ:
        room.add_source(src_pos(a))
    if model == "points":
        yaw = np.deg2rad(heading_deg)
        left = np.array([-np.sin(yaw), np.cos(yaw), 0]) * 0.09
        room.add_microphone_array(np.stack([HEAD + left, HEAD - left], axis=1))
    else:
        rot = Rotation3D([heading_deg], "z", degrees=True)
        room.add_microphone(HEAD, directivity=hrtf.get_mic_directivity("left", orientation=rot))
        room.add_microphone(HEAD, directivity=hrtf.get_mic_directivity("right", orientation=rot))
    return room


def run(model, rt60, hrtf=None):
    room = build(model, rt60, hrtf)
    t0 = time.perf_counter()
    room.compute_rir()
    t_rir = time.perf_counter() - t0
    itd = np.zeros((len(AZ), N))
    ild = np.zeros((len(AZ), N))
    bild = np.zeros((len(AZ), N, len(EDGES) - 1))
    blev = np.zeros((len(AZ), N, 2 * (len(EDGES) - 1)))
    t_proc = []
    for ai in range(len(AZ)):
        hl, hr = room.rir[0][ai], room.rir[1][ai]
        for k in range(N):
            t1 = time.perf_counter()
            s = rng.standard_normal(BURST)
            x = [np.pad(y, (0, max(0, WIN - len(y))))[:WIN] for y in (fftconvolve(s, hl), fftconvolve(s, hr))]
            itd[ai, k] = gcc_phat(x[0], x[1], FS, MAX_TAU) * 1e6
            t_proc.append(time.perf_counter() - t1)
            ild[ai, k] = 10 * np.log10(np.sum(x[0] ** 2) / np.sum(x[1] ** 2))
            bild[ai, k] = band_ild(x[0], x[1], EDGES)
            blev[ai, k] = np.concatenate([band_level(x[0], EDGES), band_level(x[1], EDGES)])
    return dict(itd=itd, ild=ild, bild=bild, blev=blev, t_rir=t_rir, t_proc=float(np.mean(t_proc)))


def fb_accuracy(feat, sigma_noise=None, rng=None):
    """Nearest-mean front/back classifier per mirror pair (phi, 180-phi), train/test split.
    feat: (40, N, d). Optionally add Gaussian noise of sigma_noise per feature dim."""
    n = feat.shape[1]
    tr, te = slice(0, n // 2), slice(n // 2, n)
    accs = []
    for i, a in enumerate(AZ):
        mirror = (180 - a) % 360
        j = int(round(mirror / 9)) % 40
        if j <= i or a in (90.0, 270.0):
            continue
        fa, fb = feat[i], feat[j]
        if sigma_noise is not None:
            fa = fa + rng.normal(0, sigma_noise, fa.shape)
            fb = fb + rng.normal(0, sigma_noise, fb.shape)
        ma, mb = fa[tr].mean(0), fb[tr].mean(0)
        ok = 0
        for X, own, other in ((fa[te], ma, mb), (fb[te], mb, ma)):
            d_own = np.linalg.norm(X - own, axis=1); d_oth = np.linalg.norm(X - other, axis=1)
            ok += np.sum(d_own < d_oth) + 0.5 * np.sum(d_own == d_oth)
        accs.append(ok / (2 * (n - n // 2)))
    return float(np.mean(accs)), float(np.mean(np.array(accs) >= 0.9))


if __name__ == "__main__":
    t0 = time.perf_counter()
    hrtf = MeasuredDirectivityFile(path="kemar", fs=FS, interp_order=None,
                                   file_reader_callback=kemar_reader)
    t_load = time.perf_counter() - t0
    out = {"t_load_hrtf_s": t_load}
    res = {}
    for model in ("points", "kemar"):
        for rt60 in (0, 0.4):
            r = run(model, rt60, hrtf)
            res[(model, rt60)] = r
            print(model, rt60, f"rir {r['t_rir']:.2f}s for 40 src, proc {r['t_proc']*1e3:.2f} ms", flush=True)
    srng = np.random.default_rng(0)
    for (model, rt60), r in res.items():
        key = f"{model}_rt{rt60}"
        mean_itd = r["itd"].mean(1)
        d = {
            "t_rir_40src_s": r["t_rir"],
            "t_proc_ms": r["t_proc"] * 1e3,
            "itd_mean_us": mean_itd.round(1).tolist(),
            "itd_max_us": float(np.abs(mean_itd).max()),
            "itd_step_from_center_us": float(mean_itd[1] - mean_itd[0]),
            "itd_scatter_us_median": float(np.median(r["itd"].std(1))),
            "ild_mean_db": r["ild"].mean(1).round(2).tolist(),
            "ild_max_db": float(np.abs(r["ild"].mean(1)).max()),
            "band_ild_max_db": float(np.abs(r["bild"].mean(1)).max()),
            "fb_itd_only": fb_accuracy(r["itd"][..., None]),
            "fb_itd_only_sigma20": fb_accuracy(r["itd"][..., None], 20, srng),
            "fb_itd_ild": fb_accuracy(np.stack([r["itd"] / 20, r["ild"]], -1)),
            "fb_band_ild": fb_accuracy(r["bild"]),
            "fb_band_levels_both_ears": fb_accuracy(r["blev"]),
            "fb_band_levels_both_ears_noise3db": fb_accuracy(r["blev"], 3, srng),
        }
        out[key] = d
    json.dump(out, open("kemar_results.json", "w"), indent=1)
    np.savez("kemar_results.npz", **{f"{m}_{rt}_{k}": v for (m, rt), r in res.items() for k, v in r.items() if isinstance(v, np.ndarray)})
    for k, d in out.items():
        if isinstance(d, dict):
            print(k, {kk: vv for kk, vv in d.items() if not isinstance(vv, list)})
