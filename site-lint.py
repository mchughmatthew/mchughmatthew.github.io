#!/usr/bin/env python3
"""Site consistency checker for mchughmatthew.github.io.

Run before committing:  python3 site-lint.py
Exits 0 if clean, 1 if any problems are found. Uses only the standard library.
"""
import glob
import json
import os
import re
import sys

GA_TAG = "G-5LNP9W9B62"
BIG_IMAGE_BYTES = 1_000_000  # flag referenced images larger than ~1 MB
problems = []


def problem(page, msg):
    problems.append(f"  {page}: {msg}")


pages = sorted(glob.glob("*.html"))

for page in pages:
    with open(page, encoding="utf-8") as fh:
        html = fh.read()
    is_404 = page == "404.html"

    # -- required head elements ------------------------------------------
    if GA_TAG not in html:
        problem(page, "missing Google Analytics tag")
    if "<title>" not in html:
        problem(page, "missing <title>")
    if 'name="viewport"' not in html:
        problem(page, "missing viewport meta")
    if not is_404:
        if 'name="description"' not in html:
            problem(page, "missing meta description")
        if 'rel="canonical"' not in html:
            problem(page, "missing canonical link")
        if "og:image" not in html:
            problem(page, "missing Open Graph tags")

    # -- completeness (file not truncated) --------------------------------
    if not html.rstrip().endswith("</html>"):
        problem(page, "file does not end with </html> (truncated?)")
    if html.count("<script") != html.count("</script>"):
        problem(page, "unbalanced <script> tags (truncated script?)")

    # -- site-wide nav: same menu on every page -----------------------------
    if not is_404:
        nav = re.search(r"<nav.*?</nav>", html, re.S)
        if not nav:
            problem(page, "missing <nav>")
        else:
            labels = re.findall(r"<li>\s*<a [^>]*>\s*([^<]+?)\s*</a>\s*</li>", nav.group(0))
            labels = [re.sub(r"^(?:&#\d+;?|\W)*", "", l) for l in labels]
            expected = ["About", "Research", "Projects", "Publications", "News",
                        "Training", "Workshop", "CHOPR", "Contact", "CV"]
            if labels != expected:
                problem(page, f"nav menu is {labels}, expected {expected}")
            pub = re.search(r'<li><a href="([^"]+)"[^>]*>\s*Publications', nav.group(0))
            if pub and pub.group(1) != "publications.html":
                problem(page, f"Publications nav link points to {pub.group(1)}")
            if page != "chopr_history.html" and 'id="nav-toggle"' not in nav.group(0):
                problem(page, "missing mobile hamburger (nav-toggle)")

    # -- conventions --------------------------------------------------------
    if re.search(r'href="mailto:(?!mchughm@nursing\.upenn\.edu)', html):
        problem(page, "mailto: link with unexpected address")

    # -- accessibility ------------------------------------------------------
    if not is_404:
        if "prefers-reduced-motion" not in html:
            problem(page, "missing prefers-reduced-motion CSS block")
        if 'class="skip-link"' not in html:
            problem(page, "missing skip-to-content link")

    # -- local references exist, and images are web-sized -------------------
    refs = re.findall(r'(?:src|href|data-full)="((?:images|pdfs)/[^"]+)"', html)
    refs += re.findall(r"url\('((?:images|pdfs)/[^']+)'\)", html)
    for ref in set(refs):
        if not os.path.exists(ref):
            problem(page, f"references missing file {ref}")
        elif ref.startswith("images/") and os.path.getsize(ref) > BIG_IMAGE_BYTES:
            mb = os.path.getsize(ref) / 1e6
            problem(page, f"references oversized image {ref} ({mb:.1f} MB)")

    # -- gallery images lazy-load ------------------------------------------
    if page.startswith("workshop-"):
        n = len(re.findall(r'<img (?![^>]*loading=)', html))
        if n:
            problem(page, f"{n} <img> tag(s) without loading=\"lazy\"")

# -- news.json ---------------------------------------------------------------
try:
    with open("news.json", encoding="utf-8") as fh:
        news = json.load(fh)
    for i, item in enumerate(news):
        for key in ("date", "type", "title", "source", "blurb"):
            if key not in item:
                problem("news.json", f"item {i} missing '{key}'")
        if item.get("type") not in ("release", "coverage", "recognition"):
            problem("news.json", f"item {i} has unknown type {item.get('type')!r}")
        if not re.match(r"\d{4}-\d{2}-\d{2}$", str(item.get("date", ""))):
            problem("news.json", f"item {i} date not YYYY-MM-DD")
except Exception as exc:  # noqa: BLE001
    problem("news.json", f"failed to parse: {exc}")

# -- sitemap covers all pages -------------------------------------------------
if os.path.exists("sitemap.xml"):
    with open("sitemap.xml", encoding="utf-8") as fh:
        sitemap = fh.read()
    for page in pages:
        if page == "404.html":
            continue
        loc = "https://mchughmatthew.github.io/" + ("" if page == "index.html" else page)
        if f"<loc>{loc}</loc>" not in sitemap:
            problem("sitemap.xml", f"missing entry for {page}")
else:
    problem("sitemap.xml", "file not found")

# -----------------------------------------------------------------------------
if problems:
    print(f"FAIL — {len(problems)} problem(s):")
    print("\n".join(problems))
    sys.exit(1)
print(f"OK — {len(pages)} pages checked, no problems found.")
