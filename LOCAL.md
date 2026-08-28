# Running locally

**Local is the primary build.** GitHub stores the repository and its history;
it does not need to run anything for the site to be correct. The Actions
workflow is manual-only — you trigger it from the Actions tab when you want an
independent check on a clean machine, and never by accident on a push.

## One-time setup (macOS)

```bash
# Quarto — required
brew install --cask quarto

# uv — the Python installer this project prefers
brew install uv

# R — only needed for the R notebooks. The site builds without it.
brew install --cask r

cd ~/repo/modelers-bench
make doctor       # what is installed, what is missing, and which python make chose
make setup        # install Python and R packages
```

### Python packages, via uv

`make setup-py` uses **uv** when it is on your PATH, and falls back to `pip`
when it is not. With no environment activated it creates `./.venv` and installs
there; with a venv or conda environment already activated it installs into that
instead.

```bash
make setup-py
source .venv/bin/activate      # do this before building
make all
```

`requirements.txt` stays the single source of dependency truth — uv reads it
through `uv pip`, so there is no second manifest to drift. `environment.yml` is
the one other copy, for the conda route.

**Activate the environment before `make render`.** `make` will find `./.venv` on
its own, but `quarto render` will not: it looks for `ipykernel` on your PATH,
and an unactivated venv fails at the first notebook rather than at the start.

Two failures uv avoids, both real:

- `error: externally-managed-environment` — a Homebrew interpreter refusing
  `pip install` under PEP 668. `uv venv` sidesteps it.
- A half-installed `./.venv` left behind by a failed run. `make setup-py` now
  fails loudly and tells you to remove it, because `make` **prefers** `./.venv`
  over anything on PATH — an incomplete one is worse than none.

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

## Publishing: the site is held on GitHub Pages

`main` publishes to <https://mgl0619.github.io/modelers-bench> through
`.github/workflows/publish.yml` on every push.

**`_freeze/` is committed on purpose.** Notebooks execute on your machine, you
look at the output, and the frozen result is what publishes. The publish
workflow therefore installs no R and no Jupyter kernel — it renders in about a
minute. The cost is one habit:

```bash
make all                                    # executes and refreshes _freeze/
git add _freeze && git commit -m "Refresh notebook freeze"
```

If you edit a notebook and forget, the published page shows output that no
longer matches its own code, and nothing in the publish path notices. That is
what `build.yml` is for: run it from the Actions tab and it renders with
`--execute`, ignoring the freeze entirely and running every cell from source on
a clean machine. If it agrees with what is published, the freeze is honest.

### The freeze trap, and why resources.qmd opts out

`freeze: auto` decides whether to re-execute by hashing the **`.qmd` source**.
It knows nothing about data files that source reads.

`resources.qmd` is generated from `resources.csv`. Adding twelve rows to the CSV
left the `.qmd` untouched, so the hash matched, so Quarto reused frozen output
built from the old data — a page showing 237 cards against 249 rows, rendered
successfully, looking entirely normal. `resources.qmd` now sets
`execute: freeze: false`; executing it is cheap and freezing it was never right.

The post-render `check-resources` pass is the backstop that caught it. If you
add another page generated from a data file, set `freeze: false` on it too.

### Repository setup

`publish.yml` calls `actions/configure-pages` with `enablement: true`, so it
switches Pages on by itself. No manual toggle is normally needed.

If the first deployment fails, that step is where to look. The two causes:

- **Pages source was set to a branch.** `configure-pages` corrects this.
- **The repository is private on GitHub Free.** Pages needs a public repository
  on Free, or Pro/Team/Enterprise for a private one. No workflow can work around
  this — make the repository public, or upgrade the plan.

The first version of this workflow relied on the manual toggle and had no
`configure-pages` step, so a missing setting surfaced only at the very end, as
`Get Pages site failed` after a full render. Failing at the top of the log is
worth the extra step.

### If you activated an environment and `make` ignored it

This one cost a build. `make` used to pick the newest `python3.N` on your PATH
and nothing else — so a Homebrew **python3.13** beat an *activated* conda
environment holding 3.12 and every package. Activating changed nothing, and the
error was byte-identical each time:

