"""
CASE-SM "Ozanib" — synthetic population PK dataset.

Ozanib is a FICTIONAL oral small molecule invented for teaching. It is a
CYP3A4 substrate with a clinically meaningful drug-drug interaction, which
makes it useful from data assembly (S0) through DDI prediction (S3).

Everything a learner needs to grade their own answer is in truth.yml.
This script is the definition of truth: if you change it, regenerate the
data and bump the version in truth.yml.

Structural model
----------------
Two-compartment, first-order absorption, first-order elimination.

    dA_gut/dt = -ka * A_gut
    dA_c/dt   =  ka * A_gut - (CL/Vc) * A_c - (Q/Vc) * A_c + (Q/Vp) * A_p
    dA_p/dt   =  (Q/Vc) * A_c - (Q/Vp) * A_p
    C         =  A_c / Vc

All disposition parameters are apparent (X/F); bioavailability is not
identifiable from oral-only data. This is deliberate — it is a teaching
point in s0-01 and s0-02.

Usage
-----
    python cases/case-sm/generate.py
"""

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

SEED = 20260821
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------- truth ----
TRUTH = {
    # typical values at the reference covariate values
    "TVCL": 12.0,    # L/h    apparent clearance, 70 kg, no inhibitor
    "TVVC": 60.0,    # L      apparent central volume, 70 kg
    "TVQ": 8.0,      # L/h    apparent intercompartmental clearance
    "TVVP": 90.0,    # L      apparent peripheral volume
    "TVKA": 1.2,     # 1/h    absorption rate constant
    # covariate effects
    "WT_REF": 70.0,          # kg
    "ALLO_CL": 0.75,         # allometric exponent on CL and Q
    "ALLO_V": 1.00,          # allometric exponent on Vc and Vp
    "DDI_CL_RATIO": 0.45,    # CL multiplier with a strong CYP3A4 inhibitor
    # between-subject variability, on the log scale (approx CV for small omega)
    "OM_CL": 0.30,
    "OM_VC": 0.25,
    "OM_KA": 0.45,
    "CORR_CL_VC": 0.5,       # correlation between eta_CL and eta_Vc
    # residual unexplained variability
    "PROP_ERR": 0.20,        # proportional, CV
    "ADD_ERR": 0.5,          # additive, ng/mL
    "LLOQ": 1.0,             # ng/mL
    # compound properties (used in the units lesson)
    "MW": 465.0,             # g/mol
    "FU_PLASMA": 0.08,
}

N_SUBJECTS = 60
DOSES_MG = [25, 50, 100]           # 20 subjects per dose group
RICH_TIMES = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 24.0]
RICH_DAYS = [1, 14]                 # rich profiles on day 1 and day 14
TROUGH_DAYS = [7, 10, 21]           # single pre-dose sample
N_DOSES = 21                        # 21 once-daily doses
TAU = 24.0


def two_cmt_oral(t_eval, dose_mg, ka, cl, vc, q, vp, n_doses=N_DOSES, tau=TAU):
    """Concentrations (ng/mL) at t_eval hours after the first dose."""
    dose_ug = dose_mg * 1000.0          # mg -> ug, so that ug/L == ng/mL

    def rhs(t, y):
        a_gut, a_c, a_p = y
        return [
            -ka * a_gut,
            ka * a_gut - (cl / vc) * a_c - (q / vc) * a_c + (q / vp) * a_p,
            (q / vc) * a_c - (q / vp) * a_p,
        ]

    dose_times = np.arange(n_doses) * tau
    t_eval = np.asarray(t_eval, dtype=float)
    out = np.zeros_like(t_eval)
    y = np.zeros(3)
    t_now = 0.0

    # integrate segment by segment, adding a bolus to the gut at each dose time
    breaks = list(dose_times) + [max(t_eval.max(), dose_times[-1]) + tau]
    for i, t_dose in enumerate(dose_times):
        y[0] += dose_ug                                   # oral bolus into gut
        t_end = breaks[i + 1]
        mask = (t_eval >= t_dose) & (t_eval <= t_end)
        want = np.sort(t_eval[mask])
        sol = solve_ivp(
            rhs, (t_dose, t_end), y, t_eval=want if want.size else None,
            rtol=1e-9, atol=1e-12, method="LSODA", dense_output=True,
        )
        if want.size:
            idx = np.searchsorted(np.sort(t_eval), want)
            order = np.argsort(t_eval)
            out[order[idx]] = sol.y[1] / vc               # ug/L == ng/mL
        y = sol.sol(t_end)
        t_now = t_end
    return out


def make_covariates(n):
    wt = np.exp(rng.normal(np.log(75.0), 0.18, n)).round(1)         # kg
    age = np.clip(rng.normal(52, 13, n), 19, 84).round(0)           # years
    sex = rng.binomial(1, 0.46, n)                                   # 1 = female
    # females a little lighter, so the covariate structure is not orthogonal
    wt = np.where(sex == 1, wt * 0.88, wt).round(1)
    crcl = np.clip(rng.normal(98, 24, n), 32, 175).round(0)          # mL/min
    alt = np.clip(np.exp(rng.normal(np.log(24), 0.4, n)), 6, 180).round(0)
    ddi = rng.binomial(1, 0.25, n)                                   # strong 3A4 inhibitor
    return wt, age, sex, crcl, alt, ddi


