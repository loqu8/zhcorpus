# Paper Publication Playbook

Loqu8/Copyworks method for academic paper preparation and submission.

## The Stack

| Layer | Tool | Notes |
|-------|------|-------|
| Writing | Markdown draft in `docs/Projects/paper-X/draft.md` | Claude-editable, version-controlled |
| Typesetting | LaTeX with ACL style files | `acl.sty` from [acl-org/acl-style-files](https://github.com/acl-org/acl-style-files) |
| Editor | [Overleaf](https://www.overleaf.com) | Free, browser-based. The GUI everyone uses. |
| Compiler | LuaLaTeX (not pdfLaTeX) | Required for CJK characters + Arabic/Cyrillic |
| References | BibTeX with `acl_natbib.bst` | DOIs required for all ACL Anthology entries |
| Review | Multi-perspective Claude review gauntlet | See "Review Process" below |

## File Structure Per Paper

```
docs/Projects/paper-X/
├── draft.md              # Source of truth (Claude-editable)
├── prior-art.md          # Literature review + gap analysis
├── paper_name.tex        # LaTeX version (generated from draft.md)
├── references.bib        # BibTeX references
├── acl-style-files/      # Cloned from GitHub (gitignored)
│   ├── acl.sty
│   ├── acl_natbib.bst
│   └── ...
└── figures/              # Any figures (PDF/PNG)
```

## Workflow

### Phase 1: Research & Draft
1. Create `prior-art.md` with gap analysis and novelty rating
2. Write `draft.md` in Markdown — Claude can iterate on this quickly
3. Build any evaluation scripts in `tools/` with test coverage
4. Run evaluations, capture results

### Phase 2: Review Gauntlet (4 passes)
1. **Reviewer 1**: General NLP journal reviewer — structure, claims, evidence
2. **Reviewer 2**: Domain expert — methodology, technical depth, comparisons
3. **Reviewer 3**: Funder/program officer — impact, vision, fundability
4. **Buddy pass**: Honest editorial — cut bloat, fix narrative, kill darlings

Key lesson: Papers get WORSE after too many reviewer passes (bloated limitations, defensive over-qualification). The buddy pass fixes this.

### Phase 3: LaTeX Conversion
1. Clone ACL style files: `git clone https://github.com/acl-org/acl-style-files.git`
2. Convert `draft.md` → `.tex` using LuaLaTeX template (for CJK support)
3. Create `references.bib` with proper BibTeX entries + DOIs
4. Compile locally or upload to Overleaf

### Phase 4: Compile

**Local (preferred — no account needed):**
```bash
# Requires: sudo apt install texlive-full fonts-noto-cjk
cd docs/Projects/paper-X/
cp acl-style-files/acl.sty acl-style-files/acl_natbib.bst .
lualatex -interaction=nonstopmode paper.tex
bibtex paper
lualatex -interaction=nonstopmode paper.tex
lualatex -interaction=nonstopmode paper.tex
```

**Overleaf (alternative — browser-based GUI):**
1. Go to [overleaf.com](https://www.overleaf.com), create account
2. New Project → Upload Project (or blank + upload files)
3. Upload: `.tex`, `.bib`, `acl.sty`, `acl_natbib.bst`
4. **Menu → Compiler → LuaLaTeX** (critical for CJK!)
5. Compile and fix any font issues

### Phase 5: Submission
1. Change `\usepackage[review]{acl}` to verify anonymous mode
2. Final PDF check: fonts embedded, A4 paper, two-column
3. Submit to ARR (ACL Rolling Review) at [aclrollingreview.org](https://aclrollingreview.org)
4. After reviews, commit to venue (e.g., EMNLP)

## ACL/EMNLP Format Rules

- **Long paper**: 8 pages content + unlimited references + appendices
- **Short paper**: 4 pages content + unlimited references
- **Abstract**: ≤ 200 words
- **Paper size**: A4 (21cm × 29.7cm)
- **Font**: Times Roman, 11pt body
- **Anonymity**: Double-blind review. No author names, no self-citations revealing identity
- **Limitations section**: MANDATORY (unnumbered `\section*{Limitations}`)
- **Acknowledgments**: NOT in review version
- **References**: Need DOIs or ACL Anthology URLs
- **Non-English text**: Must include English translation + Latin transliteration

## LuaLaTeX CJK Setup

For papers with Chinese/Japanese/Korean characters, use LuaLaTeX:

```latex
\usepackage{luatexja-fontspec}
\setmainjfont{Noto Serif CJK SC}  % Chinese
```

Overleaf has Noto CJK fonts pre-installed. For local builds:
```bash
sudo apt install texlive-full fonts-noto-cjk
```

## LaTeX Tips for CJK Papers

- Use `~` for non-breaking spaces: `CC~BY-SA~4.0`
- Use `--` for en-dash, `---` for em-dash
- Approximate sign: `{\raise.17ex\hbox{$\scriptstyle\sim$}}` or just `$\sim$`
- Chinese in running text: just type it (LuaLaTeX handles it)
- Use `\textit{pinyin}` for romanization
- Use `\textbf{term}` sparingly — ACL style prefers italics for emphasis
- `\S\ref{sec:name}` for section cross-references
- `\citet{key}` for "Author (year)", `\citep{key}` for "(Author, year)"

## BibTeX Patterns

```bibtex
% Conference paper
@inproceedings{lu2024chainofdict,
    title = {Chain-of-Dictionary Prompting...},
    author = {Lu, Yikun and others},
    booktitle = {Proceedings of {EMNLP} 2024},
    pages = {958--976},
    year = {2024},
    publisher = {Association for Computational Linguistics},
    url = {https://aclanthology.org/2024.emnlp-main.58/}
}

% Journal article
@article{navigli2012babelnet,
    title = {{BabelNet}: The Automatic Construction...},
    author = {Navigli, Roberto and Ponzetto, Simone Paolo},
    journal = {Artificial Intelligence},
    volume = {193},
    pages = {217--250},
    year = {2012},
    doi = {10.1016/j.artint.2012.04.001}
}

% Online resource
@misc{cedict,
    title = {{CC-CEDICT}: Community-Maintained Dictionary},
    howpublished = {\url{https://cc-cedict.org/}},
    note = {CC BY-SA 4.0},
    year = {2024}
}
```

## Venue Calendar (NLP/CL)

| Venue | Submission | Conference | Location |
|-------|-----------|------------|----------|
| EMNLP 2026 | ARR May cycle (~May 15) | Oct 24-29, 2026 | Budapest, Hungary |
| ACL 2026 | ARR Feb cycle | Jul/Aug 2026 | TBD |
| NAACL 2026 | ARR cycle | Apr/May 2026 | TBD |
| LREV (journal) | Rolling | N/A | Online |
| COLM 2026 | TBD | TBD | TBD |

## AI Assistance Disclosure

EMNLP/ACL policy: AI writing assistance is permitted but must be disclosed. "Entirely AI-generated papers" without human intellectual contribution are prohibited and may result in desk rejection + multi-year ban.

**What to disclose in Acknowledgments (camera-ready only):**
- AI tools used for code development, data analysis, manuscript drafting
- Which AI generated the research artifacts (e.g., MiniMax for definitions)
- Clear statement that the author is responsible for all research decisions and claims

**Template:**
> Claude (Anthropic) was used extensively as a development partner throughout this project: writing and debugging pipeline code, iterating on prompt engineering, performing data analysis, and assisting with manuscript preparation. [Model X] generated [artifacts] as described in Section N. The author is solely responsible for all research decisions, claims, and errors.

**Important:** Acknowledgments are OMITTED in the review version (double-blind). Only add them in the camera-ready after acceptance.

## Author Block

For ACL papers, the author block is minimal:
- Full name (not initials): E. Timothy Uy
- Affiliation: Loqu8, Inc.
- Location: Bellingham, WA, USA
- Email: tim@loqu8.com

No CV, ORCID, or bio needed in the paper. ARR submission form may ask for ORCID optionally — get one free at [orcid.org](https://orcid.org).

In the `.tex` file, keep `\author{Anonymous}` for review. Comment out the real author block and uncomment it for camera-ready.

## Account Setup

All accounts are required or strongly recommended before ARR submission. Set these up early — some take days to activate. All use name "E. Timothy Uy" and affiliation "Loqu8, Inc."

### ORCID (orcid.org) — DONE
- **ID**: [0009-0008-8717-2249](https://orcid.org/0009-0008-8717-2249)
- Email verified, profile public
- Fill in: Employment, Education, Keywords (research interests)
- Small companies like "Loqu8" will show as "Unidentified organization" — this is normal, the name still saves

### OpenReview (openreview.net) — PENDING ACTIVATION
- Register at [openreview.net/signup](https://openreview.net/signup)
- **Non-institutional emails** (e.g., @loqu8.com) may require manual activation — allow up to 2 weeks
- The "Complete Registration" form has 6 sections: Names, Personal Info, Emails, Personal Links, History, Expertise
- **History section gotcha**: Position, Country/Region, and Institution Domain fields are **combobox/autocomplete widgets**, not plain text. You must click to open the dropdown, then either select a predefined option or type a custom value and select it from the filtered list. Plain `fill()` won't register with form validation.
- Predefined Position options: Undergrad student, MS student, PhD student, Postdoc, Instructor, Lecturer, Assistant/Associate/Full Professor, Emeritus, Researcher, Principal Researcher, Intern. Custom values (like "CEO") can be typed and will appear as a selectable option.
- Link your ORCID in the Personal Links section
- Add Homepage URL for institutional credibility

### Semantic Scholar (semanticscholar.org) — CLAIM PENDING
- **Author page**: [semanticscholar.org/author/E.-Uy/143861946](https://www.semanticscholar.org/author/E.-Uy/143861946)
- Pre-existing profile from Stanford publications (8 papers, 84 citations, h-index 3)
- Account created and author page claimed — moderation takes 4-5 business days
- **Gotcha**: Verification email goes to SPAM — check spam folder
- Used by OpenReview for author matching and conflict-of-interest detection

### Google Scholar — DONE
- **Profile**: [scholar.google.com/citations?user=5kBACPUAAAAJ](https://scholar.google.com/citations?user=5kBACPUAAAAJ)
- 8 publications, 107 citations, public profile
- Auto-updates enabled, citation alerts on
- **Gotcha**: Google Scholar suggests "Timothy Uy" economics papers (different person) — only select "E Timothy Uy" groups

### ACL Membership (aclweb.org) — TODO
- Not required for ARR submission, but needed for EMNLP 2026 attendance at member rates
- ~$100/year for professionals

### ARR Reviewer Signup — TODO (after OpenReview activation)
- Since May 2025, all ARR authors must also register as reviewers
- Do this once OpenReview account is active, before paper submission

## Common Pitfalls

1. **Over-revision bloat**: After 3+ reviewer passes, Limitations grows longer than Results. Fix with a final buddy pass that cuts ruthlessly.
2. **Defensive tone**: Don't say "not a dictionary in the lexicographic sense" — reviewers read it as lack of confidence. State what it IS, acknowledge limits in Limitations.
3. **Circular evaluation**: If your prompt includes reference data as context, you can't evaluate against that same reference and call it independent. Disclose it.
4. **Missing ~**: LaTeX needs `{\raise.17ex\hbox{$\scriptstyle\sim$}}` for the tilde-as-approximately symbol. Plain `~` is a non-breaking space.
5. **pdfLaTeX with CJK**: Won't work. Must use LuaLaTeX or XeLaTeX.
6. **Anonymity violations**: No GitHub URLs, no "our previous work (Author, 2024)", no company names in review version.
7. **Table numbering**: Tables must be numbered sequentially as they appear. Re-check after every structural edit.

## Git Flow for Papers

Papers are features — use git flow:
```bash
# Start work on a paper
git flow feature start paper-b-draft

# When ready for submission
git flow release start 0.X.0
git flow release finish 0.X.0
git push origin master develop --tags
```

Tag releases that include paper milestones so you can always recover the exact version submitted.
