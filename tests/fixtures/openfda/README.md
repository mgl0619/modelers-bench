# openFDA fixtures

**These are SYNTHETIC.** They are not recorded API responses.

Every field name and value *shape* here was confirmed against the live openFDA
API on 2026-08-31 — `drug/drugsfda.json`, `drug/label.json` and
`transparency/crl.json` were each queried and their result fields read off. The
files themselves were then written by hand, small enough to read in one screen.

They exist so `scripts/fetch_fda.py` can be tested with no network: the parsing,
the brand-name guard and the CSV shape are all exercised offline, in CI, forever.
They are **not** evidence about what openFDA actually returns for any drug. For
that, run the fetcher against the API.

The `drugsfda` fixture deliberately contains a **brand mismatch** — a second
application whose brand is `KEYTRUDA QLEX` — so the guard that catches the
subcutaneous-coformulation trap is exercised rather than assumed.
