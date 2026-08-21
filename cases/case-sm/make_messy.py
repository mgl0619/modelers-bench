"""
Inject a known set of realistic data-assembly defects into the clean CASE-SM
dataset, so that S0-03 has something to find.

Every defect below has been seen in a real analysis dataset. The manifest is
written alongside the data, so a learner can grade their own checker.

    python cases/case-sm/make_messy.py
"""

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)

SRC = "cases/case-sm/data/ozanib_pk.csv"
OUT = "cases/case-sm/data/ozanib_pk_messy.csv"
MANIFEST = "cases/case-sm/data/ozanib_pk_messy_manifest.csv"

df = pd.read_csv(SRC)
df["ID"] = df["ID"].astype(object)
defects = []


def log(code, detail, ids):
    defects.append(dict(code=code, detail=detail, ids=";".join(map(str, ids))))


# 1. duplicated observation records ------------------------------------------
dupes = df[(df.EVID == 0) & (df.ID.isin([3, 3, 17]))].head(4)
df = pd.concat([df, dupes], ignore_index=True)
log("DUP_RECORDS", "4 observation rows duplicated exactly", sorted(set(dupes.ID)))

# 2. unit switch mid-study ----------------------------------------------------
mask = (df.ID.isin([11, 12, 13, 14])) & (df.EVID == 0) & (df.TIME >= 240) & df.DV.notna()
df.loc[mask, "DV"] = df.loc[mask, "DV"] / 1000.0
log("UNIT_SWITCH", "DV reported in ug/mL instead of ng/mL after t=240 h", [11, 12, 13, 14])

# 3. zero used to mean missing ------------------------------------------------
mask = (df.ID == 22) & (df.EVID == 0) & (df.DV.isna())
df.loc[mask, "DV"] = 0.0
log("ZERO_MEANS_MISSING", "missing DV recorded as 0 rather than NA", [22])

# 4. BLQ imputed as LLOQ/2 without a flag -------------------------------------
mask = (df.ID == 31) & (df.BLQ == 1)
df.loc[mask, "DV"] = 0.5
df.loc[mask, "BLQ"] = 0
log("BLQ_IMPUTED", "BLQ values silently replaced by LLOQ/2 and the flag cleared", [31])

# 5. missing dose record ------------------------------------------------------
drop = (df.ID == 8) & (df.EVID == 1) & (df.TIME == 96.0)
df = df[~drop]
log("MISSING_DOSE", "day-5 dose record absent while observations continue", [8])

# 6. impossible covariate value ----------------------------------------------
df.loc[df.ID == 44, "WT"] = 7.8          # decimal point error: 78.0 kg
log("IMPOSSIBLE_COVARIATE", "adult body weight recorded as 7.8 kg", [44])

# 7. non-unique / inconsistent covariate within a subject ---------------------
mask = (df.ID == 5) & (df.TIME > 200)
df.loc[mask, "AGE"] = df.loc[mask, "AGE"] + 1
log("TIME_VARYING_BASELINE", "baseline AGE changes mid-study within one subject", [5])

# 8. dose amount in the wrong unit --------------------------------------------
mask = (df.ID == 19) & (df.EVID == 1)
df.loc[mask, "AMT"] = df.loc[mask, "AMT"] * 1000.0
log("DOSE_UNIT", "AMT recorded in ug rather than mg", [19])

# 9. negative time ------------------------------------------------------------
mask = (df.ID == 27) & (df.EVID == 0) & (df.TIME == 0.5)
df.loc[mask, "TIME"] = -0.5
log("NEGATIVE_TIME", "screening sample given a negative time", [27])

# 10. dose sorted after the observation at the same time ----------------------
idx = df[(df.ID == 36) & (df.EVID == 1) & (df.TIME == 0.0)].index
df.loc[idx, "_order"] = 1
df["_order"] = df["_order"].fillna(0)
log("DOSE_ORDER", "dose record sorts after the observation at the same time", [36])

# 11. ID formatting drift ------------------------------------------------------
df.loc[df.ID == 50, "ID"] = "050"
log("ID_FORMAT", "one subject's ID zero-padded to a string", [50])

df = (df.sort_values(["ID", "TIME", "_order"], kind="stable")
        .drop(columns="_order")
        .reset_index(drop=True))

df.to_csv(OUT, index=False, float_format="%.4f")
pd.DataFrame(defects).to_csv(MANIFEST, index=False)

print(f"wrote {OUT}  ({len(df)} rows)")
print(f"wrote {MANIFEST}  ({len(defects)} defects)")
for d in defects:
    print(f"  {d['code']:22s} {d['detail']}")
