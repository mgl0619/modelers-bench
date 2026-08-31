#!/usr/bin/env python3
"""Search FDA regulatory text: Complete Response Letters and drug labels.

    make rag-build              build the corpus from openFDA (needs network)
    make rag Q="dose selection" search it
    make rag-test               ranking assertions against fixtures, offline

WHY THIS CORPUS
---------------
Complete Response Letters record the arguments that FAILED. FDA began releasing
them for unapproved applications in September 2025; before that a rejection was
not public at all. There are 458. Nobody has indexed them for this purpose, and
for a curriculum whose whole premise is learning from what went wrong, they are
better material than the approvals.

Every document here is a work of the United States Government and therefore in
the public domain, which is why this corpus can exist at all. An index over the
papers on the Reading page could not: a retrieval index stores verbatim chunks
of its sources, so an index built from copyrighted articles is a copy of them,
and this project does not carry copies. That index would have to stay on one
machine forever. This one ships.

WHY BM25 AND NOT EMBEDDINGS
---------------------------
No model, no torch, no API key, no network at query time. It runs in CI, it runs
on a plane, and the same query returns the same ranking every time -- which
matters in a repository that verifies its own outputs. For a corpus of this size
keyword ranking is also simply competitive: the queries that matter here are
drug names, application numbers and regulatory terms of art, which is exactly
where exact-term matching is strongest and paraphrase matching adds least.

The honest cost: it cannot match "heart attack" to "myocardial infarction".

A NOTE ON THE TEXT
------------------
CRL text is OCR of scanned letters and it is rough -- expect
"pute\\n\\nMie\\n\\nOAL\\n\\n DEPARTMENT OF HEALTH" rather than clean prose. Retrieval
copes better than reading does: distinctive terms survive OCR, so search works
while quoting does not. Treat every hit as a pointer to the source PDF, never as
a transcript.
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_fda import get, read_drugs, ROOT          # noqa: E402

CORPUS = ROOT / "data" / "derived" / "fda-corpus.jsonl"
FIXTURE_CORPUS = ROOT / "tests" / "fixtures" / "openfda" / "corpus.jsonl"

K1, B = 1.5, 0.75          # standard Okapi parameters
STOP = set("""a an and are as at be by for from has have in is it its of on or
that the to was were will with this these those which their they them not no
been had can may""".split())


def tokenize(text):
    """Lowercase word tokens, stopwords dropped, one-character junk dropped.

    The length filter matters more than usual here: OCR of a scanned letter
    produces a great deal of single-character debris, and without this the
    index fills with it.
    """
    return [t for t in re.findall(r"[a-z0-9][a-z0-9\-]*", (text or "").lower())
            if t not in STOP and len(t) > 1]


# --------------------------------------------------------------------------
# corpus
# --------------------------------------------------------------------------

def build(limit_per_drug=25):
    """Pull CRL and label text from openFDA into a JSONL corpus."""
    docs, seen = [], set()

    for drug in read_drugs():
        generic = drug["generic"]
        print(f"  {generic:28s} ", end="", flush=True)
        n = 0

        data = get("transparency/crl.json",
                   {"search": f'text:"{generic}"', "limit": limit_per_drug})
        for r in (data or {}).get("results", []):
            key = r.get("file_name")
            if not key or key in seen:
                continue
            seen.add(key)
            docs.append({
                "id": key,
                "kind": "crl",
                "drug": generic,
                "title": f"{r.get('letter_type','CRL')} — "
                         f"{r.get('company_name','?')} — "
                         f"{', '.join(r.get('application_number', []))}",
                "date": r.get("letter_date", ""),
                "status": r.get("approval_status", ""),
                "url": "https://api.fda.gov/transparency/crl.json?search="
                       f"file_name:%22{key}%22",
                "text": r.get("text", ""),
            })
            n += 1

        data = get("drug/label.json",
                   {"search": f'openfda.generic_name:"{generic}" '
                              f'AND _exists_:pharmacokinetics', "limit": 1})
        for r in (data or {}).get("results", []):
            key = f"label:{generic}"
            if key in seen:
                continue
            seen.add(key)
            parts = []
            for sec in ("clinical_pharmacology", "pharmacokinetics",
                        "pharmacodynamics", "dosage_and_administration"):
                parts += r.get(sec, []) or []
            docs.append({
                "id": key, "kind": "label", "drug": generic,
                "title": f"Label — {drug['brand']} ({generic})",
                "date": "", "status": "approved",
                "url": "https://api.fda.gov/drug/label.json?search="
                       f"openfda.generic_name:%22{generic}%22",
                "text": "\n".join(parts),
            })
            n += 1
        print(f"{n} document(s)")

    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d) + "\n")
    chars = sum(len(d["text"]) for d in docs)
    print(f"\n  {len(docs)} documents, {chars:,} characters "
          f"-> {CORPUS.relative_to(ROOT)}")
    if not docs:
        print("  NOTE: empty corpus. openFDA returned nothing for any drug — "
              "check the network, not the parser.")
    return 0


def load(path=None):
    p = Path(path) if path else CORPUS
    if not p.exists():
        return None
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# --------------------------------------------------------------------------
# BM25
# --------------------------------------------------------------------------

class BM25:
    def __init__(self, docs):
        self.docs = docs
        self.toks = [tokenize(d["title"] + " " + d["text"]) for d in docs]
        self.len = [len(t) for t in self.toks]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 0.0
        self.tf = [Counter(t) for t in self.toks]
        df = Counter()
        for t in self.toks:
            df.update(set(t))
        n = len(docs)
        # +1 inside the log keeps the IDF non-negative: without it a term in
        # more than half the documents scores negative and actively pushes
        # matching documents DOWN the ranking.
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5))
                    for w, c in df.items()}

    def search(self, query, top=10):
        q = tokenize(query)
        scored = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if not f:
                    continue
                denom = f + K1 * (1 - B + B * self.len[i] / (self.avg or 1))
                s += self.idf.get(w, 0.0) * f * (K1 + 1) / denom
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        return [(s, self.docs[i]) for s, i in scored[:top]]


def snippet(text, query, width=220):
    """Show the first place a query term actually appears."""
    q = set(tokenize(query))
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9\-]*", text or ""):
        if m.group(0).lower() in q:
            a = max(0, m.start() - width // 3)
            return ("…" if a else "") + \
                   " ".join(text[a:a + width].split()) + "…"
    return " ".join((text or "")[:width].split()) + "…"


# --------------------------------------------------------------------------

def query_cmd(q, top, corpus_path=None):
    docs = load(corpus_path)
    if docs is None:
        print(f"No corpus. Build it first:  make rag-build", file=sys.stderr)
        return 1
    if not docs:
        print("Corpus is empty.", file=sys.stderr)
        return 1
    hits = BM25(docs).search(q, top)
    if not hits:
        print(f'  no match for "{q}" in {len(docs)} documents')
        return 0
    print(f'  "{q}" — {len(hits)} of {len(docs)} documents\n')
    for rank, (score, d) in enumerate(hits, 1):
        print(f"  {rank}. [{score:5.2f}] {d['title']}")
        print(f"      {d['kind']}  {d.get('date','')}  {d.get('status','')}")
        print(f"      {snippet(d['text'], q)}")
        print(f"      {d['url']}\n")
    return 0


def selftest():
    docs = load(FIXTURE_CORPUS)
    if docs is None:
        print(f"missing fixture corpus {FIXTURE_CORPUS}", file=sys.stderr)
        return 1
    bm = BM25(docs)

    def top_id(q):
        h = bm.search(q, 1)
        return h[0][1]["id"] if h else None

    checks = [
        ("a distinctive term retrieves its own document",
         top_id("hyaluronidase") == "crl-b"),
        ("a second distinctive term retrieves the other one",
         top_id("sotorasib") == "crl-a"),
        ("a term in no document returns nothing",
         bm.search("zzzznotpresent", 5) == []),
        # This assertion MUST require hits before checking their sign. The
        # obvious form -- all(s > 0 for s, _ in bm.search(...)) -- is vacuously
        # true when the search returns nothing, and with the negative-IDF bug
        # it returns exactly nothing, because search() drops non-positive
        # scores. Written that way the test passed against a deliberately
        # broken IDF. Requiring the count is what makes it a test.
        ("a term in EVERY document is still found and scores positive "
         "(the classic BM25 negative-IDF bug)",
         len(bm.search("fda", 10)) == 3
         and all(s > 0 for s, _ in bm.search("fda", 10))),
        ("multi-term query ranks the document containing both first",
         top_id("dose selection sotorasib") == "crl-a"),
        ("stopwords alone match nothing",
         bm.search("the and of", 5) == []),
        ("OCR debris is not indexed as tokens",
         "n" not in bm.idf and "e" not in bm.idf),
        ("snippet centres on the query term",
         "hyaluronidase" in snippet(
             [d for d in docs if d["id"] == "crl-b"][0]["text"],
             "hyaluronidase").lower()),
    ]
    width = max(len(c[0]) for c in checks)
    bad = sum(not ok for _, ok in checks)
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:{width}s}")
    print(f"\n  {len(checks)-bad}/{len(checks)} checks passed")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="search terms")
    ap.add_argument("--build", action="store_true", help="build the corpus")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--top", type=int, default=8)
    a = ap.parse_args()
    if a.build:
        return build()
    if a.selftest:
        return selftest()
    if not a.query:
        ap.print_help()
        return 1
    return query_cmd(" ".join(a.query), a.top)


if __name__ == "__main__":
    sys.exit(main())
