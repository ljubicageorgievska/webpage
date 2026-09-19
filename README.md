# Ljubica Georgievska — academic website

**<https://ljubicageorgievska.github.io/webpage/>**

Source for the academic website of Ljubica Georgievska, Assistant Professor of
Finance at CUNEF Universidad and Visiting Assistant Professor at NYU Stern
School of Business. Research in empirical asset pricing, international finance,
derivatives, macro-finance and financial intermediation.

| | |
|---|---|
| Website | <https://ljubicageorgievska.github.io/webpage/> |
| Google Scholar | <https://scholar.google.com/citations?user=VOG7pkkAAAAJ&hl=en> |
| ORCID | <https://orcid.org/0009-0006-7871-5753> |
| SSRN | <https://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=2370219> |

## How this repository works

The site is built with [Quarto](https://quarto.org) and published to GitHub
Pages by `.github/workflows/publish.yml` on every push to `main`.

- **`papers.yml`** is the single source of truth for working papers and
  publications. `scripts/build_research_page.py` regenerates `research.qmd`
  from it before every render, so `research.qmd` is never edited by hand.
- **`_inbox/`** is the drop zone. Paste an SSRN link into `links.txt`, or drop
  in a paper PDF, a new CV, a photo, or new bio text, and
  `scripts/process_inbox.py` files it into the site on the next build.
- **`cv/cv.tex`** is the CV source. The workflow compiles it to `files/cv.pdf`
  on every build, so editing the `.tex` updates the published CV.
- **`index.qmd`** and **`assets/styles.scss`** are the home page and styling.

Setup and day-to-day instructions: [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md).
