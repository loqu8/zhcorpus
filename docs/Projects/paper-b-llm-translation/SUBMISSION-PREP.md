# ARR October 2026 Submission — Prep Package

**Target:** ARR October 12, 2026 → NAACL / COLING 2027 Findings track
**Written:** 2026-08-11
**Status:** All artifacts prepped. Execution takes ~45 min on submission day.

---

## 1. Two external services to set up

Both are free, academic, no-cost. Reviewers need no login.

### A. Anonymous mirror — `anonymous.4open.science`

Purpose: satisfy ARR's double-blind rule while still letting reviewers browse
the code. The service takes our public GitHub repo and creates an
anonymized static mirror at a random URL like
`anonymous.4open.science/r/dictionarium-sinicum-XXXX/`.

### B. Zenodo DOI for `dictmaster.db`

Purpose: permanent citable archive for the 2 GB SQLite database. The paper
lists this DOI in §3 Data Sources so reviewers can independently download
the full dictionary artifact.

---

## 2. Repository state at submission time

**Source repo (already public):** `github.com/loqu8/dictionarium-sinicum` @ tag `0.3.1`

**Snapshot on disk:**

| Path | Content | Size |
|------|---------|------|
| `~/Projects/loqu8/dictionarium-sinicum/` | Working checkout at v0.3.1 | ~2 MB (no data) |
| `~/Projects/loqu8/zhcorpus/data/artifacts/dictmaster.db` | Full 428K-headword × 18-lang DB | 2,058,850,304 B (1.92 GiB) |
| SHA-256 of DB | `e647e1638a53d033be9ff2f58103cbb5876393f7741f1ab93535bec40c8ea512` | — |

---

## 3. anonymous.4open.science recipe

### Step-by-step (browser)

1. Log into GitHub in one tab (needed to authorize the anon-github OAuth).
2. Open `https://anonymous.4open.science/` in another tab.
3. Click **"Anonymize a new repository"**.
4. Paste the source repo URL:
   ```
   https://github.com/loqu8/dictionarium-sinicum
   ```
5. Select branch `master`. Pin to tag `0.3.1` (or the latest tag at submit time).
6. **Repository name field** (this becomes the URL slug): pick something
   generic like `dictionarium-sinicum-arr2026-XXXX` where XXXX is a random
   suffix the service adds — or accept the default.
7. Under **"terms to replace"** (all case-insensitive), paste this list
   verbatim, one per line. The list is intentionally defensive: strings
   not found in the repo are silent no-ops, but a missed identifier is
   a desk-reject risk. False positives cost nothing; false negatives
   are catastrophic.

   ```
   Loqu8, Inc.
   Loqu8
   loqu8
   LOQU8
   E. Timothy Uy
   E. Timothy
   Timothy Uy
   Timothy
   Tim Uy
   Tim
   Uy
   tofutim
   tim@gig8.com
   tim@loqu8.com
   torque@gmail.com
   torque
   loqu8.com
   gig8.com
   Bellingham
   /home/tim/
   0009-0008-8717-2249
   ```

   Note: bare `Tim` will also match variable names or "TODO Tim" style
   comments in code. Reviewers correctly interpret `XXXX` as an
   anonymization mark, so this is fine — better a cluttered mirror
   than a name leak.

8. Under **"paths to exclude"** (comma or newline-separated):

   ```
   .env
   .env.*
   data/artifacts/
   *.db
   *.db-journal
   ```

   (Most of these are gitignored so shouldn't be present anyway, but list
   defensively.)

