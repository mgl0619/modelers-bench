#!/usr/bin/env python3
"""
Verify CASE-SM without comparing bytes.

Regenerating a CSV on a different machine can shift the last decimal place,
so a byte-for-byte diff is the wrong test — it fails for reasons that have
nothing to do with correctness. This checks the things that must actually
hold: the analytic solution agrees with the numerical one, superposition
gives AUC(tau,ss) = Dose/CL exactly, truth.yml's derived quantities match
what the model produces, and the shipped dataset has the shape it claims.

    python scripts/verify_case.py        # from the repository root

Exit code 0 if every check passes, 1 otherwise.
"""

import sys

import numpy as np
import pandas as pd
import yaml
from scipy.integrate import solve_ivp

# NumPy 2.0 renamed trapz -> trapezoid. Support both.
trapz = np.trapezoid if hasattr(np, "trapezoid") else np.trapz

ROOT = "cases/case-sm"
failures = []
checks = 0


def check(label, ok, detail=""):
    global checks
    checks += 1
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f"  {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def close(a, b, rtol):
    return abs(a - b) <= rtol * abs(b)


# ---------------------------------------------------------------- model ----
def hybrid(CL, Vc, Q, Vp):
    k10, k12, k21 = CL / Vc, Q / Vc, Q / Vp
    s = k10 + k12 + k21
    d = np.sqrt(s * s - 4 * k10 * k21)
    return (s + d) / 2, (s - d) / 2, k21


def conc_sd(t, dose_mg, ka, CL, Vc, Q, Vp):
    """Analytic two-compartment oral single dose, ng/mL."""
    t = np.asarray(t, float)
    a, b, k21 = hybrid(CL, Vc, Q, Vp)
    A = dose_mg * 1000.0 * ka / Vc
    return A * (((k21 - a) / ((ka - a) * (b - a))) * np.exp(-a * t)
                + ((k21 - b) / ((ka - b) * (a - b))) * np.exp(-b * t)
                + ((k21 - ka) / ((a - ka) * (b - ka))) * np.exp(-ka * t))


def conc_md(t, dose_mg, ka, CL, Vc, Q, Vp, n_doses=21, tau=24.0):
    t = np.asarray(t, float)
    out = np.zeros_like(t)
    for i in range(n_doses):
        dt = t - i * tau
        out += np.where(dt >= 0, conc_sd(np.maximum(dt, 0), dose_mg, ka, CL, Vc, Q, Vp), 0.0)
    return out


def ode_sd(t, dose_mg, ka, CL, Vc, Q, Vp):
    def rhs(_, y):
        ag, ac, ap = y
        return [-ka * ag,
                ka * ag - (CL / Vc) * ac - (Q / Vc) * ac + (Q / Vp) * ap,
                (Q / Vc) * ac - (Q / Vp) * ap]
    s = solve_ivp(rhs, (0, max(t)), [dose_mg * 1000.0, 0, 0], t_eval=t,
                  method="LSODA", rtol=1e-11, atol=1e-13)
    return s.y[1] / Vc


