"""Подстраницы с датами и каталог Erasmus Mundus: есть ли программы в HTML."""

import re
import sys

from probe import client, dates_on

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for name, url in {
        "chevening_timeline": "https://www.chevening.org/scholarships/application-timeline/",
        "gates_timeline": "https://www.gatescambridge.org/apply/timeline/",
        "rhodes_key_facts": "https://www.rhodeshouse.ox.ac.uk/scholarships/key-facts-about-the-rhodes-scholarship/",
        "lund_global": "https://www.lunduniversity.lu.se/admissions/bachelors-and-masters-studies/scholarships-and-awards/lund-university-global-scholarship",
    }.items():
        dates_on(name, url)

    html = client.get("https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en").text
    progs = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>\s*([^<]{10,120})</a>', html)
    em = [(h, t.strip()) for h, t in progs if "master" in t.lower() or "erasmus mundus" in t.lower()]
    print(f"\n== erasmus_mundus_catalogue: ссылок={len(progs)}, похожих на программы={len(em)}")
    for h, t in em[:8]:
        print(f"    {t[:70]:<70} {h[:80]}")
