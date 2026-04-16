# Build LaTeX paper PDF
# Usage: make

TEX=pdflatex -interaction=nonstopmode -halt-on-error
BIB=bibtex

all: main.pdf

main.pdf: main.tex references.bib
	$(TEX) main.tex
	$(BIB) main
	$(TEX) main.tex
	$(TEX) main.tex

clean:
	rm -f *.aux *.log *.out *.bbl *.blg *.toc *.synctex.gz *.fls *.fdb_latexmk

distclean: clean
	rm -f main.pdf

.PHONY: all clean distclean
