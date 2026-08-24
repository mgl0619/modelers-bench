# Running locally

**Local is the primary build.** GitHub stores the repository and its history;
it does not need to run anything for the site to be correct. The Actions
workflow is manual-only — you trigger it from the Actions tab when you want an
independent check on a clean machine, and never by accident on a push.

## One-time setup (macOS)

```bash
# Quarto — required
brew install --cask quarto

# R — only needed for the R notebooks. The site builds without it.
brew install --cask r

cd ~/repo/modelers-bench
make doctor       # what is installed, what is missing
make setup        # install Python and R packages
```

### Python 3.10 or newer is required

`make` picks the newest suitable interpreter it can find on your PATH
(`python3.13`, `python3.12`, … then plain `python3`). If none of them is 3.10+
it stops with an explanation rather than a confusing pip error, and lists every
interpreter you have.

The failure this prevents looks like:

```
ERROR: Could not find a version that satisfies the requirement numpy>=1.26
       (from versions: 1.3.0, ... 1.24.4)
```

That version list ending at **1.24.4** is the tell: NumPy stopped supporting
Python 3.8 after 1.24.x, so pip is offering you everything that still builds for
your interpreter and nothing newer. The project needs 3.10+.

Three ways out, best first:

```bash
# 1. a conda environment (you have mambaforge)
mamba env create -f environment.yml
conda activate modelers-bench
make check

# 2. point make at an interpreter you already have
make setup PY=python3.11
make check PY=python3.11

# 3. install one
brew install python@3.12
```

`make doctor` now prints your interpreter's version, flags it if it is too old,
and lists every `python*` on your PATH so you can pick.

`make doctor` is the one to run first. It prints the version of every tool and
names exactly what is missing, so you are never guessing.

Python needs `numpy`, `pandas`, `scipy`, `matplotlib`, `pyyaml`, and the Jupyter
pieces Quarto uses to execute notebooks (`nbclient`, `jupyter-client`,
`ipykernel`). `make setup` installs all of them from `requirements.txt`. If you
work in conda environments, activate the one you want first — `make setup` uses
whichever `python3` is on your PATH, and `make doctor` will show you which that
is.

## The daily loop

```bash
make check        # regenerate the data and verify it        ~20 s
make preview      # live-reloading site at localhost:4200
```

`make check` is the fast one, and the one to run constantly. It regenerates
`CASE-SM`, verifies the model against its published truth, and runs the S0-03
check battery against both the clean and corrupted datasets. It touches no
notebooks and no rendering, so it stays quick.

`make preview` starts Quarto's live server: edit a `.qmd`, save, and the page
reloads. This is where lesson writing actually happens.

## Before you push

```bash
make all          # check + full render, every notebook executed
```

This is the same work the CI workflow does. If it passes locally, CI has nothing
to tell you — which is the point of running locally.

## All targets

| Target | What it does |
|---|---|
| `make doctor` | Report installed tools, Python version, and missing dependencies |
| `make setup` | Install Python and R packages |
| `make data` | Regenerate `CASE-SM`, clean and corrupted copies |
| `make verify` | 22 checks of the case against `truth.yml` |
| `make battery` | The S0-03 data-check battery on both datasets |
| `make check` | `data` + `verify` + `battery` — the fast loop |
| `make render` | Build into `_site/`, executing every notebook |
| `make render-py` | Build without R — Python notebooks only |
| `make preview` | Live-reloading preview |
| `make all` | `check` + `render` |
| `make clean` | Remove `_site/`, `.quarto/`, `_freeze/` |

## If you do not have R

`make render-py` uses the `nor` Quarto profile to skip the R notebooks, so the
site builds with Python alone. The R notebook links in the sidebar will 404 in
that build — expected, and the reason `make render` is what you publish.

## What the checks actually check

`make verify` deliberately does **not** compare the regenerated CSV byte for
byte against the committed one. A different NumPy or SciPy build can shift the
last decimal place, and a byte-diff would fail for reasons that have nothing to
do with correctness. Instead it checks the things that must hold:

- the analytic two-compartment solution agrees with direct ODE integration
  (currently to 2 × 10⁻¹¹)
- superposition gives AUC(τ,ss) = Dose/CL **exactly** — 4166.7 ng·h/mL at 50 mg
- the half-lives, t~max~ and accumulation ratio match `truth.yml`
- the dataset has the subjects, dose levels, dosing records and BLQ fraction it
  claims, with doses sorted before same-time observations
- the CYP3A4 effect is present at roughly the stated magnitude, and all four
  decoy covariates are still in the data

`make battery` then requires the clean dataset to produce **zero** findings and
the corrupted copy to produce **exactly** the eleven defects in its manifest —
no misses, no false positives. If you add a check to the battery, add its defect
to `make_messy.py` too, or the battery will report it as spurious.

## Adding a lesson

```bash
cp -r lessons/s0-01-compartments-and-odes lessons/s1-01-nca
# edit index.qmd, notebook-r.qmd, notebook-py.qmd, meta.yml
# add it to the sidebar in _quarto.yml
make check && make preview
```

`CONTRIBUTING.md` has the seven-slot template and what each slot owes the reader.

## Troubleshooting

**"Unable to locate an installed version of R"** — you are running `make render`
without R. Use `make render-py`, or install R.

**"No module named nbformat"** — Quarto cannot find the Jupyter machinery.
`make setup`, and check `make doctor` points at the Python you expect. In a
conda environment, activate it before running make.

**"Could not find a version that satisfies the requirement numpy>=1.26"** —
your Python is older than 3.10. See *Python 3.10 or newer is required* above.

**Quarto executes notebooks with the wrong Python** — Quarto finds its own
kernel, which is not always the interpreter `make` uses. Set it explicitly:
`export QUARTO_PYTHON=$(which python3.12)` before `make render`, or activate
the conda environment first so both agree.

**Port 4200 already in use** — a previous `make preview` is still running.
`quarto preview --port 4300`, or close the earlier one.

**A notebook shows stale output** — Quarto caches executions in `_freeze/`.
`make clean` clears it and forces a full re-execution.

**Fonts look wrong offline** — the theme pulls Spectral and IBM Plex from Google
Fonts. Without a connection the page falls back to Georgia and the system sans;
the layout is unaffected.
