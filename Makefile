.PHONY: all

PAPER = main

all: $(PAPER).pdf reviews/pap537.html

$(PAPER).pdf:	Makefile\
		*.bst\
		*.bib\
		*.tex\
		*/*.*
	latexmk -bibtex -pdf $(PAPER)

reviews/pap537.html:	reviews/pap537.md
	pandoc -o reviews/pap537.html reviews/pap537.md

again:	distclean all

clean:
	latexmk -bibtex -c $(PAPER)

distclean:
	latexmk -bibtex -C $(PAPER)
	rm -f reviews/pap537.html

review:	reviews/pap537.html