9. **Keep** these in the mirror (they're safe or intentionally anonymized):
   - `LICENSE` (Apache-2.0 boilerplate; "Loqu8" gets replaced with XXXX)
   - `NOTICE` (same; safe after replacement)
   - `CITATION.cff` (author names and ORCID are on the replace list)
   - `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `pyproject.toml`
     (all identifying strings on the replace list)

10. Click **"Anonymize"**. The mirror is generated in seconds.
11. **Copy the shareable URL** — looks like:
    ```
    https://anonymous.4open.science/r/dictionarium-sinicum-XXXX/
    ```
    Paste this into `[ANON_MIRROR_URL]` in the paper (see §5 below).

### Verification pass (5 min)

After the mirror is live, open it and verify:

- [ ] Search page for `Loqu8` — should show `XXXX` (or `[ANONYMIZED]`) instead.
- [ ] Open `CITATION.cff` — author names + ORCID should be redacted.
- [ ] Open `LICENSE` line 189 — "Copyright 2026 Loqu8, Inc." should read
      "Copyright 2026 XXXX".
- [ ] Open `NOTICE` — same.
- [ ] Open `src/dictmaster/build_master.py` line 574 — the hardcoded
      `/home/tim/Projects/loqu8/...` path should be redacted.
- [ ] Open `pyproject.toml` — 4 URL fields + author name should be redacted.
- [ ] Commit-history tab (if present) — anon-github strips author info
      automatically.

If any leak survives, add the missing term to the replace list and
regenerate.

### Retention

- Default: 30 days from creation, extendable via a button on the
  anonymized page.
- Extend to **6 months** immediately after creation so the mirror stays
  live through the entire ARR review cycle (Oct 12 submission →
  Dec 20 meta-reviews → any late reviewer requests).

### Timing recommendation

Create the mirror **2 days before submission** (Oct 10). Not sooner — if
you make late repo edits, you'd need to regenerate the mirror. Not on
submission day — leaves no room for verification-pass fixes.

---

## 4. Zenodo recipe

### Step-by-step (browser)

1. Log into `zenodo.org` (uses ORCID or email). Tim's ORCID is
   `0009-0008-8717-2249`.
2. Click **"New Upload"**.
3. **Upload** `dictmaster.db`. On a fast connection this takes ~5 min for
   2 GB. On slower — plan accordingly.

### Metadata fields

Paste these verbatim (Zenodo lets you edit any field after publish, so
minor tweaks after DOI mint are fine):

| Field | Value |
|-------|-------|
| **Resource type** | Dataset |
| **Title** | `Dictionarium Sinicum: A Multilingual Chinese Dictionary (428K headwords × 18 languages)` |
| **Creators** | `Anonymous` (single entry; affiliation blank) — **change to real names after decision** |
| **Publication date** | Auto (today) |
| **DOI** | Auto-mint (leave "reserve DOI" checked) |
| **Description** | See "Description text" block below |
| **Keywords** | `chinese; dictionary; lexicography; multilingual; LLM-generated; CC-CEDICT; CC-CIDICT; HanDeDict; CFDICT; cantonese; hokkien; minimax; low-resource; NLP; ARR October 2026` |
| **Additional notes** | `Anonymized for double-blind review. Author identities and affiliations will be revealed post-decision.` |
| **License** | `Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)` — matches the paper |
| **Related identifiers** | (leave blank for submission; add source-code repo DOI after acceptance) |
| **Language** | Chinese (zh) primary; multilingual |
| **Communities** | Do NOT join any community for submission (would reveal author). Add post-decision. |
| **Version** | `1.0.0-arr2026` |

### Description text (paste into Description field)

```
Dictionarium Sinicum is an open multilingual Chinese dictionary
comprising 428,073 headwords with definitions in 18 target languages
(English, German, French, Indonesian, Spanish, Swedish, Japanese,
Korean, Russian, Vietnamese, Tagalog, Persian, Dutch, Portuguese,
Arabic, Thai, Hindi, Italian), constructed by merging seven
community-maintained dictionaries (CC-CEDICT, HanDeDict, CFDICT,
CC-CIDICT, CHEDICC, Wiktextract, JMdict) with glosses generated by
a single open-weight LLM (MiniMax M2.5).

This artifact contains the full SQLite database (~2 GB) with two
tables:
  * headwords (428,073 rows): traditional, simplified, pinyin,
    part-of-speech, source-frequency, target-frequency
  * definitions (~11.1 M rows): headword_id, lang, source,
    definition text, confidence tag

Also included via schema: 511,514 Cantonese and Hokkien dialect
forms from 18 open sources.

SHA-256:
e647e1638a53d033be9ff2f58103cbb5876393f7741f1ab93535bec40c8ea512

Companion code (anonymized during ARR review):
[ANON_MIRROR_URL will be added at submission time]

Submitted to ACL Rolling Review, October 2026 cycle. Author
identities and affiliations will be revealed after review decision.

