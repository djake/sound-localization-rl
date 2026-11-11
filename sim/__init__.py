"""Simulated environment for active sound localization.

A two-microphone "head" sits in a simulated room and can turn left or right.
The agent listens, turns, and eventually declares that the sound source is
straight ahead. See ``sim.env.SoundLocalizationEnv``.
"""

from sim.acoustics import HeadConfig, RoomConfig, SourceConfig, TdoaTable, build_tdoa_table
from sim.env import EnvConfig, SoundLocalizationEnv
from sim.tdoa import bucketize, gcc_phat

__all__ = [
    "EnvConfig",
    "HeadConfig",
    "RoomConfig",
    "SoundLocalizationEnv",
    "SourceConfig",
    "TdoaTable",
    "bucketize",
    "build_tdoa_table",
    "gcc_phat",
]
