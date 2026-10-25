"""Поиск подстраниц с датами и условиями для стипендий из reference_list.csv (обход на 1 уровень).

Ссылки берутся из HTML основной страницы (свой fetch) или из markdown-снимка Tavily, только с того же домена.
Ранжирование по ключевым словам в адресе и тексте ссылки; до 3 подстраниц на стипендию дописываются
в eval/gt/pages_to_fetch.csv. Затем снимки делает snapshot.py.
"""

import csv
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse

import httpx

ROOT = Path(__file__).resolve().parents[2]
GT = ROOT / "eval" / "gt"
BOT_UA = "ScholarshipNotebookBot/0.1 (student project; +https://github.com/all1as/scholarship_agent)"
RANKS = [
    (3, r"deadline|key[-_ ]?dates|timeline|important[-_ ]dates|dates|calendar|termin|frist"),
    (2, r"how[-_ ]to[-_ ]apply|apply|application|bewerbung|call[-_ ]for|regulation"),
    (1, r"eligib|who[-_ ]can[-_ ]apply|criteria|requirements|voraussetzung|amount|value|benefit"),
]
SKIP = r"login|logout|portal\.|/news/|/events?/|facebook|twitter|linkedin|instagram|youtube|mailto:|\.(jpg|png|zip|docx?)$"
MAX_SUB = 3


def same_site(a: str, b: str) -> bool:
    ha, hb = urlparse(a).netloc.lower(), urlparse(b).netloc.lower()
    root = lambda h: ".".join(h.split(".")[-2:])
    return root(ha) == root(hb)


def links_from_html(html: str, base: str) -> list[tuple[str, str]]:
    return [(urljoin(base, h), re.sub(r"<[^>]+>", " ", t)) for h, t in
            re.findall(r"<a[^>]+href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", html, re.S | re.I)]


def links_from_markdown(text: str) -> list[tuple[str, str]]:
    return [(u, t) for t, u in re.findall(r"\[([^\]]{0,120})\]\((https?://[^)\s]+)\)", text)]


def score(url: str, text: str) -> int:
    s = f"{url} {text}".lower()
    return max((r for r, pat in RANKS if re.search(pat, s)), default=0)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ids = set(sys.argv[1:])
    with (GT / "reference_list.csv").open(encoding="utf-8") as f:
        refs = [r for r in csv.DictReader(f) if not ids or r["id"] in ids]
    with (GT / "pages_to_fetch.csv").open(encoding="utf-8") as f:
        todo = list(csv.DictReader(f))
    known = {(t["id"], t["url"].rstrip("/")) for t in todo}
    client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": BOT_UA})

    added = []
    for ref in refs:
        base = ref["official_url"]
        links = []
        try:
            r = client.get(base)
            if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
                links = links_from_html(r.text, str(r.url))
        except httpx.HTTPError:
            pass
        snap = GT / "pages" / ref["id"] / "1.txt"
        if not links and snap.exists():
            links = links_from_markdown(snap.read_text(encoding="utf-8"))
        cand = {}
        for url, text in links:
            url = urldefrag(url)[0].rstrip("/")
            if not url.startswith("http") or not same_site(url, base) or re.search(SKIP, url, re.I):
                continue
            if url == base.rstrip("/") or (ref["id"], url) in known:
                continue
            s = score(url, text)
            if s:
                cand[url] = max(s, cand.get(url, 0))
        best = sorted(cand, key=lambda u: -cand[u])[:MAX_SUB]
        for url in best:
            added.append({"id": ref["id"], "url": url})
            known.add((ref["id"], url))
        print(f"{ref['id']:<32} links={len(links):<4} +{len(best)} {' '.join(best)[:200]}")

    with (GT / "pages_to_fetch.csv").open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=["id", "url"]).writerows(added)
    print(f"\nдобавлено подстраниц: {len(added)}")


if __name__ == "__main__":
    main()
