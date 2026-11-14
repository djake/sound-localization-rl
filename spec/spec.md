# Project Spec: Active Sound Localization with RL

**Team:** Jake Lambert, Rachel Ellinger, Harris Davidson · **Last updated:** 2026-11-13

This is the one document that describes what we are building. It holds only what is true **now**. Where it differs from the proposal (`report/main_proposal.tex`), this document wins. The reasons behind each choice are in [decisions.md](decisions.md), which you don't need to read to follow this document.

## How to read this document

- **Section status.** Each section is marked **Draft** (still changing), **Agreed** (the team has reviewed it), or **Frozen** (ready to build from). Coding agents build only from Frozen sections. Everything is Draft until the team's first review.
- **IDs.** Hypotheses (H1…), experiments (E0…), stretch goals (S1…), code requirements (R1…), acceptance tests (AT1…), open questions (OQ1…), and decisions (D1…) keep their IDs for the life of the project. IDs are never reused.
- **⚠ marks** a value that depends on an open question. The full list of open questions is in [Section 7](#7-open-questions).
- **Source column** in the tables: **P** = proposal · **Dn** = a decision in [decisions.md](decisions.md) · **Spike** = the [calibration test](../spikes/reverb_itd/RESULTS.md) · **New** = first written down here, so it especially needs review.
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
| **H1** | In low noise, the learning agents reach at least 90% of the oracle's return and match the hand-written strategy. |
| **H2** | The front–back check emerges unprompted: when the sound starts centered, the agent turns before it declares. |
| **H3** | As noise increases, agents listen more, and they lose less performance than the fixed hand-written strategy. |
| **H4** | Policies trained in one room keep their performance in rooms they have never seen. |

**Strategy analysis.** Search strategy (ex. move towards noise) will be addressed in that analysis of H2 and H3 including the mix of actions, typical trajectories, and how both shift with noise.

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
| Level differences (ILD) and other cues | The simulator has no head, so ILD is under 1 dB and carries nothing ITD doesn't (D5). |
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
| Mics | 2 omnidirectional point mics, symmetric about the axis | D5, D9 | |
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
| Table shape | 40 headings × 40 source azimuths per room, indexed `[heading_idx][source_idx]` | D7, D14 | Every cell is a geometry that can actually occur. |
| Readings per cell K | 200, each from a different random noise burst | D7 | Built once per room (~5–15 min on one laptop core), shared by all seeds. |
| ITD estimator | GCC-PHAT, sub-sample (parabolic) interpolation, lag search limited to ±b/c | D4, Spike | Pick the **largest positive** peak, not the largest absolute value (a bug noted in `sim/`). |
| Internal noise σ, base condition | 20 µs | New, D6 | ⚠ OQ4. Hides the room's faint front/back cue (Spike). Small next to the 82 µs ITD change from one turn away from center. |
| σ sweep (E2) | {10, 20, 40, 80, 160} µs | New | ⚠ OQ4. 160 µs ≈ two turns' worth of ITD change, which should be hard. |
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
| Declaration reward | 100 · (1 − Δθ/π), where Δθ ∈ [0, π] is the angle between the source and the declared heading, measured the short way round | P | |
| Step limit | 50 actions; then the episode ends with no declaration reward | New | ⚠ OQ8. A worst-case search (20 turns plus listens) fits. |
| Discount γ | 1 | P | Episodes are finite, and the step cost already penalizes delay. |

**Reference returns** (σ = 0):
- **Oracle** (knows θ, turns the short way, declares): return = 100 − (d + 1), where d is the number of turns. Averaged over random starts d is 10, so the **oracle averages 89.**
- **Declaring immediately** averages 50 − 1 = **49, which is 55% of the oracle.** Values near this mean nothing has been learned.

These replace the proposal's 88 and 49, which assumed a source anywhere on the circle (D14).

### 4.7 Agent state

The environment emits raw readings o_t. **Each agent builds its own state** from the history of readings and actions. This keeps the environment the same for every agent and lets the state design vary by algorithm.

| Option | Definition | Size (tabular) | Source |
|---|---|---|---|
| A. Proposal | (bin of o_t, bin of o_{t−1} or none, previous action or none) | 120 | P |
| B. Evidence summary | (bin of the mean reading at the current heading, number of listens at the current heading capped at 3, bin of the mean reading at the previous heading or none, last turn direction or none) | ~360 | New |

⚠ OQ2: Option A remembers only two readings, so the agent can't build up evidence by listening repeatedly, which H3 depends on. To be decided when the algorithms are chosen (OQ3).

### 4.8 Evaluation

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Training room | One fixed room (R0) for all training | D8 | |
| Final evaluation | 1,000 episodes per room, greedy policy (exploration off), fixed seeds | P, D8 | R3 |
| Validation during training | 200 episodes per room, greedy, every N training episodes | D8 | ⚠ OQ8: N |
| Rooms evaluated | R0 plus the held-out rooms | D8 | |
| Completion | The agent declares within one turn of the source (Δθ ≤ 9°) | P | Timeouts and wider misses count as failures. |
| Primary metrics | Completion rate · learning curve (greedy validation return vs. training episodes, mean and spread across seeds) · fraction of oracle return | P, D8 | |
| Secondary metrics | Angular error at declaration · steps before declaring · fraction of steps spent listening | P | |
| Success, base condition | At least 99% completion, a learning curve that levels off, and at least 90% of oracle return. The hand-written baseline is run first to confirm these are attainable at base σ. | P | |

### 4.9 Baselines

| Baseline | Definition | Source |
|---|---|---|
| Random | Uniform over the 4 actions | P |
| Hand-written | Turn toward the side the reading points to until it's centered. Make one extra turn to check front vs. back: if the reading moves the "wrong" way, the source is behind, so turn 180° (20 turns) and recenter. Then declare. | P |
| Oracle | Knows θ. An upper bound only, not a target. | P |

How the hand-written baseline handles noise (e.g. how many listens before it trusts a reading) will be set in the agents component spec.

### 4.10 Training budget

| Parameter | Default | Source | Notes |
|---|---|---|---|
| Seeds per configuration | Pilot with 30, then decide | New | ⚠ OQ8. 100+ was floated; compute allows it for the tabular agents. |
| Training episodes per run | To be set from the pilot (expect roughly 10⁴–10⁵ for tabular) | New | ⚠ OQ8 |

### 4.11 Hardware compatibility

The simulation is kept compatible with a simple physical rig, so S2 stays possible without redesign (D9).

- **One ITD function.** It takes two audio signals and returns an ITD. The same code runs on simulated and real recordings.
- **Swappable acoustic front end.** The environment asks a front end for an ITD reading at the current geometry. In simulation the front end draws from the table. On hardware it records a burst and calls the ITD function. Episode logic, agents, and the harness don't know which one is in use.
- **Simulated settings match a simple rig:** one rotation axis, stepper-motor turns, two omnidirectional mics on a single stereo interface (one shared clock, which valid ITD requires), 48 kHz, and a speaker playing white-noise bursts.
- **The agent listens only while stopped.** Readings are taken after the motor finishes moving, so motor noise never reaches a reading.

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
- **Setup:** room with no reflections (max_order = 0), no mic noise, no internal noise, default b, fs, and signal.
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

### OQ1. How central should the algorithm comparison be?
We lean toward a short comparison with the focus on the localization hypotheses. Most RL papers compare 2–3 algorithms. We need to confirm what the course expects. This affects how many agents are core and how many are stretch (OQ3).

### OQ2. What does the agent's state contain?
The two candidates are in §4.7. The proposal's state can't accumulate evidence over repeated listens, which H3 depends on. Decide together with OQ3.

### OQ3. Which algorithms, and how many?
The proposal's list: tabular Q-learning, SARSA, semi-gradient SARSA with tile coding, REINFORCE with a baseline or actor-critic, and DQN as a stretch. Depends on OQ1 and OQ2.

### OQ4. Which noise levels?
Draft values are in §4.4: a base σ of 20 µs and a sweep of {10, 20, 40, 80, 160} µs. Confirm the base value and the range. At 20 µs or more, the room's faint front/back cue is hidden.

### OQ5. Which held-out rooms?
How many, and how they differ from the training room: dimensions, RT60, head position, source distance.

### OQ6. Are harder acoustic conditions needed?
The spike used the easiest case (white noise, source 1.5–2 m away), and ITD came through almost untouched. A farther source, speech, or narrowband sounds would degrade ITD more. Decide whether any of these belong in the core, and avoid claiming "reverb doesn't matter" beyond the conditions tested. Closely tied to OQ14.

### OQ7. Are the bin edges right?
Draft edges are in §4.4 (±40 and ±260 µs). They interact with the turn size and the noise level: at σ = 20 µs a centered reading will sometimes fall outside the ±40 µs center bin. Confirm or adjust when the tabular agents are specified.

### OQ8. Training budget, seeds, step limit
Number of seeds (the class norm is many; 100+ was floated), episodes per run, the 50-action step limit (§4.6), and how often to validate during training. A small pilot measuring the variance between seeds should come before fixing the seed count.

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

In code, the sound is a table-builder setting (one table per room and sound), so it's cheap to change. In experiment design it's expensive.

### Resolved

| ID | Question | Outcome |
|---|---|---|
| OQ9 | Which proposal experiments get cut? | D12: see §3.3 |
| OQ15 | Is the source on the heading grid or anywhere on the circle? | D14: on the grid |
| OQ16 | Does a turn also return a reading? | D15: yes |
