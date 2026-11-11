import pytest

from sim.acoustics import HeadConfig, RoomConfig, SourceConfig, build_tdoa_table
from sim.env import EnvConfig

# A coarse grid keeps the test suite fast: 8 head angles x 16 source angles.
SMALL = EnvConfig(head=HeadConfig(n_angles=8), source=SourceConfig(n_angles=16))


@pytest.fixture(scope="session")
def small_config():
    return SMALL


@pytest.fixture(scope="session")
def small_table():
    return build_tdoa_table(SMALL.room, SMALL.head, SMALL.source, cache_dir=None)
