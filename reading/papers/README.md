# Your personal library

Put PDFs you download here. **This directory is gitignored** — `*.pdf` and
`*.epub` are blocked repository-wide, so nothing in here can be committed by
accident.

Why the separation:

- **Reading a paper you downloaded is fine.** Personal scholarly copies are
  ordinary practice, and free-to-read on PubMed Central means you may read it.
- **Redistributing it is not.** Most of the Reading page is
  all-rights-reserved, and the openly licensed remainder largely carries
  Creative Commons NC/ND terms that this project's CC BY-SA licence cannot
  absorb. See `../../reading.qmd` for the per-paper licence audit.

Do not hand-count the page here. It was written when the list held 28 works and
was wrong for months afterwards; the numbers now live in
`download-list.html`, which is generated.

A suggested naming scheme, so citations stay traceable:

    bergstrand-2011-pcvpc-PMC3085712.pdf
    beal-2001-blq-PMID11768292.pdf

`scripts/fetch_papers.py` applies this scheme for you:

    python3 scripts/fetch_papers.py --list    # regenerate download-list.html
    python3 scripts/fetch_papers.py --fetch   # collect what PMC allows

Keeping the PMID or PMC ID in the filename means you can always get back to the
record in `../../references.bib`.
