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
  body.tex          Shared source for the proposal and the final report
  proposal.tex      Builds the proposal (sets \proposaltrue, inputs body.tex)
  final.tex         Builds the final report (sets \proposalfalse, inputs body.tex)
  references.bib    BibTeX references
  Makefile          latexmk build targets
```

Simulation and training code will live alongside `report/` as it is added.

## Building the report

The proposal and final report share one source file, `report/body.tex`.
Sections that differ between the two are wrapped in
`\ifproposal ... \else ... \fi`; everything else appears in both. Edit
`body.tex`, then build whichever document you need.

### Install requirements

You need a TeX distribution that provides `pdflatex`, `bibtex` and `latexmk`,
plus `make`. The report only uses standard packages (`natbib`, `graphicx`,
`amsmath`, `amssymb`, `hyperref`), which every distribution below includes.

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
make proposal          # -> report/build/proposal.pdf
make final             # -> report/build/final.pdf
make                   # both
make watch-proposal    # rebuild on every save (also watch-final)
make clean             # remove build output
```

Without `make`:

```sh
cd report
latexmk -pdf -outdir=build proposal.tex
```

Build output goes to `report/build/`, which is git-ignored.

### Editor and Overleaf

- **VS Code:** the [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)
  extension uses `latexmk` and builds on save. Open `proposal.tex` or
  `final.tex` (not `body.tex`) when you build.
- **Overleaf:** upload the contents of `report/` and set the main document
  (Menu → Main document) to `proposal.tex` or `final.tex`. The course's
  original template is
  [here](https://www.overleaf.com/project/5bd749283ef78423cd076886).

## License

[MIT](LICENSE)