License: CC BY-SA 4.0. Source dictionaries retain their original
CC BY-SA licenses (3.0 or 4.0 depending on source).
```

4. Click **"Save"** (draft), then **"Publish"** → DOI mints instantly
   (looks like `10.5281/zenodo.XXXXXXX`).
5. Copy the DOI. This is `[ZENODO_DOI]` in the paper patches below.

### Post-decision edit (after acceptance)

Zenodo allows editing metadata without changing the DOI or minting a
new version. After acceptance:

1. Log back in.
2. Find the record → click **"Edit"**.
3. Replace **Creators**: `Anonymous` → real author info (name, ORCID,
   affiliation).
4. Update **Additional notes**: strike the "anonymized" sentence, add
   a "Published in [venue] YYYY, cite as: [bibtex]" line.
5. Optional: join relevant Zenodo communities.
6. Save. Same DOI, updated metadata. No re-upload.

### Timing recommendation

Upload **3-4 days before submission** (Oct 8-9). Rationale:
- Zenodo DOI is instant, but the 2 GB upload can take 5-30 min
  depending on connection.
- Gives you time to backfill the DOI into the paper `[ZENODO_DOI]`
  placeholder and rebuild the PDF.
- Leaves a buffer if Zenodo has an outage or metadata needs revision.

---

## 5. Paper patches to apply after both services are set up

### 5.1 Add a "Data and Code Availability" section

Insert this immediately AFTER the Conclusion (line 566 area, before the
Acknowledgments comment block or `\bibliography`):

```latex
%% ============================================================
\section*{Data and Code Availability}
\label{sec:availability}

The full \textit{Dictionarium Sinicum} SQLite database (2\,GB,
428{,}073 headwords $\times$ 18 languages, SHA-256
\texttt{e647e163\ldots8ea512}) is archived at
Zenodo:~\url{[ZENODO_DOI]}. All pipeline code, evaluation scripts,
and reproducibility artifacts (Apache-2.0 licensed) are mirrored
anonymously at~\url{[ANON_MIRROR_URL]} for the review period; the
production repository URL will be provided in the camera-ready.
```

### 5.2 Update `dictionarium-sinicum/README.md`

Add near the top (after the badges, before "Quickstart"):

```markdown
## Data availability

The full 2 GB SQLite database (`dictmaster.db`) is archived at Zenodo:
**DOI: [ZENODO_DOI]**

SHA-256: `e647e1638a53d033be9ff2f58103cbb5876393f7741f1ab93535bec40c8ea512`

Download and place at `data/artifacts/dictmaster.db` before running eval
scripts. Community-dictionary source files retain their original licenses
(CC BY-SA 3.0 or 4.0 depending on source).
```

### 5.3 Update `dictionarium-sinicum/CITATION.cff`

Add a `preferred-citation` block at the end (below existing top-level
`authors` block):

```yaml
preferred-citation:
  type: dataset
  title: "Dictionarium Sinicum: A Multilingual Chinese Dictionary (428K headwords × 18 languages)"
  doi: "[ZENODO_DOI_bare_no_url]"
  year: 2026
  authors:
    - given-names: "E. Timothy"
      family-names: "Uy"
      affiliation: "Loqu8, Inc."
      orcid: "https://orcid.org/0009-0008-8717-2249"
