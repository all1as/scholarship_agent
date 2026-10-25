"""Спайк: можно ли получить текст страниц стипендий своим fetch + trafilatura.

Для каждого URL проверяем robots.txt, HTTP-статус, длину основного текста,
наличие слова deadline и дат, упоминания циклов 2025-2027, стабильность хэша
основного текста между двумя загрузками и наличие снапшотов в Wayback Machine.
"""

import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura

from urls import AGGREGATORS, OFFICIAL

BOT_UA = "ScholarshipNotebookBot/0.1 (student project; +https://github.com/all1as/scholarship_agent)"
OUT = Path(__file__).parent / "out"

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})\s+20\d\d\b"
    rf"|\b(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+20\d\d\b"
    r"|\b\d{1,2}\.\d{1,2}\.20\d\d\b",
    re.IGNORECASE,
)
DEADLINE_RE = re.compile(r"deadline|closing date|apply by|application period", re.IGNORECASE)


async def robots_allowed(client: httpx.AsyncClient, url: str) -> bool | None:
    parts = urlparse(url)
    try:
        r = await client.get(f"{parts.scheme}://{parts.netloc}/robots.txt", headers={"User-Agent": BOT_UA})
    except httpx.HTTPError:
        return None
    if r.status_code >= 400:
        return True
    rp = RobotFileParser()
    rp.parse(r.text.splitlines())
    return rp.can_fetch(BOT_UA, url)


async def fetch(client: httpx.AsyncClient, url: str, ua: str) -> tuple[int | None, str, str]:
    try:
        r = await client.get(url, headers={"User-Agent": ua})
        return r.status_code, r.headers.get("content-type", ""), r.text
    except httpx.HTTPError as e:
        return None, type(e).__name__, ""


def extract(html: str) -> str:
    return trafilatura.extract(html, include_tables=True, favor_recall=True) or ""


async def wayback(client: httpx.AsyncClient, url: str, ts: str) -> str | None:
    try:
        r = await client.get("https://archive.org/wayback/available", params={"url": url, "timestamp": ts})
        snap = r.json().get("archived_snapshots", {}).get("closest")
        return snap["timestamp"] if snap and snap.get("available") else None
    except (httpx.HTTPError, ValueError):
        return None


async def check(client: httpx.AsyncClient, sem: asyncio.Semaphore, name: str, url: str, kind: str) -> dict:
    async with sem:
        res = {"name": name, "kind": kind, "url": url, "robots_allowed": await robots_allowed(client, url)}
        if res["robots_allowed"] is False:
            res.update(status="robots", text_len=0, has_deadline_word=False, years={},
                       wayback_2025=await wayback(client, url, "20250301"), wayback_2024=None)
            return res
        status, ctype, html = await fetch(client, url, BOT_UA)
        res["status"] = status
        res["content_type"] = ctype
        text = extract(html) if status == 200 else ""
        res["html_len"] = len(html)
        res["text_len"] = len(text)
        res["has_deadline_word"] = bool(DEADLINE_RE.search(text))
        res["dates"] = sorted(set(m.group(0) for m in DATE_RE.finditer(text)))[:8]
        res["years"] = {y: text.count(y) for y in ("2025", "2026", "2027")}
        m = DEADLINE_RE.search(text)
        res["deadline_snippet"] = text[max(0, m.start() - 80): m.end() + 160].replace("\n", " ") if m else ""

        # второй fetch: стабилен ли хэш основного текста (нужно для дешёвой перепроверки)
        if text:
            _, _, html2 = await fetch(client, url, BOT_UA)
            text2 = extract(html2)
            res["hash_stable_text"] = hashlib.sha256(text.encode()).hexdigest() == hashlib.sha256(text2.encode()).hexdigest()
            res["hash_stable_html"] = hashlib.sha256(html.encode()).hexdigest() == hashlib.sha256(html2.encode()).hexdigest()

        res["wayback_2025"] = await wayback(client, url, "20250301")
        res["wayback_2024"] = await wayback(client, url, "20240301")
        return res


async def main() -> None:
    OUT.mkdir(exist_ok=True)
    sem = asyncio.Semaphore(6)
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        tasks = [check(client, sem, n, u, "official") for n, u in OFFICIAL.items()]
        tasks += [check(client, sem, n, u, "aggregator") for n, u in AGGREGATORS.items()]
        results = await asyncio.gather(*tasks)
    (OUT / "fetch_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    for r in results:
        print(
            f"{r['name']:<26} robots={str(r['robots_allowed']):<5} status={str(r['status']):<4} "
            f"text={r['text_len']:<6} dl={int(r['has_deadline_word'])} "
            f"y={r['years']} hashT={r.get('hash_stable_text', '-')} hashH={r.get('hash_stable_html', '-')} "
            f"wb25={r['wayback_2025']} wb24={r['wayback_2024']}"
        )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
