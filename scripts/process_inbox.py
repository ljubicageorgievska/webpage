#!/usr/bin/env python3
"""Process the _inbox/ drop zone.

What it does, fully automatically on every push:
  1. Any line in _inbox/links.txt that contains an SSRN URL is fetched and
     the paper's title, authors and abstract are read from SSRN's metadata.
  2. Any PDF dropped in _inbox/ is parsed: title, authors, abstract and the
     presentations list are extracted from the front matter. If the
     ANTHROPIC_API_KEY repository secret is set, a language model performs
     the extraction (very robust); otherwise careful heuristics are used
     and the entry is flagged needs_review: true.
  3. A PDF whose filename contains "appendix" is attached to the existing
     paper whose title best matches the rest of the filename, instead of
     creating a new entry.
  4. New entries are added to papers.yml with the next number and a "New"
     badge; PDFs are moved into papers/ so they are hosted on the site.

The GitHub workflow then commits the updated papers.yml and rebuilds the
website, so a single upload publishes the paper end to end.
"""
from __future__ import annotations

import difflib
import json
import os
import pathlib
import re
import sys
import unicodedata

import requests
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
INBOX = ROOT / "_inbox"
PAPERS_DIR = ROOT / "papers"
DATA_FILE = ROOT / "papers.yml"
LINKS_FILE = INBOX / "links.txt"

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/124.0 Safari/537.36")}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def load_data() -> dict:
    data = yaml.safe_load(DATA_FILE.read_text(encoding="utf-8")) or {}
    data.setdefault("working_papers", [])
    data.setdefault("publications", [])
    return data


def save_data(data: dict) -> None:
    DATA_FILE.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=78),
        encoding="utf-8",
    )


def slugify(text: str, maxlen: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:maxlen].rstrip("-") or "paper"


def next_number(data: dict) -> int:
    nums = [p.get("number") or 0 for p in data["working_papers"]]
    return (max(nums) if nums else 0) + 1


def already_listed(data: dict, title: str) -> bool:
    existing = [p.get("title", "").lower() for p in data["working_papers"]]
    return bool(difflib.get_close_matches(title.lower(), existing, n=1, cutoff=0.85))


def split_authors(raw_authors: list[str]) -> list[str]:
    """Drop the site owner from the coauthor list."""
    out = []
    for a in raw_authors:
        a = a.strip()
        if not a:
            continue
        if "georgievska" in a.lower() and "a." not in a.lower().split()[0]:
            continue
        if a.lower() in {"ljubica georgievska", "georgievska, ljubica"}:
            continue
        out.append(a)
    return out


# --------------------------------------------------------------------------
# SSRN links
# --------------------------------------------------------------------------
def parse_ssrn(url: str) -> dict | None:
    try:
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! could not fetch {url}: {exc}")
        return None
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(r.text, "html.parser")

    def metas(name: str) -> list[str]:
        return [m.get("content", "").strip()
                for m in soup.find_all("meta", attrs={"name": name})
                if m.get("content")]

    title = (metas("citation_title") or [""])[0]
    authors = metas("citation_author")
    abstract = ""
    abs_div = soup.find(class_=re.compile("abstract", re.I))
    if abs_div:
        ptag = abs_div.find("p")
        abstract = (ptag.get_text(" ", strip=True) if ptag
                    else abs_div.get_text(" ", strip=True))
        abstract = re.sub(r"^\s*Abstract\s*", "", abstract, flags=re.I)
    if not abstract:
        og = soup.find("meta", attrs={"property": "og:description"})
        abstract = og.get("content", "").strip() if og else ""

    if not title:
        return None
    return {"title": title, "authors": authors, "abstract": abstract, "url": url}


