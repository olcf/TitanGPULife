.PHONY: all

PAPER = main

all: $(PAPER).pdf

$(PAPER).pdf:	Makefile\
		*.bst\
		*.bib\
		*.tex\
		*/*.*
		latexmk -bibtex -pdf $(PAPER)

again:		distclean
		@make $(PAPER).pdf

clean:
		latexmk -bibtex -c $(PAPER)

distclean:
		latexmk -bibtex -C $(PAPER)
review:
		pandoc -o reviews/pap537.html reviews/pap537.md
