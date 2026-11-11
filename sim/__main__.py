"""Quick look at the environment: ``python -m sim``.

Builds (or loads) the delay table for the default configuration, prints the
reading the head gets as it turns past a source, then plays a few episodes
with a random policy.
"""

from __future__ import annotations

import numpy as np

from sim.acoustics import build_tdoa_table
from sim.env import EnvConfig, SoundLocalizationEnv
from sim.tdoa import bucketize


def main() -> None:
    config = EnvConfig()
    print("Building delay table (cached after the first run)...")
    table = build_tdoa_table(config.room, config.head, config.source, verbose=False)
    print(f"{len(table.head_angles)} head angles x {len(table.source_angles)} source angles, "
          f"max delay {table.max_tau * 1e6:.0f} us\n")

    print("Source at 0 deg; head sweeping around it:")
    print(f"{'head':>6}  {'delay (us)':>10}  bucket")
    j = 0
    for i, h in enumerate(table.head_angles):
        tau = table.tau[i, j]
        b = bucketize(tau, table.max_tau, config.n_buckets)
        bar = "." * b + "|" + "." * (config.n_buckets - 1 - b)
        print(f"{h:6.0f}  {tau * 1e6:10.1f}  {b}  {bar}")

    print("\nRandom policy, 5 episodes:")
    env = SoundLocalizationEnv(config, table=table)
    rng = np.random.default_rng(0)
    for ep in range(5):
        obs, info = env.reset(seed=ep)
        total, done = 0.0, False
        while not done:
            obs, reward, terminated, truncated, info = env.step(int(rng.integers(env.n_actions)))
            total += reward
            done = terminated or truncated
        outcome = {True: "correct", False: "wrong"}.get(info.get("correct"), "timed out")
        print(f"  episode {ep}: {info['steps']:2d} steps, return {total:6.1f}, {outcome} "
              f"(source {info['source_angle']:.0f} deg, head {info['head_angle']:.0f} deg)")


if __name__ == "__main__":
    main()