def llm_ssrn(url: str) -> dict | None:
    """SSRN blocks robot IPs; if an ANTHROPIC_API_KEY secret is set, read the
    page through the Claude API's web search instead."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    prompt = (
        f"Open this SSRN page: {url}\n"
        "Return ONLY a JSON object, no markdown fences, with keys: "
        "title (string), authors (list of full names in order), "
        "abstract (string, the full abstract verbatim)."
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2000,
                  "tools": [{"type": "web_search_20250305",
                             "name": "web_search"}],
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=180,
        )
        r.raise_for_status()
        raw = "".join(b.get("text", "") for b in r.json().get("content", [])
                      if b.get("type") == "text")
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
        start, end = raw.find("{"), raw.rfind("}")
        out = json.loads(raw[start:end + 1])
        out["url"] = url
        return out if out.get("title") else None
    except Exception as exc:  # noqa: BLE001
        print(f"  ! model-based SSRN extraction failed: {exc}")
        return None


def process_links(data: dict) -> bool:
    if not LINKS_FILE.exists():
        return False
    lines = [ln.strip() for ln in LINKS_FILE.read_text(encoding="utf-8").splitlines()]
    urls = [ln for ln in lines if re.search(r"ssrn\.com", ln)]
    if not urls:
        return False
    changed = False
    for url in urls:
        print(f"Processing SSRN link: {url}")
        meta = parse_ssrn(url) or llm_ssrn(url)
        if not meta:
            print("  ! extraction failed; leaving the link in the inbox")
            continue
        meta.setdefault("authors", [])
        meta.setdefault("abstract", "")
        if already_listed(data, meta["title"]):
            print(f"  = '{meta['title']}' already on the site; updating its link")
            for p in data["working_papers"]:
                if difflib.SequenceMatcher(
                        None, p.get("title", "").lower(),
                        meta["title"].lower()).ratio() > 0.85:
                    p["draft_url"] = url
                    if meta.get("abstract"):
                        p["abstract"] = meta["abstract"]
        else:
            entry = {
                "number": next_number(data),
                "title": meta["title"],
                "coauthors": split_authors(meta["authors"]),
                "new": True,
                "presentations": "",
                "abstract": meta["abstract"],
                "draft_url": url,
            }
            data["working_papers"].insert(0, entry)
            print(f"  + added working paper #{entry['number']}: {entry['title']}")
        lines = [ln for ln in lines if ln.strip() != url]
        changed = True
    LINKS_FILE.write_text("\n".join(ln for ln in lines if ln.strip()) + "\n",
                          encoding="utf-8")
    return changed


# --------------------------------------------------------------------------
# PDFs
# --------------------------------------------------------------------------
def pdf_front_text(path: pathlib.Path, pages: int = 3) -> str:
    import pdfplumber
    chunks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:pages]:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def pdf_title_by_font(path: pathlib.Path) -> str:
    """Title = the largest-font text near the top of page one."""
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        words = pdf.pages[0].extract_words(extra_attrs=["size"])
    if not words:
        return ""
    max_size = max(w["size"] for w in words)
    title_words = [w["text"] for w in words if w["size"] > max_size - 0.5]
    return re.sub(r"\s+", " ", " ".join(title_words)).strip()


def heuristic_extract(path: pathlib.Path) -> dict:
    text = pdf_front_text(path)
    title = pdf_title_by_font(path)

    abstract = ""
    m = re.search(r"\bAbstract\b[:\s]*(.+?)(?:\bKeywords?\b|\bJEL\b|We thank|Acknowledg|\n\s*\n\s*1[\.\s]|\Z)",
                  text, flags=re.S | re.I)
    if m:
        abstract = re.sub(r"\s+", " ", m.group(1)).strip()[:3000]

    authors: list[str] = []
    if title:
        after = text.split("\n")
        try:
            idx = next(i for i, ln in enumerate(after) if title[:25].lower()
                       in re.sub(r"\s+", " ", ln).lower())
        except StopIteration:
            idx = 0
        for ln in after[idx + 1: idx + 8]:
            ln = ln.strip()
            if re.search(r"abstract", ln, re.I):
                break
            names = re.findall(r"[A-Z][a-zA-Z\-']+\s+(?:[A-Z]\.\s+)?[A-Z][a-zA-Z\-']+",
                               ln)
            title_words = set(re.findall(r"[a-z']+", title.lower()))
            for n in names:
                parts = set(re.findall(r"[a-z']+", n.lower()))
                if not parts or len(parts & title_words) < len(parts):
                    authors.append(n)

    pres = ""
    m = re.search(r"(?:presented at|presentations?:|seminar participants at)"
                  r"(.+?)(?:\.\s|\n\n|\Z)", text, flags=re.S | re.I)
    if m:
        pres = re.sub(r"\s+", " ", m.group(1)).strip(" .:")[:1500]

    return {"title": title, "authors": authors, "abstract": abstract,
            "presentations": pres, "confident": False}


def llm_extract(path: pathlib.Path) -> dict | None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    text = pdf_front_text(path, pages=4)[:16000]
    prompt = (
        "Below is the front matter of an academic finance working paper. "
        "Return ONLY a JSON object, no markdown fences, with keys: "
        "title (string), authors (list of full names in order), "
        "abstract (string, the full abstract verbatim), "
        "presentations (string: the list of conferences/seminars where the "
        "paper was presented, taken from the acknowledgements or title-page "
        "footnote, formatted as a readable comma-separated list; empty "
        "string if none are mentioned).\n\n---\n" + text
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2000,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=120,
        )
        r.raise_for_status()
        raw = "".join(b.get("text", "") for b in r.json().get("content", []))
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
        out = json.loads(raw)
        out["confident"] = True
        return out
    except Exception as exc:  # noqa: BLE001
        print(f"  ! model extraction failed ({exc}); falling back to heuristics")
        return None


def attach_appendix(data: dict, pdf: pathlib.Path) -> bool:
    stem = re.sub(r"appendix", " ", pdf.stem, flags=re.I)
    stem = re.sub(r"[_\-]+", " ", stem).strip().lower()
    titles = [p.get("title", "") for p in data["working_papers"]]
    match = difflib.get_close_matches(stem, [t.lower() for t in titles],
                                      n=1, cutoff=0.3)
    target = None
    if match:
        target = data["working_papers"][[t.lower() for t in titles].index(match[0])]
    else:
        newest = [p for p in data["working_papers"] if p.get("new")]
        target = newest[0] if newest else None
    if not target:
        print(f"  ! could not match appendix {pdf.name} to a paper; skipped")
        return False
    dest = PAPERS_DIR / f"{slugify(target['title'])}-appendix.pdf"
    dest.write_bytes(pdf.read_bytes())
    pdf.unlink()
    target["appendix_pdf"] = dest.name
    print(f"  + attached {dest.name} to '{target['title']}'")
    return True


def process_pdfs(data: dict) -> bool:
    changed = False
    for pdf in sorted(INBOX.glob("*.pdf")):
        print(f"Processing PDF: {pdf.name}")
        if "appendix" in pdf.name.lower():
            changed |= attach_appendix(data, pdf)
            continue
        meta = llm_extract(pdf) or heuristic_extract(pdf)
        title = (meta.get("title") or pdf.stem.replace("_", " ")).strip()
        dest = PAPERS_DIR / f"{slugify(title)}.pdf"
        dest.write_bytes(pdf.read_bytes())
        pdf.unlink()
        if already_listed(data, title):
            for p in data["working_papers"]:
                if difflib.SequenceMatcher(None, p.get("title", "").lower(),
                                           title.lower()).ratio() > 0.85:
                    p["pdf"] = dest.name
                    confident = bool(meta.get("confident"))
                    if meta.get("abstract") and (confident or not p.get("abstract")):
                        p["abstract"] = meta["abstract"]
                    if meta.get("presentations") and (confident or not p.get("presentations")):
                        p["presentations"] = meta["presentations"]
                    print(f"  = updated existing entry '{p['title']}'")
        else:
            entry = {
                "number": next_number(data),
                "title": title,
                "coauthors": split_authors(meta.get("authors") or []),
                "new": True,
                "presentations": meta.get("presentations", "") or "",
                "abstract": meta.get("abstract", "") or "",
                "draft_url": "",
                "pdf": dest.name,
            }
            if not meta.get("confident"):
                entry["needs_review"] = True
            data["working_papers"].insert(0, entry)
            print(f"  + added working paper #{entry['number']}: {title}")
        changed = True
    return changed



# --------------------------------------------------------------------------
# CV, photo, and bio dropped into the inbox
# --------------------------------------------------------------------------
FILES_DIR = ROOT / "files"
INDEX_FILE = ROOT / "index.qmd"
BIO_FILE = INBOX / "bio.txt"
BIO_PLACEHOLDER = ("# Type your new bio below this line, then commit. "
                   "The robot replaces the bio on the home page.\n")


def process_cv_and_photo() -> bool:
    changed = False
    FILES_DIR.mkdir(exist_ok=True)
    for pdf in sorted(INBOX.glob("*.pdf")):
        if "cv" in re.sub(r"[^a-z]", "", pdf.name.lower())[:20] and \
                "cv" in pdf.stem.lower().replace("_", " ").replace("-", " "):
            (FILES_DIR / "cv.pdf").write_bytes(pdf.read_bytes())
            pdf.unlink()
            print(f"  + {pdf.name} installed as the CV (files/cv.pdf)")
            changed = True
    for img in sorted(list(INBOX.glob("*.jpg")) + list(INBOX.glob("*.jpeg"))
                      + list(INBOX.glob("*.png"))):
        (FILES_DIR / "profile.jpg").write_bytes(img.read_bytes())
        img.unlink()
        print(f"  + {img.name} installed as the profile photo")
        changed = True
    return changed


def process_bio() -> bool:
    if not BIO_FILE.exists():
        BIO_FILE.write_text(BIO_PLACEHOLDER, encoding="utf-8")
        return False
    lines = [ln for ln in BIO_FILE.read_text(encoding="utf-8").splitlines()
             if not ln.strip().startswith("#")]
    new_bio = "\n".join(lines).strip()
    if not new_bio:
        return False
    text = INDEX_FILE.read_text(encoding="utf-8")
    start = "<!-- BIO-START (managed by the robot: edit _inbox/bio.txt instead) -->"
    end = "<!-- BIO-END -->"
    if start not in text or end not in text:
        print("  ! bio markers missing in index.qmd; bio not updated")
        return False
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    INDEX_FILE.write_text(f"{head}{start}\n{new_bio}\n{end}{tail}",
                          encoding="utf-8")
    BIO_FILE.write_text(BIO_PLACEHOLDER, encoding="utf-8")
    print("  + home-page bio replaced with the text from _inbox/bio.txt")
    return True


def main() -> int:
    INBOX.mkdir(exist_ok=True)
    PAPERS_DIR.mkdir(exist_ok=True)
    data = load_data()
    changed = False
    changed |= process_cv_and_photo()
    changed |= process_bio()
    changed |= process_links(data)
    changed |= process_pdfs(data)
    if changed:
        save_data(data)
        print("papers.yml updated.")
    else:
        print("Inbox empty; nothing to do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
