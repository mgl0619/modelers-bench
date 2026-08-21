# CASE-SM — "Ozanib"

A **fictional** oral small molecule, invented for teaching. CYP3A4 substrate,
once daily, 21 days, three dose levels.

Nothing in this directory derives from a real programme, a company dataset, or
any patient. The generating model is published in `truth.yml`, so every exercise
built on this case can be graded against the answer.

| File | What it is |
|---|---|
| `generate.py` | Canonical generator. Run it to rebuild the data. |
| `generate.R` | The same model in R. Different RNG stream, so different rows. |
| `truth.yml` | Every true parameter, including the covariates that do **nothing**. |
| `data/ozanib_pk.csv` | The dataset learners work with. |
| `data/ozanib_individual_truth.csv` | Per-subject true CL, Vc, Q, Vp, ka. |

## Don't peek too early

`ozanib_individual_truth.csv` and the `IPRED_TRUE` column are the answer key.
Fit first, then compare. Half the value of this case is finding out how far a
reasonable analysis lands from the truth.

## Deliberate traps

- **CRCL, AGE, SEX and ALT have no true effect.** They are in the dataset so
  that covariate-selection lessons have genuine false positives to catch. Please
  do not "fix" this.
- **Everything is apparent (X/F).** There is no IV arm, so bioavailability is
  not identifiable. A learner who reports "clearance is 12 L/h" without the
  `/F` has made a real error, and the case is built to expose it.
- **4% of samples are below the limit of quantification**, set to `NA` with
  `BLQ = 1`. How you handle them changes the answer, which is the point.

## Regenerating

```bash
python cases/case-sm/generate.py
```

Bump `version` in `truth.yml` if you change the model, and say what changed.
