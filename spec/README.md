# How we work on this spec

Read this first if you are new to the `spec/` folder, whether you are a teammate or an AI agent picking up the work in a fresh session.

## What's here

| File | What it is | Who reads it |
|---|---|---|
| [spec.md](spec.md) | The one living document. It holds only what is true **now**: research question, experiments, problem formulation, conventions, acceptance tests, open questions. | Everyone |
| [decisions.md](decisions.md) | History. One line per decision: what, why, what it changed. Append-only. | Anyone asking "why did we do it this way?" |
| `components/` (not created yet) | Build-level detail for one component each: interfaces, file formats, tests, tasks. | Coding agents, and whoever reviews their work |

Supporting evidence lives outside this folder: the calibration test in [`spikes/reverb_itd/RESULTS.md`](../spikes/reverb_itd/RESULTS.md) and the original proposal in `report/main_proposal.tex`. The proposal is non-binding; where it differs from `spec.md`, the spec wins.

## The strategy

We are defining the problem and writing the spec at the same time, and the first readers are three people, not agents. So:

1. **One document while things are still moving.** People lose the thread when they have to jump between many files. Everything current goes in `spec.md`, short and skimmable.
2. **Current state and history are kept apart.** `spec.md` says what is true. `decisions.md` says why. Nobody should have to replay a list of decisions to learn the current plan.
3. **Split only when a section has settled.** Detail is added as certainty grows, not before.

## Rules that keep the later split cheap

- **Stable IDs.** Hypotheses (H), experiments (E), stretch goals (S), code requirements (R), acceptance tests (AT), open questions (OQ), decisions (D). IDs are never reused or renumbered, even when an item is resolved or dropped.
- **Section status.** Every section of `spec.md` is **Draft** (still changing), **Agreed** (the team has reviewed it), or **Frozen** (ready to build from). Only the team moves a section forward.
- **Each fact lives in one place.** If a value appears in `spec.md`, other files refer to it and do not repeat it.
- **Unknowns are written down, not guessed.** An open question gets an OQ entry in Section 7 of `spec.md` and a ⚠ marker next to every value it affects.
- **Values that haven't been reviewed are marked New** in the Source column.

## How to make a change

- **Resolving an open question:** update the affected section of `spec.md`, add one line to `decisions.md`, and move the question to the Resolved table in Section 7.
- **Any other decision:** change `spec.md` to the new current state and add one line to `decisions.md` saying what changed and why. If it reverses an earlier decision, say which.
- **Every testable requirement gets an acceptance test** in Section 6, written so a machine can check it.
- **All changes go through a pull request** on a new branch. Jake, Rachel, and Harris review by PR, sometimes with a call; whatever a call decides still lands as a PR.

## The path to agent-written code

The team intends for AI agents to write all or almost all of the code, working from this spec.

| Step | What happens | State (2026-11-13) |
|---|---|---|
| 1 | Research question and hypotheses | Drafted (§2) |
| 2 | Experiment plan | Drafted (§3) |
| 3 | Problem formulation: every parameter with a default | Drafted (§4) |
| — | **Team review by PR.** Sections move from Draft to Agreed. | **Next** |
| 4 | Component specs, one file each under `components/`: acoustic table builder, ITD function, environment, agents, harness and evaluation, analysis and plots. Each has a purpose, interfaces, parameters, acceptance tests, and an out-of-scope list. | Not started |
| 5 | Tasks and build order. Thin end-to-end slice first: table → environment → random and hand-written baselines → tabular Q-learning → one learning-curve plot. Then widen. | Not started |

**When a section is ready to split out:** it is Frozen, and it needs detail that people don't need to read day to day. `spec.md` keeps a short summary and a link; the component file adds detail underneath and never contradicts it.

**What a coding agent is given:** `spec.md`, the one component file it is building, and the acceptance tests it must pass. It builds only from Frozen sections. If it hits something the spec doesn't answer, it stops and raises an open question; it does not guess.

## Pending threads

- **Hardware discussion** (OQ11): parts, owner, and whether a demo is expected. Not yet had.
- **Teaching team check** (OQ1): how central the algorithm comparison should be.
- **Team conversations** flagged for Jake and Rachel: the source sound (OQ14) and a reverb sweep (OQ13).
- **Agent state and choice of algorithms** (OQ2, OQ3): needed before the agents component spec.
