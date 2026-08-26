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

# Pick the newest suitable interpreter unless the caller overrides PY.
# Override explicitly with:  make check PY=python3.11
PY ?= $(shell for c in python3.13 python3.12 python3.11 python3.10 python3; do \
	  command -v $$c >/dev/null 2>&1 && $$c -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1 && { echo $$c; break; }; \
	done)
ifeq ($(strip $(PY)),)
PY := python3
endif

.DEFAULT_GOAL := help

.PHONY: help setup setup-py setup-r doctor-r serve data verify battery check check-resources render render-py preview clean distclean doctor guard-python guard-r

help:
	@echo ""
	@echo "  The Modeler's Bench — local targets"
	@echo ""
	@echo "  make doctor    report which tools are installed and what is missing"
	@echo "  make setup     install Python and R dependencies"
	@echo "  make setup-r   install just the R packages"
	@echo "  make doctor-r  where R looks for packages, and what it finds"
	@echo ""
	@echo "  make data      regenerate CASE-SM (clean + corrupted copies)"
	@echo "  make verify    check the case against its published truth"
	@echo "  make battery   run the S0-03 data-check battery on both datasets"
	@echo "  make check-resources  validate resources.csv against its schema"
	@echo "  make check     data + verify + battery + resources   <- the fast loop"
	@echo ""
	@echo "  make render    build the site into _site/ (executes every notebook)"
	@echo "  make render-py build without R — Python notebooks only"
	@echo "  make preview   live-reloading preview in your browser (needs Quarto)"
	@echo "  make serve     serve an already-built _site/ on localhost:8000"
	@echo "  make all       check + render                   <- what CI would do"
	@echo ""
	@echo "  make clean     remove build output, keep the data"
	@echo ""

doctor:
	@if command -v $(PY) >/dev/null 2>&1; then \
	  echo "python  : $$($(PY) --version 2>&1)   [$$(command -v $(PY))]$$($(PY) -c 'import sys; print("" if sys.version_info >= (3,10) else "   TOO OLD — needs 3.10+")')"; \
	else echo "python  : MISSING"; fi
	@if command -v quarto >/dev/null 2>&1; then \
	  echo "quarto  : $$(quarto --version)"; \
	else echo "quarto  : MISSING  -> brew install --cask quarto"; fi
	@if command -v R >/dev/null 2>&1; then \
	  echo "R       : $$(R --version | head -1)"; \
	else echo "R       : MISSING  -> brew install --cask r        (only for the R notebooks; make render-py works without it)"; fi
	@echo ""
	@$(PY) -c "import importlib.util as u; miss=[m for m in ['numpy','pandas','scipy','matplotlib','yaml','nbclient','jupyter_client','ipykernel'] if not u.find_spec(m)]; print('python packages : OK' if not miss else 'python packages : MISSING '+', '.join(miss)+'   -> make setup')" 2>/dev/null || echo "python packages : cannot check"
	@if command -v Rscript >/dev/null 2>&1; then \
	  Rscript -e 'p <- c("deSolve","dplyr","ggplot2","MASS","knitr","rmarkdown"); m <- p[!p %in% rownames(installed.packages())]; cat(if (length(m)) paste0("R packages      : MISSING ", paste(m, collapse=", "), "   -> make setup\n") else "R packages      : OK\n")'; \
	else echo "R packages      : skipped (no R)"; fi
	@echo ""
	@$(PY) -c "import importlib.util as u; ok = u.find_spec('scipy') and u.find_spec('pandas'); print('can run: make battery' + ('  make data  make verify' if ok else '   (data/verify need scipy)'))"
	@echo ""
	@echo "interpreters on PATH:"
	@for c in python3.13 python3.12 python3.11 python3.10 python3 python; do \
	  command -v $$c >/dev/null 2>&1 && echo "  $$c  ->  $$($$c -V 2>&1)"; \
	done; true

guard-python:
	@$(PY) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null || { \
	  echo ""; \
	  echo "  ERROR  $(PY) is $$($(PY) -V 2>&1), but this project needs Python 3.10 or newer."; \
	  echo "         (NumPy 1.26+ and SciPy 1.11+ do not build for older versions — that is why"; \
	  echo "          pip offered you nothing past numpy 1.24.4.)"; \
	  echo ""; \
	  echo "  Fixes, best first:"; \
	  echo "    conda activate <an env with 3.10+>   then re-run make"; \
	  echo "    make setup PY=python3.11             point make at a specific interpreter"; \
	  echo "    brew install python@3.12             if you have none"; \
	  echo ""; \
	  echo "  Interpreters on your PATH:"; \
	  for c in python3.13 python3.12 python3.11 python3.10 python3 python; do \
	    command -v $$c >/dev/null 2>&1 && echo "    $$c  ->  $$($$c -V 2>&1)"; \
	  done; \
	  echo ""; \
	  exit 1; }

