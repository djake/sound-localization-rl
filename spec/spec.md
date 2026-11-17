# Project Spec: Active Sound Localization with RL

**Team:** Jake Lambert, Rachel Ellinger, Harris Davidson · **Last updated:** 2026-11-16

This is the one document that describes what we are building. It holds only what is true **now**. Where it differs from the proposal (`report/main_proposal.tex`), this document wins. The reasons behind each choice are in [decisions.md](decisions.md), which you don't need to read to follow this document.

## How to read this document

- **Section status.** Each section is marked **Draft** (still changing), **Agreed** (the team has reviewed it), or **Frozen** (ready to build from). Coding agents build only from Frozen sections. Everything is Draft until the team's first review.
- **IDs.** Hypotheses (H1…), experiments (E0…), stretch goals (S1…), code requirements (R1…), acceptance tests (AT1…), open questions (OQ1…), and decisions (D1…) keep their IDs for the life of the project. IDs are never reused.
- **⚠ marks** a value that depends on an open question. The full list of open questions is in [Section 7](#7-open-questions).
- **Source column** in the tables: **P** = proposal · **Dn** = a decision in [decisions.md](decisions.md) · **Spike** = the [calibration test](../spikes/reverb_itd/RESULTS.md) · **HW3** = [findings from Harris's Homework 3](../spikes/hw3_formula/FINDINGS.md), which ran hand-written policies on a formula-only version of this environment · **Head spike** = the [simulated-head test](../spikes/kemar_head/RESULTS.md) · **New** = first written down here, so it especially needs review.
- **Later:** when a section is Frozen and needs build-level detail (interfaces, file formats, tasks), that detail goes in its own file under `spec/components/`. This document keeps the summary and links to it.

---

## 1. Summary

*Status: Draft*

We are building a simulated two-microphone "head" that can turn left and right, and training reinforcement learning agents to find a sound source with it. On each step the agent hears one number: the **interaural time difference (ITD)**, the difference in when the sound reaches each microphone. One ITD reading can't tell a sound in front from its mirror image behind, so the agent has to turn its head to find out. We want to know whether RL agents learn to do that on their own, and how their behavior changes as the readings get noisier.

The paper is about the localization behavior. We compare algorithms along the way, but the comparison is not the headline (⚠ OQ1: to be confirmed with the teaching team).

**How the system works, in one paragraph:** A room simulator (pyroomacoustics) produces what each microphone records for every combination of head direction and source direction. A standard signal-processing step (GCC-PHAT) turns each pair of recordings into an ITD. We do this once per room and store the results in a table. During training, each step looks up a stored reading, adds a controlled amount of random noise, and gives it to the agent. This keeps training fast enough to run many seeds on a laptop.

## 2. Research question and hypotheses

*Status: Draft*

**Research question:** Can an RL agent that hears only interaural time differences learn to move its head to resolve front–back ambiguity, and how does its strategy (turning, listening, declaring) change as sensory noise increases?

| ID | Hypothesis |
|---|---|
| **H1** | In low noise, the learning agents match the hand-written check strategy (§4.9) and beat the no-memory rule. ⚠ OQ17 |
| **H2** | The front–back check emerges unprompted: when the sound starts centered, the agent turns before it declares. ⚠ OQ18 |
| **H3** | As noise increases, agents listen more, and they lose less performance than the fixed hand-written strategy. |
| **H4** | Policies trained in one room keep their performance in rooms they have never seen. |

**Strategy analysis.** Search strategy (e.g. moving toward the sound) is covered in the analysis of H2 and H3: the mix of actions, typical trajectories, and how both shift with noise.

**Algorithm comparison.** Each hypothesis is examined across the algorithms we train. Which algorithms, and how many, is open (⚠ OQ1, OQ3).

## 3. Experiments and scope

*Status: Draft*

### 3.1 Core experiments

| ID | Experiment | What varies | Tests |
|---|---|---|---|
| **E0** | Pipeline check | Nothing. Two figures: the echo-free table matches the ITD formula, and the calibration results. Not to be included in the report. | Trust in the setup |
| **E1** | Base condition | Agents vs. baselines, at base noise, in the training room | H1, H2 |
| **E2** | Noise sweep | Noise level σ (5 values, see §4.4) | H3, strategy analysis |
| **E3** | Room transfer | Policies from E1 and E2, evaluated in held-out rooms with no retraining | H4 |

All training happens in one moderately reverberant room. There is no reverb sweep in the core (⚠ OQ13).

### 3.2 Stretch goals, in priority order

| ID | Stretch goal | Notes |
|---|---|---|
| **S1** | Moving source | ⚠ OQ10 |
| **S2** | Hardware: a physical two-mic head (sim-to-real) | ⚠ OQ11. Includes motor errors (missed steps). |
| **S3** | Monaural agent with a directional microphone | |
| **S4** | Marco Polo (multi-agent) | |

### 3.3 Out of scope

| Item | Why |
|---|---|
| Competing sounds | A whole new dimension (D12). |
| Microphone errors | Gain mismatch doesn't affect ITD (D12). |
| Level differences (ILD) and other cues | With the default point mics, ILD is under 1 dB and carries nothing ITD doesn't (D5). With a simulated head (§4.12) ILD would be a real cue, and level differences by frequency band settle front vs. back from one reading (Head spike). Whether to study that is part of ⚠ OQ21. |
| A second axis of rotation (tilt) | Multiplies the table size and the state space. Not on the stretch list. |
| A new random room every episode | Would need live simulation, which is ~1,000× slower per step. Held-out rooms (E3) cover the same concern. |

### 3.4 What the experiments require from the code

| ID | Requirement | Needed for |
|---|---|---|
| **R1** | Every run is fully described by a config: room, noise level, agent, seed. | All |
| **R2** | Every trained policy is saved so it can be evaluated again later. | E3 |
| **R3** | Each room has a fixed, seeded set of evaluation episodes, so every agent faces the same starts and noise draws. | E1–E3 |
| **R4** | Each episode's full trajectory is logged (actions, readings, hidden state), not only its return. | H2, strategy analysis |
| **R5** | **Matched environments across agents.** For a given seed, every agent faces the same environment in training and in validation. Details below. | Fair comparison of algorithms, all experiments |

**R5 in detail.** Environment randomness and agent randomness come from separate random streams, so nothing an agent does can change what the environment would have produced.

- **Same episodes.** The environment's randomness for an episode is derived only from (environment seed, training or validation, episode number). Episode k of training therefore starts with the same head heading and source azimuth for every agent on that seed. The same holds for every validation episode.
- **Same readings for the same actions.** Within an episode, the acoustic draw and the internal noise at step t are fixed in advance by (environment seed, episode number, step number). Two agents that take the same actions up to step t receive identical readings. Once their actions differ they are in different geometries, so their readings differ, as they should.
- **Agent randomness is separate.** Exploration, weight initialization, and any other agent-side randomness use the agent's own stream, set by the same run seed. Changing the agent or its settings never changes the environment's sequence.
- **Validation is identical across agents and across checkpoints.** Every validation pass during training uses the same fixed episode set (R3).

## 4. Problem formulation

*Status: Draft*

Every setting of the problem, with its default value.

### 4.1 Notation

- **Azimuth** is measured in the horizontal plane, **counter-clockwise positive** (positive = to the left). 0 is the room's +x axis.
- **θ** is the source azimuth and **ĥ_t** is the head's heading at step t, both in the room's frame.
- **φ_t = wrap(θ − ĥ_t)** ∈ (−π, π] is the source direction relative to the nose. φ > 0 means the source is to the left.
- **ITD = t_right − t_left.** A source on the left gives a **positive** ITD. The reference model is τ(φ) = (b/c)·sin φ.
  ⚠ The spike script and the old `sim/` code use the opposite sign. New code follows this document.

### 4.2 World and geometry

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Room model | pyroomacoustics shoebox, 3D, image-source method | D4, Spike | |
| Training room R0 | 6 × 5 × 3 m, RT60 target 0.4 s | D10, D13, Spike | Record the *measured* RT60 (the spike got 0.49 s for a 0.4 s target). |
| Held-out rooms | 2–3 rooms differing in size, RT60, and head position | D8 | ⚠ OQ5: exact list |
| Head position | Off-center, e.g. (2.6, 2.2, 1.2) m in R0 | D10 | Off-center avoids symmetric reflections that could make the room artificially easy. |
| Rotation | Left-right only (yaw), about a vertical axis through the midpoint between the mics | P, D9 | |
| Mic spacing b | 0.18 m | D10 | Match hardware if built (⚠ OQ11). |
| Receiver | 2 omnidirectional point mics, symmetric about the axis | D5, D9, D22 | The receiver is a table-builder setting. A simulated head is specified as an option in §4.12. Whether and how it is used is ⚠ OQ21. |
| Source distance | 1.75 m from head center, at ear height | D10 | Horizontal plane only. |
| Source azimuth grid | 40 values, 9° apart, **on the same grid as the headings** | D14 | Changed from the proposal, which implied a source anywhere on the circle. |
| Source motion | Static within an episode | P | Moving source is S1. |
| Speed of sound c | 343 m/s | — | |

### 4.3 Source signal

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Signal | White-noise burst, 50 ms | D10, Spike | ⚠ OQ14: the choice of sound could change the experiments substantially. |
| Sample rate fs | 48 kHz | D10 | |
| Mic self-noise (SNR) | None by default | D6 | Noise enters through the internal-noise term in §4.4. SNR stays available as a setting. |

### 4.4 Observation

The agent's only input is ITD (D5). Each reading is built in two stages:

```
o_t = r_t + ε_t
  r_t ~ uniform draw from table[room][heading][source]   (acoustic reading)
  ε_t ~ N(0, σ²)                                         (internal noise)
```

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Acoustic pipeline | One pipeline for everything: pyroomacoustics recordings → GCC-PHAT → ITD | D4 | The formula τ(φ) is used only to explain the base case in the report and as test AT1. |
| Table shape | 40 headings × 40 source azimuths per room, indexed `[heading_idx][source_idx]` | D7, D14 | Every cell is a geometry that can actually occur. One table per combination of room, sound (§4.3), and receiver (§4.2). |
| Readings per cell K | 200, each from a different random noise burst | D7 | Built once per room (~5–15 min on one laptop core with point mics), shared by all seeds. |
| ITD estimator | GCC-PHAT, sub-sample (parabolic) interpolation, lag search limited to ±b/c | D4, Spike | Pick the **largest positive** peak, not the largest absolute value (a bug noted in `sim/`). These settings are for point mics. The head option needs a wider lag search and a shorter analysis window (§4.12). |
| Internal noise σ, base condition | 20 µs | New, D6 | ⚠ OQ4. Hides the room's faint front/back cue (Spike). Small next to the 82 µs ITD change from one turn away from center. |
| σ sweep (E2) | {10, 20, 40, 80, 160} µs | New | ⚠ OQ4. 160 µs ≈ two turns' worth of ITD change, which should be hard. In the homework test it was too hard to be informative: the hand-written policies dithered until the step limit (HW3). |
| What the agent sees | Only o_t. Never θ, ĥ_t, or φ_t. | P | Hidden state is logged for analysis (R4) but never passed to agents. |

**Why add noise at all?** Simulated ITD is nearly perfect (typical error under 3 µs, even with reverb), so without added noise the "listen" action is useless and H3 has nothing to test. We frame the Gaussian term as neural/internal noise, a standard modeling device in hearing science (D6).

**Discretization (tabular agents only).** Five bins on o_t:

| Bin | Range (µs) | Rough meaning at σ = 0 |
|---|---|---|
| far right | o < −260 | φ < −30° |
| right | −260 ≤ o < −40 | |
| center | −40 ≤ o ≤ 40 | \|φ\| ≲ 4.4° |
| left | 40 < o ≤ 260 | |
| far left | o > 260 | φ > 30° |

Source: New. ⚠ OQ7. The ±40 µs center edge is chosen so that one 9° turn away from a centered source (82 µs) leaves the center bin. ±260 µs corresponds to 30°.

### 4.5 Actions and dynamics

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Action set | {turn left, turn right, listen, declare} | P | |
| Turn size | 9°, so 40 headings | P | 5 steps of a 1.8°-per-step stepper motor. |
| Reading after an action | **Every action except declare returns one reading**, taken after any motion has finished | D15 | "Listen" means stay put and draw a fresh reading. |
| Declare | The answer is the current heading. The episode ends. | P | |
| Start state | Heading and source azimuth drawn independently, uniform over their 40-value grids | P | |
| Initial observation | One reading at the starting heading, given before the first action | New | |

### 4.6 Reward and termination

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Step cost | −1 per action, including declare | P | |
| Declaration reward | 1000 · (1 − Δθ/π), where Δθ ∈ [0, π] is the angle between the source and the declared heading, measured the short way round | D19, HW3 | Ten times the proposal's 100. Declaring one turn (9°) off costs 50 points, the same as 50 actions. |
| Step limit | 50 actions; then the episode ends with no declaration reward | New | ⚠ OQ8. A worst-case search (20 turns plus listens) fits. |
| Discount γ | 1 | P | Episodes are finite, and the step cost already penalizes delay. |

**Reference returns** (σ = 0):
- **Oracle** (knows θ, turns the short way, declares): return = 1000 − (d + 1), where d is the number of turns. Averaged over random starts d is 10, so the **oracle averages 989.**
- **Declaring immediately** averages 500 − 1 = **499, which is 50% of the oracle.** Values near this mean nothing has been learned.
- **Running out the step limit** returns −50.

These replace the proposal's 88 and 49, which used a reward of 100 and assumed a source anywhere on the circle (D14, D19).

**Why 1000 and not 100?** Under the proposal's reward, one action cost as much as 1.8° of error, so a listen could never pay for itself. In a test with hand-written policies, listening raised completion but lowered return at every noise level, which would leave H3 with nothing to test. At 1000, one more reading gained about 9 points at σ = 40 µs and 15 points at σ = 80 µs, and made no difference at σ ≤ 20 µs. That is the pattern H3 predicts. The evidence is from the formula-only environment with untuned policies (HW3), so it should be rechecked on the room table.

### 4.7 Agent state

The environment emits raw readings o_t. **Each agent builds its own state** from the history of readings and actions. This keeps the environment the same for every agent and lets the state design vary by algorithm.

| Option | Definition | Size (tabular) | Source |
|---|---|---|---|
| A. Proposal | (bin of o_t, bin of o_{t−1} or none, previous action or none) | 120 | P |
| B. Evidence summary | (bin of the mean reading at the current heading, number of listens at the current heading capped at 3, bin of the mean reading at the previous heading or none, last turn direction or none) | ~360 | New |

⚠ OQ2: Option A remembers only two readings, so the agent can't build up evidence by listening repeatedly, which H3 depends on. To be decided when the algorithms are chosen (OQ3).

Evidence so far (HW3, hand-written policies): one bit of memory, "have I turned yet?", is enough for the front–back check at σ ≤ 20 µs. Richer memory matters only for averaging readings under noise. The homework's Option A array has 150 entries, not 120, because it keeps an unused slot for "declare" as the previous action.

### 4.8 Evaluation

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Training room | One fixed room (R0) for all training | D8 | |
| Final evaluation | 1,000 episodes per room: 25 from each of the 40 starting directions (the source direction relative to the nose at the start), with the starting heading drawn at random. Greedy policy (exploration off), fixed seeds. | P, D8, D20, HW3 | R3. ⚠ OQ19. Training episodes still use random starts (§4.5). |
| Validation during training | Same design as the final evaluation (25 × 40 episodes per room), greedy, every N training episodes | D8, D20, HW3 | ⚠ OQ8: N. ⚠ OQ19: was 200 episodes with random starts, which samples the dead-behind start only about 5 times. May be cut back if it slows training. |
| Rooms evaluated | R0 plus the held-out rooms | D8 | |
| Completion | The agent declares within one turn of the source (Δθ ≤ 9°) | P | Timeouts and wider misses count as failures. |
| Primary metrics | Completion rate · learning curve (greedy validation return vs. training episodes, mean and spread across seeds) · fraction of oracle return | P, D8 | |
| Secondary metrics | Angular error at declaration · steps before declaring · fraction of steps spent listening · completion and listens broken down by starting direction | P, D20, HW3 | The by-direction breakdown is what shows a front–back failure. |
| Success, base condition | At least 99% completion, a learning curve that levels off, and a return that matches the check baseline (§4.9) within a margin still to be set. | P, D21, HW3 | ⚠ OQ17. On the formula-only environment the check baseline reached 99.9% completion at σ = 20 µs, so the bar is attainable there. An agent with no memory tops out at 97.5%. To be confirmed on the room table. |

### 4.9 Baselines

| Baseline | Definition | Source |
|---|---|---|
| Random | Uniform over the 4 actions | P |
| No memory | Turn toward the side the reading points to. Declare when the reading is centered (\|o_t\| ≤ 40 µs). | HW3, D20 |
| Check (the hand-written strategy) | As no memory, but it never declares before it has turned at least once. | HW3, D20 |
| Check + k readings | As check, but when a reading looks centered it gathers k readings at that heading and decides on their mean. | HW3, D20 |
| Oracle | Knows θ. An upper bound only, not a target. | P |

⚠ OQ19. The proposal's hand-written strategy made one extra turn to check in every episode, then turned 180° if the source was behind. The check rule reaches the same completion in fewer steps, because turning toward the reading already brings a source behind the head round to the front. The check is needed only when the first reading is centered (HW3).

For scale, on the formula-only environment at σ = 20 µs the no-memory rule averaged 963, check 987, and the oracle 989 (HW3).

The value of k will be set in the agents component spec. The homework tried k = 2 and k = 4.

### 4.10 Training budget

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Seeds per configuration | Pilot with 30, then decide | New | ⚠ OQ8. 100+ was floated; compute allows it for the tabular agents. |
| Training episodes per run | To be set from the pilot | New, HW3 | ⚠ OQ8. The earlier guess of 10⁴–10⁵ for tabular agents looks optimistic: in a Monte Carlo pilot, Options A and B were far from converged after 50,000 episodes. Q-learning and SARSA are untested. |

### 4.11 Hardware compatibility

The simulation is kept compatible with a simple physical rig, so S2 stays possible without redesign (D9).

- **One ITD function.** It takes two audio signals and returns an ITD. The same code runs on simulated and real recordings.
- **Swappable acoustic front end.** The environment asks a front end for an ITD reading at the current geometry. In simulation the front end draws from the table. On hardware it records a burst and calls the ITD function. Episode logic, agents, and the harness don't know which one is in use.
- **Simulated settings match a simple rig:** one rotation axis, stepper-motor turns, two omnidirectional mics on a single stereo interface (one shared clock, which valid ITD requires), 48 kHz, and a speaker playing white-noise bursts.
- **The agent listens only while stopped.** Readings are taken after the motor finishes moving, so motor noise never reaches a reading.
- **The point-mic receiver is the one that matches this rig.** A table built with the simulated head (§4.12) would match only a rig with a physical head or baffle between the mics (⚠ OQ21, OQ11).

### 4.12 Optional receiver: a simulated head

*Not part of the core. Whether and how it is used is ⚠ OQ21.*

pyroomacoustics can replace the two point mics with a measured dummy head, the MIT KEMAR. It is a table-builder setting: choosing it produces a different table, and the environment, agents, reward, and harness don't change. The agent still receives one ITD number per reading. The values below come from one small test (Head spike) and are what a head table would need in order to be correct.

| Parameter | Value with the head | Source | Notes |
|---|---|---|---|
| Head model | MIT KEMAR, normal pinna (Gardner & Martin, 1994) | Head spike | Free to use if cited. Loaded with pyroomacoustics' `MeasuredDirectivityFile`. Both ears sit at the head center and each ear's measured response is rotated with the heading. The ITD comes from the measured responses, so the spacing b is not used. |
| Direction lookup | Nearest measured direction (`interp_order=None`) | Head spike | The interpolated mode corrupts ITD and collapses it to about 0 µs in a reverberant room. KEMAR is measured every 5°, so the lookup is at most 2.5° off our 9° grid. |
| ITD range | Up to about 820 µs, near 108° (just behind the ear) | Head spike | Point mics peak at 525 µs at 90°. The curve is bumpier than a sine. The reference for tests is KEMAR's own echo-free table, not τ(φ). |
| Lag search | ±1 ms | Head spike | ±b/c would cut off the largest ITDs. |
| Analysis window | Only the first few ms after the sound arrives | Head spike | The full 100 ms window fails in reverb with a head: readings were off by more than 100 µs 43% of the time at RT60 0.4 s. ⚠ The exact window length is not pinned down, and the spike placed the window using the known emission time. A physical rig would have to detect the arrival. |
| Bins (§4.4) | Unchanged | Head spike | One turn from center is still 82 µs, so the ±40 µs edge works. ±260 µs falls near 33° with the head. |
| Front/back hint in ITD | Mirror angles differ by 10–20 µs | Head spike | One reading told front from back 71% of the time at σ = 20 µs with no echoes (47% with point mics). It belongs to the head, so it would carry over to other rooms. It doesn't help when the source is directly behind, where the ITD is 0 either way. |
| Table build time | About 2–2.5 core-hours per room (estimate) | Head spike | Against 5–15 minutes for point mics. Scaled from a cloud machine and not yet timed on a laptop. Built once and cached. |
| Extra dependencies | `python-sofa`, `netCDF4`, and the KEMAR SOFA file | Head spike | The spike loaded the data through the `slab` package as a workaround. The standard download path is untested. |

**Limits of the test.** One head direction (facing 0°), one room, 20 bursts per cell. A rotating head, laptop build time, and the analysis window need a short follow-up test before any head table is used for results.

## 5. Conventions

*Status: Draft*

Rules that apply to every component (D16).

- **Grid indices in code.** Head headings and source azimuths are stored as **integer grid indices 0–39** (9° per step), not as float angles. Convert to radians only where the physics needs it (table builder, reward calculation). Convert to degrees only for logs, plots, and the report. This avoids wrap-around errors (2π vs. 0) and makes table lookups exact.
- **Units in names.** Variable and config names carry their units, e.g. `turn_size_deg`, `azimuth_rad`, `itd_us`, `sigma_us`, `heading_idx`. Unit mix-ups between modules then show up in review.
- **Config files use degrees or grid indices.** Configs are edited by hand, so angles in a config are in degrees (or indices) and are converted once, at load time. No component should have to guess the unit of a config value.
- **ITD is passed between components in µs** (`itd_us`, `sigma_us`): table entries, observations, and noise σ. The table builder may work in seconds internally but stores µs.

## 6. Acceptance tests

*Status: Draft*

Each test is implemented as an automated test and must pass before the component it covers counts as done. Component specs will add tests here as they are written.

### AT1. The echo-free table matches the ITD formula
- **Covers:** table builder and ITD estimator (§4.4)
- **Setup:** point-mic receiver, room with no reflections (max_order = 0), no mic noise, no internal noise, default b, fs, and signal.
- **Pass:** for every (heading_idx, source_idx) cell, the mean table reading is within **1 sample (≈ 20.8 µs at 48 kHz)** of τ(φ) = (b/c)·sin φ, using the sign convention in §4.1. The spike achieved 0.6 µs, so a much tighter tolerance (e.g. 2 µs) is a reasonable target.

### AT2. Grid-index conversions round-trip and wrap correctly
- **Covers:** shared angle/grid utilities used by all components (§5)
- **Pass:**
  1. For all 40 indices, index → radians → degrees → index returns the original index.
  2. The wrapped angular difference is correct across the 0°/360° boundary, e.g. heading_idx 39 vs. 0 is 9°, not 351°. Check every pair of indices against the shortest-way-round distance, min(|i − j|, 40 − |i − j|) × 9°.

### AT3. Agents on the same seed face the same environment
- **Covers:** environment and harness seeding (R3, R5)
- **Pass:**
  1. Two different agents trained with the same seed log identical starting headings and source azimuths for every training episode and every validation episode.
  2. Replaying one fixed action sequence in the same episode (same seed, same episode number) twice returns identical readings at every step.
  3. Changing only the agent, or only the agent's settings (e.g. exploration rate), leaves items 1 and 2 unchanged.
  4. Changing the seed changes the episode starts.

### AT4. An echo-free table depends only on the relative direction
- **Covers:** how the table builder turns the receiver (§4.2, §4.12). Applies to every receiver.
- **Setup:** room with no reflections, no mic noise, no internal noise.
- **Pass:** any two cells with the same (source_idx − heading_idx) mod 40 have mean readings within 2 µs of each other. This catches a head or mic pair rotated the wrong way or about the wrong point.

### AT5. The echo-free head table matches the KEMAR data
- **Covers:** the head receiver (§4.12). Required only if a head table is built (⚠ OQ21).
- **Setup:** head receiver, room with no reflections, no mic noise, no internal noise.
- **Pass:** for every cell, the mean table reading is within **1 sample (≈ 20.8 µs)** of the ITD computed with the same estimator from the raw KEMAR impulse responses at the nearest measured direction, with a source on the left giving a positive ITD. The spike agreed to within 1 µs at 30°, 90°, and 150°.

### AT6. A reverberant table stays close to the echo-free one
- **Covers:** the ITD estimator's settings in reverb (§4.4, §4.12). Applies to every receiver.
- **Setup:** training room R0, no internal noise.
- **Pass:** in at least 95% of cells, the median reading is within 1 sample (≈ 20.8 µs) of the same cell's echo-free reading, and no cell's median falls on the wrong side of zero by more than 1 sample. This catches the two failures seen in the head spike: the full analysis window and the interpolated direction lookup. The thresholds are drafts.

## 7. Open questions

When a question is resolved: update the affected section above, add a line to [decisions.md](decisions.md), and move the question to the Resolved list at the bottom.

| ID | Question | Owner | Needed before |
|---|---|---|---|
| OQ1 | How central should the algorithm comparison be? | TBD (ask teaching team) | Choosing algorithms |
| OQ2 | What does the agent's state contain? | TBD | Agents spec |
| OQ3 | Which algorithms, and how many? | TBD | Agents spec |
| OQ4 | Which noise levels? | TBD | Running E1 |
| OQ5 | Which held-out rooms? | TBD | Running E3 |
| OQ6 | Are harder acoustic conditions needed? | TBD | Freezing §3 |
| OQ7 | Are the bin edges right? | TBD | Agents spec |
| OQ8 | Training budget, seeds, step limit | TBD | Running E1 |
| OQ10 | Moving source design | TBD | Starting S1 |
| OQ11 | Hardware: parts, owner, is a demo expected? | TBD | Starting S2 |
| OQ12 | What to do with the old `sim/` code? | Jake | First code PR |
| OQ13 | Should the core include a reverb sweep? | Jake & Rachel | Freezing §3 |
| OQ14 | What sound should the source play? | Jake & Rachel | Freezing §4.3 |
| OQ17 | How should H1 and the success bar be worded? | TBD | Running E1 |
| OQ18 | Is the front–back check too rare to study as planned? | TBD | Freezing §2 |
| OQ19 | Do we adopt the homework's baselines and balanced evaluation? | TBD | Agents spec |
| OQ20 | Can the formula-only environment be used for tests and pilots? | TBD | First code PR |
| OQ21 | Do we use a simulated head, and how? | TBD | Freezing §3 |

### OQ1. How central should the algorithm comparison be?
We lean toward a short comparison with the focus on the localization hypotheses. Most RL papers compare 2–3 algorithms. We need to confirm what the course expects. This affects how many agents are core and how many are stretch (OQ3).

### OQ2. What does the agent's state contain?
The two candidates are in §4.7. The proposal's state can't accumulate evidence over repeated listens, which H3 depends on. Decide together with OQ3.

Evidence from HW3: a hand-written rule with one bit of memory ("have I turned yet?") came within 2 points of the oracle's 989 at σ = 20 µs. So the front–back problem needs very little memory, and richer memory is for averaging readings under noise. In a Monte Carlo pilot, a state holding only the current reading's bin learned fastest. Options A and B were far from converged after 50,000 episodes. A smaller third option (current bin plus a "have I turned" bit) may be worth adding to the candidates.

### OQ3. Which algorithms, and how many?
The proposal's list: tabular Q-learning, SARSA, semi-gradient SARSA with tile coding, REINFORCE with a baseline or actor-critic, and DQN as a stretch. Depends on OQ1 and OQ2.

Untested reasoning from HW3: with greedy evaluation, SARSA may undervalue listening, because it prices in its own exploratory declarations and turns. No run has confirmed this.

### OQ4. Which noise levels?
Draft values are in §4.4: a base σ of 20 µs and a sweep of {10, 20, 40, 80, 160} µs. Confirm the base value and the range. At 20 µs or more, the room's faint front/back cue is hidden.

Evidence from HW3 (formula-only environment, hand-written policies, D19 reward): extra listening paid at σ = 40 and 80 µs, made no difference at σ ≤ 20 µs, and σ = 160 µs was too noisy to be informative. Consider whether 160 µs stays in the sweep, and whether a value between 80 and 160 µs would tell us more.

### OQ5. Which held-out rooms?
How many, and how they differ from the training room: dimensions, RT60, head position, source distance.

### OQ6. Are harder acoustic conditions needed?
The spike used the easiest case (white noise, source 1.5–2 m away), and ITD came through almost untouched. A farther source, speech, or narrowband sounds would degrade ITD more. Decide whether any of these belong in the core, and avoid claiming "reverb doesn't matter" beyond the conditions tested. Closely tied to OQ14.

The head spike adds one case where reverb does matter: with a simulated head, the far ear is shadowed, and full-window ITD in the RT60 0.4 s room was off by more than 100 µs 43% of the time (§4.12).

### OQ7. Are the bin edges right?
Draft edges are in §4.4 (±40 and ±260 µs). They interact with the turn size and the noise level: at σ = 20 µs a centered reading will sometimes fall outside the ±40 µs center bin. Confirm or adjust when the tabular agents are specified.

### OQ8. Training budget, seeds, step limit
Number of seeds (the class norm is many; 100+ was floated), episodes per run, the 50-action step limit (§4.6), and how often to validate during training. A small pilot measuring the variance between seeds should come before fixing the seed count.

Evidence from HW3: in a first Monte Carlo pilot (ε = 0.1, 8 seeds), every agent still scored about 500 after 10,000 episodes, which is what declaring immediately earns. Returns swing by hundreds of points between episodes while the gap between a good and a bad action is tens of points. Learning speed may be the main schedule risk, so a pilot with the algorithms we plan to use should come before §4.6 and §4.7 are frozen. At σ = 160 µs the hand-written policies ran into the 50-action limit.

### OQ10. Moving source design (S1)
The motion model (speed, continuous or step-wise), how the reward handles a moving target, and whether the table grid still suffices.

### OQ11. Hardware (S2)
Were parts ordered (mics, audio interface, motor)? Does the teaching team expect a physical demo? Who owns it? The rig must use a single stereo interface so both mics share one clock (§4.11).

### OQ12. What to do with the old `sim/` code?
Keep it as a reference, archive it, or remove it. It was a library test and doesn't bind the design (D11).

### OQ13. Should the core include a reverb sweep?
The plan trains in one moderately reverberant room, because the spike showed reverb barely affects ITD under our conditions. A sweep needs **no architecture change**: each reverb level is another room config with its own table (~5–15 min to build). The real cost is that it multiplies the number of training runs (agents × σ × reverb levels × seeds). It can be added later without rework.

### OQ14. What sound should the source play?
The default is a 50 ms white-noise burst. This choice could change the experiments substantially:
- **Broadband noise** (current) is the easiest signal for ITD. GCC-PHAT finds one sharp peak, so ITD is near-exact.
- **A pure tone or smoke-detector-style beep** (narrowband, ~3 kHz): one cycle at 3 kHz lasts ~330 µs, shorter than our largest ITD (~525 µs). Several time lags line up equally well, so **ITD becomes ambiguous left–right, not just front–back.** This is a known reason high-pitched beeps, like a chirping smoke alarm, are hard for people to localize. People fall back on level differences at high frequencies, but our simulation has none (§3.3). The task may become much harder or unsolvable for an ITD-only agent. That's interesting research, but a different project.
- **Middle options:** band-limited noise, speech, or short clicks.

Evidence from the head spike, which tried a 3.2 kHz, 100 ms beep:
- **ITD does wrap.** A true 371 µs read as 58 µs, even using only the start of the beep. This happens with or without a head.
- **Level difference over the whole beep is set by the room, not the direction.** At 90° it pointed to the wrong side.
- **With a head, the level difference in the first ~3 ms gives a clear left/right cue** (up to about 18 dB). It is the same in front and behind, so turning is still needed. This would require the head option (OQ21) and a level observation.
- **Narrowband sounds need some mic noise in simulation.** Without it, GCC-PHAT recovers the ITD from faint content in the fade-in that real noise would bury.

In code, the sound is a table-builder setting (one table per room and sound), so it's cheap to change. In experiment design it's expensive.

### OQ17. How should H1 and the success bar be worded?
H1 used to ask for 90% of the oracle's return. A rule with no memory already reaches about 97% (963 of 989 at σ = 20 µs, HW3), so that bar can't tell a good agent from a mediocre one. The draft H1 and the success bar in §4.8 now compare agents with the check baseline. Still open:
- **The margin that counts as "matching".** Check and no-memory are only about 24 points apart, so the margin has to be set from the variance between seeds.
- **The headline metric.** Under the proposal's reward, listening raised completion and lowered return. Under the D19 reward the two agree at σ = 40 and 80 µs. Decide whether return or completion leads.

### OQ18. Is the front–back check too rare to study as planned?
Turning toward the sound brings a source behind the head round to the front without any explicit check. In the homework test the check mattered only when the source started directly behind, which is 1 start in 40. It was worth about 24 points of 989 on average (HW3). The behavior at the center of H2 is therefore rare and worth little return, which makes it slow to learn and hard to show. Options:
- **Report H2 on centered starts only.** The by-direction evaluation (§4.8) already supports this.
- **Sample centered starts more often** in training, in evaluation, or both.
- **Reframe.** "Turning toward the sound resolves most front–back confusion for free" would itself be a finding, with the explicit check as the edge case.

More noise widens the set of starts that look centered, so the check may matter more in E2 than in E1.

### OQ19. Do we adopt the homework's baselines and balanced evaluation?
§4.8 and §4.9 now carry the homework's design as a draft: three hand-written baselines (no memory, check, check + k readings) and evaluation with 25 episodes from each of the 40 starting directions. Confirm or change:
- Whether check replaces the proposal's "one extra turn every episode" strategy, or both are kept.
- The validation size during training. 1,000 episodes per room per pass is thorough but may slow training once there are several rooms.
- Whether training episodes should also be balanced by starting direction. They are random for now.

### OQ20. Can the formula-only environment be used for tests and pilots?
D4 chose one acoustic pipeline and kept the formula for the report and AT1 only. A formula-only environment now exists from HW3. It uses numpy only, follows this spec's sign and unit conventions, and its default reward matches D19. It could be a third acoustic front end (§4.11) for fast unit tests and for pilots of the training budget and state design, with no reported result coming from it. Also to settle: whether course policy allows homework code to be reused in the team project, and how it would be shared.

### OQ21. Do we use a simulated head, and how?
The head spike showed that pyroomacoustics can simulate a measured dummy head in place of the two point mics. §4.12 records what a head table would need. The options, from least to most change:

| Option | What we would do | What we get | What it costs |
|---|---|---|---|
| A. Leave it out | Point mics only. Cite the spike as a known limit. | Nothing new to build. ITD checks against the formula. Matches the bare two-mic rig (§4.11). | No answer if a reader asks whether the results hold for a real head. |
| B. Check only | Train on point mics. Evaluate the trained policies on a head table with no retraining, like E3. | One result on whether the learned behavior survives a realistic head. | One head table per room tested, the onset-window estimator, and AT5. No extra training runs. |
| C. Train on both | Add the head as a second condition in E1, and possibly E2. | A direct comparison of strategies learned with and without a head. | Up to twice the training runs. Head tables for every room. |
| D. Head replaces point mics | The head is the receiver for all core experiments. | The most realistic core setup. | Tests compare against KEMAR data, not the formula. About 20× the table build time. No longer matches a bare two-mic rig. |
| E. Head plus level cues | The agent also observes level differences. | A different question: does the agent stop turning when one reading is enough? | Changes the research question, H2, and D5. Larger observation and agent state. |

In A–D the agent observes ITD only. Options B–E rest on a test of one head direction and need the follow-up test in §4.12 first.

### Resolved

| ID | Question | Outcome |
|---|---|---|
| OQ9 | Which proposal experiments get cut? | D12: see §3.3 |
| OQ15 | Is the source on the heading grid or anywhere on the circle? | D14: on the grid |
| OQ16 | Does a turn also return a reading? | D15: yes |
