# Spike: what does reverberation do to ITD?

Throwaway calibration run (2026-11-13), not project code. It asks how realistic pyroomacoustics readings differ from the ideal formula, and how long building a lookup table takes.

**Reproduce** (from the repo root; about 1 minute):

```
.venv/bin/pip install -r spikes/reverb_itd/requirements.txt
.venv/bin/python spikes/reverb_itd/spike.py     # simulate -> results.npz, timing.json
.venv/bin/python spikes/reverb_itd/analyze.py   # stats.json + fig1..fig5
```

Versions: Python 3.12.11, pyroomacoustics 0.10.1, numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2. Machine: Apple M3 Pro, single core.

## Setup

| Parameter | Value |
|---|---|
| Room | 3D shoebox, 6 × 5 × 3 m; head at (2.6, 2.2, 1.2) m, slightly off-center |
| Microphones | 2 point mics (no head model), 0.18 m apart, centered on the rotation axis; left mic at +y, right at −y |
| Head | facing +x (0°) for the whole run |
| Source | 1.75 m away, same height; 40 azimuths in 9° steps |
| Signal | 48 kHz; each reading is a fresh 50 ms white-noise burst, analyzed in a 100 ms window (burst plus 50 ms of echo tail); 50 readings per angle |
| Reverb | `pra.inverse_sabine` targets RT60 = 0 (anechoic), 0.2, 0.4, 0.7 s. **Measured** RT60s were 0.19, 0.49 and 0.92 s: the image-source rooms run longer than the Sabine targets. Plots use the target labels. |
| Mic noise | added by hand (not `sigma2_awgn`): independent white Gaussian noise on each mic, scaled to SNR = none, 20, 10 or 0 dB relative to the mean clean mic power in the window |
| ITD | `sim.tdoa.gcc_phat` from the repo (GCC-PHAT, 16× upsampled, so 1.3 µs resolution; search limited to ±b/c = ±525 µs) |
| ILD | 10·log10(E_left / E_right) |

**Sign convention** (same as `sim/`): ITD = t_left − t_right, and φ is measured counterclockwise, so + = left. A source on the left reaches the left mic first, so **ITD is negative on the left**: ITD = −(b/c)·sin φ. ILD is positive when the left mic is louder.

## Results

### 1. Anechoic sanity check: passes

The largest error against the formula is **0.59 µs (0.03 samples)**. Against the exact near-field geometry it is 0.79 µs. Readings are identical from burst to burst (spread 0). The pipeline matches the formula, and the signs are correct.

### 2. ITD is very robust to reverb and mic noise (fig1, fig2)

Median absolute error, all angles pooled (µs):

| | no noise | 20 dB | 10 dB | 0 dB |
|---|---|---|---|---|
| anechoic | 0.08 | 0.08 | 0.09 | 0.09 |
| RT60 0.2 | 0.09 | 0.09 | 0.09 | 0.59 |
| RT60 0.4 | 0.71 | 0.71 | 1.17 | 1.34 |
| RT60 0.7 | 1.25 | 1.27 | 1.30 | 2.65 |

Fraction of readings off by more than 100 µs (about 1.2 of the agent's 9° turns near center):

| | no noise | 10 dB | 0 dB |
|---|---|---|---|
| RT60 0.4 | 0 | 0 | 0.8% |
| RT60 0.7 | 0.3% | 0.65% | **13.4%** (3.7% on the wrong side) |

For scale: a 9° turn away from center changes ITD by about 82 µs, and one of five equal buckets is about 210 µs wide. **In every condition except "RT60 0.7 s and 0 dB SNR", the noise is far too small to matter to the agent.**

### 3. The errors are not Gaussian (fig3)

Most readings are almost exact, plus a few large outliers. Excess kurtosis (0 for a Gaussian) is 1–4 with little or no reverb, 51 at RT60 0.7 s with no noise, and **205 at RT60 0.4 s with 0 dB SNR**.

Most of the error is a **fixed bias per cell** (the same angle reads the same wrong value every time), not burst-to-burst scatter. At RT60 0.7 s with no noise, the bias RMS is 13 µs while the scatter within a cell is 4.7 µs.

### 4. ILD is tiny (fig4)

The largest mean ILD is **0.9 dB anechoic**, falling to 0.6 dB at RT60 0.7 s. It tracks sin φ (correlation 0.999 anechoic, 0.64 at RT60 0.7 s). The cause is the near-field distance difference (1.75 m ± 9 cm, about 0.9 dB), not a head shadow. Human ILDs reach about 20 dB. ILD here is a weak, front-back-symmetric copy of the ITD information.

### 5. Front/back leakage in a fixed room: real but microsecond-scale (fig5)

Test: a nearest-mean classifier, trained on 25 readings and tested on 25 held-out readings, for each mirror pair (φ, 180° − φ), using one ITD reading with the head still.

| | mean accuracy | pairs with ≥ 90% accuracy |
|---|---|---|
| anechoic | 0.50 (exactly chance, as theory predicts) | 0% |
| RT60 0.2 | 0.53 | 5% |
| RT60 0.4 | 0.74 | 16% |
| RT60 0.7 | 0.78 | 32% |

At 20 dB SNR the numbers are similar. The cue comes from room-specific ITD biases of a few µs. A five-bucket tabular agent can't see differences that small. An agent reading continuous ITD values (tile coding, DQN) could in principle memorize them.

### 6. Timing (single core, M3 Pro)

| RT60 target | RIR per cell | process one reading (convolve + noise + GCC + ILD) | full table estimate (1,600 cells × 200 readings) |
|---|---|---|---|
| 0 | 1 ms | 0.9 ms | **4.8 min** |
| 0.2 | 6 ms | 1.0 ms | **5.7 min** |
| 0.4 | 44 ms | 1.2 ms | **7.4 min** |
| 0.7 | 228 ms | 1.5 ms | **14.3 min** |

Putting all 40 sources in one room did not speed up RIR computation (9.0 s for 40 sources versus 40 × 0.23 s). Processing the readings dominates, except at RT60 0.7 s. The work splits trivially across cores.

## So what

- **Table build time is a non-issue:** 5–15 minutes once per room configuration, shared by every seed.
- **Realistic acoustics barely perturb ITD here.** With broadband 50 ms bursts and GCC-PHAT, ITD stays accurate to a few µs even at RT60 ≈ 0.9 s (measured). Only the combination of heavy reverb and 0 dB SNR produces errors the agent would notice. **So the simulator alone gives a nearly noise-free ITD.** That makes the "listen" action and hypothesis 3 meaningless unless noise is added on purpose: an internal-noise Gaussian on the ITD, much lower SNR, shorter bursts, or competing sources.
- **A Gaussian is the wrong shape for reverberant errors** (heavy-tailed, mostly fixed bias per cell), but those errors are so small that the Gaussian "internal noise" knob would dominate anyway. That makes a Gaussian defensible as an explicit, explainable noise model.
- **The fixed room does leak front/back information** (up to 78% single-reading accuracy at RT60 0.7 s), but only at the µs level. Internal noise of roughly 20 µs or more would wipe it out. If agents with continuous inputs are used without such noise, test them in a different room.
- **ILD from point mics is near-useless**, as expected.

## Note on existing code

`sim/acoustics.py` already builds a TDOA table, but with different defaults from the proposal and this spike:

- a 2D room, 16 kHz sampling, 0.15 m spacing, 24 head angles (15° steps) and 72 source angles;
- a single fixed noise signal, so one deterministic reading per cell instead of many;
- `gcc_phat` takes `argmax(|cc|)`, which could in principle lock onto a negative correlation peak. That didn't cause problems here.
