"""Проверка, что цитаты из извлечения есть в тексте страницы (с нормализацией кавычек и markdown-разметки)."""

import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).parent / "out"


def norm(s: str) -> str:
    return " ".join(re.sub(r"[“”«»\"*|#\[\]]", " ", s).split())


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    total = ok = 0
    for x in json.loads((OUT / "extract_results.json").read_text(encoding="utf-8")):
        text = norm((OUT / "pages" / f"{x['name']}.txt").read_text(encoding="utf-8"))
        e = x["extraction"]
        quotes = [d["quote"] for d in e["deadlines"]] + ([e["amount"]["quote"]] if e["amount"] else [])
        bad = [q for q in quotes if norm(q) not in text]
        total += len(quotes)
        ok += len(quotes) - len(bad)
        for q in bad:
            print(f"{x['name']}: NOT FOUND: {q[:160]}")
    print(f"verbatim after normalisation: {ok}/{total}")


if __name__ == "__main__":
    main()
