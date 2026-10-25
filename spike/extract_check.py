"""Спайк: извлечение фактов о стипендии LLM-моделью по JSON-схеме на страницах с ловушками.

Текст страниц: свой fetch + trafilatura, для страниц, недоступных нам, — Tavily Extract.
Проверяем автоматически, что каждая цитата буквально есть в тексте; правильность значений сверяется вручную.
"""

import json
import os
import sys
import time
from pathlib import Path

import httpx
import trafilatura
from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

from fetch_check import BOT_UA

load_dotenv(Path(__file__).parent.parent / ".env")
OUT = Path(__file__).parent / "out"
MODEL = "gpt-5.4-mini-2026-03-17"
TODAY = "2026-10-25"

PAGES = {
    "eiffel": "https://www.campusfrance.org/en/eiffel-scholarship-program-of-excellence",
    "chevening_timeline": "https://www.chevening.org/scholarships/application-timeline/",
    "lund_global_old": "https://www.lunduniversity.lu.se/admissions/bachelors-and-masters-studies/scholarships-and-awards/lund-university-global-scholarship",
    "commonwealth_masters": "https://cscuk.fcdo.gov.uk/scholarships/commonwealth-masters-scholarships/",
    "nl_scholarship": "https://www.studyinnl.org/finances/nl-scholarship",
    "gates_timeline": "https://www.gatescambridge.org/apply/timeline/",
    "boell": "https://www.boell.de/en/scholarships",
    "knight_hennessy_deadlines": "https://knight-hennessy.stanford.edu/admission/preparing-your-applications/application-deadlines",
    "si_global_professionals": "https://si.se/en/apply/scholarships/swedish-institute-scholarships-for-global-professionals/",
    "daad_detail_57742130": "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database?detail=57742130",
    "eth_dates": "https://ethz.ch/en/studies/master/application/dates.html",
    "rhodes_key_facts": "https://www.rhodeshouse.ox.ac.uk/scholarships/key-facts-about-the-rhodes-scholarship/",
    "vanier": "https://vanier.gc.ca/en/home-accueil.html",
    "seo_gates_2027": "https://opportunitiescorners.com/gates-cambridge-scholarship-2027",
    "seo_daad_2027": "https://opportunitiesnexus.com/daad-scholarship-2027-germany",
}

QUOTE = {"type": "string", "description": "дословная цитата из текста страницы, подтверждающая значение"}
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scholarship_name", "funder", "levels", "cycle", "deadlines", "amount", "citizenship_restrictions",
                 "status_for_target_cycle", "notes"],
    "properties": {
        "scholarship_name": {"type": "string"},
        "funder": {"type": "string"},
        "levels": {"type": "array", "items": {"type": "string", "enum": ["bachelor", "master", "phd", "postdoc", "other"]}},
        "cycle": {"type": ["string", "null"], "description": "учебный год начала обучения, к которому относятся даты, напр. 2027/28"},
        "deadlines": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["date", "granularity", "type", "scope", "scope_detail", "quote"],
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD, YYYY-MM если известен только месяц"},
                    "granularity": {"type": "string", "enum": ["day", "month"]},
                    "type": {"type": "string", "enum": ["application", "offer_or_documents", "results", "opening", "other"]},
                    "scope": {"type": "string", "enum": ["global", "country", "university", "program", "applicant_group"]},
                    "scope_detail": {"type": ["string", "null"]},
                    "quote": QUOTE,
                },
            },
        },
        "amount": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["value", "currency", "period", "coverage", "quote"],
            "properties": {
                "value": {"type": ["number", "null"]},
                "currency": {"type": ["string", "null"]},
                "period": {"type": ["string", "null"], "enum": ["month", "year", "total", None]},
                "coverage": {"type": ["string", "null"]},
                "quote": QUOTE,
            },
        },
        "citizenship_restrictions": {"type": ["string", "null"]},
        "status_for_target_cycle": {"type": "string", "enum": ["confirmed", "only_past_cycle", "not_found"]},
        "notes": {"type": "string"},
    },
}

SYSTEM = f"""Ты извлекаешь факты о стипендии из текста одной веб-страницы. Сегодня {TODAY}. Целевой цикл — начало обучения в 2027 году (2027/28).
Правила:
- Используй только текст страницы. Ничего не добавляй из своих знаний.
- У каждого значения должна быть дословная цитата из текста.
- Дедлайн без года не достраивай; если известен только месяц — granularity=month.
- Различай тип даты: подача заявки, дедлайн документов/оффера, результаты, открытие приёма.
- Если дедлайн зависит от страны, университета или программы — укажи scope и scope_detail.
- status_for_target_cycle=confirmed только если на странице есть даты именно для цикла 2027/28; если даты только прошлого цикла — only_past_cycle.
- Если чего-то нет на странице — null или пустой список."""


def page_text(url: str, client: httpx.Client, tavily: TavilyClient) -> tuple[str, str]:
    try:
        r = client.get(url)
        if r.status_code == 200:
            text = trafilatura.extract(r.text, include_tables=True, favor_recall=True) or ""
            if len(text) > 300:
                return text, "own_fetch"
    except httpx.HTTPError:
        pass
    ex = tavily.extract([url])
    text = (ex.get("results") or [{}])[0].get("raw_content") or ""
    return text, "tavily_extract" if text else "none"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    (OUT / "pages").mkdir(parents=True, exist_ok=True)
    client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": BOT_UA})
    tavily = TavilyClient(os.environ["TAVILY_API_KEY"])
    llm = OpenAI()

    results, tokens_in, tokens_out = [], 0, 0
    for name, url in PAGES.items():
        text, src = page_text(url, client, tavily)
        (OUT / "pages" / f"{name}.txt").write_text(text, encoding="utf-8")
        if not text:
            print(f"{name}: нет текста")
            continue

        t0 = time.time()
        resp = llm.responses.create(
            model=MODEL,
            input=[{"role": "system", "content": SYSTEM},
                   {"role": "user", "content": f"URL: {url}\n\nТекст страницы:\n{text[:60000]}"}],
            text={"format": {"type": "json_schema", "name": "scholarship", "schema": SCHEMA, "strict": True}},
            reasoning={"effort": "low"},
        )
        dt = time.time() - t0
        data = json.loads(resp.output_text)
        tokens_in += resp.usage.input_tokens
        tokens_out += resp.usage.output_tokens

        quotes = [d["quote"] for d in data["deadlines"]] + ([data["amount"]["quote"]] if data["amount"] else [])
        norm = " ".join(text.split())
        grounded = [q for q in quotes if " ".join(q.split()) in norm]
        results.append({"name": name, "url": url, "source": src, "text_len": len(text), "latency_s": round(dt, 1),
                        "tokens": [resp.usage.input_tokens, resp.usage.output_tokens],
                        "quotes_total": len(quotes), "quotes_verbatim": len(grounded), "extraction": data})
        dl = "; ".join(f"{d['date']}[{d['type'][:4]},{d['scope'][:4]}]" for d in data["deadlines"])
        print(f"{name:<26} src={src:<14} cycle={data['cycle']} status={data['status_for_target_cycle']:<15} "
              f"levels={data['levels']} quotes={len(grounded)}/{len(quotes)} t={dt:.1f}s\n    deadlines: {dl}\n"
              f"    amount: {data['amount'] and (data['amount']['value'], data['amount']['currency'], data['amount']['period'])}")

    (OUT / "extract_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmodel={MODEL} tokens in={tokens_in} out={tokens_out}")


if __name__ == "__main__":
    main()
