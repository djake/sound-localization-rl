import sys, types, time
sys.modules.setdefault("sounddevice", types.ModuleType("sounddevice"))
import numpy as np, pyroomacoustics as pra
from pyroomacoustics.directivities import MeasuredDirectivityFile, Rotation3D
sys.path.insert(0, ".")
from spike_kemar import kemar_reader, gcc_phat, src_pos, HEAD, ROOM, FS

# raw KEMAR: onset difference at az=90 (left) in the data itself
ir, fs, sph, rec, _, _ = kemar_reader(None, FS)
az = np.rad2deg(sph[0]); el = 90 - np.rad2deg(sph[1])
for a in (0, 30, 90, 150):
    i = np.argmin(np.abs(((az - a + 180) % 360) - 180) + 10 * np.abs(el))
    l, r = ir[i]
    print(f"raw az={az[i]:.0f} el={el[i]:.0f}: peak L {np.argmax(abs(l))} R {np.argmax(abs(r))}  "
          f"gcc ITD {gcc_phat(l, r, FS, 1e-3)*1e6:.0f} us")

for order in (None, 12):
    h = MeasuredDirectivityFile(path="kemar", fs=FS, interp_order=order, file_reader_callback=kemar_reader)
    for rt in (0, 0.4):
        for a in (0, 30, 90, 150):
            if rt == 0:
                room = pra.ShoeBox(ROOM, fs=FS, max_order=0, air_absorption=False)
            else:
                e, mo = pra.inverse_sabine(rt, ROOM)
                room = pra.ShoeBox(ROOM, fs=FS, materials=pra.Material(e), max_order=mo)
            room.add_source(src_pos(a))
            rot = Rotation3D([0.0], "z", degrees=True)
            room.add_microphone(HEAD, directivity=h.get_mic_directivity("left", orientation=rot))
            room.add_microphone(HEAD, directivity=h.get_mic_directivity("right", orientation=rot))
            t = time.perf_counter(); room.compute_rir(); t = time.perf_counter() - t
            l, r = room.rir[0][0], room.rir[1][0]
            n = min(len(l), len(r))
            # direct-path segment only (first 5 ms after the earliest peak)
            p = min(np.argmax(abs(l)), np.argmax(abs(r)))
            seg = slice(max(0, p - 100), p + 240)
            print(f"order={order} rt={rt} az={a}: len {len(l)} peakL {np.argmax(abs(l))} peakR {np.argmax(abs(r))} "
                  f"ITD full {gcc_phat(l[:n], r[:n], FS, 1e-3)*1e6:.0f} direct {gcc_phat(l[seg], r[seg], FS, 1e-3)*1e6:.0f} us  rir {t:.2f}s")
            if rt == 0.4 and a == 90:
                break  # reverberant is slow; one angle is enough
