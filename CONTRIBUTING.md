# Contributing

The most useful contribution is usually the least glamorous: telling us exactly
where you got stuck. Open an issue with the lesson, the paragraph, and what you
expected to happen.

## Ground rules

1. **No real clinical data, ever.** All cases are simulated from published
   generative models. A pull request containing patient-level data will be
   closed and the branch deleted.
2. **No proprietary software, licence keys, or vendor model files.** Reference
   them and link to their documentation; never redistribute.
3. **No papers.** Never commit a PDF, a scanned chapter, or a copied figure.
   Of the 96 works cited on the Reading page, 89 are all-rights-reserved and 6
   of the remaining 7 are Creative Commons **NC**/**ND**, which this project's
   CC BY-SA licence cannot absorb. Free to read on PubMed Central is a
   permission to read, not a licence to copy. Cite by DOI, add the entry to
   `references.bib`, and draw any figure yourself from the equations or the
   underlying data.

   The one exception is instructive: Liu 2017 in *Protein Cell*
   ([DOI](https://doi.org/10.1007/s13238-017-0408-4)) is plain **CC BY 4.0**, so
   its figures *could* be adapted here with attribution. One paper in
   ninety-six. Check the licence before assuming you are in that case — and
   note that the PubMed API reports licences incompletely, so a paper showing no
   licence may still carry one.
4. **Nothing traceable to a real programme.** No compound names, no internal
   methods, no unpublished parameter values.
5. **One working copy.** Edit tracked files in the repository, not in a copy
   made elsewhere. A file edited in two places outside git will diverge without
   any warning, and the older version can silently win — see *One working copy*
   in `LOCAL.md` for the time this happened and what it cost.
6. **Every runnable lesson must execute in CI.** A notebook that does not run is
   a build failure, not a footnote.

## Adding a lesson

Copy an existing lesson directory and fill the seven slots.

```
lessons/sX-NN-short-slug/
├── index.qmd        slots 1, 2, 4, 5, 6, 7
├── notebook-r.qmd   slot 3, R      (if runnable)
├── notebook-py.qmd  slot 3, Python (if runnable)
└── meta.yml
```

`meta.yml`:

```yaml
id: s0-01
strand: S0
title: Compartments and ODEs from first principles
paths: [PATH-A, PATH-B]
prereqs: [s0-00]
next: s0-02
runnable: true
notebooks: [notebook-r.qmd, notebook-py.qmd]
case: CASE-SM
reviewed: 2026-08-21
```

### The seven slots

| Slot | Requirement | Budget |
|---|---|---|
| 1 · The decision | One sentence naming a real development decision. **If you cannot write it, the lesson is not ready.** | 5 min |
| 2 · Concept | 800–1,200 words. One figure. No derivation for its own sake. | 60 min |
| 3 · Notebook | Runs top to bottom on case data with open tools. | 45 min |
| 4 · Rosetta | A second language or engine, in a `panel-tabset`. | 20 min |
| 5 · Failure mode | Break it on purpose; show the diagnostic. | 20 min |
| 6 · Self-check | Three questions in collapsed callouts, with real answers. | 10 min |
| 7 · Going further | Next lesson, what uses this, two or three references, a "seen in the wild" note. | 10 min |

Slots 1 and 5 are what experience buys and what nothing else supplies. If time
is short, protect those and let the prose be plainer.

## Style

- **Name the decision, not the technique.** "Which structural model can the data
  support" beats "an introduction to compartmental analysis".
- **Show the failure, do not describe it.** Run the broken thing.
- **Both languages, equal weight.** R and Python notebooks are peers.
- **State uncertainty honestly.** If a method usually fails on real data, say so.
- **No hedging filler.** Say the thing.

## Adding a case

Cases live in `cases/<case-id>/` and must ship:

- `generate.py` (canonical) and ideally `generate.R`
- `truth.yml` — every true parameter, **including covariates with no effect**
- `README.md` — what it is, its deliberate traps, how to regenerate
- Validation: check the generator against an independent implementation, and
  against an analytical solution where one exists. Say so in the README.

## Review

Pull requests need one reviewer. A reviewer checks: does the notebook run, does
slot 1 name a real decision, is the failure mode real, and is anything asserted
that has not been computed?
