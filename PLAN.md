# The Modeler's Bench — build plan

*An open, reproducible curriculum for quantitative pharmacology — one drug, many models, every result runnable.*

| | |
|---|---|
| Shape | Docs/course site + thin discussion layer |
| Year-1 cash cost | ~$15 (a domain) |
| Time budget | 6 h/week, solo |
| Target at month 12 | ~45 lessons, 3 learner paths |

Drafted 21 Aug 2026.

---

## 1. Positioning — what exists and what it leaves open

| What exists | Does well | Leaves open |
|---|---|---|
| **ISoP Discussion Forum** (discuss.go-isop.org) | Live practitioner Q&A across PopPK, PBPK, QSP, NONMEM, R; ~15 categories | Threads, not a curriculum. Answers are prose, not runnable. Nothing sequences a beginner. |
| **ISoP Learn / ACCP–UMD web resource** | Curated beginner theory, definitions, NONMEM+R code library, videos | Membership-shaped, refreshed slowly, weighted to PopPK; little PBPK/QSP/Bayes. |
| **Cohort courses** (PMx Africa Moodle, universities, society workshops) | Mentored, structured, credentialed | Enrollment windows, capacity, fees. Nothing to hand someone on a Tuesday. |
| **Vendor training** (Certara, Simulations Plus, Metrum, OSP) | Deep, well-produced, current | Tool-shaped not concept-shaped; no cross-tool comparison, by design. |
| **GitHub / blogs / YouTube / preprints** | Free, current, sometimes excellent | Unindexed, uneven, no path, no maintenance guarantee. |

**The gap.** No free, version-controlled, publicly maintained curriculum that (a) runs end to end on open tools, (b) carries a learner from NCA through PopPK, PBPK and QSP to an actual development decision as *one* path, (c) shows the same drug problem in more than one modeling idiom, and (d) is maintained in the open so it doesn't rot.

**Strategic consequence: build the curriculum, rent the community.** A rival general forum to ISoP's would split a small field and lose. Discussion attaches to lessons (one thread per page); you participate in the existing forum rather than compete with it. This removes the biggest solo-maintainer cost: moderation.

---

## 2. Thesis and audiences

> Learn quantitative pharmacology by rebuilding the same set of decisions about the same molecules — in the tools a sponsor would actually use, with data whose true parameters you can check your answer against.

Two differentiators sit in that sentence. **Same molecules**: a shared case spine means NCA, TMDD, covariate modeling, DDI prediction and dose optimization are facets of one problem, not five unrelated courses. **True parameters**: teaching data are simulated from documented generative models, so every exercise has a right answer — and no license or IP question touches it.

**Three paths, one library.** Paths are *orderings* of a shared module library, not separate content. This is the difference between something one person can maintain and something that collapses in month seven.

- **PATH-A — The New Modeler** (junior industry, 0–5 yr): *your first defensible PopPK analysis in eight weeks.* Workflow, data assembly, diagnostics, how the result gets used. Ends at a written model report, not a converged run.
- **PATH-B — The Trainee** (grad student, postdoc): *from ODEs to a model you can defend in a viva.* Theory, estimation mechanics, identifiability, uncertainty. Ends at a reproducible, citable analysis with a Zenodo DOI.
- **PATH-C — The Crossover** (bench pharmacologist, clinician, DMPK, statistician, data scientist): *read a modeling report without bluffing*, then branch into A or B — or stop satisfied. Both are wins.

---

## 3. Curriculum — eight strands, deliberately wider than the usual four

PBPK, QSP, PKPD and PopPK/PD are load-bearing but not sufficient. What separates a competent modeler from a valuable one is the strand around them: statistics, decision science, and the engineering craft that makes an analysis survive a submission.

**P — Pharmacology from the beginning (18).** Added 2026-08-25 after a review
found the curriculum taught modelling to people who already knew pharmacology,
and offered nothing to the statisticians, engineers and data scientists crossing
over. Assumes no biology at all. Part 1 targets and binding · Part 2 the four
ADME domains · Part 3 physiology for modellers · Part 4 dose–response, biomarkers
and safety · Part 5 how a drug gets made and how therapeutic areas differ. Nine
of the eighteen carry runnable notebooks. Sits ahead of S0; Path C starts here,
Paths A and B name it as a skippable prerequisite.

