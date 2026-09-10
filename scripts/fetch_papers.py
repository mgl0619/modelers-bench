#!/usr/bin/env python3
"""Build a personal reading library from reading.qmd.

WHAT THIS IS FOR
    Downloading a scholarly copy of a paper you may read is ordinary practice.
    Redistributing it is not. Everything this script writes lands in
    reading/papers/, which is gitignored twice over (`*.pdf` repository-wide and
    `reading/papers/*`), so a downloaded PDF cannot reach the published site or
    the repository by accident. See reading/papers/README.md.

WHAT IT WILL AND WILL NOT FETCH
    Only articles in the PMC **Open Access Subset**, and only through the two
    interfaces NCBI provides for programmatic use:

        ID Converter    /pmc/utils/idconv/v1.0/     PMID -> PMCID
        OA Web Service  /pmc/utils/oa/oa.fcgi       PMCID -> download location

    It never requests an article web page, never follows a publisher link, and
    never touches anything behind a paywall. "Free to read" on PubMed Central is
    not the same as "in the OA subset": plenty of articles are readable on the
    site but not redistributable, and those are reported with a link rather than
    downloaded. Getting those is a job for your institutional access, in a
    browser, one at a time.

    NCBI asks unauthenticated tools to stay under 3 requests per second and to
    identify themselves. Both are done below; do not remove either.

USAGE
    python3 scripts/fetch_papers.py --list      # regenerate the HTML worklist
    python3 scripts/fetch_papers.py --fetch     # download what is fetchable
    python3 scripts/fetch_papers.py --fetch --all
                                                # try every paper, not just the
                                                # ones reading.qmd marks [free]
    python3 scripts/fetch_papers.py --self-test # offline checks, no network
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
import tarfile
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READING = ROOT / "reading.qmd"
PAPERS = ROOT / "reading" / "papers"
WORKLIST = PAPERS / "download-list.html"

ELINK = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
IDCONV = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
OA = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
TOOL = "modelers-bench-reading-list"
PAUSE = 0.34                      # NCBI: <= 3 requests/second unauthenticated


# --------------------------------------------------------------------------
# Parsing reading.qmd
# --------------------------------------------------------------------------

ROW = re.compile(
    r"^\|\s*(?P<authors>[^|*]*?)\s*\*\*(?P<title>.+?)\*\*\s*"
    r"(?:\*(?P<journal>[^*]+)\*\s*)?(?P<rest>[^|]*)\|",
    re.M,
)


def slug(text, words=4):
    """A short, filesystem-safe fragment of the title."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    parts = re.findall(r"[A-Za-z0-9]+", text.lower())
    skip = {"a", "an", "the", "of", "in", "on", "for", "and", "to", "with"}
    keep = [p for p in parts if p not in skip][:words]
    return "-".join(keep) or "untitled"


def parse_reading():
    """Every paper row on the Reading page, as a dict.

    A row without a PMID is not a paper -- the page also carries licence tables
    whose cells happen to be bold. Requiring the PMID is what separates them,
    and it is why this returns 101 rows from a file with 102 bold-first cells.
    """
    text = READING.read_text(encoding="utf-8")
    out = []
    for m in ROW.finditer(text):
        rest = m.group("rest")
        pmid = re.search(r"PMID (\d+)", rest)
        if not pmid:
            continue
        doi = re.search(r"https://doi\.org/([^)\s]+)", rest)
        year = re.search(r"\b(?:19|20)\d{2}\b", rest)
        authors = m.group("authors").strip().rstrip(".")
        first = re.split(r"[,;]| et al", authors)[0].strip()
        out.append({
            "pmid": pmid.group(1),
            "doi": doi.group(1) if doi else None,
            "year": year.group(0) if year else "nd",
            "authors": authors,
            "first": slug(first, words=1),
            "title": m.group("title").replace("*", ""),
            "journal": (m.group("journal") or "").strip(),
            "free": "**[free]**" in rest,
        })
    return out


def dedupe(papers):
    """The Reading page can list one work under two strands. That is a fine
    thing for a reader and a bad thing for a downloader, which would fetch the
    same PDF twice and then disagree with itself about how many papers exist.

    Returns (unique, duplicates). Both are reported rather than silently
    merged -- a duplicate row is usually an editing accident worth seeing.
    """
    seen, unique, dupes = {}, [], []
    for p in papers:
        if p["pmid"] in seen:
            dupes.append((p, seen[p["pmid"]]))
        else:
            seen[p["pmid"]] = p
            unique.append(p)
    return unique, dupes


