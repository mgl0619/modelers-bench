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
    return 0


if __name__ == "__main__":
    sys.exit(main())