**S0 — Foundations (6).** Compartments and ODEs from first principles · units, scaling, allometry · data assembly (NM-TRAN, ADPPK, CDISC lineage) · R/Python/Julia stack choice · git and project structure · how to read a modeling report.

**S1 — PK/PD core (8).** NCA and when it's enough · 1/2/3-compartment, absorption, flip-flop · nonlinear elimination and TMDD (full → QSS → MM) · turnover and indirect response · Emax and exposure–response abuses · biologics (mAbs, ADCs, bispecifics, ADA) · cell and gene therapy kinetics (expansion, contraction, persistence) · target engagement and biomarker chains.

**S2 — PopPK/PD (9, spine of Path A).** Why mixed effects; what η and ε really are · **Rosetta: one model in NONMEM, nlmixr2, Monolix, Pumas** · FOCE-I / SAEM / Laplace · covariate modeling and selection traps · residual error, BLQ, missingness, adherence · evaluation (GOF, VPC/pcVPC, NPDE, bootstrap, shrinkage) · simulation and uncertainty propagation · writing the analysis plan before fitting.

**S3 — PBPK (8).** Whole-body physiology and partitioning · IVIVE (permeability, metabolism, transporters) · oral absorption (ACAT/ADAM class) · DDI prediction and regulatory expectations · special populations (pediatric, pregnancy, renal/hepatic, obesity) · hands-on PK-Sim/MoBi · platform verification vs compound qualification · PBPK in submissions.

**S4 — QSP and systems (8).** Pathway diagram to defensible ODE system · structural and practical identifiability · global sensitivity analysis (Morris, Sobol) · virtual populations and plausible-patient generation · model reduction and lumping · immuno-oncology and CAR-T cytokine dynamics · bridging QSP to PopPK for a decision · credibility assessment (V&V 40 thinking).

**S5 — Statistics, Bayes and ML (8, the widening strand).** Bayesian PKPD with Stan/Torsten and brms · priors that encode pharmacology · MCMC diagnostics as model criticism · model-based meta-analysis · ML for covariate discovery and why it usually loses · neural ODEs / universal differential equations (SciML) · calibration and honest UQ · LLM and agentic workflows: where they help, where they fabricate.

**S6 — Decisions and MIDD (8).** The MIDD framework · clinical trial simulation end to end · dose optimization and the Project Optimus shift · adaptive designs and interim rules · probability of success, assurance, go/no-go · E–R for efficacy and safety in labeling · briefing documents and regulatory interactions · qualification vs validation.

**S7 — Practice and craft (7, runs alongside).** Reproducible scaffolds (renv/uv, targets/snakemake, containers) · versioning an analysis dossier · plot craft · writing the modeling report · presenting to clinicians, statisticians, executives · peer-reviewing a model · QC in a GxP-adjacent world.

62 lessons at full build; year one targets ~45, weighted to S0–S3 and S6.

---

## 4. The lesson unit — seven fixed slots

A fixed template is the highest-leverage decision in this plan: authoring becomes mechanical, contribution becomes possible, and lesson 30 costs less than lesson 3.

| Slot | Contents | Budget |
|---|---|---|
| 1. The decision | One sentence: which real development decision this serves. If you can't write it, the lesson doesn't exist yet. | 5 min |
| 2. Concept | 800–1,200 words, one hand-made figure, no derivation for its own sake. | 60 min |
| 3. Runnable notebook | Open tools, one case dataset, executes top to bottom in CI. **No lesson ships without this.** | 45 min |
| 4. Rosetta panel | Quarto tabset: same fit in a second tool (R↔Python↔Julia, nlmixr2↔NONMEM). | 20 min |
| 5. Failure mode | Break it on purpose, show the diagnostic. Senior people can write this; nobody else can. | 20 min |
| 6. Self-check | Three questions, folded answers. Because data are simulated, one is always "how close to truth?" | 10 min |
| 7. Thread + citations | giscus thread, 2–3 papers, a "seen in the wild" note from practice. | 10 min |

**≈2.8 h per lesson** once case data exist — the load-bearing assumption of the roadmap. Treat it as a measurement to make in Phase 0, not a fact.

*Your unfair advantage is slots 1 and 5.* Which decision this serves, and how it fails, is what thirty years buys and what no textbook, vendor course or language model reliably supplies. When time is tight, protect those two and let the prose be plainer.

