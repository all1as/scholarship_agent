"""Проверка меток A2: JSON-схема, соответствие формата даты точности, цитаты есть в снимках.

Запуск: python eval/scripts/validate.py eval/gt/labels_a.jsonl
"""

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "eval" / "gt" / "pages"
SCHEMA = json.loads((ROOT / "eval" / "schema" / "label.schema.json").read_text(encoding="utf-8"))
DATE_BY_GRANULARITY = {"day": r"^\d{4}-\d{2}-\d{2}$", "month": r"^\d{4}-\d{2}$", "day_no_year": r"^--\d{2}-\d{2}$"}


def norm(s: str) -> str:
    return " ".join(re.sub(r"[“”«»\"*|#\[\]]", " ", s).split()).lower()


def quoted(label: dict):
    """Все пары (путь к полю, цитата, страница) из метки."""
    for key in ("levels", "fields", "covers", "open_to_ru"):
        if label[key]["quote"]:
            yield key, label[key]["quote"], label[key]["page"]
    if label["amount"]:
        yield "amount", label["amount"]["quote"], label["amount"]["page"]
    for kind in ("application_deadlines", "other_dates"):
        for i, d in enumerate(label[kind]):
            yield f"{kind}[{i}]", d["quote"], d["page"]


def check(label: dict) -> list[str]:
    errors = [f"schema: {'/'.join(map(str, e.path))}: {e.message}"
              for e in Draft202012Validator(SCHEMA).iter_errors(label)]
    if errors:
        return errors
    for kind in ("application_deadlines", "other_dates"):
        for i, d in enumerate(label[kind]):
            if not re.match(DATE_BY_GRANULARITY[d["granularity"]], d["date"]):
                errors.append(f"{kind}[{i}]: дата {d['date']} не соответствует точности {d['granularity']}")
    for field, quote, page in quoted(label):
        if not page.startswith(label["id"] + "/"):
            errors.append(f"{field}: снимок {page} не принадлежит {label['id']}")
            continue
        path = PAGES / page
        if not path.exists():
            errors.append(f"{field}: нет снимка {page}")
        elif norm(quote) not in norm(path.read_text(encoding="utf-8")):
            errors.append(f"{field}: цитата не найдена в {page}: {quote[:80]!r}")
    has_2027 = any(d["cycle"] == "2027/28" for d in label["application_deadlines"])
    if label["cycle_status"] == "published" and not has_2027:
        errors.append("cycle_status=published, но нет дедлайна подачи цикла 2027/28")
    if label["cycle_status"] != "published" and has_2027:
        errors.append(f"cycle_status={label['cycle_status']}, но есть дедлайн подачи цикла 2027/28")
    return errors


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "eval" / "gt" / "labels_a.jsonl")
    ids, bad = set(), 0
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        label = json.loads(line)
        if label["id"] in ids:
            print(f"строка {line_no}: повтор id {label['id']}")
            bad += 1
        ids.add(label["id"])
        errors = check(label)
        bad += bool(errors)
        for e in errors:
            print(f"{label['id']}: {e}")
    print(f"\n{len(ids)} меток, с ошибками: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
