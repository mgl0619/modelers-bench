# The Modeler's Bench

**An open, reproducible curriculum for quantitative pharmacology.**
One drug, many models — every result runnable, every case gradeable against
published truth.

Learners rebuild the same set of development decisions about the same fictional
molecules, in the tools a sponsor would actually use, with data whose true
generating parameters are published. That last part is the point: no course
built on real data can tell you how far your estimate landed from the answer.

## Status

| Strand | Lessons | Status |
|---|---|---|
| **S0 · Foundations** | 7 | complete |
| S1 · PK/PD core | 8 | planned |
| S2 · Population PK/PD | 9 | planned |
| S3 · PBPK | 8 | planned |
| S4 · QSP and systems | 8 | planned |
| S5 · Statistics, Bayes and ML | 8 | planned |
| S6 · Decisions and MIDD | 8 | planned |
| S7 · Practice and craft | 7 | planned |

## Quick start

```bash
make doctor       # what is installed, what is missing
make setup        # install Python and R packages
make check        # regenerate and verify the case data   (~20 s)
make preview      # live-reloading site at localhost:4200
```

**The build is local.** `make all` runs everything CI would; the GitHub Actions
workflow is manual-only, triggered from the Actions tab when you want an
independent check on a clean machine. See [LOCAL.md](LOCAL.md) for setup,
every target, and troubleshooting.

Runnable lessons ship in **both R and Python**. Pick one; the other is there
when you need it. No R? `make render-py` builds the site without it.

### Requirements

- **Quarto** ≥ 1.4 — `brew install --cask quarto`
- **Python** ≥ 3.10 with the packages in `requirements.txt`. If your system
  `python3` is older, `mamba env create -f environment.yml` gives you a working
  one; `make` will tell you plainly if the interpreter it finds is too old.
- **R** ≥ 4.2 with `deSolve`, `dplyr`, `ggplot2`, `MASS` — only for the R notebooks

## How a lesson is built

Seven slots, every time. See `CONTRIBUTING.md` for the template.

1. **The decision it serves** — one sentence naming a real development decision.
2. **Concept** — 800–1,200 words.
3. **Runnable notebook** — open tools, case data, executed in CI.
4. **Rosetta panel** — the same thing in a second language or engine.
5. **Failure mode** — broken on purpose, with the diagnostic that catches it.
6. **Self-check** — three questions with folded answers.
7. **Discussion and citations.**

## Layout

```
.
├── _quarto.yml            site config and navigation
├── index.qmd              front page
├── cases.qmd  about.qmd
├── assets/theme.scss      the visual system
├── paths/                 PATH-A / B / C — orderings, not content
├── lessons/
│   └── s0-01-compartments-and-odes/
│       ├── index.qmd      slots 1, 2, 4, 5, 6, 7
│       ├── notebook-r.qmd slot 3 (R)
│       ├── notebook-py.qmd slot 3 (Python)
│       └── meta.yml       strand, paths, prereqs, reviewed date
├── cases/case-sm/         generator, truth, data
├── scripts/
│   ├── verify_case.py     22 checks of the case against truth.yml
│   └── check_data.py      the S0-03 battery, as a standalone script
├── Makefile               the local build
└── .github/workflows/     manual build, monthly staleness check
```

`meta.yml` carries a `reviewed:` date. A scheduled CI job opens an issue for any
lesson older than 18 months — that is the whole content-decay strategy.

## Licence

Content **CC BY-SA 4.0**. Code and data-generation scripts **MIT**.

## Disclaimer

Educational material. The compounds are fictional, the models illustrative.
Nothing here is clinical guidance or a regulatory position.
