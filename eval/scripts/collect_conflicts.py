"""Сбор кандидатов для A3 (пары «официальный источник vs агрегатор / прошлогодний снимок»).

Для стипендий видимой части с подтверждённым дедлайном 2027/28:
- агрегатор: поиск Tavily «<название> deadline 2027» без официального домена и соцсетей, первый результат с текстом;
- прошлый цикл: снимок официальной страницы в Wayback Machine около октября 2025.
Тексты сохраняются в eval/gt/pages/<id>/agg_1.txt и wb_1.txt (+ строка в manifest.csv), дальше пары размечаются вручную.
"""

import csv
import hashlib
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
from dotenv import load_dotenv
from tavily import TavilyClient

ROOT = Path(__file__).resolve().parents[2]
GT = ROOT / "eval" / "gt"
BOT_UA = "ScholarshipNotebookBot/0.1 (student project; +https://github.com/all1as/scholarship_agent)"
SOCIAL = ["facebook.com", "instagram.com", "linkedin.com", "reddit.com", "quora.com", "youtube.com", "x.com", "twitter.com"]

load_dotenv(ROOT / ".env")


def save(sid: str, name: str, url: str, text: str, source: str, manifest: list) -> None:
    (GT / "pages" / sid / f"{name}.txt").write_text(text, encoding="utf-8")
    manifest.append({"id": sid, "n": name, "url": url, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                     "fetched_at": date.today().isoformat(), "source": source, "chars": len(text)})


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    labels = [json.loads(l) for l in (GT / "labels_a.jsonl").read_text(encoding="utf-8").splitlines() if l]
    refs = {r["id"]: r for r in csv.DictReader((GT / "reference_list.csv").open(encoding="utf-8"))}
    with (GT / "pages" / "manifest.csv").open(encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    tavily = TavilyClient(os.environ["TAVILY_API_KEY"])
    client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": BOT_UA})

    targets = [l for l in labels if l["cycle_status"] == "published"]
    for l in targets:
        sid, ref = l["id"], refs[l["id"]]
        official_host = ".".join(urlparse(ref["official_url"]).netloc.split(".")[-2:])
        res = tavily.search(f"{l['name']} deadline 2027", max_results=6, search_depth="basic", include_raw_content=True,
                            exclude_domains=SOCIAL + [official_host])
        agg = next((r for r in res["results"] if len(r.get("raw_content") or "") > 800), None)
        if agg:
            save(sid, "agg_1", agg["url"], agg["raw_content"], "tavily_search_raw", manifest)
        wb_url = None
        try:
            r = client.get("https://archive.org/wayback/available",
                           params={"url": ref["official_url"], "timestamp": "20251015"})
            snap = r.json().get("archived_snapshots", {}).get("closest")
            if snap and snap.get("available") and snap["timestamp"] < "20260301":
                wb_url = snap["url"]
                page = client.get(wb_url)
                text = trafilatura.extract(page.text, include_tables=True, favor_recall=True) or ""
                if len(text) > 300:
                    save(sid, "wb_1", wb_url, text, f"wayback_{snap['timestamp'][:8]}", manifest)
                else:
                    wb_url = None
        except (httpx.HTTPError, ValueError):
            wb_url = None
        print(f"{sid:<30} agg={'+' if agg else '-'} {agg['url'][:70] if agg else ''} | wb={'+' if wb_url else '-'}")
        time.sleep(2)

    with (GT / "pages" / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "n", "url", "sha256", "fetched_at", "source", "chars"])
        w.writeheader()
        w.writerows(manifest)


if __name__ == "__main__":
    main()
