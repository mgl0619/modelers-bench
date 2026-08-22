# The Modeler's Bench — local build.
#
# Everything here runs on your own machine. GitHub is storage and history;
# it does not have to run anything for the site to be correct.
#
#   make check     fast: regenerate data and verify it            (~20 s)
#   make preview   live-reloading site in your browser
#   make all       the full local build, same as CI would do
#
# Run `make` on its own for the list.

PY ?= python3
.DEFAULT_GOAL := help

.PHONY: help setup data verify battery check render render-py preview clean distclean doctor

help:
	@echo ""
	@echo "  The Modeler's Bench — local targets"
	@echo ""
	@echo "  make doctor    report which tools are installed and what is missing"
	@echo "  make setup     install Python and R dependencies"
	@echo ""
	@echo "  make data      regenerate CASE-SM (clean + corrupted copies)"
	@echo "  make verify    check the case against its published truth"
	@echo "  make battery   run the S0-03 data-check battery on both datasets"
	@echo "  make check     data + verify + battery          <- the fast loop"
	@echo ""
	@echo "  make render    build the site into _site/ (executes every notebook)"
	@echo "  make render-py build without R — Python notebooks only"
	@echo "  make preview   live-reloading preview in your browser"
	@echo "  make all       check + render                   <- what CI would do"
	@echo ""
	@echo "  make clean     remove build output, keep the data"
	@echo ""

doctor:
	@echo "python3 : $$($(PY) --version 2>&1 || echo MISSING)"
	@echo "quarto  : $$(quarto --version 2>/dev/null || echo 'MISSING  -> brew install --cask quarto')"
	@echo "R       : $$(R --version 2>/dev/null | head -1 || echo 'MISSING  -> brew install --cask r   (only for the R notebooks)')"
	@echo ""
	@$(PY) -c "import importlib,sys; miss=[m for m in ['numpy','pandas','scipy','matplotlib','yaml','nbclient','jupyter_client','ipykernel'] if not importlib.util.find_spec(m)]; print('python packages: OK' if not miss else 'python packages MISSING: '+', '.join(miss)+'   -> make setup')"
	@Rscript -e 'p <- c("deSolve","dplyr","ggplot2","MASS","knitr","rmarkdown"); m <- p[!p %in% rownames(installed.packages())]; cat(if (length(m)) paste0("R packages MISSING: ", paste(m, collapse=", "), "   -> make setup\n") else "R packages: OK\n")' 2>/dev/null || echo "R packages: skipped (no R)"

setup:
	$(PY) -m pip install -r requirements.txt
	@Rscript -e 'p <- c("deSolve","dplyr","ggplot2","MASS","knitr","rmarkdown"); m <- p[!p %in% rownames(installed.packages())]; if (length(m)) install.packages(m, repos="https://cloud.r-project.org")' 2>/dev/null || echo "(no R found — skipping R packages; the Python notebooks will still build)"

data:
	$(PY) cases/case-sm/generate.py
	$(PY) cases/case-sm/make_messy.py

verify:
	$(PY) scripts/verify_case.py

battery:
	$(PY) scripts/check_data.py

check: data verify battery

render:
	quarto render

render-py:
	QUARTO_PROFILE=nor quarto render

preview:
	quarto preview

all: check render

clean:
	rm -rf _site .quarto _freeze

distclean: clean
	rm -f cases/case-sm/data/*.csv
