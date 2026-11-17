# Spike: a simulated head (MIT KEMAR HRTF) in place of two point mics

*Run 2026-11-14. Exploratory: 20 bursts per cell, one room, head facing 0° unless noted, simple nearest-mean classifiers. Timings are from a cloud sandbox, not the team's laptops.*

## Question

What would it cost to swap the two omnidirectional point mics (spec §4.2) for a dummy head in pyroomacoustics, and what changes in the cues the agent could observe?

## Setup

Same geometry as [`spikes/reverb_itd`](../reverb_itd/RESULTS.md): 6 × 5 × 3 m room, head at (2.6, 2.2, 1.2) m, source 1.75 m away at ear height, 40 azimuths 9° apart, 48 kHz, 50 ms white-noise bursts, anechoic (max_order = 0) and RT60 target 0.4 s. ITD sign follows spec §4.1 (t_right − t_left, positive = source on the left).

The head is the **MIT KEMAR, normal pinna** (Gardner & Martin, MIT Media Lab, 1994; free to use if cited), loaded with `pyroomacoustics.directivities.MeasuredDirectivityFile` and attached as two microphones at the **same point** (head center), with left- and right-ear directivities rotated by `Rotation3D([heading_deg], "z")`. The interaural delay comes from the HRIRs, so the mics are not spaced apart.

Data source: sofacoustics.org was not reachable from the sandbox, so `kemar_reader()` in `spike_kemar.py` loads the same KEMAR set from the `slab` package and passes it in through `file_reader_callback`. On a normal machine, use `MeasuredDirectivityFile(path="mit_kemar_normal_pinna.sofa", ...)`, which pyroomacoustics' `SOFADatabase` downloads, plus `python-sofa` and `netCDF4`.

## Findings

### 1. Use `interp_order=None` (nearest measured direction). Spherical-harmonic interpolation corrupts ITD.

| Setting | 30° | 90° | 150° | Reverberant room |
|---|---|---|---|---|
| Raw KEMAR data (reference) | 246 µs | 723 µs | 259 µs | — |
| `interp_order=None` | 245 µs | 723 µs | 259 µs | Correct (e.g. 30° → 246 µs) |
| `interp_order=12` | **−29 µs** | 723 µs | **69 µs** | **Collapses to ~0 µs at every angle** |

KEMAR is measured every 5° on the horizontal plane, so nearest-neighbor lookup is at most 2.5° off the 9° grid. (`debug_rir.py`)

### 2. Build cost: roughly 120× slower impulse responses

| Receiver | RT60 0.4 s, per (heading, source) cell |
|---|---|
| Point mics | 0.12 s |
| KEMAR | 14.2 s |

Scaled to the reverb_itd spike's laptop timing (~44 ms per point-mic cell), a 1,600-cell KEMAR table is roughly **2–2.5 core-hours per room**, or about 15–25 minutes split across cores. Drawing noisy readings from the table costs about the same as now. Anechoic builds are fast for both.

### 3. ITD curve shape

| Azimuth | 0° | 9° | 27° | 45° | 90° | 108° | 135° | 162° | 180° |
|---|---|---|---|---|---|---|---|---|---|
| Point mics, b = 0.18 m | 0 | 82 | 238 | 371 | 525 | 499 | 371 | 163 | 0 |
| KEMAR (anechoic) | 0 | 82 | 206 | 370 | 723 | **820** | 375 | 181 | 0 |

- The step from centered to one turn away is the same (~82 µs). The current ±40 µs center bin still works.
- The maximum is ~820 µs, behind the ear (near 108°), not 525 µs at 90°, and the curve is bumpy. The ±260 µs ≈ 30° edge and the ±b/c lag-search limit no longer hold. The lag search needs about ±1 ms.
  - *Correction, 2026-11-16:* the ±260 µs edge does roughly hold. In `kemar_results.json` the KEMAR ITD is 206 µs at 27° and 287 µs at 36°, so 260 µs falls near 33° in front, and near 32° from directly behind. Only the lag-search limit and the maximum change.
- The formula τ = (b/c)·sin φ is no longer the reference for AT1-style tests. KEMAR's own anechoic table is.
- Mirror angles differ by 10–20 µs (e.g. 18° → 164 µs vs. 162° → 181 µs). That's a small front/back cue, mostly hidden at σ = 20 µs.

### 4. Full-window GCC-PHAT breaks in reverb with a head. Use the onset (~first 10 ms).

The head shadow lowers the far ear's direct-to-reverberant ratio:

| | Near ear DRR | Far ear DRR |
|---|---|---|
| Point mics (45°) | −4.9 dB | −5.5 dB |
| KEMAR (45° / 63° / 135°) | −2.3 / −3.4 / −3.9 dB | **−11.3 / −17.0 / −12.7 dB** |

