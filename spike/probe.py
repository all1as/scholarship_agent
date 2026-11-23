"""Точечные проверки: Wayback из Python, JS-каталоги (DAAD, Erasmus Mundus), подстраницы с датами."""

import re
import sys

import httpx
import trafilatura

from fetch_check import BOT_UA, DATE_RE

client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": BOT_UA})


def wayback_python() -> None:
    r = client.get("https://archive.org/wayback/available",
                   params={"url": "https://www.chevening.org/scholarships/", "timestamp": "20250301"})
    print("wayback:", r.status_code, r.text[:300])


def look_for_api(name: str, url: str) -> None:
    r = client.get(url)
    html = r.text
    hits = sorted(set(re.findall(r"""["'](/[^"']*(?:api|json|search|ajax)[^"']*)["']""", html, re.I)))[:15]
    print(f"\n== {name}: status={r.status_code} html={len(html)} script_tags={html.count('<script')}")
    for h in hits:
        print("   ", h)


def subpage_links(name: str, url: str) -> None:
    r = client.get(url)
    links = re.findall(r"""href=["']([^"']+)["'][^>]*>([^<]{0,80})<""", r.text)
    keep = [(h, t.strip()) for h, t in links
            if re.search(r"date|deadline|apply|timeline|eligib|how-to|key", h + t, re.I)]
    print(f"\n== {name}: {len(keep)} подходящих ссылок")
    for h, t in keep[:12]:
        print(f"    {t[:40]:<40} {h}")


def dates_on(name: str, url: str) -> None:
    r = client.get(url)
    text = trafilatura.extract(r.text, include_tables=True, favor_recall=True) or ""
    dates = sorted(set(m.group(0) for m in DATE_RE.finditer(text)))
    print(f"\n== {name}: status={r.status_code} text={len(text)} dates={dates[:10]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    wayback_python()
    look_for_api("daad_database", "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/")
    look_for_api("erasmus_mundus_catalogue", "https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en")
    for name, url in {
        "chevening": "https://www.chevening.org/scholarships/",
        "gates_cambridge": "https://www.gatescambridge.org/apply/",
        "eth_esop": "https://ethz.ch/students/en/studies/financial/scholarships/excellencescholarship.html",
        "rhodes": "https://www.rhodeshouse.ox.ac.uk/scholarships/apply/",
    }.items():
        subpage_links(name, url)
