# The Modeler's Bench

**An open, reproducible curriculum for quantitative pharmacology.**
One drug, many models — every result runnable, every case gradeable against
published truth.

Learners rebuild the same set of development decisions in the tools a sponsor
would actually use. The material comes from two sources, and the difference
between them shapes everything else:

- **Synthetic cases**, on fictional molecules whose true generating parameters
  are published. No course built on real data can tell you how far your estimate
  landed from the answer; these can.
- **Real approval packages**, in strand `C`. FDA review documents are US
  government works in the public domain, so their numbers can be committed to
  this repository and re-analysed here. That is what makes a strand about real
  drugs possible without a licence problem — and it is the reason strand `C`
  looks different from the rest.

No real patient-level data appears anywhere in this repository, in either case.

**Live site: <https://mgl0619.github.io/modelers-bench>** — rebuilt from `main`
on every push.

## Status

Four kinds of strand, not one ladder. `P` assumes no pharmacology, `S` is the
methodological spine, `D` is where biology changes model structure, and `C`
reads the arguments regulators actually accepted.

| Strand | What it is | Written |
|---|---|---|
| **P · Pharmacology from the beginning** | for people arriving from statistics, maths, engineering or software | **5 of 18** |
| **S0 · Foundations** | the workflow, before any estimation | **7 of 7** — complete |
| S1 · PK/PD core | | 0 of 8 |
| S2 · Population PK/PD | | 0 of 9 |
| S3 · PBPK | | 0 of 8 |
| S4 · QSP and systems | | 0 of 8 |
| S5 · Statistics, Bayes and ML | | 0 of 8 |
| S6 · Decisions and MIDD | | 0 of 8 |
| S7 · Practice and craft | | 0 of 7 |
| **D · Disease areas** | one disease at a time; D1 is pancreatic cancer, outline and verified sources published | **0 of 12** |
| **C · Approved drugs** | clinical pharmacology read out of public-domain FDA reviews | **3 of 13** |

`make check` verifies this table against the `meta.yml` files on disk, so it
cannot quietly drift out of date. If you add a lesson, the count here is part of
the change.

## Quick start

```bash
make doctor       # what is installed, what is missing
make setup        # install Python and R packages (or setup-py / setup-r)
make check        # case data, resources, site links, FDA and RAG tools
make preview      # live-reloading site at localhost:4200
```

**The build is local.** `make all` runs everything CI would; the GitHub Actions
workflow `build.yml` is manual-only, triggered from the Actions tab when you want
an independent check on a clean machine — it renders with `--execute`, ignoring
the committed freeze, which is how you confirm the freeze still matches its own
source. `publish.yml` runs on every push to `main` and deploys the site to
GitHub Pages. See [LOCAL.md](LOCAL.md) for setup,
every target, and troubleshooting.

Runnable lessons ship in **both R and Python**. Pick one; the other is there
when you need it. No R? `make render-py` builds the site without it.

The notebooks are **not** in the site sidebar — a reader choosing what to study
next is choosing a lesson, not a language. Each lesson page links its own two
notebooks from the "Work through it" slot, and `make check` fails if a notebook
is ever left unreachable.

### Requirements

- **Quarto** ≥ 1.4 — `brew install --cask quarto`
- **Python** ≥ 3.10 with the packages in `requirements.txt`. If your system
  `python3` is older, `mamba env create -f environment.yml` gives you a working
  one; `make` will tell you plainly if the interpreter it finds is too old.
- **R** ≥ 4.2 with `deSolve`, `dplyr`, `ggplot2`, `MASS`, `knitr`, `rmarkdown`, `jsonlite` — only for the R notebooks

## How a lesson is built

Seven slots, every time. See `CONTRIBUTING.md` for the template.

1. **The decision it serves** — one sentence naming a real development decision.
2. **Concept** — 800–1,200 words.
3. **Runnable notebook** — open tools, case data, executed in CI.
4. **Rosetta panel** — the same thing in a second language or engine.
5. **Failure mode** — broken on purpose, with the diagnostic that catches it.
6. **Self-check** — three questions with folded answers.
7. **Going further** — where to read next, and what the lesson deliberately
   omitted.

## Layout

```
.
├── _quarto.yml            site config and navigation
├── index.qmd              front page
├── pharmacology.qmd       strand P index
├── diseases.qmd           strand D index — D1 pancreatic cancer
├── drugs.qmd              strand C index — the thirteen approval packages
├── reading.qmd            every paper, verified against PubMed
├── resources.qmd          generated from resources.csv, never frozen
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
├── data/                  committed inputs — pdac-drugs.csv, derived/
├── tests/fixtures/        synthetic openFDA responses, clearly labelled as such
├── scripts/
│   ├── verify_case.py     22 checks of the case against truth.yml
│   ├── check_data.py      the S0-03 battery, as a standalone script
│   ├── check_resources.py resources.csv schema, site links, orphaned
│   │                      notebooks, the README status table, rendered page
│   ├── check_freeze.py    which notebooks have no committed freeze
│   ├── fetch_fda.py       openFDA retrieval for strand C  (`make fda`)
│   └── rag.py             BM25 over the FDA corpus        (`make rag`)
├── references.bib  resources.csv     the two source-of-truth data files
├── Makefile               the local build
└── .github/workflows/     publish on push, manual build, staleness check
```

`meta.yml` carries a `reviewed:` date. A scheduled CI job opens an issue for any
lesson older than 18 months — that is the whole content-decay strategy.

## Licence

Content **CC BY-SA 4.0**. Code and data-generation scripts **MIT**.

## Disclaimer

Educational material. The compounds are fictional, the models illustrative.
Nothing here is clinical guidance or a regulatory position.
