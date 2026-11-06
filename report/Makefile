# Build the proposal and final report with latexmk.
# Output PDFs land in report/build/.

LATEXMK = latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build

.PHONY: all proposal final watch-proposal watch-final clean

all: proposal final

proposal:
	$(LATEXMK) main_proposal.tex

final:
	$(LATEXMK) main_final.tex

# Rebuild automatically whenever a source file changes.
watch-proposal:
	$(LATEXMK) -pvc main_proposal.tex

watch-final:
	$(LATEXMK) -pvc main_final.tex

clean:
	latexmk -C -outdir=build main_proposal.tex main_final.tex
	rm -rf build