def main():
    n = N_SUBJECTS
    wt, age, sex, crcl, alt, ddi = make_covariates(n)
    dose = np.repeat(DOSES_MG, n // len(DOSES_MG))
    rng.shuffle(dose)

    # correlated etas for CL and Vc, independent eta for ka
    r = TRUTH["CORR_CL_VC"]
    cov = np.array([[TRUTH["OM_CL"] ** 2, r * TRUTH["OM_CL"] * TRUTH["OM_VC"]],
                    [r * TRUTH["OM_CL"] * TRUTH["OM_VC"], TRUTH["OM_VC"] ** 2]])
    eta_cl_vc = rng.multivariate_normal([0, 0], cov, n)
    eta_cl, eta_vc = eta_cl_vc[:, 0], eta_cl_vc[:, 1]
    eta_ka = rng.normal(0, TRUTH["OM_KA"], n)

    wt_cl = (wt / TRUTH["WT_REF"]) ** TRUTH["ALLO_CL"]
    wt_v = (wt / TRUTH["WT_REF"]) ** TRUTH["ALLO_V"]
    ddi_eff = np.where(ddi == 1, TRUTH["DDI_CL_RATIO"], 1.0)

    cl = TRUTH["TVCL"] * wt_cl * ddi_eff * np.exp(eta_cl)
    vc = TRUTH["TVVC"] * wt_v * np.exp(eta_vc)
    q = TRUTH["TVQ"] * wt_cl
    vp = TRUTH["TVVP"] * wt_v
    ka = TRUTH["TVKA"] * np.exp(eta_ka)

    rows = []
    for i in range(n):
        times = []
        for d in RICH_DAYS:
            t0 = (d - 1) * TAU
            times += [t0 + t for t in RICH_TIMES]
        for d in TROUGH_DAYS:
            times.append((d - 1) * TAU)                   # pre-dose trough
        times = sorted(set(times))

        ipred = two_cmt_oral(times, dose[i], ka[i], cl[i], vc[i], q[i], vp[i])
        eps_p = rng.normal(0, TRUTH["PROP_ERR"], len(times))
        eps_a = rng.normal(0, TRUTH["ADD_ERR"], len(times))
        dv = ipred * (1 + eps_p) + eps_a
        dv = np.maximum(dv, 0.0)

        for t, ip, obs in zip(times, ipred, dv):
            rows.append(dict(
                ID=i + 1, TIME=round(t, 2), NTIME=round(t % TAU, 2),
                DAY=int(t // TAU) + 1,
                AMT=np.nan, DV=obs, IPRED_TRUE=ip,
                DOSE=dose[i], WT=wt[i], AGE=int(age[i]), SEX=int(sex[i]),
                CRCL=int(crcl[i]), ALT=int(alt[i]), DDI=int(ddi[i]),
            ))
        for k in range(N_DOSES):
            rows.append(dict(
                ID=i + 1, TIME=round(k * TAU, 2), NTIME=0.0, DAY=k + 1,
                AMT=float(dose[i]), DV=np.nan, IPRED_TRUE=np.nan,
                DOSE=dose[i], WT=wt[i], AGE=int(age[i]), SEX=int(sex[i]),
                CRCL=int(crcl[i]), ALT=int(alt[i]), DDI=int(ddi[i]),
            ))

    df = pd.DataFrame(rows)
    df["EVID"] = np.where(df["AMT"].notna(), 1, 0)
    df["MDV"] = np.where(df["DV"].isna(), 1, 0)
    df["CMT"] = np.where(df["EVID"] == 1, 1, 2)
    df["BLQ"] = np.where((df["EVID"] == 0) & (df["DV"] < TRUTH["LLOQ"]), 1, 0)
    df.loc[df["BLQ"] == 1, "DV"] = np.nan
    df.loc[df["BLQ"] == 1, "MDV"] = 1
    # dose record sorts before the observation at the same time
    df = df.sort_values(["ID", "TIME", "EVID"], ascending=[True, True, False])
    df = df.reset_index(drop=True)

    cols = ["ID", "TIME", "NTIME", "DAY", "AMT", "DV", "EVID", "MDV", "CMT",
            "BLQ", "DOSE", "WT", "AGE", "SEX", "CRCL", "ALT", "DDI",
            "IPRED_TRUE"]
    df[cols].to_csv("cases/case-sm/data/ozanib_pk.csv", index=False,
                    float_format="%.4f")

    ind = pd.DataFrame(dict(ID=np.arange(1, n + 1), CL=cl, VC=vc, Q=q, VP=vp,
                            KA=ka, WT=wt, DDI=ddi, DOSE=dose))
    ind.to_csv("cases/case-sm/data/ozanib_individual_truth.csv",
               index=False, float_format="%.5f")

    print(f"subjects            : {n}")
    print(f"rows                : {len(df)}")
    print(f"observation records : {(df.EVID == 0).sum()}")
    print(f"BLQ observations    : {df.BLQ.sum()} "
          f"({100 * df.BLQ.sum() / (df.EVID == 0).sum():.1f}% of samples)")
    print(f"dose groups         : {sorted(set(dose))} mg QD")
    print(f"subjects on a strong CYP3A4 inhibitor: {int(ddi.sum())}")
    print(f"median CL (L/h)     : {np.median(cl):.2f}  "
          f"[no DDI {np.median(cl[ddi == 0]):.2f}, DDI {np.median(cl[ddi == 1]):.2f}]")
    print(f"observed Cmax range (ng/mL): {df.DV.min():.2f} – {df.DV.max():.1f}")


if __name__ == "__main__":
    main()
