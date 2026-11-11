import numpy as np

from sim.env import angle_diff


def _rel(table):
    return np.array([[angle_diff(s, h) for s in table.source_angles] for h in table.head_angles])


def test_tau_matches_geometry(small_table):
    # Anechoic room: tau should follow -max_tau * sin(source - head).
    expected = -small_table.max_tau * np.sin(np.deg2rad(_rel(small_table)))
    assert np.max(np.abs(small_table.tau - expected)) < 0.05 * small_table.max_tau


def test_sign_flips_as_head_turns_past_source(small_table):
    j = 0  # source at 0 degrees
    taus = {round(h): small_table.tau[i, j] for i, h in enumerate(small_table.head_angles)}
    assert taus[45] > 0  # head turned left of the source -> source on the right
    assert taus[315] < 0  # head turned right of the source -> source on the left
    assert abs(taus[0]) < 0.05 * small_table.max_tau


def test_front_and_back_sound_the_same(small_table):
    # A single reading cannot tell front from back.
    i = 0  # head facing 0 degrees
    front = small_table.tau[i, list(small_table.source_angles).index(0.0)]
    back = small_table.tau[i, list(small_table.source_angles).index(180.0)]
    assert abs(front - back) < 0.05 * small_table.max_tau
