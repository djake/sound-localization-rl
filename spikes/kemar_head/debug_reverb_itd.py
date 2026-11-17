import sys, types
sys.modules.setdefault("sounddevice", types.ModuleType("sounddevice"))
import numpy as np, pyroomacoustics as pra
from scipy.signal import fftconvolve, butter, sosfiltfilt
from pyroomacoustics.directivities import MeasuredDirectivityFile, Rotation3D
sys.path.insert(0, ".")
from spike_kemar import kemar_reader, gcc_phat, src_pos, HEAD, ROOM, FS

h = MeasuredDirectivityFile(path="kemar", fs=FS, interp_order=None, file_reader_callback=kemar_reader)
e, mo = pra.inverse_sabine(0.4, ROOM)
rng = np.random.default_rng(1)
lp = butter(6, 1500, "low", fs=FS, output="sos")
BURST, WIN = int(0.05 * FS), int(0.10 * FS)


def drr(rir, d_samp):
    p = np.argmax(np.abs(rir[: d_samp + 200]))
    direct = np.sum(rir[max(0, p - 48): p + 96] ** 2)
    return 10 * np.log10(direct / (np.sum(rir ** 2) - direct))


for model in ("points", "kemar"):
    for a in (45, 63, 135):
        room = pra.ShoeBox(ROOM, fs=FS, materials=pra.Material(e), max_order=mo)
        room.add_source(src_pos(a))
        if model == "points":
            room.add_microphone_array(np.stack([HEAD + [0, .09, 0], HEAD - [0, .09, 0]], 1))
        else:
            rot = Rotation3D([0.0], "z", degrees=True)
            room.add_microphone(HEAD, directivity=h.get_mic_directivity("left", orientation=rot))
            room.add_microphone(HEAD, directivity=h.get_mic_directivity("right", orientation=rot))
        room.compute_rir()
        hl, hr = room.rir[0][0], room.rir[1][0]
        d = int(1.75 / 343 * FS) + 400
        res = {"full": [], "lp1.5k": [], "onset10ms": [], "onset10ms_lp": []}
        for k in range(20):
            s = rng.standard_normal(BURST)
            xl = np.pad(fftconvolve(s, hl), (0, WIN))[:WIN]
            xr = np.pad(fftconvolve(s, hr), (0, WIN))[:WIN]
            o = slice(0, int(0.01 * FS) + 400)  # first 10 ms of arrival (plus pra's fixed delay)
            res["full"].append(gcc_phat(xl, xr, FS, 1e-3))
            res["lp1.5k"].append(gcc_phat(sosfiltfilt(lp, xl), sosfiltfilt(lp, xr), FS, 1e-3))
            res["onset10ms"].append(gcc_phat(xl[o], xr[o], FS, 1e-3))
            res["onset10ms_lp"].append(gcc_phat(sosfiltfilt(lp, xl)[o], sosfiltfilt(lp, xr)[o], FS, 1e-3))
        print(f"{model} az={a}: DRR L {drr(hl, d):+.1f} dB, R {drr(hr, d):+.1f} dB | " +
              " ".join(f"{k}: med {np.median(v)*1e6:.0f} us, IQR {np.subtract(*np.percentile(v,[75,25]))*1e6:.0f}" for k, v in res.items()))