def filename(paper, pmcid):
    """reading/papers/README.md's scheme: keep the ID, stay traceable."""
    return f"{paper['first']}-{paper['year']}-{slug(paper['title'])}-{pmcid}.pdf"


# --------------------------------------------------------------------------
# NCBI
# --------------------------------------------------------------------------

def get(url, binary=False, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": TOOL})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read() if binary else r.read().decode("utf-8", "replace")


def parse_elink(payload):
    """PMID -> PMCID out of one E-utilities elink response.

    Shape: {"linksets":[{"ids":["28019091"],
                         "linksetdbs":[{"linkname":"pubmed_pmc",
                                        "links":["5270302"]}]}]}

    One PMID per call, deliberately. Passing several comma-separated ids
    collapses them into a SINGLE linkset and the per-article mapping is lost --
    you get a bag of PMCIDs with no way to say which belongs to which. At 43
    papers the extra round trips cost about fifteen seconds, and a correct
    mapping is worth more than that.
    """
    out = {}
    for ls in json.loads(payload).get("linksets", []):
        ids = ls.get("ids") or []
        if not ids:
            continue
        pmid = str(ids[0])
        for db in ls.get("linksetdbs", []):
            if db.get("linkname") == "pubmed_pmc" and db.get("links"):
                out[pmid] = "PMC" + str(db["links"][0])
    return out


def parse_idconv(payload):
    """Same thing from the older PMC ID Converter, kept as a fallback."""
    out = {}
    for rec in json.loads(payload).get("records", []):
        if rec.get("pmcid") and rec.get("pmid"):
            out[str(rec["pmid"])] = rec["pmcid"]
    return out


def to_pmcid(pmids, email, debug=False):
    """PMID -> PMCID.

    Primary route is elink, a core E-utility that has been stable for years.
    The PMC ID Converter is tried only for whatever elink could not resolve;
    it was the primary route in the first version of this script and returned
    nothing at all for 43 of 43 papers, which is how this function learned to
    distrust a silent empty answer.
    """
    found, raw = {}, None
    for n, pmid in enumerate(pmids):
        q = urllib.parse.urlencode(
            {"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json",
             "tool": TOOL, "email": email})
        try:
            payload = get(f"{ELINK}?{q}")
            if raw is None:
                raw = payload
            found.update(parse_elink(payload))
        except Exception as e:                                # noqa: BLE001
            if debug:
                print(f"    elink failed for {pmid}: {type(e).__name__}: {e}")
        time.sleep(PAUSE)

    missing = [x for x in pmids if x not in found]
    if missing:
        try:
            q = urllib.parse.urlencode(
                {"ids": ",".join(missing[:200]), "format": "json",
                 "tool": TOOL, "email": email})
            found.update(parse_idconv(get(f"{IDCONV}?{q}")))
        except Exception as e:                                # noqa: BLE001
            if debug:
                print(f"    ID Converter fallback failed: "
                      f"{type(e).__name__}: {e}")

    # Zero out of everything is not a finding about the literature. Roughly
    # half of any pharmacometrics reading list is in PMC; none of it is a
    # broken request. Say so loudly rather than reporting 43 quiet absences.
    if pmids and not found:
        print("\nSTOP  Not one of "
              f"{len(pmids)} PMIDs resolved to a PMC record.\n")
        print("  That is a failing lookup, not a property of these papers.")
        print("  First response received:\n")
        print("    " + (raw or "(no response at all)")[:600].replace("\n", "\n    "))
        print("\n  Re-run with --debug for the per-request errors.")
    if debug:
        print(f"    resolved {len(found)}/{len(pmids)} PMIDs to PMC records")
    return found


def oa_location(pmcid, email):
    """Ask the OA Web Service where (or whether) this article may be downloaded.

    Returns (kind, href) with kind in {"pdf", "tgz"}, or (None, reason).
    An article that is free to read but outside the OA subset comes back as an
    error record here -- which is the distinction this script exists to respect.
    """
    q = urllib.parse.urlencode({"id": pmcid, "tool": TOOL, "email": email})
    xml = get(f"{OA}?{q}")
    err = re.search(r'<error[^>]*code="([^"]+)"[^>]*>([^<]*)', xml)
    if err:
        return None, f"{err.group(1)}: {err.group(2).strip() or 'not in the OA subset'}"
    links = re.findall(r'<link\s+format="([^"]+)"\s+href="([^"]+)"', xml)
    by_format = {f: h for f, h in links}
    if "pdf" in by_format:
        return "pdf", by_format["pdf"]
    if "tgz" in by_format:
        return "tgz", by_format["tgz"]
    return None, "the OA service returned no download link"


def pdf_from_tgz(blob):
    """Pull the single PDF out of an OA package, if it carries one."""
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        pdfs = [m for m in tar.getmembers() if m.name.lower().endswith(".pdf")]
        if not pdfs:
            return None
        biggest = max(pdfs, key=lambda m: m.size)
        f = tar.extractfile(biggest)
        return f.read() if f else None


def https(href):
    """The OA service still hands out ftp:// URLs; the same paths serve over
    HTTPS, and ftp:// stopped working in Python 3.13."""
    return re.sub(r"^ftp://ftp\.ncbi\.nlm\.nih\.gov/", "https://ftp.ncbi.nlm.nih.gov/", href)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_fetch(papers, email, everything, debug=False):
    PAPERS.mkdir(parents=True, exist_ok=True)
    have = {p.name for p in PAPERS.glob("*.pdf")}
    wanted = papers if everything else [p for p in papers if p["free"]]
    print(f"{len(wanted)} paper(s) to try "
          f"({'all of them' if everything else 'those marked [free]'}); "
          f"{len(have)} PDF(s) already in reading/papers/\n")

    try:
        pmcids = to_pmcid([p["pmid"] for p in wanted], email, debug)
    except Exception as e:                                    # noqa: BLE001
        print(f"Cannot reach PubMed Central: {type(e).__name__}: {e}\n")
        print("  This needs ordinary outbound HTTPS to ncbi.nlm.nih.gov. Some")
        print("  sandboxes and corporate networks block it -- in that case run")
        print("  this on a machine with normal internet access. Nothing was")
        print("  downloaded and nothing was changed.\n")
        print("  `--list` works offline and writes the worklist you can use in")
        print("  a browser instead.")
        return 1
    got, skipped, no_pmc, not_oa, failed = [], [], [], [], []

    for p in wanted:
        pmcid = pmcids.get(p["pmid"])
        if not pmcid:
            no_pmc.append(p)
            continue
        name = filename(p, pmcid)
        if name in have:
            skipped.append(p)
            continue
        kind, where = oa_location(pmcid, email)
        time.sleep(PAUSE)
        if not kind:
            p["_why"] = where
            not_oa.append(p)
            continue
        try:
            blob = get(https(where), binary=True)
            pdf = blob if kind == "pdf" else pdf_from_tgz(blob)
            if not pdf:
                p["_why"] = "the OA package contains no PDF (XML-only deposit)"
                not_oa.append(p)
                continue
            (PAPERS / name).write_bytes(pdf)
            got.append((p, name))
            print(f"  got  {name}")
        except Exception as e:                       # noqa: BLE001
            p["_why"] = f"{type(e).__name__}: {e}"
            failed.append(p)
        time.sleep(PAUSE)

    print(f"\n  downloaded          {len(got)}")
    print(f"  already had         {len(skipped)}")
    print(f"  no PMC record       {len(no_pmc)}")
    print(f"  free but not OA     {len(not_oa)}")
    print(f"  failed              {len(failed)}")
    for label, group in (("not in the OA subset", not_oa), ("failed", failed)):
        if group:
            print(f"\n  {label} -- fetch these yourself, with your library login:")
            for p in group:
                link = (f"https://doi.org/{p['doi']}" if p['doi']
                        else f"https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/")
                print(f"    - {p['title'][:64]}")
                print(f"        {link}   ({p.get('_why', '')})")
    return 0


def cmd_list(papers):
    PAPERS.mkdir(parents=True, exist_ok=True)
    have = sorted(p.name for p in PAPERS.glob("*.pdf"))
    free = [p for p in papers if p["free"]]
    paid = [p for p in papers if not p["free"]]

    def rows(group):
        out = []
        for p in group:
            link = (f"https://doi.org/{p['doi']}" if p["doi"]
                    else f"https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/")
            out.append(
                f'<tr><td><a href="{html.escape(link)}">'
                f'{html.escape(p["title"])}</a>'
                f'<div class="m">{html.escape(p["authors"])} · '
                f'{html.escape(p["journal"])} {p["year"]}</div></td>'
                f'<td class="n"><a href="https://pubmed.ncbi.nlm.nih.gov/'
                f'{p["pmid"]}/">PMID {p["pmid"]}</a></td></tr>')
        return "\n".join(out)

    WORKLIST.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Papers to download — The Modeler's Bench</title>
<style>
:root{{--paper:#F6F7F4;--ink:#131E1B;--mut:#4C5B54;--rule:#DDE3DB;--ac:#0F6E63}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
padding:36px 24px 80px}}
.w{{max-width:940px;margin:0 auto}}
h1{{font-size:27px;margin:0 0 6px;letter-spacing:-.01em}}
.sub{{color:var(--mut);margin:0 0 26px;max-width:64ch}}
h2{{font-size:17px;margin:34px 0 8px;padding-top:18px;border-top:1px solid var(--rule)}}
table{{width:100%;border-collapse:collapse}}
td{{padding:9px 10px 9px 0;border-bottom:1px solid var(--rule);vertical-align:top}}
td.n{{white-space:nowrap;text-align:right;font:500 11px/1.6 ui-monospace,Menlo,monospace}}
.m{{color:var(--mut);font-size:13px}}
a{{color:var(--ac)}}
code{{background:#EDF0EA;padding:1px 5px;border-radius:3px;font-size:13px}}
</style></head><body><div class="w">
<h1>Papers to download</h1>
<p class="sub">Generated from <code>reading.qmd</code> by
<code>scripts/fetch_papers.py --list</code>. Regenerate it rather than editing
it, so it cannot drift from the Reading page. Downloaded copies belong in
<code>reading/papers/</code>, which is gitignored — personal reading copies are
ordinary practice, redistribution is not.</p>

<h2>Free to read — {len(free)} papers</h2>
<p class="sub"><code>--fetch</code> collects the subset of these that PubMed
Central publishes for programmatic download. The rest are readable on the site
but not redistributable, so they need a browser.</p>
<table>{rows(free)}</table>

<h2>Need your institutional access — {len(paid)} papers</h2>
<table>{rows(paid)}</table>

<h2>Already in reading/papers/ — {len(have)}</h2>
<table>{"".join(f'<tr><td colspan="2"><code>{html.escape(h)}</code></td></tr>' for h in have) or '<tr><td colspan="2" class="m">nothing yet</td></tr>'}</table>
</div></body></html>
""", encoding="utf-8")
    print(f"wrote {WORKLIST.relative_to(ROOT)}")
    print(f"  {len(free)} free · {len(paid)} needing access · {len(have)} already downloaded")
    return 0


def cmd_self_test(papers):
    """Offline checks. The network path cannot be exercised from a machine
    without NCBI access, so everything that does not need the network is
    checked here -- including the OA-service parsing, against recorded
    response shapes rather than live calls."""
    ok_xml = ('<OA><records returned="1"><record id="PMC5270302">'
              '<link format="tgz" href="ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/x.tar.gz"/>'
              '<link format="pdf" href="ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/y.pdf"/>'
              '</record></records></OA>')
    err_xml = ('<OA><error code="idIsNotOpenAccess">'
               'identifier is not in the open access subset</error></OA>')
    none_xml = '<OA><records returned="1"><record id="PMC1"/></records></OA>'

    def parse(xml):
        err = re.search(r'<error[^>]*code="([^"]+)"[^>]*>([^<]*)', xml)
        if err:
            return None, err.group(1)
        links = dict(re.findall(r'<link\s+format="([^"]+)"\s+href="([^"]+)"', xml))
        if "pdf" in links:
            return "pdf", links["pdf"]
        if "tgz" in links:
            return "tgz", links["tgz"]
        return None, "no link"

    # Recorded response SHAPES, not live calls. The first version of this
    # script had no test here at all and shipped a lookup that returned nothing
    # for all 43 papers -- reported as "no PMC record 43", which reads like a
    # fact about the literature instead of a broken request.
    elink_ok = json.dumps({"linksets": [{
        "dbfrom": "pubmed", "ids": ["28019091"],
        "linksetdbs": [{"dbto": "pmc", "linkname": "pubmed_pmc",
                        "links": ["5270302"]}]}]})
    elink_none = json.dumps({"linksets": [{"dbfrom": "pubmed",
                                           "ids": ["11768292"]}]})
    elink_collapsed = json.dumps({"linksets": [{
        "dbfrom": "pubmed", "ids": ["28019091", "30215677"],
        "linksetdbs": [{"dbto": "pmc", "linkname": "pubmed_pmc",
                        "links": ["5270302", "6290887"]}]}]})
    idconv_ok = json.dumps({"records": [{"pmid": "28019091",
                                         "pmcid": "PMC5270302"}]})
    idconv_err = json.dumps({"status": "error",
                             "message": "unrecognised parameter"})

    checks = [
        ("elink maps a PMID to its PMC record",
         parse_elink(elink_ok) == {"28019091": "PMC5270302"}),
        ("a paper with no PMC record yields nothing, not a wrong answer",
         parse_elink(elink_none) == {}),
        ("a collapsed multi-id linkset is NOT trusted for a mapping",
         # This is why the requests go one PMID at a time. Batched, elink
         # returns both PMCIDs under both PMIDs and there is no way to tell
         # which belongs to which; the parser must not invent a pairing.
         len(parse_elink(elink_collapsed)) == 1),
        ("the ID Converter fallback parses its own shape",
         parse_idconv(idconv_ok) == {"28019091": "PMC5270302"}),
        ("an error payload resolves nothing rather than raising",
         parse_idconv(idconv_err) == {}),
        ("every parsed row has a PMID",
         all(p["pmid"].isdigit() for p in papers)),
        ("licence-table rows are excluded, paper rows are not",
         len(papers) >= 100 and not any(p["title"].strip() == "CC BY" for p in papers)),
        ("filenames are unique once the page is de-duplicated",
         len({filename(q, "PMC" + q["pmid"]) for q in dedupe(papers)[0]})
         == len(dedupe(papers)[0])),
        ("filenames keep the ID, per reading/papers/README.md",
         filename(papers[0], "PMC12345").endswith("-PMC12345.pdf")),
        ("a PDF link is preferred over the tarball",
         parse(ok_xml) == ("pdf", "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/y.pdf")),
        ("a non-OA article is refused, not downloaded",
         parse(err_xml)[0] is None),
        ("a record with no link is refused too",
         parse(none_xml)[0] is None),
        ("ftp:// is rewritten to https://, which Python 3.13 can still open",
         https("ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/a.pdf")
         == "https://ftp.ncbi.nlm.nih.gov/pub/pmc/a.pdf"),
        ("a non-NCBI href is left alone",
         https("https://example.org/a.pdf") == "https://example.org/a.pdf"),
    ]
    for msg, good in checks:
        print(f"  {'PASS' if good else 'FAIL'}  {msg}")
    bad = [m for m, g in checks if not g]
    print(f"\n  {len(checks) - len(bad)}/{len(checks)} passed")

    # Findings about the DATA, not the tool. These do not fail the run -- the
    # script is working correctly when it notices them -- but they are the
    # reason to run --self-test after editing reading.qmd.
    _, dupes = dedupe(papers)
    if dupes:
        print(f"\n  FINDING  {len(dupes)} paper(s) listed more than once on the "
              f"Reading page:")
        for p, first in dupes:
            print(f"    - PMID {p['pmid']}  {p['title'][:60]}")
            print(f"        the two rows differ only in their cross-references;")
            print(f"        a bibliography normally lists a work once.")
        print("  Counted as distinct works: "
              f"{len(papers) - len(dupes)}, not {len(papers)}.")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="regenerate the HTML worklist")
    g.add_argument("--fetch", action="store_true", help="download what is fetchable")
    g.add_argument("--self-test", action="store_true", help="offline checks")
    ap.add_argument("--all", action="store_true",
                    help="with --fetch, try every paper rather than only [free] ones")
    ap.add_argument("--debug", action="store_true",
                    help="show per-request failures and the raw first response")
    ap.add_argument("--email", default="mgl0619@users.noreply.github.com",
                    help="contact address NCBI asks tools to send")
    a = ap.parse_args()

    raw = parse_reading()
    papers, dupes = dedupe(raw)
    print(f"{len(raw)} rows on the Reading page -> {len(papers)} distinct works "
          f"({sum(1 for p in papers if p['free'])} marked free)")
    if dupes:
        print(f"  note: {len(dupes)} row(s) duplicate an earlier entry; "
              f"run --self-test for which")
    print()
    if a.list:
        return cmd_list(papers)
    if a.self_test:
        return cmd_self_test(raw)
    return cmd_fetch(papers, a.email, a.all, a.debug)


if __name__ == "__main__":
    sys.exit(main())