```

(Post-decision only. During the submission window, this file is
`Anonymous`-fied by the anon-mirror.)

---

## 6. Submission-day runbook (Oct 12, ~45 min total)

### T-3 days (Oct 9)

- [ ] Upload `dictmaster.db` to Zenodo (recipe §4).
- [ ] Copy DOI. Paste into `[ZENODO_DOI]` placeholder in
      `SUBMISSION-PREP.md` for reference.
- [ ] Apply patch §5.1 to `dictionarium_sinicum.tex` (paper) — with
      `[ZENODO_DOI]` filled but `[ANON_MIRROR_URL]` still as
      placeholder.
- [ ] Apply patch §5.2 to `README.md` (dictionarium-sinicum repo).
- [ ] Rebuild the paper (`lualatex + bibtex + 2x lualatex`); verify
      still 8 body pages.
- [ ] Commit + release bump on dictionarium-sinicum (v0.3.2 or v0.4.0)
      — this becomes the version anonymous.4open.science mirrors.
- [ ] Push to GitHub. This is the last dict-sinicum commit before the
      anon-mirror is generated.

### T-2 days (Oct 10)

- [ ] Create anon-mirror at anonymous.4open.science (recipe §3).
- [ ] Run verification pass (recipe §3, checklist).
- [ ] Extend retention to 6 months.
- [ ] Copy anon URL. Paste into `[ANON_MIRROR_URL]` in the tex.
- [ ] Rebuild paper. Verify 8 body pages, no undefined references.
- [ ] Commit paper (`paper-b: fill anon-mirror URL for submission`)
      on zhcorpus develop. Do NOT tag/release; this is a submission
      snapshot, not a public release.
- [ ] Take a fresh backup of the built PDF into a safe place.

### T-0 (Oct 12, submission day)

- [ ] Open ARR portal (openreview.net for ACL, or ARR-specific portal
      if migrated).
- [ ] Log in. Start new submission.
- [ ] Track: check that the paper title matches abstract.
- [ ] Upload the PDF.
- [ ] Upload supplementary ZIP (optional but recommended): include the
      `eval/results/*.json` files as evidence of the numbers in the
      paper.
- [ ] Fill in author info in the portal (portal keeps this separate
      from the anonymous PDF).
- [ ] Fill in a **response letter to the March 2026 reviewers** in the
      "revision notes" field. Point to specific paper sections that
      address each objection. See §7 below.
- [ ] Submit. Screenshot the confirmation. Save.

### Failure modes + rollback

| Failure | Rollback |
|---------|----------|
| Zenodo upload fails partway | Retry; the upload is chunked and resumable. If Zenodo is down entirely, use the fallback: cite the SHA-256 in the paper and say "artifact available on request" — LESS ideal but survives service outage. |
| Anon-mirror shows a leak in verification | Add missing term to replace list, click "regenerate mirror" — same URL, updated content. |
| PDF grows past 8 body pages after adding availability section | The section is ~4 lines; if it pushes, tighten a Future Work bullet or trim §5.3 back-translation paragraph. |
| ARR portal rejects submission | Read the specific error. If a formatting issue, fix + resubmit. |

---

## 7. Response letter to March 2026 reviewers

Draft this ~1 week before submission. One paragraph per major reviewer
objection, pointing to the paper section that now addresses it. Skeleton:

- **SamJ, "consider COMET / BERTScore":** addressed by new Table 7
  columns (BSc F1, COMET-DA) and reference-free CometKiwi across all
  18 languages (§5.2, §5.3, Table 12).
- **SamJ, "small-scale human eval":** framed as future work pending
  per-language recruitment funding (§7).
- **SamJ, "second-model verification of backfill":** addressed by
  §5.6, using an open-weight verifier (Gemma-4-31B) — n=2800 rated,
  macro 4.47/5.
- **AC / gKVr, "pivot bias / Anglocentric":** addressed by §5.4
  pivot-ablation with Llama-3.3-70B on vi + th — pivot bias is
  language-dependent, not uniform quality loss.
- **AC / gKVr, "single proprietary model":** MiniMax M2.5 is
  open-weight (paper §1, §4.1, §6, §7 now explicitly note this;
  Fireworks + NIM third-party hosting supports reproducibility).
- **AC, "error analysis" / gKVr, "per-language breakdown":** addressed
  by §5.5 and Appendix C tab:error-taxonomy (18-lang full-corpus
  automated error signals).
- **gKVr, "limited eval scope on 12 non-community-ref langs":**
  addressed by CometKiwi across all 18 (Table 12) and Gemma-4-31B
  verifier across all 14 non-community-ref langs (Table implicit in
  §5.6).
- **PDF formatting typos (SamJ):** hyphenation glitches fixed (Tier 1
  #2 in the revision plan, committed 4fd52be on the develop branch).

---

## 8. Time budget summary

| Task | Elapsed |
|------|---------|
| Zenodo upload + DOI + metadata (T-3) | 30 min |
| Anon-mirror + verification (T-2) | 20 min |
| Paper backfill + rebuild + commit (T-2) | 15 min |
| Response letter draft (T-1) | 60 min |
| Actual submission (T-0) | 30 min |
| **Total elapsed effort** | **~2.5 hrs spread over 3-4 days** |

Cost: **$0** (both services free, ARR/OpenReview submission free).

---

## Appendix A: If Zenodo has a 2 GB upload issue

Fallback options in order of preference:

1. **Retry** — Zenodo uses chunked uploads and is generally reliable.
2. **Compress with xz first** — `xz -9e dictmaster.db` typically gets
   SQLite DBs down by ~60%. Upload the `.xz` file; note the SHA-256
   of the compressed AND uncompressed files in the metadata.
3. **Split into shards** — Zenodo allows up to 100 files per record.
   `split -b 500M dictmaster.db dictmaster.db.part.`
4. **Alternative host** — Harvard Dataverse (free, 2.5 TB per dataset)
   or figshare (free, 20 GB per file). Both provide DOIs. Zenodo is
   preferred for NLP community familiarity.

## Appendix B: If anonymous.4open.science is rate-limited or down

Fallback: build an anonymized zip locally and attach as ACL
supplementary material:

```bash
cd ~/Projects/loqu8/dictionarium-sinicum
git archive --format=zip HEAD -o /tmp/dictionarium-sinicum-anon.zip
# then manually redact identifying strings in the zip:
zip -d /tmp/dictionarium-sinicum-anon.zip 'CITATION.cff' 'NOTICE'
# review LICENSE, README.md, etc. manually
```

Less browsable than the anon-mirror; only use as fallback.
