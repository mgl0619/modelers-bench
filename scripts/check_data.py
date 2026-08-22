#!/usr/bin/env python3
"""
The S0-03 data-check battery, as a standalone script.

Runs the same eleven checks the lesson builds, against both the clean
dataset (which must be silent) and the corrupted copy (which must produce
exactly the defects listed in the manifest).

    python scripts/check_data.py                 # both datasets
    python scripts/check_data.py path/to.csv     # any dataset

Exit code 0 if the clean dataset is silent and the corrupted copy matches
its manifest, 1 otherwise.
"""

import sys

import numpy as np
import pandas as pd

LLOQ = 1.0
CLEAN = "cases/case-sm/data/ozanib_pk.csv"
MESSY = "cases/case-sm/data/ozanib_pk_messy.csv"
MANIFEST = "cases/case-sm/data/ozanib_pk_messy_manifest.csv"


def run_battery(path):
    """Return a list of (code, message, ids) findings."""
    raw = pd.read_csv(path, dtype={"ID": str})
    findings = []

    def flag(code, msg, ids=()):
        findings.append((code, msg, sorted(set(map(str, ids)))))

    # C01 identifier format
    bad = [i for i in raw.ID.unique() if str(i) != str(int(float(i)))]
    if bad:
        flag("ID_FORMAT", f"{len(bad)} ID(s) not in canonical numeric form", bad)

    # C02 duplicate event keys
    d = raw[raw.duplicated(["ID", "TIME", "EVID", "CMT"], keep=False)]
    if len(d):
        flag("DUP_RECORDS", f"{len(d)} rows share an (ID, TIME, EVID, CMT) key", d.ID.unique())

    # C03 negative time
    d = raw[raw.TIME < 0]
    if len(d):
        flag("NEGATIVE_TIME", f"{len(d)} record(s) with TIME < 0", d.ID.unique())

    # C04 dose must sort before an observation at the same time
    bad = [i for i, g in raw.groupby("ID", sort=False)
           for _, gt in g.groupby("TIME")
           if len(gt) > 1 and gt.EVID.iloc[0] == 0 and (gt.EVID == 1).any()]
    if bad:
        flag("DOSE_ORDER", "observation sorts before the dose at the same TIME", bad)

    # C05 regular dosing intervals
    bad = []
    for i, g in raw.groupby("ID", sort=False):
        dt = np.sort(g.loc[g.EVID == 1, "TIME"].values)
        if len(dt) == 0:
            bad.append(i)
            continue
        gaps = np.diff(dt)
        if len(gaps) and (np.abs(gaps - np.median(gaps)) > 1e-6).any():
            bad.append(i)
    if bad:
        flag("MISSING_DOSE", "irregular gap in the dosing sequence", bad)

    # C06 zero used to mean missing
    d = raw[(raw.EVID == 0) & (raw.DV == 0)]
    if len(d):
        flag("ZERO_MEANS_MISSING", f"{len(d)} observation(s) with DV exactly 0", d.ID.unique())

    # C07 BLQ consistency
    d = raw[(raw.EVID == 0) & raw.DV.notna() & (raw.DV < LLOQ) & (raw.BLQ == 0)]
    if len(d):
        flag("BLQ_IMPUTED", f"{len(d)} value(s) below LLOQ not flagged BLQ", d.ID.unique())

    # C08 unit switch, judged within subject
    o = raw[(raw.EVID == 0) & raw.DV.notna() & (raw.TIME > 0)]
    bad = []
    for i, g in o.groupby("ID", sort=False):
        early, late = g[g.TIME < 240].DV, g[g.TIME >= 240].DV
        if len(early) > 2 and len(late) > 0 and late.median() < early.median() / 100:
            bad.append(i)
    if bad:
        flag("UNIT_SWITCH", "late concentrations >100x lower than early ones", bad)

    # C09 covariate plausibility
    d = raw[(raw.WT < 35) | (raw.WT > 250)]
    if len(d):
        flag("IMPOSSIBLE_COVARIATE", "body weight outside 35-250 kg", d.ID.unique())

    # C10 baseline covariates constant within subject
    bad_cols = [c for c in ["AGE", "SEX", "WT", "DOSE"] if raw.groupby("ID")[c].nunique().max() > 1]
    if bad_cols:
        ids = set()
        for c in bad_cols:
            n = raw.groupby("ID")[c].nunique()
            ids |= set(n[n > 1].index)
        flag("TIME_VARYING_BASELINE", f"baseline covariate(s) vary within subject: {bad_cols}", ids)

    # C11 dose magnitude
    d = raw[(raw.EVID == 1) & ((raw.AMT < 1) | (raw.AMT > 1000))]
    if len(d):
        flag("DOSE_UNIT", "AMT outside a plausible 1-1000 mg range", d.ID.unique())

    return findings


def report(path, findings):
    print(f"\n{path}")
    if not findings:
        print("  no findings")
        return
    for code, msg, ids in findings:
        shown = ",".join(ids[:6]) + ("..." if len(ids) > 6 else "")
        print(f"  {code:22s} {msg:55s} -> ID {shown}")


def main(argv):
    if len(argv) > 1:
        for path in argv[1:]:
            report(path, run_battery(path))
        return 0

    rc = 0

    clean = run_battery(CLEAN)
    report(CLEAN, clean)
    if clean:
        print(f"  ERROR: the clean dataset should produce no findings, got {len(clean)}")
        rc = 1

    messy = run_battery(MESSY)
    report(MESSY, messy)
    injected = set(pd.read_csv(MANIFEST).code)
    found = {c for c, _, _ in messy}
    missed, spurious = sorted(injected - found), sorted(found - injected)
    print(f"\n  injected {len(injected)} | detected {len(found & injected)}"
          f" | missed {missed or 'none'} | spurious {spurious or 'none'}")
    if missed or spurious:
        rc = 1

    print("\nOK" if rc == 0 else "\nFAILED")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
