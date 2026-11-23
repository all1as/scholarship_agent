"""Сохраняет снимки страниц для эталонной разметки.

Вход: eval/gt/pages_to_fetch.csv (id,url). Для каждой пары, которой ещё нет в манифесте:
свой fetch (честный User-Agent, robots.txt) + trafilatura (PDF — pypdf), при 403 / JS-оболочке — Tavily Extract.
Выход: eval/gt/pages/<id>/<n>.txt и строка в eval/gt/pages/manifest.csv (id, n, url, sha256, fetched_at, source, chars).
"""

import csv
import hashlib
import io
import os
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura
from dotenv import load_dotenv
from pypdf import PdfReader
from pypdf.errors import PyPdfError as PdfError
from tavily import TavilyClient

ROOT = Path(__file__).resolve().parents[2]
GT = ROOT / "eval" / "gt"
PAGES = GT / "pages"
MANIFEST = PAGES / "manifest.csv"
FIELDS = ["id", "n", "url", "sha256", "fetched_at", "source", "chars"]
BOT_UA = "ScholarshipNotebookBot/0.1 (student project; +https://github.com/all1as/scholarship_agent)"
MIN_CHARS = 300

load_dotenv(ROOT / ".env")


def read_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def robots_allowed(client: httpx.Client, url: str, cache: dict) -> bool:
    host = urlparse(url)
    base = f"{host.scheme}://{host.netloc}"
    if base not in cache:
        rp = RobotFileParser()
        try:
            r = client.get(f"{base}/robots.txt")
            rp.parse(r.text.splitlines() if r.status_code < 400 else [])
        except httpx.HTTPError:
            rp.parse([])
        cache[base] = rp
    return cache[base].can_fetch(BOT_UA, url)


def pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except PdfError:
        return ""


def own_fetch(client: httpx.Client, url: str) -> str:
    try:
        r = client.get(url)
    except httpx.HTTPError:
        return ""
    if r.status_code != 200:
        return ""
    if "pdf" in r.headers.get("content-type", "") or url.lower().endswith(".pdf"):
        return pdf_text(r.content)
    return trafilatura.extract(r.text, include_tables=True, favor_recall=True) or ""


def tavily_fetch(tavily: TavilyClient, url: str) -> str:
    res = tavily.extract([url])
    return (res.get("results") or [{}])[0].get("raw_content") or ""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    PAGES.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest()
    done = {(m["id"], m["url"]) for m in manifest}
    with (GT / "pages_to_fetch.csv").open(encoding="utf-8", newline="") as f:
        todo = [row for row in csv.DictReader(f) if (row["id"], row["url"]) not in done]

    client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": BOT_UA})
    tavily = TavilyClient(os.environ["TAVILY_API_KEY"])
    robots: dict = {}
    for row in todo:
        sid, url = row["id"], row["url"]
        text, source = "", "none"
        if robots_allowed(client, url, robots):
            text, source = own_fetch(client, url), "own_fetch"
        if len(text) < MIN_CHARS:
            text, source = tavily_fetch(tavily, url), "tavily_extract"
        if len(text) < MIN_CHARS:
            print(f"FAIL {sid} {url}")
            continue
        n = 1 + sum(1 for m in manifest if m["id"] == sid)
        (PAGES / sid).mkdir(exist_ok=True)
        (PAGES / sid / f"{n}.txt").write_text(text, encoding="utf-8")
        manifest.append({"id": sid, "n": n, "url": url, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                         "fetched_at": date.today().isoformat(), "source": source, "chars": len(text)})
        print(f"ok   {sid}/{n}.txt {source} {len(text)} {url}")
        time.sleep(1)

    with MANIFEST.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(manifest)


if __name__ == "__main__":
    main()