---

## 5. The case spine — four molecules, carried through everything

Each case is **simulated from a documented generative model**, published with its true parameters and generating script. Nothing derives from company data, licensed datasets or patient records — which removes the IP/consent question entirely and makes the pedagogy stronger.

| Case | What it is | Strands it carries |
|---|---|---|
| `CASE-SM` "Ozanib" | Oral small molecule, CYP3A4 substrate, food effect, moderate DDI liability | S0 assembly → S1 compartmental → S2 covariates → S3 DDI and pediatric → S6 labeling |
| `CASE-MAB` "Tezumab" | IgG1 mAb, TMDD, subcutaneous, immunogenicity | S1 TMDD → S2 nonlinear PopPK → S4 receptor occupancy → S6 exposure–response |
| `CASE-CELL` "CT-19" | CD19 CAR-T: expansion, contraction, persistence, CRS | S1 cell kinetics → S4 QSP cytokine network → S6 safety E–R and dose selection |
| `CASE-ONC` | Oncology dose-optimization exercise, Project Optimus framing | S6 trial simulation, go/no-go; capstone for all three paths |

Use the small public teaching sets (theophylline, warfarin, Indometh, CDISC pilot ADaM) where real-world messiness helps — never as the spine, because they carry no truth to check against.

---

## 6. Stack

| Layer | Choice | Why | $/yr |
|---|---|---|---|
| Authoring | **Quarto** | Executes R, Python, Julia in one document; native tabsets (Rosetta panels), cross-refs, citations, code-folding. MkDocs/Docusaurus would need bolted-on execution. | 0 |
| Source | Public GitHub monorepo | Content, code and discussion in one place; PRs are the contribution mechanism. | 0 |
| Hosting | GitHub Pages (Cloudflare Pages as escape hatch) | ~1 GB site / 100 GB monthly bandwidth soft caps — ample for text and figures. | 0 |
| Discussion | **giscus → GitHub Discussions** | Thread per lesson, GitHub-authenticated. No spam surface, no moderation queue, no database. | 0 |
| Search | Pagefind | Static index built at deploy, works offline. | 0 |
| Interactivity | Colab/Binder links; JupyterLite for pure-Python; WebR for small R demos | Browser execution covers SciPy-class work. It **cannot** run NONMEM or PK-Sim — those ship a container recipe and a recorded walkthrough. Say so on the page. | 0 |
| CI | GitHub Actions | Every notebook re-executes on every push. This is what stops silent rot. | 0 |
| Analytics | GoatCounter or Cloudflare Web Analytics | Cookieless, no consent banner. | 0 |
| List | Buttondown free tier + Releases RSS | A monthly "what shipped" note is the cheapest retention there is. | 0 |
| Archival DOI | Zenodo on each release | Makes it citable — converts effort into academic credit and gives contributors a reason. | 0 |
| Domain | One `.org` | The only thing worth paying for in year one. | ~15 |

### Repository layout

```
modelers-bench/
├── _quarto.yml            # site config, nav, paths
├── paths/                 # PATH-A / B / C — orderings only, no content
├── lessons/
│   └── s2-04-covariates/
│       ├── index.qmd      # slots 1,2,5,6,7
│       ├── notebook.qmd   # slot 3 — executed in CI
│       ├── rosetta.qmd    # slot 4
│       └── meta.yml       # strand, path, prereqs, reviewed: 2026-09-01
├── cases/
│   └── case-sm/
│       ├── generate.R     # the truth — versioned, re-runnable
│       ├── truth.yml      # true parameter values
│       └── data/
├── _extensions/           # theme, callout styles
└── .github/workflows/     # build, execute-all, link-check, staleness-flag
```

`meta.yml` earns its place: a `reviewed:` date plus a scheduled CI job that opens an issue for anything older than 18 months is the whole content-decay strategy, and it costs an afternoon.

---

## 7. Community, staged

**Anti-goal: do not launch an empty forum.** An empty forum is worse than none — a visible signal that nobody is here, and very hard to recover from. Each stage below is gated on demand that already exists.

