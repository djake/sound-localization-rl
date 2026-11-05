# Build the proposal and final report with latexmk.
# Output PDFs land in report/build/.

LATEXMK = latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build

.PHONY: all proposal final watch-proposal watch-final clean

all: proposal final

proposal:
	$(LATEXMK) proposal.tex

final:
	$(LATEXMK) final.tex

# Rebuild automatically whenever a source file changes.
watch-proposal:
	$(LATEXMK) -pvc proposal.tex

watch-final:
	$(LATEXMK) -pvc final.tex

clean:
	latexmk -C -outdir=build proposal.tex final.tex
	rm -rf build
