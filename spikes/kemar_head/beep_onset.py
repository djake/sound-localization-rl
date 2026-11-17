import sys, types
sys.modules.setdefault("sounddevice", types.ModuleType("sounddevice"))
import numpy as np
sys.path.insert(0, ".")
import beep_test as B  # reuses setup (runs its main loop on import is avoided below)
from scipy.signal import fftconvolve
FS=B.FS
for ramp in (0.005, 0.0005):
    B.RAMP = ramp; B.env = np.minimum(1, np.minimum(B.t, B.DUR - B.t) / ramp)
    for model in ("points", "kemar"):
        angles = np.array([0, 18, 45, 72, 90, 108, 135, 162, 180.0])
        room = B.build(model, 0.4, angles)
        print(f"\n{model} RT60 0.4, ramp {ramp*1e3:.1f} ms: az | ref ITD | onset-window xcorr ITD | onset ILD | full ILD")
        for i, a in enumerate(angles):
            hl, hr = room.rir[0][i], room.rir[1][i]
            arr = min(np.argmax(np.abs(hl[:600])), np.argmax(np.abs(hr[:600])))
            ref = B.gcc_phat(hl[:420], hr[:420], FS, 1e-3) * 1e6
            o = slice(max(0, arr - 48), arr + int(0.003 * FS))  # ~3 ms: before floor reflection (~3.6 ms)
            itds, ilds, fild = [], [], []
            for k in range(10):
                s = B.beep()
                xl = fftconvolve(s, hl)[: B.WIN]; xr = fftconvolve(s, hr)[: B.WIN]
                itds.append(B.gcc_plain(xl[o], xr[o]) * 1e6)
                ilds.append(10*np.log10(np.sum(xl[o]**2)/np.sum(xr[o]**2)))
                fild.append(10*np.log10(np.sum(xl**2)/np.sum(xr**2)))
            print(f"  {a:5.0f} | {ref:5.0f} | {np.mean(itds):6.0f}±{np.std(itds):3.0f} | {np.mean(ilds):5.1f}±{np.std(ilds):.1f} | {np.mean(fild):5.1f}")