```
python3.13 cases/case-sm/generate.py
ModuleNotFoundError: No module named 'numpy'
```

`make` now honours an active environment first. The order is:

1. `PY=...` on the command line — explicit always wins
2. an activated venv (`$VIRTUAL_ENV`)
3. an activated conda environment (`$CONDA_PREFIX`)
4. `./.venv`
5. the newest `python3.N` on PATH that is 3.10+

`make doctor` prints which one was chosen **and why**, which is the fastest way
to tell "the packages are missing" from "make is looking at the wrong python".
The two produce the same `ModuleNotFoundError` and have different fixes.

`guard-python` also checks that numpy, pandas, scipy, matplotlib and yaml are
importable, so a bare-but-modern interpreter now stops with a named list and a
pointer to `make setup-py` instead of a traceback from inside `generate.py`.

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
| `make setup-py` | Just the Python packages |
| `make setup-r` | Just the R packages |
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

## One working copy

This repository is the only copy. Edit files here, run `make check` here, commit
here.

That sounds too obvious to write down, and it is the rule this project has
already broken once. `scripts/check_resources.py` was extended in place with a
site-link audit; a separate copy of the same file, made earlier elsewhere and
edited in parallel, was later copied back over it. The audit disappeared
silently — the script still ran, still printed `OK`, and simply stopped checking
one of the two things it existed to check. It was noticed by chance.

The failure mode is worth naming because it is not a merge conflict. Git never
saw the second copy, so nothing warned anybody. Two files diverged outside
version control and the older one won.

So: no scratch copies of tracked files outside this working tree. If you need to
generate a tracked file from a script, put the script in `scripts/` and commit
it, so the generation is reproducible and the output has one lineage. If you
edit a tracked file anywhere other than here, treat it as untrusted and diff it
before it comes back.

`make check` is the backstop. It validates `resources.csv` against its schema and
audits every external link on the site, and it is cheap enough to run before
every commit.

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

**"there is no package called 'deSolve'"** — R is installed but its packages are
not. `make setup-r`. This happens when an earlier `make setup` failed at the
Python step and never reached the R one, which is why the two are now separate
targets. `make render` checks for all six packages up front and names the
missing ones rather than failing halfway through a render.

**"No module named nbformat"** — Quarto cannot find the Jupyter machinery.
`make setup`, and check `make doctor` points at the Python you expect. In a
conda environment, activate it before running make.

**"Could not find a version that satisfies the requirement numpy>=1.26"** —
your Python is older than 3.10. See *Python 3.10 or newer is required* above.

**Quarto executes notebooks with the wrong Python** — Quarto finds its own
kernel, which is not always the interpreter `make` uses. The symptom is a
traceback whose path points somewhere you did not expect, e.g.
`~/mambaforge/lib/python3.8/site-packages/numpy`. Fix it by making the
environment active before you render:

```bash
conda activate modelers-bench
python -m ipykernel install --user --name modelers-bench   # once
export QUARTO_PYTHON=$(which python)                       # belt and braces
make render
```

**`AttributeError: module 'numpy' has no attribute 'trapezoid'`** — you are on
NumPy 1.x, where the function is called `trapz`; NumPy 2.0 renamed it. The
notebooks and scripts bind whichever exists:

```python
trapz = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
```

Note the `hasattr` rather than `getattr(np, "trapezoid", np.trapz)` — the
`getattr` form evaluates its default eagerly and so raises on NumPy 2, where
`np.trapz` no longer exists. If you write similar shims, use the `hasattr`
form. The deeper fix is still to render from an environment with a current
NumPy.

**Port 4200 already in use** — a previous `make preview` is still running.
`quarto preview --port 4300`, or close the earlier one.

**A notebook shows stale output** — Quarto caches executions in `_freeze/`.
`make clean` clears it and forces a full re-execution.

**Fonts look wrong offline** — the theme pulls Spectral and IBM Plex from Google
Fonts. Without a connection the page falls back to Georgia and the system sans;
the layout is unaffected.
