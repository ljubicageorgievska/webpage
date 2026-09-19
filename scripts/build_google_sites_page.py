#!/usr/bin/env python3
"""Generate files/google-sites.html: a paste-ready copy of the site.

The old Google Sites page still ranks highly for "Ljubica Georgievska",
because sites.google.com inherits google.com's standing, while this site
is treated by search engines as a brand new one. Keeping real content on
that page is what keeps it findable, but maintaining a second page by
hand means it goes stale.

So this builds that page's content from the same papers.yml and index.qmd
the real site uses, and writes it to files/google-sites.html. Open that
page, press the copy button, and paste into Google Sites. Nothing is ever
written twice: edit papers.yml as usual and the copy refreshes itself on
the next deploy.

It is a summary, not a mirror: paper titles link out to the full text, but
abstracts are left out so the page stays short enough to read.

The page carries a noindex tag, so it never competes with the real site
in search results.
"""
from __future__ import annotations

import html
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "papers.yml"
INDEX = ROOT / "index.qmd"
OUT = ROOT / "files" / "google-sites.html"

SITE_URL = "https://ljubicageorgievska.github.io/webpage/"


def bio_text() -> str:
    """The bio between the markers in index.qmd, as plain paragraphs."""
    src = INDEX.read_text(encoding="utf-8")
    m = re.search(r"<!-- BIO-START.*?-->(.*?)<!-- BIO-END -->", src, re.S)
    if not m:
        return ""
    return m.group(1).strip()


def md_links_to_html(text: str) -> str:
    """Turn [label](url) into an anchor and *word* into italics."""
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def paragraphs(text: str) -> str:
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = re.sub(r"\s+", " ", block).strip()
        if block:
            out.append(f"<p>{md_links_to_html(block)}</p>")
    return "\n".join(out)


def join_names(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def paper_html(p: dict) -> str:
    title = html.escape((p.get("title") or "Untitled").strip())
    link = (p.get("draft_url") or "").strip()
    if not link and (p.get("pdf") or "").strip():
        link = f"{SITE_URL}papers/{p['pdf'].strip()}"
    heading = f'<a href="{html.escape(link)}">{title}</a>' if link else title

    bits = [f"<p><strong>{heading}</strong>"]
    coauthors = p.get("coauthors") or []
    if coauthors:
        bits.append(f"<br><em>with {html.escape(join_names(coauthors))}</em>")
    bits.append("</p>")

    # Abstracts are deliberately left out: they make the pasted page far too
    # long to read. The linked title leads to the full paper, and the real
    # site carries the abstracts behind their collapsible headings.
    pres = (p.get("presentations") or "").strip()
    if pres:
        one_line = re.sub(r"\s+", " ", pres)
        bits.append("<p><strong>Presentations:</strong> "
                    + md_links_to_html(one_line) + "</p>")
    return "\n".join(bits)


def main() -> int:
    data = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
    papers = sorted(data.get("working_papers") or [],
                    key=lambda p: p.get("number") or 0, reverse=True)
    pubs = data.get("publications") or []

    body = [f"<h1>Ljubica Georgievska</h1>", paragraphs(bio_text())]
    body.append(
        f'<p><strong>Full website, always up to date: '
        f'<a href="{SITE_URL}">{SITE_URL}</a></strong></p>'
    )

    body.append("<h2>Working Papers</h2>")
    body.extend(paper_html(p) for p in papers)

    if pubs:
        body.append("<h2>Publications</h2>")
        for pub in pubs:
            text = re.sub(r"\s+", " ", (pub.get("citation") or "").strip())
            body.append(f"<p>{md_links_to_html(text)}</p>")

    body.append("<h2>Contact</h2>")
    body.append(
        "<p>Department of Finance, Leonard N. Stern School of Business, "
        "44 West Fourth Street, New York 10012, USA<br>"
        '<a href="mailto:lg4086@nyu.edu">lg4086@nyu.edu</a></p>'
        "<p>Department of Finance, CUNEF Universidad, Madrid, Spain<br>"
        '<a href="mailto:ljubica.georgievska@cunef.edu">'
        "ljubica.georgievska@cunef.edu</a></p>"
    )

    content = "\n".join(body)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<title>Content to paste into Google Sites</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
         max-width: 46rem; margin: 2rem auto; padding: 0 1rem; color: #24292f;
         line-height: 1.5; }}
  .howto {{ background: #f4f1ea; border-left: 4px solid #c9a35a;
            padding: 0.9rem 1.1rem; border-radius: 4px; font-size: 0.95rem; }}
  .howto ol {{ margin: 0.5rem 0 0 1.1rem; padding: 0; }}
  button {{ font: inherit; font-weight: 600; background: #1b2a41; color: #fff;
            border: 0; border-radius: 4px; padding: 0.6rem 1.1rem;
            cursor: pointer; margin: 1.2rem 0; }}
  button:hover {{ background: #33495e; }}
  #content {{ border-top: 2px solid #e6e6e6; padding-top: 1.2rem; }}
  #content h1 {{ font-size: 1.6rem; }}
  #content h2 {{ font-size: 1.2rem; margin-top: 1.6rem; }}
  a {{ color: #7d5a2a; }}
</style>
</head>
<body>
<div class="howto">
  <strong>This page is not part of the website.</strong> It exists only to keep
  the old Google Sites page current, so that page stays findable for searches
  of your name.
  <ol>
    <li>Press <em>Copy everything below</em>.</li>
    <li>Open the Google Sites page, select the old text and paste over it.</li>
    <li>Publish.</li>
  </ol>
  It is rebuilt from <code>papers.yml</code> on every deploy, so repeat this
  whenever you have added a paper and want the other page to match.
</div>

<button id="copy">Copy everything below</button>

<div id="content">
{content}
</div>

<script>
document.getElementById('copy').addEventListener('click', async () => {{
  const el = document.getElementById('content');
  const btn = document.getElementById('copy');
  try {{
    await navigator.clipboard.write([new ClipboardItem({{
      'text/html': new Blob([el.innerHTML], {{type: 'text/html'}}),
      'text/plain': new Blob([el.innerText], {{type: 'text/plain'}})
    }})]);
  }} catch (e) {{
    const r = document.createRange();
    r.selectNodeContents(el);
    const s = getSelection();
    s.removeAllRanges();
    s.addRange(r);
    document.execCommand('copy');
  }}
  btn.textContent = 'Copied \\u2014 now paste into Google Sites';
}});
</script>
</body>
</html>
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT} with {len(papers)} working papers and {len(pubs)} publications.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