setup: setup-py setup-r

doctor-r:
	@if command -v Rscript >/dev/null 2>&1; then \
	  echo "Rscript : $$(command -v Rscript)"; \
	  Rscript -e 'lib <- Sys.getenv("R_LIBS_USER"); if (!nzchar(lib)) lib <- file.path(path.expand("~"), "R", "modelers-bench-library"); dir.create(lib, recursive=TRUE, showWarnings=FALSE); .libPaths(c(lib, .libPaths())); p <- c("deSolve","dplyr","ggplot2","MASS","knitr","rmarkdown"); cat("version :", R.version.string, "\n\nlibrary paths R will search:\n"); for (l in .libPaths()) cat("  ", l, if (file.access(l, 2) == 0) "  (writable)" else "  (NOT writable)", "\n"); cat("\npackages:\n"); for (q in p) { f <- find.package(q, quiet=TRUE); cat("  ", formatC(q, width=-10), if (length(f)) paste("found at", f[1]) else "MISSING", "\n") }'; \
	else echo "Rscript : MISSING — no R found — install it with: brew install --cask r     (or skip the R notebooks: make render-py)"; fi


setup-py: guard-python
	$(PY) -m pip install -r requirements.txt

setup-r:
	@if command -v Rscript >/dev/null 2>&1; then \
	  Rscript -e 'lib <- Sys.getenv("R_LIBS_USER"); if (!nzchar(lib)) lib <- file.path(path.expand("~"), "R", "modelers-bench-library"); dir.create(lib, recursive=TRUE, showWarnings=FALSE); .libPaths(c(lib, .libPaths())); p <- c("deSolve","dplyr","ggplot2","MASS","knitr","rmarkdown"); cat("R          :", R.version.string, "\n"); cat("library    :", lib, "\n"); m <- p[!p %in% rownames(installed.packages())]; if (length(m)) { cat("installing :", paste(m, collapse=", "), "\n"); install.packages(m, lib=lib, repos="https://cloud.r-project.org") } else cat("status     : all six already present\n"); still <- p[!p %in% rownames(installed.packages())]; if (length(still)) { cat("\n  STILL MISSING after install:", paste(still, collapse=", "), "\n  scroll up for the download or compiler error.\n\n"); quit(status=1) } else cat("status     : OK, all six installed and visible\n")'; \
	else echo "no R found — install it with: brew install --cask r     (or skip the R notebooks: make render-py)"; fi

data: guard-python
	$(PY) cases/case-sm/generate.py
	$(PY) cases/case-sm/make_messy.py

verify: guard-python
	$(PY) scripts/verify_case.py

battery: guard-python
	$(PY) scripts/check_data.py

check-resources: guard-python
	@$(PY) scripts/check_resources.py

check: data verify battery check-resources

guard-r:
	@command -v Rscript >/dev/null 2>&1 || { \
	  echo ""; echo "  ERROR  R is not installed, and the R notebooks need it."; \
	  echo "         brew install --cask r    then    make setup-r"; \
	  echo "         or skip them entirely:   make render-py"; echo ""; exit 1; }
	@Rscript -e 'lib <- Sys.getenv("R_LIBS_USER"); if (!nzchar(lib)) lib <- file.path(path.expand("~"), "R", "modelers-bench-library"); dir.create(lib, recursive=TRUE, showWarnings=FALSE); .libPaths(c(lib, .libPaths())); p <- c("deSolve","dplyr","ggplot2","MASS","knitr","rmarkdown"); m <- p[!p %in% rownames(installed.packages())]; if (length(m)) { cat("\n  ERROR  missing R packages:", paste(m, collapse=", "), "\n         searched:", paste(.libPaths(), collapse=" , "), "\n         run:  make setup-r      or skip them:  make render-py\n\n"); quit(status=1) }; cat("guard-r    : all six R packages found\n")'

render: guard-r
	quarto render

render-py:
	QUARTO_PROFILE=nor quarto render

preview:
	quarto preview

# Serve whatever is already built in _site/ — no Quarto needed, and unlike
# opening index.html directly this makes full-text search work.
PORT ?= 8000
serve:
	@test -d _site || { echo ""; echo "  _site/ does not exist yet."; \
	  echo "  Build it first:  make render     (or make render-py without R)"; \
	  echo "  Or unzip a preview build into this folder."; echo ""; exit 1; }
	@echo "serving _site on http://localhost:$(PORT)   (ctrl-C to stop)"
	@$(PY) -m http.server $(PORT) --directory _site

all: check render

clean:
	rm -rf _site .quarto _freeze

distclean: clean
	rm -f cases/case-sm/data/*.csv
