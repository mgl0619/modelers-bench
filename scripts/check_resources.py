#!/usr/bin/env python3
"""Validate resources.csv — the resource database for The Modeler's Bench.

Every row must have been fetched and confirmed before it was added. This script
cannot re-check that (it does no network access, by design: `make check` must
work offline). What it CAN enforce is that the file stays structurally honest:
controlled vocabularies, unique ids, no empty required fields, no row without a
verification date.

Run:  python3 scripts/check_resources.py
      make check-resources

Exit code 0 = clean, 1 = problems found (each printed with its row number).
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "resources.csv"

COLUMNS = [
    "id", "name", "category", "subcategory", "domains", "url", "cost",
    "licence", "language", "maintainer", "description", "best_for",
    "notes", "verified",
]

CATEGORIES = {"software", "course", "guidance", "repository", "reference"}
COSTS = {"free", "free-academic", "freemium", "commercial", "unknown"}
DOMAINS = {
    "pharmacology", "pkpd", "poppk", "pbpk", "qsp",
    "stats-ml", "regulatory", "general",
}

# Required to be non-empty. `notes` and `subcategory` may be blank.
REQUIRED = ["id", "name", "category", "domains", "url", "cost",
            "licence", "maintainer", "description", "best_for", "verified"]

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MAX_DESCRIPTION = 260


def main() -> int:
    if not CSV_PATH.exists():
        print(f"FAIL  {CSV_PATH} not found")
        return 1

    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLUMNS:
            print("FAIL  column header does not match the schema")
            print(f"      expected: {COLUMNS}")
            print(f"      found:    {reader.fieldnames}")
            return 1
        rows = list(reader)

    problems = []
    seen_ids = {}
    seen_urls = {}

    def bad(n, msg):
        problems.append(f"row {n} ({rows[n - 2].get('id', '?')}): {msg}")

    for n, row in enumerate(rows, start=2):
        for col in REQUIRED:
            if not (row.get(col) or "").strip():
                bad(n, f"empty required field '{col}'")

        rid = row["id"]
        if not ID_RE.match(rid):
            bad(n, f"id '{rid}' is not lowercase-kebab-case")
        if rid in seen_ids:
            bad(n, f"duplicate id '{rid}' (first seen at row {seen_ids[rid]})")
        seen_ids[rid] = n

        url = row["url"]
        if not url.startswith(("http://", "https://")):
            bad(n, f"url does not look like a URL: {url!r}")
        if url in seen_urls:
            bad(n, f"duplicate url (first seen at row {seen_urls[url]})")
        seen_urls[url] = n

        if row["category"] not in CATEGORIES:
            bad(n, f"category '{row['category']}' not in {sorted(CATEGORIES)}")
        if row["cost"] not in COSTS:
            bad(n, f"cost '{row['cost']}' not in {sorted(COSTS)}")

        for d in row["domains"].split("|"):
            if d not in DOMAINS:
                bad(n, f"domain '{d}' not in {sorted(DOMAINS)}")

        if not DATE_RE.match(row["verified"]):
            bad(n, f"verified '{row['verified']}' is not YYYY-MM-DD")

        if len(row["description"]) > MAX_DESCRIPTION:
            bad(n, f"description is {len(row['description'])} chars "
                   f"(max {MAX_DESCRIPTION})")

        # A free entry with a proprietary licence is not necessarily wrong —
        # ADAPT and IQR Tools are both real examples — but it is the kind of
        # thing worth a second look, so say so without failing the build.
        if row["cost"] == "free" and row["licence"] == "proprietary":
            print(f"NOTE  row {n} ({rid}): cost=free but licence=proprietary "
                  f"— free to use is not the same as open source. Confirm the "
                  f"note explains this.")

    if problems:
        print(f"FAIL  {len(problems)} problem(s) in {CSV_PATH.name}\n")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"OK    {len(rows)} resources, schema clean\n")
    for label, key in (("category", "category"), ("cost", "cost")):
        print(f"  by {label}:")
        for k, v in Counter(r[key] for r in rows).most_common():
            print(f"    {k:<16s} {v:>4d}")
        print()

    domains = Counter()
    for r in rows:
        for d in r["domains"].split("|"):
            domains[d] += 1
    print("  by domain (a resource may carry several):")
    for k, v in domains.most_common():
        print(f"    {k:<16s} {v:>4d}")

    free = sum(1 for r in rows if r["cost"] in ("free", "free-academic"))
    print(f"\n  usable at no cost: {free} of {len(rows)} "
          f"({100 * free / len(rows):.0f}%)")

    return audit_site_links({r["url"] for r in rows})


def audit_site_links(known_urls):
    """Every external link on the site must trace to something we verified.

    The rule this enforces: a reader clicking a link on any page is clicking
    something that was either (a) a row in resources.csv, whose URL was fetched
    and confirmed, or (b) a DOI or PubMed/PMC link, which reading.qmd verified
    against PubMed. Anything else is a link nobody checked, and this is where
    rot starts.

    Add a genuine exception to ALLOWED below rather than weakening the rule.
    """
    import glob

    ALLOWED = {
        # self-reference to this repository
        "https://github.com/mgl0619/modelers-bench/blob/main/resources.csv",
    }

    root = CSV_PATH.parent
    pattern = re.compile(r"\]\((https?://[^)\s]+)\)")
    found = {}
    for pat in ("*.qmd", "lessons/*/*.qmd", "paths/*.qmd"):
        for path in sorted(root.glob(pat)):
            text = path.read_text(encoding="utf-8")
            for url in pattern.findall(text):
                found.setdefault(url, set()).add(
                    str(path.relative_to(root)))

    def traced(u):
        return (u in known_urls or u in ALLOWED
                or "doi.org" in u or "ncbi.nlm.nih.gov" in u)

    untraced = {u: v for u, v in found.items() if not traced(u)}

    print(f"\n  site links checked: {len(found)}")
    print(f"    in resources.csv : "
          f"{sum(1 for u in found if u in known_urls)}")
    print(f"    DOI / PubMed     : "
          f"{sum(1 for u in found if 'doi.org' in u or 'ncbi.nlm.nih.gov' in u)}")

    if untraced:
        print(f"\nFAIL  {len(untraced)} link(s) on the site trace to nothing "
              f"we verified:\n")
        for u, files in sorted(untraced.items()):
            print(f"  - {u}")
            print(f"      in: {', '.join(sorted(files))}")
        print("\n  Fix by adding the resource to resources.csv (after "
              "fetching it), or\n  by adding it to ALLOWED in this script "
              "with a reason.")
        return 1

    print("    untraced         : 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