**Stage 1 — threads attached to lessons.** From launch, giscus, ~0 h/week. Questions arrive attached to the paragraph that caused them, which is also your best signal for what to rewrite. *Seed with 25 pre-written Q&A threads* drawn from questions you have actually answered over thirty years — the difference between "quiet" and "dead".

**Stage 2 — a real forum, only if threads overflow.** Trigger: ≥30 threads/month, or ≥3 questions/week you can't answer alone. Discourse now has a free hosted plan (unlimited members, two staff seats, `.discourse.group` subdomain), so the cost is moderation time, not money. Categories mirror the eight strands. Precondition: two or three co-moderators recruited *before* opening, plus a public statement that ISoP's forum remains the place for field-wide discussion.

**Stage 3 — contributors.** Trigger: ≥5 people have opened a substantive PR or issue. "Adopt a lesson" ownership, named review rota, guest lessons with bylines, Zenodo authorship on releases. The DOI is the currency — academics can put it on a CV, a real incentive at zero cost.

**First hundred readers.** Soft launch to 20 people you know, with a direct ask ("work one lesson, tell me where you got stuck") · one lesson/month cross-posted as a substantive ISoP forum answer, contribution first · monthly office hour scheduled as a GitHub Discussion so the transcript becomes content · offer Path C to two university courses and one company's onboarding — institutional adoption beats individual signups by an order of magnitude · ACoP/PAGE poster on the teaching method, not a product pitch.

---

## 8. Twelve-month roadmap at 6 h/week

Six hours a week is ~290 h/year. At 2.8 h/lesson, authoring alone consumes 125 h for 45 lessons. Weekly split: **3.5 h authoring · 1 h code and data · 1 h community · 0.5 h ops.** Protect the first block absolutely.

**Phase 0 — weeks 1–4 (~24 h). Build the machine, publish nothing.**
Name, domain, repo, Quarto scaffold, theme, CI that executes every notebook · write the lesson template as an actual working lesson (the reference implementation) · generate `CASE-SM` with truth file and script · **measure your real hours-per-lesson and re-plan against it**.
*Ship: a private repo, one complete lesson, a green CI badge.*

**Phase 1 — months 2–4 (~72 h, 12 lessons). Path A end to end, then launch.**
S0 ×3, S1 ×4, S2 ×5 — raw data to a fitted, evaluated PopPK model · Pagefind, giscus, 25 seeded threads, Path-A landing page · soft launch to 20 people in month 3, fix what they trip on, public launch end of month 4.
*Ship: a site that already keeps its central promise for one audience. Twelve good lessons beat forty stubs.*

**Phase 2 — months 5–8 (~96 h, +16 lessons). Widen to PBPK and decisions.**
Finish S2, all of S3 (PK-Sim/MoBi hands-on), open S6 with trial simulation and dose optimization · `CASE-MAB` · first Rosetta panels (nlmixr2 ↔ NONMEM) · Path C assembled from existing lessons at near-zero marginal cost · newsletter and office hours begin; first guest lesson.
*Ship: 28 lessons, two complete paths, first Zenodo DOI.*

**Phase 3 — months 9–12 (~96 h, +17 lessons). QSP, Bayes/ML, hand off load.**
S4 with `CASE-CELL` · S5 Bayesian and SciML · S7 craft · contributor guide, three co-maintainers, review rota · Stage-2 forum decision made on metrics not enthusiasm · year-one review published openly.
*Ship: ~45 lessons; Paths A and C complete, Path B ~70%.*

**Cut list, in order** (the schedule will slip): Rosetta panels → `CASE-CELL` → newsletter → Path B depth. **Never cut** the runnable notebook, the failure-mode slot, or CI execution. Those three are the product.

---

## 9. Risk and governance

| Risk | Severity | Mitigation |
|---|---|---|
| **Employer IP / conflict of interest** — anything traceable to a real program or internal method | Highest | Written clearance before launch. Personal hardware and accounts only. Fully synthetic cases with published generating models. Explicit "views are my own"; no compound, program or internal terminology, ever. |
| **Solo burnout** — the standard cause of death | High | 6 h is the ceiling, not the floor. Template-driven authoring. Publish the roadmap so slipping is visible and normal. Recruit co-maintainers in Phase 3 whether or not it feels necessary. |
| **Proprietary tool licensing** (NONMEM, Monolix, Simcyp, GastroPlus) | Medium | Never redistribute software, keys or vendor model files. Teach on open tools (nlmixr2, mrgsolve, PK-Sim, Stan, Pumas academic terms); reference proprietary syntax and link to vendor docs. |
| **Content decay** | Medium | `reviewed:` dates, CI re-execution, staleness issue at 18 months, pinned environments (renv/uv lockfiles). |
| **Quiet launch** | Medium | Seeded threads, 20-person soft launch, institutional adoption as primary growth channel. |
| **Read as competition** by ISoP/ACCP | Low–Med | Explicit complementary positioning from day one, prominent links out, contribute to their forum, offer material to their education committees early rather than after it looks like a rival. |

