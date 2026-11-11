"""Time difference of arrival (TDOA) estimation and bucketing."""

from __future__ import annotations

import numpy as np


def gcc_phat(left: np.ndarray, right: np.ndarray, fs: int, max_tau: float, interp: int = 16) -> float:
    """Estimate the delay between two microphone signals with GCC-PHAT.

    Returns ``tau = t_left - t_right`` in seconds: the time the sound reached
    the left microphone minus the time it reached the right one. ``tau`` is
    positive when the sound reached the right microphone first, i.e. when the
    source is to the head's right, and negative when it is to the left.

    ``max_tau`` limits the search to physically possible delays (microphone
    spacing divided by the speed of sound). ``interp`` upsamples the
    cross-correlation so delays smaller than one sample can be resolved.
    """
    n = len(left) + len(right)
    spec = np.fft.rfft(left, n=n) * np.conj(np.fft.rfft(right, n=n))
    spec /= np.abs(spec) + 1e-12  # PHAT weighting: keep phase, drop magnitude
    cc = np.fft.irfft(spec, n=interp * n)

    max_shift = min(int(interp * fs * max_tau), interp * n // 2)
    # Rearrange so index max_shift corresponds to zero lag.
    cc = np.concatenate((cc[-max_shift:], cc[: max_shift + 1]))
    shift = int(np.argmax(np.abs(cc))) - max_shift
    return shift / float(interp * fs)


def bucketize(tau: float, max_tau: float, n_buckets: int) -> int:
    """Map a delay in ``[-max_tau, max_tau]`` to a bucket index.

    Bucket 0 is far left, ``n_buckets - 1`` is far right, and with an odd
    ``n_buckets`` the middle bucket holds delays near zero (source straight
    ahead or straight behind). Delays outside the range are clipped.
    """
    if n_buckets < 1:
        raise ValueError("n_buckets must be at least 1")
    frac = (np.clip(tau, -max_tau, max_tau) + max_tau) / (2 * max_tau)
    return int(min(n_buckets - 1, np.floor(frac * n_buckets)))
