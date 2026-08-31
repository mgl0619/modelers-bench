#!/usr/bin/env python3
"""Fetch openFDA material for the drugs that matter to this curriculum.

    make fda            index documents for every drug in data/pdac-drugs.csv
    make fda-test       run the parser against fixtures, no network

WHAT IT COLLECTS, and what it deliberately does not
---------------------------------------------------
Three openFDA endpoints, all free and unauthenticated:

  drug/drugsfda.json     application and submission metadata. Critically this
                         carries `application_docs`, giving the TYPE and URL of
                         every published document per submission -- letters,
                         labels and reviews. The PDFs are not bulk-downloadable,
                         but they are enumerable, which is the next best thing.

  drug/label.json        structured label text, including the pharmacokinetics
                         and clinical pharmacology sections.

  transparency/crl.json  Complete Response Letters. FDA began releasing these
                         for UNAPPROVED applications in September 2025; before
                         that, a rejection was not public at all. 458 letters at
                         the time of writing.

By default this writes an INDEX of documents -- one CSV row per document, with
its URL and the date it was seen -- and caches the raw JSON. It does not
download PDFs unless asked (--pdfs), and the cache is gitignored, because this
repository does not carry PDFs.

The CSV is committable: it is small, every row carries provenance, and the
underlying documents are US Government works in the public domain.

THE TRAP THIS GUARDS AGAINST
----------------------------
An unfiltered `openfda.generic_name` query returns whichever label ranks first.
For pembrolizumab and nivolumab that is now the SUBCUTANEOUS coformulation --
KEYTRUDA QLEX, OPDIVO QVANTIG -- not the intravenous product the modelling
literature describes. Querying by generic name alone silently hands back a
different drug. So data/pdac-drugs.csv carries an expected brand name and this
script checks it, reporting a mismatch rather than writing the row.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRUGS = ROOT / "data" / "pdac-drugs.csv"
OUT = ROOT / "data" / "fda-documents.csv"
CACHE = ROOT / "fda-cache"
FIXTURES = ROOT / "tests" / "fixtures" / "openfda"

API = "https://api.fda.gov"
UA = "modelers-bench/1.0 (educational; https://github.com/mgl0619/modelers-bench)"

# openFDA allows 240 requests/minute/IP without a key. One request every 0.4s
# stays inside that with room to spare. Set OPENFDA_API_KEY to raise the limit.
DELAY = 0.4

FIELDS = ["drug", "brand", "role", "strand", "source", "application_number",
          "submission", "doc_type", "url", "retrieved"]


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

def get(path, params, offline=False):
    """One GET against openFDA. Returns parsed JSON, or None for 'no match'.

    openFDA answers a query that matches nothing with HTTP 404 and a NOT_FOUND
    body. That is a normal, expected answer -- most drugs have no CRL -- so it
    is returned as None rather than raised. Anything else is a real failure and
    is allowed to propagate.
    """
    if offline:
        fx = FIXTURES / (path.replace("/", "_").replace(".json", "") + ".json")
        if not fx.exists():
            return None
        return json.loads(fx.read_text(encoding="utf-8"))

    key = os.environ.get("OPENFDA_API_KEY")
    if key:
        params = dict(params, api_key=key)
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None                       # no match: normal
        if e.code == 429:
            print("    rate limited; waiting 20s", flush=True)
            time.sleep(20)
            return get(path, params, offline)
        raise
    finally:
        if not offline:
            time.sleep(DELAY)


def cache_write(name, payload):
    CACHE.mkdir(exist_ok=True)
    (CACHE / f"{name}.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------
# per-drug collection
# --------------------------------------------------------------------------

def brand_ok(result, expected):
    """Is this the product we asked for, or a same-molecule impostor?"""
    brands = [b.upper() for b in
              (result.get("openfda", {}) or {}).get("brand_name", [])]
    if not brands:
        brands = [(p.get("brand_name") or "").upper()
                  for p in result.get("products", [])]
    return any(expected.upper() in b for b in brands), brands


def collect(drug, offline=False):
    """Return (rows, notes) for one drug."""
    generic, brand = drug["generic"], drug["brand"]
    rows, notes = [], []
    today = date.today().isoformat()

    def row(**kw):
        base = dict.fromkeys(FIELDS, "")
        base.update(drug=generic, brand=brand, role=drug["role"],
                    strand=drug["strand"], retrieved=today)
        base.update(kw)
        return base

    # ---- 1. application metadata, and the document URLs it carries ----
    q = f'openfda.generic_name:"{generic}"'
    data = get("drug/drugsfda.json", {"search": q, "limit": 5}, offline)
    if not data:
        notes.append(f"{generic}: no Drugs@FDA record")
    else:
        cache_write(f"drugsfda_{generic.replace(' ', '_')}", data)
        matched = False
        for res in data.get("results", []):
            ok, seen = brand_ok(res, brand)
            if not ok:
                notes.append(f"{generic}: skipped application "
                             f"{res.get('application_number')} — brand {seen} "
                             f"does not match expected {brand!r}")
                continue
            matched = True
            appno = res.get("application_number", "")
            for sub in res.get("submissions", []):
                subid = (f"{sub.get('submission_type','')}"
                         f"-{sub.get('submission_number','')}")
                for doc in sub.get("application_docs", []) or []:
                    rows.append(row(source="drugsfda",
                                    application_number=appno,
                                    submission=subid,
                                    doc_type=doc.get("type", ""),
                                    url=doc.get("url", "")))
        if not matched:
            notes.append(f"{generic}: NO application matched brand {brand!r} — "
                         f"check data/pdac-drugs.csv")

    # ---- 2. label ----
    data = get("drug/label.json",
               {"search": f'{q} AND _exists_:pharmacokinetics', "limit": 1},
               offline)
    if data and data.get("results"):
        cache_write(f"label_{generic.replace(' ', '_')}", data)
        res = data["results"][0]
        ok, seen = brand_ok(res, brand)
        rows.append(row(source="label",
                        doc_type="label (pharmacokinetics present)"
                                 if ok else f"label MISMATCH {seen}",
                        url=f"{API}/drug/label.json?search="
                            f"{urllib.parse.quote(q)}"))
        if not ok:
            notes.append(f"{generic}: label query returned {seen}, not {brand!r}")
    else:
        notes.append(f"{generic}: no label with a pharmacokinetics section")

    # ---- 3. complete response letters ----
    # Matched on company/application text rather than generic name: the CRL
    # dataset has no generic_name field, only application_number, company_name
    # and OCR'd text.
    data = get("transparency/crl.json",
               {"search": f'text:"{generic}"', "limit": 10}, offline)
    if data and data.get("results"):
        cache_write(f"crl_{generic.replace(' ', '_')}", data)
        for res in data["results"]:
            rows.append(row(source="crl",
                            application_number=
                                ", ".join(res.get("application_number", [])),
                            doc_type=f"{res.get('letter_type','CRL')} "
                                     f"({res.get('approval_status','?')})",
                            submission=res.get("letter_date", ""),
                            url=f"{API}/transparency/crl.json?search="
                                f"file_name:%22{res.get('file_name','')}%22"))
    return rows, notes


# --------------------------------------------------------------------------

def read_drugs():
    lines = [l for l in DRUGS.read_text(encoding="utf-8").splitlines()
             if not l.startswith("#")]
    return list(csv.DictReader(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true",
                    help="parse recorded fixtures instead of calling the API")
    ap.add_argument("--drug", help="just this generic name")
    ap.add_argument("--selftest", action="store_true",
                    help="offline run plus assertions; used by `make fda-test`")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    drugs = read_drugs()
    if args.drug:
        drugs = [d for d in drugs if d["generic"] == args.drug]
        if not drugs:
            print(f"no such drug in {DRUGS.name}", file=sys.stderr)
            return 1

    print(f"{'OFFLINE (fixtures)' if args.offline else 'openFDA'}: "
          f"{len(drugs)} drug(s)\n")

    all_rows, all_notes = [], []
    for d in drugs:
        print(f"  {d['generic']:28s} ", end="", flush=True)
        try:
            rows, notes = collect(d, args.offline)
        except Exception as e:                       # noqa: BLE001
            print(f"FAILED {type(e).__name__}: {e}")
            all_notes.append(f"{d['generic']}: {type(e).__name__}: {e}")
            continue
        all_rows += rows
        all_notes += notes
        kinds = {}
        for r in rows:
            kinds[r["source"]] = kinds.get(r["source"], 0) + 1
        print(", ".join(f"{v} {k}" for k, v in sorted(kinds.items()))
              or "nothing found")

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(all_rows)

    print(f"\n  {len(all_rows)} documents indexed -> {OUT.relative_to(ROOT)}")
    if not args.offline:
        print(f"  raw responses cached in {CACHE.relative_to(ROOT)}/ "
              f"(gitignored)")
    if all_notes:
        print(f"\n  {len(all_notes)} note(s) — these are the interesting part:")
        for n in all_notes:
            print(f"    - {n}")
    return 0


def selftest():
    """Assert the parser's behaviour against the fixtures.

    The point of this is the brand guard. Everything else here would fail
    loudly on its own; a brand guard that silently stops guarding would not,
    and the failure it prevents -- indexing a different product's documents
    under this drug's name -- looks entirely normal in the output.
    """
    drug = {"generic": "sotorasib", "brand": "LUMAKRAS",
            "role": "test", "strand": "C-04"}
    rows, notes = collect(drug, offline=True)
    urls = [r["url"] for r in rows]
    by = {}
    for r in rows:
        by[r["source"]] = by.get(r["source"], 0) + 1

    checks = [
        ("indexes the matching application's documents",
         by.get("drugsfda") == 4),
        ("BRAND GUARD: does not index the mismatched application",
         not any("should-not-be-indexed" in u for u in urls)),
        ("BRAND GUARD: reports the mismatch rather than staying silent",
         any("does not match expected" in n for n in notes)),
        ("finds the label", by.get("label") == 1),
        ("finds the CRL", by.get("crl") == 1),
        ("carries a Review document URL, not only letters and labels",
         any(r["doc_type"] == "Review" for r in rows)),
        ("every row has a url", all(r["url"] for r in rows)),
        ("every row is dated", all(r["retrieved"] for r in rows)),
    ]
    width = max(len(c[0]) for c in checks)
    bad = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:{width}s}")
        bad += not ok
    print(f"\n  {len(checks) - bad}/{len(checks)} checks passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
