"""Спайк: что возвращает Tavily на запросы из eval-сета и читает ли он сайты, которые блокируют наш fetch."""

import json
import os
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv(Path(__file__).parent.parent / ".env")
OUT = Path(__file__).parent / "out"

AGGREGATOR_HINTS = (
    "scholars4dev", "scholarshipportal", "mastersportal", "studyportals", "opportunitydesk", "scholarshipsads",
    "afterschoolafrica", "scholarshipdb", "opportunitiesforafricans", "youthop", "scholarshiproar", "scholarship-positions",
    "wemakescholars", "scholarshipscorner", "scholarshiptab", "studyabroad", "topuniversities", "shiksha", "leverageedu",
    "idp.com", "collegedunia", "yocket", "reddit", "quora", "youtube", "medium.com", "linkedin", "facebook",
)

QUERIES = [
    ("discovery", "master scholarship computer science Germany international students 2027"),
    ("discovery", "fully funded masters scholarship data science Netherlands Sweden 2027"),
    ("discovery", "fully funded masters scholarship engineering UK international students 2027"),
    ("discovery", "Erasmus Mundus joint master embedded systems scholarship"),
    ("discovery", "master's scholarship machine learning Canada international students"),
    ("discovery", "masters scholarships open to Russian citizens Europe 2027"),
    ("fact", "Chevening scholarship application deadline 2027/28"),
    ("fact", "Eiffel Excellence scholarship monthly allowance coverage"),
    ("fact", "Swedish Institute Scholarships for Global Professionals language requirements"),
    ("fact", "NL Scholarship Holland deadline 2027-2028"),
    ("fact", "DAAD study scholarship master's deadline 2027"),
    ("fact", "Knight-Hennessy Scholars application deadline 2027"),
    ("fact", "Gates Cambridge scholarship deadline 2027 entry"),
    ("fact", "ETH Zurich Excellence Scholarship ESOP application deadline"),
    ("fact", "Lund University Global Scholarship deadline 2027"),
]

# сайты, на которых наш fetch получил 403 или JS-оболочку
EXTRACT_URLS = [
    "https://www.ox.ac.uk/clarendon",
    "https://www.mastersportal.com/scholarships/",
    "https://www.scholarshipportal.com/",
    "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/",
    "https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en",
]


def domain_kind(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return "aggregator" if any(h in host for h in AGGREGATOR_HINTS) else "official?"


def usage(key: str) -> dict | None:
    try:
        r = httpx.get("https://api.tavily.com/usage", headers={"Authorization": f"Bearer {key}"}, timeout=20)
        return r.json() if r.status_code == 200 else {"status": r.status_code}
    except httpx.HTTPError:
        return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    key = os.environ["TAVILY_API_KEY"]
    client = TavilyClient(key)
    before = usage(key)

    results = []
    for kind, q in QUERIES:
        r = client.search(q, max_results=10, search_depth="basic", include_raw_content=True)
        items = [{
            "url": it["url"],
            "title": it.get("title", ""),
            "kind": domain_kind(it["url"]),
            "score": it.get("score"),
            "snippet": it.get("content", "")[:300],
            "raw_len": len(it.get("raw_content") or ""),
            "years": {y: (it.get("raw_content") or it.get("content", "")).count(y) for y in ("2025", "2026", "2027")},
        } for it in r["results"]]
        results.append({"kind": kind, "query": q, "items": items})
        c = Counter(i["kind"] for i in items)
        print(f"\n[{kind}] {q}\n  official?={c['official?']} aggregator={c['aggregator']} "
              f"raw_ok={sum(i['raw_len'] > 500 for i in items)}/{len(items)}")
        for i in items:
            print(f"   {i['kind'][:4]} raw={i['raw_len']:<6} y={list(i['years'].values())} {i['url'][:110]}")

    ex = client.extract(EXTRACT_URLS)
    print("\n[extract]")
    extract = []
    for it in ex.get("results", []):
        extract.append({"url": it["url"], "raw_len": len(it.get("raw_content") or ""),
                        "head": (it.get("raw_content") or "")[:400]})
        print(f"   ok   raw={len(it.get('raw_content') or ''):<6} {it['url']}")
    for it in ex.get("failed_results", []):
        extract.append({"url": it.get("url"), "error": it.get("error")})
        print(f"   FAIL {it.get('url')} {it.get('error')}")

    after = usage(key)
    print("\nusage before:", before, "\nusage after:", after)
    (OUT / "tavily_results.json").write_text(
        json.dumps({"search": results, "extract": extract, "usage": [before, after]}, ensure_ascii=False, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    main()
