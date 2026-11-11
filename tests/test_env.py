import numpy as np

from sim.env import DECLARE, TURN_LEFT, TURN_RIGHT, SoundLocalizationEnv


def make_env(small_config, small_table):
    return SoundLocalizationEnv(small_config, table=small_table)


def test_reset_and_step_api(small_config, small_table):
    env = make_env(small_config, small_table)
    obs, info = env.reset(seed=0)
    assert len(obs) == 3 and obs[1] == small_config.n_buckets and obs[2] == 0
    assert 0 <= env.state_index(obs) < env.n_states
    obs, reward, terminated, truncated, info = env.step(TURN_LEFT)
    assert reward == small_config.step_reward
    assert not terminated and not truncated
    assert obs[2] == 1  # turned left


def test_declare_correct_when_facing_source(small_config, small_table):
    env = make_env(small_config, small_table)
    env.reset(options={"head_angle": 90, "source_angle": 90})
    _, reward, terminated, _, info = env.step(DECLARE)
    assert terminated and info["correct"]
    assert reward == small_config.step_reward + small_config.correct_reward


def test_declare_wrong_when_source_behind(small_config, small_table):
    env = make_env(small_config, small_table)
    env.reset(options={"head_angle": 0, "source_angle": 180})
    _, reward, terminated, _, info = env.step(DECLARE)
    assert terminated and not info["correct"]
    assert reward == small_config.step_reward + small_config.wrong_reward


def test_turning_distinguishes_front_from_back(small_config, small_table):
    env = make_env(small_config, small_table)
    front, _ = env.reset(options={"head_angle": 0, "source_angle": 0})
    back, _ = env.reset(options={"head_angle": 0, "source_angle": 180})
    assert front == back  # identical before turning

    env.reset(options={"head_angle": 0, "source_angle": 0})
    after_front, *_ = env.step(TURN_LEFT)
    env.reset(options={"head_angle": 0, "source_angle": 180})
    after_back, *_ = env.step(TURN_LEFT)
    assert after_front != after_back
    assert after_front[0] > after_back[0]  # source in front moves right; behind moves left


def test_left_and_right_turns_are_inverse(small_config, small_table):
    env = make_env(small_config, small_table)
    env.reset(options={"head_angle": 0, "source_angle": 45})
    env.step(TURN_LEFT)
    _, _, _, _, info = env.step(TURN_RIGHT)
    assert info["head_angle"] == 0.0


def test_truncates_after_max_steps(small_config, small_table):
    env = make_env(small_config, small_table)
    env.reset(seed=1)
    truncated = False
    for _ in range(small_config.max_steps):
        _, _, terminated, truncated, _ = env.step(TURN_LEFT)
        assert not terminated
    assert truncated


def test_random_policy_episodes_terminate(small_config, small_table):
    env = make_env(small_config, small_table)
    rng = np.random.default_rng(0)
    for ep in range(20):
        env.reset(seed=ep)
        done = False
        while not done:
            _, _, terminated, truncated, _ = env.step(int(rng.integers(env.n_actions)))
            done = terminated or truncated
