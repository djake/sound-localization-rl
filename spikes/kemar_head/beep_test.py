"""Smoke-detector-style beep (3.2 kHz, 100 ms, 5 ms ramps): ITD / ILD with point mics vs KEMAR."""
import sys, types
sys.modules.setdefault("sounddevice", types.ModuleType("sounddevice"))
import numpy as np, pyroomacoustics as pra
from scipy.signal import fftconvolve
from pyroomacoustics.directivities import MeasuredDirectivityFile, Rotation3D
sys.path.insert(0, ".")
from spike_kemar import kemar_reader, gcc_phat, src_pos, HEAD, ROOM, FS

F0, DUR, RAMP = 3200.0, 0.10, 0.005
t = np.arange(int(DUR * FS)) / FS
env = np.minimum(1, np.minimum(t, DUR - t) / RAMP)
WIN = int(0.15 * FS)
rng = np.random.default_rng(3)
h = MeasuredDirectivityFile(path="kemar", fs=FS, interp_order=None, file_reader_callback=kemar_reader)


def beep():
    return env * np.sin(2 * np.pi * F0 * t + rng.uniform(0, 2 * np.pi))


def gcc_plain(xl, xr, max_tau=1e-3, interp=16):
    """Plain cross-correlation (no PHAT), t_right - t_left."""
    n = len(xl) + len(xr)
    cc = np.fft.irfft(np.fft.rfft(xr, n) * np.conj(np.fft.rfft(xl, n)), interp * n)
    m = int(interp * FS * max_tau)
    cc = np.concatenate((cc[-m:], cc[: m + 1]))
    return (np.argmax(cc) - m) / (interp * FS)


def onset_itd(xl, xr, frac=0.3):
    """Envelope onset: time each ear's Hilbert envelope first crosses frac of its max."""
    from scipy.signal import hilbert
    el, er = np.abs(hilbert(xl)), np.abs(hilbert(xr))
    tl = np.argmax(el > frac * el.max()); tr = np.argmax(er > frac * er.max())
    return (tr - tl) / FS


def build(model, rt, angles):
    if rt == 0:
        room = pra.ShoeBox(ROOM, fs=FS, max_order=0, air_absorption=False)
    else:
        e, mo = pra.inverse_sabine(rt, ROOM)
        room = pra.ShoeBox(ROOM, fs=FS, materials=pra.Material(e), max_order=mo)
    for a in angles:
        room.add_source(src_pos(a))
    if model == "points":
        room.add_microphone_array(np.stack([HEAD + [0, .09, 0], HEAD - [0, .09, 0]], 1))
    else:
        rot = Rotation3D([0.0], "z", degrees=True)
        room.add_microphone(HEAD, directivity=h.get_mic_directivity("left", orientation=rot))
        room.add_microphone(HEAD, directivity=h.get_mic_directivity("right", orientation=rot))
    room.compute_rir()
    return room


if __name__ == "__main__":
  for rt, angles in ((0, np.arange(0, 181, 9.0)), (0.4, np.array([0, 18, 45, 72, 90, 108, 135, 162, 180.0]))):
      for model in ("points", "kemar"):
          room = build(model, rt, angles)
          print(f"\n== {model}, RT60 {rt} ==  az | true(broadband) | GCC-PHAT | plain xcorr | onset-env | ILD dB (mean±sd over 10 beeps)")
          for i, a in enumerate(angles):
              hl, hr = room.rir[0][i], room.rir[1][i]
              # broadband reference ITD from the RIRs' direct path
              ref = gcc_phat(hl[:600] if rt == 0 else hl[:420], hr[:600] if rt == 0 else hr[:420], FS, 1e-3) * 1e6
              r = {"phat": [], "plain": [], "onset": [], "ild": []}
              for k in range(10):
                  s = beep()
                  xl = np.pad(fftconvolve(s, hl), (0, WIN))[:WIN]
                  xr = np.pad(fftconvolve(s, hr), (0, WIN))[:WIN]
                  r["phat"].append(gcc_phat(xl, xr, FS, 1e-3) * 1e6)
                  r["plain"].append(gcc_plain(xl, xr) * 1e6)
                  r["onset"].append(onset_itd(xl, xr) * 1e6)
                  r["ild"].append(10 * np.log10(np.sum(xl**2) / np.sum(xr**2)))
              f = lambda v: f"{np.mean(v):6.0f}±{np.std(v):3.0f}"
              print(f"  {a:5.0f} | {ref:6.0f} | {f(r['phat'])} | {f(r['plain'])} | {f(r['onset'])} | {np.mean(r['ild']):5.1f}±{np.std(r['ild']):.1f}")