- On the full 100 ms window, GCC-PHAT on KEMAR signals at RT60 0.4 s gives readings off by more than 100 µs **43%** of the time and on the wrong side **6%** of the time. Point mics: median error 1.3 µs.
- Using only the first ~10 ms after arrival recovers accurate ITD: 45° → 370 µs (spread 3 µs), 63° → 561 µs (1 µs), 135° → 380 µs (2 µs). This is the precedence effect, and real hardware would need the same estimator. (`debug_reverb_itd.py`)
- Low-pass filtering before GCC-PHAT does **not** work. PHAT undoes the filter. Band-limiting has to happen in the PHAT-weighted spectrum.

### 5. ILD becomes a real cue

| Azimuth | 9° | 18° | 45° | 72° | 90° | 108° | 135° | 162° | 171° |
|---|---|---|---|---|---|---|---|---|---|
| Point mics, anechoic | 0.1 | 0.2 | 0.6 | 0.9 | 0.9 | 0.9 | 0.6 | 0.2 | 0.1 dB |
| KEMAR, anechoic | 3.5 | 6.4 | 10.6 | 16.6 | 11.8 | 17.5 | 9.9 | 3.5 | 1.5 dB |
| KEMAR, RT60 0.4 (full window) | 1.1 | 1.6 | 3.6 | 4.1 | 4.0 | 4.4 | 2.7 | 0.8 | 0.1 dB |

Broadband ILD is a few dB louder in front than at the mirror angle behind.

### 6. Front/back from a single reading

Nearest-mean classifier per mirror pair (φ vs. 180° − φ), half the readings to train, half to test. 50% = chance.

| Observed features | Point mics, anechoic | KEMAR, anechoic | Point mics, RT60 0.4 | KEMAR, RT60 0.4 |
|---|---|---|---|---|
| ITD only, σ = 20 µs added | 47% | 71% | 57% | 64% |
| ITD + broadband ILD (no σ) | 55% | 96% | 65% | 68% |
| ILD in 12 log-spaced bands, 300 Hz–16 kHz | 53% | 97% | 94% | 99% |
| 12 band levels per ear | 47% | 100% | 84% | 98% |
| 12 band levels per ear, 3 dB noise | 49% | 99% | 61% | 76% |

- Anechoic is the clean comparison. In a fixed room, the room's reflections also give a learnable front/back fingerprint even for point mics (94% with band ILD at RT60 0.4). That fingerprint won't transfer to held-out rooms.
- **Implication for D5 / H2:** with spectral (per-band) cues, a single reading mostly settles front vs. back, so the exploratory check turn becomes largely unnecessary. With ITD only, the head barely changes this.
- The KEMAR RT60 0.4 ITD rows used the full-window estimator (finding 4), so they understate ITD.

### 7. Narrowband beep (3.2 kHz, 100 ms) — relevant to OQ14

(`beep_test.py`, `beep_onset.py`)

- **ITD wraps** because one cycle (312 µs) is shorter than the largest ITD. Even in the onset window at RT60 0.4, the true 371 µs reads as 58 µs and 525 µs reads as 212 µs (one cycle off). That's left-right ambiguity, with or without a head.
- **Full-beep ILD in reverb is set by room modes, not direction.** KEMAR at 90° reads −3.0 dB (wrong side). The values are deterministic per cell, so a tabular agent could memorize them in R0, and they wouldn't transfer.
- **Onset ILD (first ~3 ms, before the floor reflection) with the head works:**

| Azimuth | 0° | 18° | 45° | 72° | 90° | 108° | 135° | 162° |
|---|---|---|---|---|---|---|---|---|
| KEMAR onset ILD | 0.0 | 6.1 | 13.1 | 17.8 | 12.2 | 17.8 | 13.0 | 4.5 dB |
| Point-mic onset ILD | 0.0 | 1.3 | 2.2 | 3.0 | 3.2 | 3.0 | 2.2 | 1.3 dB |

  The spread from beep to beep is 0.1–0.2 dB. It gives clear left/right, but front/back is symmetric (45° ≈ 135°), and the curve dips at 90°. Turning is needed to resolve both.
- **Simulation artifact:** in the anechoic room with no mic noise, GCC-PHAT gets the tone's ITD exactly right, because PHAT amplifies faint broadband content from the 5 ms fade-in. Any real noise would bury it. Narrowband sounds need a nonzero mic SNR in simulation.

### 8. Table size (not measured; arithmetic)

40 × 40 cells × K = 200 readings × 13 float32 values (ITD + 12 band ILDs) = **16.6 MB per room per sound**. ITD only = 1.3 MB. Caching the RT60 0.4 KEMAR impulse responses (~45k samples × 2 ears × 1,600 cells, float32) would be ~580 MB per room, and is useful for re-extracting features without recomputing.

## Files

| File | What it does |
|---|---|
| `spike_kemar.py` | Main comparison (findings 2, 3, 5, 6); writes `kemar_results.json` / `.npz` |
| `debug_rir.py` | Interpolation check (finding 1) |
| `debug_reverb_itd.py` | DRR and estimator variants under reverb (finding 4) |
| `beep_test.py`, `beep_onset.py` | Narrowband beep (finding 7) |
| `requirements.txt` | Versions used |

The scripts stub out `sounddevice` before importing `slab`, because the sandbox has no audio device.