def main():
    truth = yaml.safe_load(open(f"{ROOT}/truth.yml"))
    tv = truth["typical_values"]
    P = dict(ka=tv["ka"]["value"], CL=tv["CL_F"]["value"], Vc=tv["Vc_F"]["value"],
             Q=tv["Q_F"]["value"], Vp=tv["Vp_F"]["value"])
    d = truth["derived_quantities"]

    print(f"CASE-SM {truth['name']} v{truth['version']}\n")

    # 1 -- the analytic solution agrees with direct integration
    print("Structural model")
    t = np.linspace(0.01, 72, 200)
    rel = np.max(np.abs(conc_sd(t, 50, **P) - ode_sd(t, 50, **P)) / ode_sd(t, 50, **P))
    check("analytic solution matches the ODE solver", rel < 1e-7, f"max rel err {rel:.1e}")

    # 2 -- hybrid rate constants match the published half-lives
    a, b, _ = hybrid(P["CL"], P["Vc"], P["Q"], P["Vp"])
    t_alpha, t_beta = np.log(2) / a, np.log(2) / b
    check("distribution half-life matches truth.yml", close(t_alpha, d["half_life_distribution_h"], 1e-3),
          f"{t_alpha:.2f} h vs {d['half_life_distribution_h']} h")
    check("terminal half-life matches truth.yml", close(t_beta, d["half_life_terminal_h"], 1e-3),
          f"{t_beta:.2f} h vs {d['half_life_terminal_h']} h")

    # 3 -- superposition: AUC(tau,ss) must equal Dose/CL exactly
    print("\nSuperposition")
    g_ss = np.linspace(480, 504, 24001)
    g_1 = np.linspace(0, 24, 24001)
    auc_ss = trapz(conc_md(g_ss, 50, **P), g_ss)
    auc_1 = trapz(conc_md(g_1, 50, **P), g_1)
    expected = 50 * 1000 / P["CL"]
    check("AUC(tau,ss) equals Dose/CL", close(auc_ss, expected, 1e-4),
          f"{auc_ss:.1f} vs {expected:.1f} ng*h/mL")
    check("AUC(tau,ss) matches truth.yml", close(auc_ss, d["auc_tau_ss_ng_h_per_mL_at_50mg"], 1e-3))
    check("accumulation ratio matches truth.yml", close(auc_ss / auc_1, d["accumulation_ratio_auc"], 5e-3),
          f"{auc_ss / auc_1:.3f} vs {d['accumulation_ratio_auc']}")

    fine = np.linspace(0, 24, 24001)
    c1 = conc_md(fine, 50, **P)
    check("tmax matches truth.yml", close(fine[c1.argmax()], d["tmax_h"], 0.05),
          f"{fine[c1.argmax()]:.2f} h vs {d['tmax_h']} h")

    # 4 -- the shipped dataset is what truth.yml describes
    print("\nShipped dataset")
    df = pd.read_csv(f"{ROOT}/data/ozanib_pk.csv")
    ind = pd.read_csv(f"{ROOT}/data/ozanib_individual_truth.csv")
    des = truth["design"]

    check("subject count", df.ID.nunique() == des["n_subjects"], f"{df.ID.nunique()}")
    check("dose levels", sorted(df.DOSE.unique()) == des["doses_mg"], f"{sorted(df.DOSE.unique())}")
    obs = df[df.EVID == 0]
    blq_frac = obs.BLQ.mean()
    check("BLQ fraction is small but non-zero", 0.005 < blq_frac < 0.15, f"{100*blq_frac:.1f}%")
    check("every BLQ observation has DV missing",
          df.loc[df.BLQ == 1, "DV"].isna().all())
    check("dose records sort before same-time observations",
          all(g.EVID.iloc[0] == 1 for _, g in df.groupby(["ID", "TIME"]) if (g.EVID == 1).any()))
    check("21 dose records per subject",
          (df[df.EVID == 1].groupby("ID").size() == 21).all())

    # 5 -- the covariate structure, including the decoys
    print("\nCovariate structure")
    cov = truth["covariate_model"]
    clean = ind[ind.DDI == 0]
    ratio = ind[ind.DDI == 1].CL.median() / (
        clean.CL.median() * (ind[ind.DDI == 1].WT.median() / clean.WT.median()) ** 0.75)
    check("CYP3A4 inhibitor lowers CL by roughly the stated factor",
          0.30 < ratio < 0.65,
          f"observed ~{ratio:.2f}, truth {cov['strong_cyp3a4_inhibitor']['multiplier']}")
    check("inhibitor prevalence near 25%", 0.10 < ind.DDI.mean() < 0.45, f"{100*ind.DDI.mean():.0f}%")

    # the decoys must be present in the data and absent from the model
    for c in cov["deliberately_absent"]:
        check(f"decoy covariate {c} present in the dataset", c in df.columns)

    # weight really does drive CL in the truth, with the stated exponent
    slope = np.polyfit(np.log(clean.WT / 70), np.log(clean.CL), 1)[0]
    check("weight-clearance relationship is positive and plausible", 0.4 < slope < 1.4,
          f"regressed exponent {slope:.2f} (true 0.75 — a wide window on purpose, see S0-02)")

    # 6 -- the corrupted copy and its manifest
    print("\nCorrupted copy")
    try:
        man = pd.read_csv(f"{ROOT}/data/ozanib_pk_messy_manifest.csv")
        messy = pd.read_csv(f"{ROOT}/data/ozanib_pk_messy.csv", dtype={"ID": str})
        check("manifest lists 11 defects", len(man) == 11, f"{len(man)}")
        check("corrupted copy differs from the clean one", len(messy) != len(df))
    except FileNotFoundError:
        check("corrupted copy exists (run make data)", False)

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("\nFAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
