# Sound Localization with Reinforcement Learning

Final project for CS 138 (Reinforcement Learning).

An agent controls a servo with one or two microphones mounted on it and must
locate a sound source, which may be moving, as effectively and efficiently as
possible. The core RL problem is planning how to move the servo so that it
collects the data needed to localize the sound. Everything is simulated; there
is no physical hardware.

Stretch goals:

- A transfer learning component.
- A multi-agent version (Marco Polo).

## Team

| Name            | GitHub                                     |
| --------------- | ------------------------------------------ |
| Jake            | [@djake](https://github.com/djake)         |
| Harris Davidson | [@hrrs](https://github.com/hrrs)           |
| Rachel Ellinger | [@rellin01](https://github.com/rellin01)   |

## Repository layout

```
report/
  main_proposal.tex   Project proposal (deliverable 1)
  main_final.tex      Final report (deliverable 2)
  references.bib      BibTeX references, shared by both
  Makefile            latexmk build targets
sim/
  acoustics.py        Room simulation (pyroomacoustics) and the cached delay table
  tdoa.py             Delay estimation between the two mics (GCC-PHAT) and bucketing
  env.py              The RL environment: state, actions, reward
  __main__.py         `python -m sim` demo
tests/                pytest suite for sim/
pyproject.toml        Python package and dependencies
```

## Simulation environment

The agent controls a two-microphone head in a simulated room.
[pyroomacoustics](https://pypi.org/project/pyroomacoustics/) simulates what
each microphone hears from a sound source. It handles the travel delay to each
mic and, optionally, echoes off the walls. From the two recordings we estimate
the time difference of arrival (TDOA) and bucket it from far left to far right.

Simulating on every step would be slow. Instead, `sim.acoustics.build_tdoa_table`
simulates every (head angle, source angle) pair once and caches the delays in
`.cache/tdoa/`. The first build of the default table takes about 15 seconds;
after that it loads instantly. Changing any setting in `RoomConfig`,
`HeadConfig` or `SourceConfig` builds a new table.

The default setup is a quiet 8 × 8 m room with no echoes, mics 15 cm apart, 24
head angles (15° steps), and a stationary source 2 m away at one of 72 angles
(5° steps), playing three 50 ms bursts of static.

| | |
| --- | --- |
| **State** | `(bucket, prev_bucket, last_turn)`: the current delay bucket (0 = far left … 8 = far right), the bucket before the last turn (9 = no turn yet), and the last turn (0 = none, 1 = left, 2 = right). One reading can't tell front from back; a turn can. |
| **Actions** | 0 = turn left (counterclockwise 15°), 1 = turn right, 2 = declare the source is straight ahead |
| **Reward** | −1 per step; +20 for a correct declaration (source within 7.5° of the facing direction), −20 for a wrong one. Episodes end on a declaration or are truncated after 50 steps. |

The interface follows Gymnasium (`reset()` returns `(obs, info)`, and `step()`
returns `(obs, reward, terminated, truncated, info)`) without depending on it.
`env.state_index(obs)` flattens an observation for a Q-table of size
`env.n_states × env.n_actions`. `info` includes the true head and source
angles and the angle error, for evaluation.

```python
from sim import SoundLocalizationEnv

env = SoundLocalizationEnv()
obs, info = env.reset(seed=0)
obs, reward, terminated, truncated, info = env.step(0)  # turn left
```

### Setup

Python 3.9 or later.

```sh
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
python -m sim      # demo: delay sweep and a few random-policy episodes
pytest             # run the tests
```

## Building the report

The proposal and the final report are separate documents, matching the
course's Overleaf template: `report/main_proposal.tex` and
`report/main_final.tex`. They share `references.bib`. Text written for the
proposal (introduction, background) is carried into the final report by
copying it over.

### Install requirements

You need a TeX distribution that provides `pdflatex`, `bibtex` and `latexmk`,
plus `make`. The report only uses standard packages (`natbib`, `graphicx`, `array`), which
every distribution below includes.

**macOS**

```sh
brew install --cask mactex-no-gui    # full TeX Live, ~5 GB
```

Or, for a smaller install (BasicTeX, ~100 MB):

```sh
brew install --cask basictex
eval "$(/usr/libexec/path_helper)"   # or open a new terminal
sudo tlmgr update --self
sudo tlmgr install latexmk
```

`make` comes with the Xcode Command Line Tools (`xcode-select --install`).

**Ubuntu / Debian**

```sh
sudo apt install texlive-latex-base texlive-latex-recommended latexmk make
```

**Windows**

Install [MiKTeX](https://miktex.org/download) (it installs missing packages on
demand) and [Strawberry Perl](https://strawberryperl.com/), which `latexmk`
needs. Then run the `latexmk` commands below directly, or use `make` from WSL or
Git Bash. Alternatively, use WSL and follow the Ubuntu instructions.

Check the install:

```sh
pdflatex --version
latexmk -v
```

### Build

```sh
cd report
make proposal          # -> report/build/main_proposal.pdf
make final             # -> report/build/main_final.pdf
make                   # both
make watch-proposal    # rebuild on every save (also watch-final)
make clean             # remove build output
```

Without `make`:

```sh
cd report
latexmk -pdf -outdir=build main_proposal.tex
```

Build output goes to `report/build/`, which is git-ignored.

### Editor and Overleaf

- **VS Code:** the [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)
  extension uses `latexmk` and builds on save.
- **Overleaf:** upload the contents of `report/` and set the main document
  (Menu → Main document) to `main_proposal.tex` or `main_final.tex`. These
  files and `references.bib` start from the course's
  [Overleaf template](https://www.overleaf.com/project/5bd749283ef78423cd076886).

## License

[MIT](LICENSE)