**Licensing.** Content **CC BY-SA 4.0** — reusable in university teaching, derivatives stay open. (CC BY-NC-SA would block vendor and corporate-training reuse: defensible, but it also blocks the company-onboarding adoption channel, one of your best growth paths.) Code and data-generation scripts **MIT**. Standing disclaimer: educational material, illustrative models, not clinical guidance and not a regulatory position. Accessibility as policy: alt text on every figure, never meaning encoded in color alone — half the crossover audience reads on a phone.

---

## 10. Metrics and pivot criteria

| Type | Metric | Year-1 target |
|---|---|---|
| Leading | Lessons shipped per month | ≥ 4 |
| Leading | Lessons with a CI-executed notebook | 100% |
| Leading | Median time to first reply in a thread | < 48 h |
| Lagging | Monthly unique readers by month 12 | 1,000 |
| Lagging | Returning-reader share | ≥ 25% |
| Lagging | Self-reported path completions | ≥ 50 |
| Lagging | External contributors with a merged PR | ≥ 5 |
| Lagging | Courses or teams adopting a path | ≥ 2 |

**Pivot criteria at month 12, written in advance on purpose.** If monthly readers are under 300 *and* threads under 10/month *and* there are no outside contributors: stop adding lessons, cut a final Zenodo release, freeze the site as a static reference archive with a DOI, and let it sit there costing $15/year. That is a genuinely good outcome — a citable open curriculum that exists — and far better than two more years of slow, guilty maintenance. Decide now, while it's cheap to decide.

---

## 11. If it works

Not year-one activities; listed so the year-one architecture doesn't foreclose them. Open license, public repo and a DOI keep every door below open.

- **Society partnership** — ISoP or ACCP endorsement, or adoption of a path as an official trainee resource. Highest value, lowest cost; negotiate editorial independence carefully.
- **Sponsored strand** — a tool vendor funds a strand behind a written, public editorial firewall. Real money, real reputational exposure.
- **Paid cohort workshops** twice a year using the free material as the textbook. The open-core education model, and the likeliest to work here.
- **University adoption** as an assigned open textbook — for you, also a publication and teaching-portfolio line.
- **Education grant** (NIH R25-style, or an industry consortium) once there's a year of usage evidence.
- **A book** from the S0–S2 spine, site stays free. Publishers respond to traffic numbers, not proposals.

---

## 12. Next ten actions

1. Start the employer/institution IP clearance conversation. Nothing else matters until this is settled in writing.
2. Choose the name and register the `.org`. (*The Modeler's Bench* is the working name; *Open QP Commons* and *One Drug Many Models* are alternates.)
3. Create the public GitHub repo with the section-6 layout and a README stating the thesis in three sentences.
4. Scaffold Quarto, pick the two typefaces, build the theme once so you never think about design again.
5. Write `cases/case-sm/generate.R` and its `truth.yml`. The data spine comes before the first lesson.
6. Write `s2-04-covariates` completely, all seven slots — the hardest realistic lesson, as the reference implementation.
7. Time yourself doing it, and rewrite the section-8 arithmetic against the real number.
8. Stand up the CI workflow that re-executes every notebook and fails the build if any break.
9. Draft the 25 seeded Q&A threads in one sitting, from memory, while the template is fresh.
10. List the twenty people for the soft launch, by name, today.

---

*Landscape review covers ISoP's discussion forum and learning portal, the ACCP/University of Maryland web resource, Pharmacometrics Africa's Moodle portal, and vendor training from Certara, Simulations Plus, Metrum and Open Systems Pharmacology. Cost and platform-limit figures are current as of August 2026 and should be re-checked at Phase 0.*
