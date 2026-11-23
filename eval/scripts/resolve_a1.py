"""Поиск официальных страниц для кандидатов эталонного списка A1.

Вход: eval/gt/candidates_a1.csv (id, name, country, type, domain_hint, query, url).
Для строк без url — поиск Tavily по query; берётся первый результат с домена domain_hint.
Затем каждая страница загружается своим fetch (без подмены User-Agent): статус и длина текста.
Выход: eval/gt/candidates_a1_resolved.csv — для ручного просмотра перед составлением reference_list.csv.
"""

import csv
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
from dotenv import load_dotenv
from tavily import TavilyClient

ROOT = Path(__file__).resolve().parents[2]
GT = ROOT / "eval" / "gt"
BOT_UA = "ScholarshipNotebookBot/0.1 (student project; +https://github.com/all1as/scholarship_agent)"
SOCIAL = ("facebook.", "instagram.", "linkedin.", "reddit.", "quora.", "youtube.", "x.com", "twitter.")

load_dotenv(ROOT / ".env")


def host_matches(url: str, hint: str) -> bool:
    host = urlparse(url).netloc.lower()
    return bool(hint) and (host == hint or host.endswith("." + hint))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    tavily = TavilyClient(os.environ["TAVILY_API_KEY"])
    client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": BOT_UA})
    with (GT / "candidates_a1.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    out = []
    for row in rows:
        url, how, alternatives = row["url"], "given", ""
        if not url:
            res = tavily.search(row["query"], max_results=6, search_depth="basic",
                                exclude_domains=["facebook.com", "instagram.com", "linkedin.com", "reddit.com",
                                                 "quora.com", "youtube.com"])
            results = [r["url"] for r in res["results"] if not any(s in r["url"] for s in SOCIAL)]
            match = next((u for u in results if host_matches(u, row["domain_hint"])), None)
            url, how = (match, "search_hint") if match else ("", "no_match")
            alternatives = " | ".join(results[:3])
        status, chars = "", 0
        if url:
            try:
                r = client.get(url)
                status = r.status_code
                chars = len(trafilatura.extract(r.text) or "") if r.status_code == 200 else 0
            except httpx.HTTPError as e:
                status = type(e).__name__
        out.append({**row, "url": url, "how": how, "status": status, "chars": chars, "alternatives": alternatives})
        print(f"{row['id']:<32} {how:<12} {str(status):<5} {chars:<6} {url or alternatives[:150]}")

    with (GT / "candidates_a1_resolved.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"\nвсего {len(out)}, без совпадения: {sum(o['how'] == 'no_match' for o in out)}, "
          f"не 200: {sum(bool(o['url']) and o['status'] != 200 for o in out)}")


if __name__ == "__main__":
    main()
