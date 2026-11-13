"""Analyze results.npz from spike.py: checks, stats, and figures.

    .venv/bin/python spikes/reverb_itd/analyze.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import kurtosis  # noqa: E402

OUT = Path(__file__).resolve().parent
d = np.load(OUT / "results.npz")
itd, ild, az = d["itd"] * 1e6, d["ild"], d["az"]  # ITD in microseconds
rt60s, snrs = d["rt60s"], d["snrs"]
f_us, g_us = d["itd_formula"] * 1e6, d["itd_geom"] * 1e6
fs, max_tau_us = int(d["fs"]), float(d["max_tau"]) * 1e6
sample_us = 1e6 / fs
snr_lbl = ["no noise" if np.isnan(s) else f"{s:.0f} dB" for s in snrs]
rt_lbl = ["anechoic" if r == 0 else f"RT60 {r} s" for r in rt60s]
stats: dict = {}

# 1. Anechoic, no-noise check -------------------------------------------------
an = itd[0, 0]  # (az, bursts)
err_formula = an - f_us[:, None]
err_geom = an - g_us[:, None]
stats["check_anechoic"] = {
    "max_abs_err_vs_formula_us": float(np.abs(err_formula).max()),
    "max_abs_err_vs_formula_samples": float(np.abs(err_formula).max() / sample_us),
    "max_abs_err_vs_geometry_us": float(np.abs(err_geom).max()),
    "max_abs_err_vs_geometry_samples": float(np.abs(err_geom).max() / sample_us),
    "within_cell_std_us_max": float(an.std(axis=1).max()),
    "sample_period_us": sample_us,
    "gcc_resolution_us": sample_us / 16,
    "max_tau_us": max_tau_us,
}


def band_plot(ax, data, title):
    m = data.mean(axis=1)
    lo, hi = np.percentile(data, [5, 95], axis=1)
    ax.fill_between(az, lo, hi, alpha=0.3, label="5–95% of readings")
    ax.plot(az, m, ".-", ms=4, label="mean reading")
    ax.plot(az, f_us, "k--", lw=1, label="formula −(b/c)·sin φ")
    ax.set_title(title, fontsize=9)
    ax.set_xticks([0, 90, 180, 270, 360])
    ax.set_ylim(-max_tau_us * 1.15, max_tau_us * 1.15)
    ax.grid(alpha=0.3)


# 2a. ITD vs azimuth per RT60 (no noise) --------------------------------------
fig, axs = plt.subplots(1, 4, figsize=(15, 3.6), sharey=True)
for ri, ax in enumerate(axs):
    band_plot(ax, itd[ri, 0], rt_lbl[ri])
    ax.set_xlabel("source azimuth φ (deg, + = left)")
axs[0].set_ylabel("ITD (µs)")
axs[0].legend(fontsize=7, loc="upper right")
fig.suptitle("ITD estimate vs true azimuth, no mic noise (50 bursts per angle)")
fig.tight_layout()
fig.savefig(OUT / "fig1_itd_vs_azimuth_by_rt60.png", dpi=130)

# 2b. ITD vs azimuth per SNR, for anechoic and RT60 0.4 -----------------------
fig, axs = plt.subplots(2, 4, figsize=(15, 6.5), sharey=True, sharex=True)
for row, ri in enumerate([0, 2]):
    for si in range(len(snrs)):
        band_plot(axs[row, si], itd[ri, si], f"{rt_lbl[ri]}, SNR {snr_lbl[si]}")
    axs[row, 0].set_ylabel("ITD (µs)")
for ax in axs[1]:
    ax.set_xlabel("source azimuth φ (deg)")
axs[0, 0].legend(fontsize=7, loc="upper right")
fig.suptitle("Effect of microphone noise (SNR) on ITD estimates")
fig.tight_layout()
fig.savefig(OUT / "fig2_itd_vs_azimuth_by_snr.png", dpi=130)

# 3. Error stats + histograms --------------------------------------------------
stats["error_by_rt60_snr"] = {}
fig, axs = plt.subplots(1, 4, figsize=(15, 3.6), sharey=True)
bins = np.linspace(-2 * max_tau_us, 2 * max_tau_us, 81)
for ri in range(len(rt60s)):
    for si in range(len(snrs)):
        x = itd[ri, si]
        err = x - f_us[:, None]
        bias = x.mean(axis=1) - f_us  # per-cell systematic offset
        within = x.std(axis=1)  # per-cell burst-to-burst spread
        stats["error_by_rt60_snr"][f"{rt_lbl[ri]} | {snr_lbl[si]}"] = {
            "rms_err_us": float(np.sqrt(np.mean(err**2))),
            "median_abs_err_us": float(np.median(np.abs(err))),
            "rms_bias_across_cells_us": float(np.sqrt(np.mean(bias**2))),
            "mean_within_cell_std_us": float(within.mean()),
            "frac_abs_err_gt_100us": float(np.mean(np.abs(err) > 100)),
            "frac_wrong_side": float(np.mean(np.sign(x[np.abs(f_us) > 50]) != np.sign(f_us[np.abs(f_us) > 50, None]))),
            "excess_kurtosis": float(kurtosis(err.ravel())) if err.std() > 0 else None,
        }
    err = (itd[ri, 0] - f_us[:, None]).ravel()
    ax = axs[ri]
    ax.hist(err, bins=bins, density=True, alpha=0.7, label="observed error")
    s = err.std()
    if s > 0:
        xs = np.linspace(bins[0], bins[-1], 400)
        ax.plot(xs, np.exp(-0.5 * ((xs - err.mean()) / s) ** 2) / (s * np.sqrt(2 * np.pi)), "r-", lw=1, label="Gaussian, same std")
    ax.set_yscale("log")
    ax.set_title(f"{rt_lbl[ri]} (std {s:.0f} µs)", fontsize=9)
    ax.set_xlabel("ITD error vs formula (µs)")
axs[0].set_ylabel("density (log)")
axs[1].legend(fontsize=7)
fig.suptitle("Distribution of ITD errors, all angles pooled, no mic noise")
fig.tight_layout()
fig.savefig(OUT / "fig3_error_histograms.png", dpi=130)

# 4. ILD ------------------------------------------------------------------------
fig, axs = plt.subplots(1, 4, figsize=(15, 3.4), sharey=True)
stats["ild_db"] = {}
for ri, ax in enumerate(axs):
    x = ild[ri, 0]
    lo, hi = np.percentile(x, [5, 95], axis=1)
    ax.fill_between(az, lo, hi, alpha=0.3)
    ax.plot(az, x.mean(axis=1), ".-", ms=4)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_title(rt_lbl[ri], fontsize=9)
    ax.set_xlabel("azimuth φ (deg)")
    ax.set_xticks([0, 90, 180, 270, 360])
    ax.grid(alpha=0.3)
    stats["ild_db"][rt_lbl[ri]] = {
        "max_abs_mean_ild_db": float(np.abs(x.mean(axis=1)).max()),
        "corr_mean_ild_with_sin_phi": float(np.corrcoef(x.mean(axis=1), np.sin(np.deg2rad(az)))[0, 1]),
        "mean_within_cell_std_db": float(x.std(axis=1).mean()),
    }
axs[0].set_ylabel("ILD (dB, + = left louder)")
fig.suptitle("ILD vs azimuth (point microphones, no head), no mic noise")
fig.tight_layout()
fig.savefig(OUT / "fig4_ild_vs_azimuth.png", dpi=130)

# 5. Front/back distinguishability from ITD alone -------------------------------
# Mirror pairs: phi and 180-phi have identical formula ITD. Exclude 90/270 (self-mirror).
pairs = []
for i, p in enumerate(az):
    m = (180 - p) % 360
    j = int(np.where(np.isclose(az, m))[0][0])
    if np.cos(np.deg2rad(p)) > 1e-9:  # p is the front member
        pairs.append((i, j))
half = itd.shape[-1] // 2
stats["front_back"] = {}
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
for col, si in enumerate([0, 1]):
    for ri in range(len(rt60s)):
        accs, dps = [], []
        for i, j in pairs:
            a, b = itd[ri, si, i], itd[ri, si, j]
            # nearest-mean classifier: fit on first half of bursts, test on second half
            ma, mb = a[:half].mean(), b[:half].mean()
            if np.isclose(ma, mb):
                acc = 0.5
            else:
                thr, front_hi = (ma + mb) / 2, ma > mb
                acc = 0.5 * (np.mean((a[half:] > thr) == front_hi) + np.mean((b[half:] > thr) != front_hi))
            pooled = np.sqrt(0.5 * (a.var() + b.var()))
            dps.append(abs(a.mean() - b.mean()) / pooled if pooled > 0 else (0.0 if np.isclose(a.mean(), b.mean()) else np.inf))
            accs.append(acc)
        accs = np.array(accs)
        stats["front_back"][f"{rt_lbl[ri]} | {snr_lbl[si]}"] = {
            "mean_accuracy": float(accs.mean()),
            "frac_pairs_acc_ge_0.9": float(np.mean(accs >= 0.9)),
            "median_dprime": float(np.median(dps)),
        }
        axs[col].plot([az[i] for i, _ in pairs], accs, "o-", ms=3, label=rt_lbl[ri])
    axs[col].axhline(0.5, color="k", lw=0.8, ls=":")
    axs[col].set_title(f"SNR {snr_lbl[si]}", fontsize=9)
    axs[col].set_xlabel("front azimuth φ of mirror pair (φ, 180°−φ)")
axs[0].set_ylabel("held-out accuracy telling front from back\n(one ITD reading, head still)")
axs[0].legend(fontsize=7)
fig.suptitle("Can a single ITD reading tell front from back in this fixed room?")
fig.tight_layout()
fig.savefig(OUT / "fig5_front_back.png", dpi=130)

(OUT / "stats.json").write_text(json.dumps(stats, indent=2))
print(json.dumps(stats, indent=2))
