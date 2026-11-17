# Findings from CS 138 Homework 3 that bear on the Final Project

Source: Harris's Homework 3 (solo), Part 3, which uses a formula-only version of this
project's environment. Date: 2026-11-16. These are inputs for the team to weigh, not
decisions. Please log anything adopted in `spec/decisions.md` and raise the rest as
open questions.

## How these numbers were produced

- Environment: this spec's rules (40 headings, 9° turns, actions turn left / turn right /
  listen / declare, −1 per action, 50-action limit, ITD positive when the source is left),
  with one substitution: reading = (b/c)·sin φ + N(0, σ²), b/c ≈ 525 µs. No room
  simulator and no lookup table.
- Policies: hand-written, fixed rules, untuned. 20,000 episodes per cell.
  - **No memory:** turn toward the side the reading points to; declare when
    |reading| ≤ ~40 µs.
  - **Check:** the same, but never declares before it has turned at least once.
  - **Check + k listens:** as check, but when a reading looks centered it gathers
    k readings and decides on their mean.
- "Complete" = declared within one turn (9°) of the source.

## 1. Under the spec's reward, listening does not pay (affects H3, §4.6)

Reward as specified: 100·(1 − Δθ/π) on declaring, −1 per action.

| σ (µs) | Policy | Return | Complete |
|---|---|---|---|
| 0 | Oracle | 88.9 | 100% |
| 0 | No memory | 86.9 | 97.5% |
| 0 | Check | 88.9 | 100% |
| 20 | No memory | 86.7 | 97.5% |
| 20 | Check | 88.7 | 99.9% |
| 20 | Check + 2 readings | 87.8 | 100% |
| 80 | No memory | 82.4 | 90.1% |
| 80 | Check | 83.6 | 91.8% |
| 80 | Check + 2 readings | 81.1 | 98.5% |
| 80 | Check + 4 readings | 76.8 | 98.4% |
| 160 | No memory | 76.4 | 65.7% |
| 160 | Check | 77.4 | 67.5% |
| 160 | Check + 2 readings | 58.9 | 77.9% |

- Listening raised completion but lowered return at every noise level. A listen costs
  1 point; declaring one turn off costs only 5.
- Consequence: an agent that maximizes return has little reason to listen, so H3
  ("as noise increases, agents listen more") may not be testable with this reward.

With the declaration reward multiplied by 10 (1000·(1 − Δθ/π), step cost still −1):

| σ (µs) | No memory | Check | Check + 2 readings | Check + 4 readings |
|---|---|---|---|---|
| 20 | 962.9 | 987.2 | 987.8 | 985.7 |
| 40 | 952.1 | 971.8 | 981.1 | 982.9 |
| 80 | 928.1 | 944.3 | 959.3 | 954.1 |
| 160 | 874.3 | 888.7 | 821.6 | 753.5 |

- Listening then pays at σ = 40 and 80 (about 9 and 15 points for one extra reading) and
  makes no difference at σ ≤ 20. That is the pattern H3 predicts.
- σ = 160 µs was too noisy to be informative: the fixed policies dithered and ran into
  the 50-action limit. Relevant to the σ sweep in §4.4 and to OQ4.
- Homework 3 adopted the ×10 reward as a single fixed setting. Whether the project
  should change its reward is a team decision.

## 2. A no-memory agent already does very well (affects H1, H2, OQ2, §4.8, §4.9)

- "Turn toward the sound, declare when centered" completes 97.5% of episodes at low
  noise and scores 86.9 against the oracle's 88.9. A source behind the head gets swept
  round to the front as the agent turns toward the reading.
- It fails in exactly one case: the source starts dead behind (1 start in 40). The
  reading is near zero, so it declares facing the wrong way.
- One bit of memory ("have I turned yet?") closes the gap completely at σ ≤ 20. The
  front–back check is only needed when the first reading is centered. This supports H2
  as worded and is evidence for OQ2: very little memory is needed for the front–back
  problem; richer memory matters only for averaging readings under noise.
- H1's bar of 90% of oracle return is easy: the no-memory rule is already at about 98%.
- The 99% completion criterion in §4.8 is out of reach for any agent without memory
  (ceiling 97.5%).
- The hand-written baseline in §4.9 makes "one extra turn to check" every episode.
  Checking only when it has not yet turned gives the same completion for fewer steps.

## 3. Tabular learning was slow and noisy in a first pilot (affects §4.10, OQ8)

Pilot: Harris's Homework 2 on-policy Monte Carlo agent (ε = 0.1), ×10 reward, 8 seeds,
greedy evaluation. Three agent states: M0 = bin of the current reading (5 entries);
M1 = this spec's Option A (150 entries as built); M2 = Option B (360 entries).
Hand-written targets on the same evaluation: no memory 964 / 928, check 987 / 945,
check + 1 listen 988 / 959, oracle 989 (σ = 20 / 80).

| State | Median return, σ = 20 | Median return, σ = 80 |
|---|---|---|
| M0 | 928 | 884 |
| M1 | 761 | 702 |
| M2 | 722 | 722 |

(α = 0.01, 50,000 episodes.)

- After 10,000 episodes every agent still scored about 500, which is what declaring
  immediately earns.
- M0 reached its ceiling (964) in some seeds by 50,000 episodes. M1 and M2 were far
  from converged.
- At α = 0.1 (20,000 episodes) no agent came near its target.
- Likely cause: returns swing by hundreds of points between episodes while the gap
  between a good and a bad action is tens of points.
- The estimate of 10⁴–10⁵ training episodes for tabular agents may be optimistic.
- Limits: this is Monte Carlo only. Q-learning and Sarsa have not been run yet.

## 4. Evaluation should be large and balanced (affects §4.8)

- The gaps between agents are small (about 2 of 89 points under the spec's reward).
- With 200 validation episodes and random starts, the dead-behind start comes up only
  about 5 times, so the one case that separates agents is barely sampled.
- Homework 3 uses 25 episodes from each of the 40 starting directions (1,000 per
  evaluation) and records completion and listens by starting direction. The
  by-direction record is what shows the front–back failure.

## Reusable code

In `/Users/harris/Documents/Classes/CS138/Assignment3/` (committed on `main`):

- `hw3/envs/sound.py`: the formula-only environment. Numpy only, no other imports,
  written to this spec's sign and unit conventions, so it can be copied in as is.
  **Its default `declare_scale` is 1000; pass 100 for this spec's reward.**
  Actions: 0 turn left (heading +1), 1 turn right, 2 listen, 3 declare.
- `hw3/memory.py`: state builders for Options A and B, using the five reading bins
  from §4.4 (edges ±40 and ±260 µs).
- `hw3/sound_eval.py`: the balanced evaluation and the hand-written baselines.
- `spikes/itd_memory/RESULTS.md`: the tables above with the reproduce command.
- `tests/test_part3.py`: tests for all of the above.

Homework 3 is Harris's solo work, and course policy has him write the RL algorithms
himself. The files listed above contain no learning rules.

## Caveats

- The policies in sections 1 and 2 are simple and untuned. They show effect sizes,
  not the best achievable behavior. A cleverer policy might find a small return gain
  from listening even under the spec's reward.
- Everything ran on the formula, not the room simulator. Reverberation and the
  lookup-table sampling are not represented.
- Untested reasoning: with greedy evaluation, Sarsa may undervalue listening, because
  it prices in its own accidental declarations and turns while exploring. Homework 3
  chose Q-learning for that reason. No run has confirmed it. Relevant to OQ3.
