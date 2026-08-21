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
# generate the case data (Python 3.10+, numpy/pandas/scipy)
python cases/case-sm/generate.py
python cases/case-sm/make_messy.py

# build the site
quarto preview
```

Runnable lessons ship in **both R and Python**. Pick one; the other is there
when you need it.

### Requirements

- **Quarto** ≥ 1.4
- **Python** ≥ 3.10 with `numpy`, `pandas`, `scipy`, `matplotlib` (`requirements.txt`)
- **R** ≥ 4.2 with `deSolve`, `dplyr`, `ggplot2` — only if you run the R notebooks

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
└── .github/workflows/     build, execute, staleness
```

`meta.yml` carries a `reviewed:` date. A scheduled CI job opens an issue for any
lesson older than 18 months — that is the whole content-decay strategy.

## Licence

Content **CC BY-SA 4.0**. Code and data-generation scripts **MIT**.

## Disclaimer

Educational material. The compounds are fictional, the models illustrative.
Nothing here is clinical guidance or a regulatory position.
