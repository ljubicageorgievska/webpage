# Your new academic website: setup and daily use

This folder contains your complete website. You never need to write code.
The one-time setup below takes about fifteen minutes; after that, adding a
paper is a single upload from any device.

---

## Part 1. One-time setup (about 15 minutes)

### Step 1. Create the repository

1. Go to github.com and log in.
2. Click the "+" at the top right, then "New repository".
3. Name it exactly: `website`
4. Set it to "Public" (required for free GitHub Pages). Do not tick any
   of the initialisation boxes. Click "Create repository".

### Step 2. Upload this folder

1. On the empty repository page, click the link "uploading an existing
   file".
2. Drag ALL the contents of this folder (not the folder itself) into the
   upload area: `_quarto.yml`, `index.qmd`, `papers.yml`,
   `SETUP_INSTRUCTIONS.md`, `.gitignore`, and the folders `_inbox`,
   `assets`, `files`, `papers`, `scripts`, `.github`.

   Important: the `.github` folder contains the automation and is hidden
   on Mac by default. In Finder press Cmd+Shift+. (full stop) to reveal
   hidden files before dragging. If the browser upload refuses folders,
   use Safari or Chrome, which both support dragging folders.
3. In the "Commit changes" box at the bottom, click "Commit changes".

### Step 3. Switch on the website

1. In the repository, go to Settings > Pages (left-hand menu).
2. Under "Build and deployment", set Source to "GitHub Actions".
3. Go to the "Actions" tab. If it asks you to enable workflows, click
   "I understand my workflows, go ahead and enable them", then open the
   workflow named "Build and publish website" and press "Run workflow".
4. After two to three minutes, your site is live at:
   `https://YOUR-USERNAME.github.io/website/`

### Step 4. Connect Google Analytics

1. Go to analytics.google.com, create an account and a "GA4" property
   for your website, choosing "Web" as the platform and entering your
   site address from Step 3.
2. Google gives you a Measurement ID that looks like `G-AB12CD34EF`.
3. In the repository, open the file `_quarto.yml`, press the pencil icon,
   and replace `G-REPLACEME` with your Measurement ID. Press
   "Commit changes". The site rebuilds itself with tracking enabled.

Within a day you will see, in Google Analytics, how many people visit,
which papers they open, which links they click, how long they stay, and
which country, city, and often which institution's network they come from.

### Step 5 (strongly recommended). Add the AI extraction key

The robot can extract a paper's details in two ways: with careful built-in
rules, or, much more reliably, by asking an AI model to read the front
matter. The second mode also makes SSRN links work dependably, because
SSRN blocks ordinary robots but not this route.

1. Go to console.anthropic.com, create an account, and under "API keys"
   create a key (a few dollars of credit is ample; each paper costs less
   than one cent to process).
2. In your repository go to Settings > Secrets and variables > Actions >
   "New repository secret". Name: `ANTHROPIC_API_KEY`. Value: paste the
   key. Save.

Without this key everything still works; the robot simply marks entries
it was less sure about with `needs_review: true` in `papers.yml` so you
can glance at them.

### Step 6 (optional). Finishing touches

1. Photo: upload your portrait as `files/profile.jpg` (repository >
   `files` folder > "Add file" > "Upload files"). The home page picks it
   up automatically; without it, the page simply shows no photo.
2. CV: currently the CV button points to your Dropbox link. If you
   prefer, upload `cv.pdf` into `files/` and change the CV link in
   `_quarto.yml` to `files/cv.pdf`.
3. Custom domain: in Settings > Pages you can attach a domain such as
   ljubicageorgievska.com (bought from any registrar for roughly £10 a
   year); GitHub provides the instructions on that page.

---

## Part 2. Daily use: adding a new paper (under a minute, any device)

### If the paper is on SSRN

1. Open your repository (bookmark it), go into the `_inbox` folder, open
   `links.txt`, and press the pencil icon.
2. Paste the SSRN link on a new line. Press "Commit changes".
3. Done. Within about three minutes the paper appears on your Research
   page with its title, coauthors, abstract, an "Updated draft" button,
   and a "New" badge. Add the presentations list whenever you like by
   editing the entry in `papers.yml` (the robot cannot know it from SSRN).

### If you only have the PDF (not yet on SSRN)

1. Open your repository, go into the `_inbox` folder, press "Add file" >
   "Upload files", and drag the paper's PDF in. Press "Commit changes".
2. Done. The robot reads the PDF, extracts the title, authors, abstract,
   and the presentations list from your acknowledgements footnote, hosts
   the PDF on the site, and publishes the entry.

### Internet appendices

Upload the appendix PDF the same way, with the word "appendix" in the
filename (ideally together with a few title words, for example
`hairy premium appendix.pdf`). It attaches to the matching paper as an
"Internet Appendix" button rather than creating a new entry.

### From your phone or iPad

Exactly the same steps in the browser at github.com, or more comfortably
in the free GitHub mobile app, which can upload files from your camera
roll or Files app and edit `links.txt` and `papers.yml` directly.

### Correcting or polishing an entry

Open `papers.yml`, press the pencil icon, edit the relevant field (title,
coauthors, presentations, abstract, links), and commit. The page rebuilds
itself. To remove the "New" badge later, change `new: true` to
`new: false`. If the robot flagged `needs_review: true`, check the entry
once and delete that line.

### Field reference for papers.yml

number (order, highest first); title; coauthors (a list, `[]` if solo);
new (true/false badge); presentations (free text, shown after a bold
"Presentations:" label); awards; note (italic line under the title);
abstract; abstract_label ("Abstract" by default, or "Summary");
draft_url (SSRN link); pdf (a filename inside `papers/`); appendix_url or
appendix_pdf; extra_links (a list of `{text: ..., url: ...}`).

---

## Part 3. How it works, in one paragraph

Your repository holds the site's content; `papers.yml` is the single
source of truth for the Research page. Every time anything changes, a
GitHub "Action" (the file `.github/workflows/publish.yml`) wakes up,
first runs `scripts/process_inbox.py` to turn anything in `_inbox/` into
entries in `papers.yml`, then runs `scripts/build_research_page.py` to
regenerate the Research page, renders the site with Quarto, and publishes
it to GitHub Pages. You can watch each run live under the "Actions" tab,
which is also where to look if something ever seems not to have updated.
