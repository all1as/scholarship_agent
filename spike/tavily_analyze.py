"""Разбор выдачи Tavily: официальные домены / SEO-блоги / соцсети. Классификация доменов — ручная, по результатам прогона."""

import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura

from fetch_check import BOT_UA

OUT = Path(__file__).parent / "out"

SOCIAL = ("facebook.", "instagram.", "linkedin.", "reddit.", "quora.", "youtube.")
OFFICIAL = (
    "daad.de", "daad.org", "studyinnl.org", "britishcouncil.org", "ed.ac.uk", "gov.uk", "chevening.org", "uni-kl.de",
    "eminent-master.eu", "europa.eu", "uni-siegen.de", "unfc.ca", "utoronto.ca", "iie.org", "mun.ca", "misis.ru",
    "rosalux.de", "diplomatie.gouv.fr", "campusfrance.org", "si.se", "rug.nl", "maastrichtuniversity.nl", "ru.nl",
    "utwente.nl", "nuffic.nl", "stanford.edu", "gatescambridge.org", "ethz.ch", "ethz-foundation.ch", "lu.se",
)


def kind(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if any(s in host for s in SOCIAL):
        return "social"
    if any(host == d or host.endswith("." + d) for d in OFFICIAL):
        return "official"
    return "seo"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    data = json.loads((OUT / "tavily_results.json").read_text(encoding="utf-8"))
    total = Counter()
    for q in data["search"]:
        kinds = [kind(i["url"]) for i in q["items"]]
        c = Counter(kinds)
        total.update({f"{q['kind']}:{k}": v for k, v in c.items()})
        top3 = [kind(i["url"]) for i in q["items"][:3]]
        off_raw = sum(1 for i in q["items"] if kind(i["url"]) == "official" and i["raw_len"] > 500)
        print(f"{q['kind']:<9} off={c['official']:<2} seo={c['seo']:<2} soc={c['social']:<2} "
              f"official_in_top3={top3.count('official')} official_with_text={off_raw}  {q['query'][:60]}")
    print("\nИтого по типам запросов:", dict(total))

    print("\n[extract] начало текста:")
    for e in data["extract"]:
        print(f"--- {e['url']}\n{(e.get('head') or e.get('error') or '')[:400]}\n")

    # детальные страницы базы DAAD: отдаёт ли их наш fetch
    client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": BOT_UA})
    for d in ("57742130", "50026200", "50076777"):
        url = f"https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database?detail={d}"
        r = client.get(url)
        text = trafilatura.extract(r.text, include_tables=True, favor_recall=True) or ""
        print(f"DAAD detail {d}: status={r.status_code} text={len(text)} :: {text[:200]!r}")


if __name__ == "__main__":
    main()
