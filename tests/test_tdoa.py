import numpy as np
import pytest

from sim.tdoa import bucketize, gcc_phat

FS = 16000


@pytest.mark.parametrize("delay_samples", [-5, -2, 0, 3, 6])
def test_gcc_phat_recovers_integer_delay(delay_samples):
    rng = np.random.default_rng(1)
    x = rng.standard_normal(4000)
    # left lags right by delay_samples -> tau = t_left - t_right = delay / fs
    left = np.roll(x, delay_samples)
    tau = gcc_phat(left, x, FS, max_tau=10 / FS)
    assert tau == pytest.approx(delay_samples / FS, abs=1 / (16 * FS))


def test_bucketize_edges_and_center():
    assert bucketize(-1.0, 1.0, 9) == 0
    assert bucketize(1.0, 1.0, 9) == 8
    assert bucketize(0.0, 1.0, 9) == 4
    assert bucketize(5.0, 1.0, 9) == 8  # clipped
    assert bucketize(-5.0, 1.0, 9) == 0
