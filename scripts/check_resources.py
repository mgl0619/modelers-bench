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
    "id", "name", "category", "subcategory", "domains", "modality", "disease",
    "url", "cost", "licence", "language", "maintainer", "description",
    "best_for", "notes", "verified",
]

CATEGORIES = {"software", "course", "guidance", "repository", "reference"}
COSTS = {"free", "free-academic", "freemium", "commercial", "unknown"}
DOMAINS = {
    "pharmacology", "pkpd", "poppk", "pbpk", "qsp",
    "stats-ml", "regulatory", "general",
}

# Drug modality. `any` is the honest default and the majority value: an ODE
# solver does not care what the molecule is. Tag a row only where the resource
# is genuinely specialised — tagging a general tool with a modality would make
# the facet worse than useless, because a filtered view would then be wrong
# rather than merely incomplete.
MODALITIES = {
    "any", "small-molecule", "peptide", "protein-mab", "adc", "bispecific",
    "oligonucleotide", "cell-therapy", "gene-therapy", "vaccine", "radioligand",
}

# Therapeutic area. Same rule: `any` unless the resource is about one disease.
DISEASES = {
    "any", "oncology", "immunology", "infectious-disease", "cns",
    "cardiometabolic", "respiratory", "hepatology", "nephrology",
    "haematology", "rare-disease",
}

# Required to be non-empty. `notes` and `subcategory` may be blank.
REQUIRED = ["id", "name", "category", "domains", "modality", "disease", "url",
            "cost", "licence", "maintainer", "description", "best_for",
            "verified"]

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

        for field, vocab in (("modality", MODALITIES), ("disease", DISEASES)):
            values = row[field].split("|")
            for v in values:
                if v not in vocab:
                    bad(n, f"{field} '{v}' not in {sorted(vocab)}")
            # "any" means "not specialised"; combining it with a specific value
            # is a contradiction, and it makes the filter behave unpredictably.
            if "any" in values and len(values) > 1:
                bad(n, f"{field} combines 'any' with a specific value: "
                       f"{row[field]!r} — pick one or the other")

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

    for label, key in (("domain", "domains"), ("modality", "modality"),
                       ("disease", "disease")):
        counts = Counter()
        for r in rows:
            for v in r[key].split("|"):
                counts[v] += 1
        print(f"  by {label} (a resource may carry several):")
        for k, v in counts.most_common():
            flag = "  <- not specialised" if k == "any" else ""
            print(f"    {k:<20s} {v:>4d}{flag}")
        print()

    free = sum(1 for r in rows if r["cost"] in ("free", "free-academic"))
    print(f"  usable at no cost: {free} of {len(rows)} "
          f"({100 * free / len(rows):.0f}%)")

    return audit_site_links({r["url"] for r in rows})


def audit_site_links(known_urls):
    """Every external link on the site must trace to something we verified.

    The rule: a reader clicking a link on any page is clicking something that
    was either (a) a row in resources.csv, whose URL was fetched and confirmed,
    or (b) a DOI or PubMed/PMC link, which reading.qmd verified against PubMed.
    Anything else is a link nobody checked, and that is where rot starts.

    Add a genuine exception to ALLOWED below rather than weakening the rule.
    """
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
                found.setdefault(url, set()).add(str(path.relative_to(root)))

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
        print("\n  Fix by adding the resource to resources.csv (after fetching "
              "it), or\n  by adding it to ALLOWED in this script with a reason.")
        return 1

    print("    untraced         : 0")

    return audit_rendered_page(len(known_urls))


def audit_rendered_page(n_expected):
    """If the site has been built, check that resources.html actually rendered.

    This exists because of a specific failure. resources.qmd generates its cards
    from Python, and Quarto passes that output through Pandoc as markdown. A
    generated line indented four spaces inside a raw HTML block is an indented
    CODE block to Pandoc, so the anchor and cost badge on every card were
    rendered as escaped source text instead of as a link. The page looked
    plausible, the build succeeded, and nothing failed - it was caught by eye.

    So: two assertions against the built page, and only if it exists. Skipping
    when unbuilt keeps `make check` usable offline and before a render.
    """
    # Auditing the built page only makes sense straight after a render, so the
    # caller says when that is: `check_resources.py --post-render`, which is
    # what `make check-rendered` passes.
    #
    # The first design inferred it from mtime, comparing the page against the
    # CSV. That was guesswork dressed as a check - any touch of either file
    # flipped the verdict, and it did, during testing. An explicit flag cannot
    # be fooled that way.
    #
    # Why it must be opt-in at all: `make all` is check -> render -> audit. The
    # pre-render `check` runs against a page that render is about to replace,
    # so failing there blocks the very build that would fix it. That bug made
    # `make all` impossible to pass on any commit touching resources.csv.
    post_render = "--post-render" in sys.argv
    page = CSV_PATH.parent / "_site" / "resources.html"

    if not post_render:
        print("\n  rendered page      : not audited here - runs after render "
              "(`make check-rendered`)")
        return 0

    if not page.exists():
        print("\nFAIL  --post-render was passed but _site/resources.html "
              "does not exist.\n\n  Render first:   make render\n")
        return 1

    # Explicitly asked to audit, but the page predates the data: that is a
    # stale build, not lost cards. Different message, different fix.
    if page.stat().st_mtime < CSV_PATH.stat().st_mtime:
        print("\nFAIL  _site/resources.html is older than resources.csv.\n")
        print("  The audit was requested, but this page was built before the")
        print("  current data. Re-render, then audit:")
        print("      make render && make check-rendered\n")
        return 1

    html = page.read_text(encoding="utf-8", errors="replace")
    problems = []

    # 1. No escaped markup. If Pandoc turned generated HTML into a code block,
    #    the literal string `&lt;a class=` or `&lt;span class=` appears.
    for needle in ("&lt;a class=", "&lt;span class=", "&lt;div class="):
        n = html.count(needle)
        if n:
            problems.append(f"{n} occurrence(s) of escaped markup {needle!r} "
                            f"- generated HTML was parsed as a code block")

    # 2. Every row reached the page. Silent card loss is the other way this
    #    generation step can fail without erroring.
    n_cards = html.count('class="res-item"')
    if n_cards != n_expected:
        problems.append(f"{n_cards} cards rendered but {n_expected} rows in "
                        f"the CSV")

    print(f"\n  rendered page      : {n_cards} cards")
    if not problems:
        print("    escaped markup   : none")
        return 0

    # Getting here means the page is at least as new as the CSV - a genuinely
    # stale build returned earlier. So a shortfall with clean markup is not
    # staleness: cards were lost during the render itself, which is a real and
    # much less obvious bug than the indentation one. Say so, rather than
    # repeating advice about four-space indents that does not apply.
    lost = (not any("escaped markup" in pr for pr in problems)
            and n_cards < n_expected)

    if lost:
        print(f"\nFAIL  cards went missing during render:\n")
        print(f"  - {n_cards} cards on a freshly built page, "
              f"{n_expected} rows in the CSV")
        print("\n  The markup is clean and the page is not stale, so rows were")
        print("  dropped while generating. Check the loop in resources.qmd for")
        print("  a filter or an exception swallowing rows.")
        return 1

    print(f"\nFAIL  resources.html did not render correctly:\n")
    for pr in problems:
        print(f"  - {pr}")
    print("\n  The usual cause is a generated HTML line indented four or "
          "more\n  spaces. Emit each card on a single line instead.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
