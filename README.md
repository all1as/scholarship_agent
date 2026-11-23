# scholarship_agent

Агент-«тетрадь» для поиска и отслеживания стипендий на магистратуру (STEM/IT, ЕС, UK, США, Канада). Подробности — в [design doc](docs/design_doc.md).

## Структура

- `docs/design_doc.md` — design doc проекта.
- `docs/spike_kt2.md` — проверка источников данных и LLM-извлечения перед КТ2.
- `spike/` — скрипты спайка.
- `eval/` — eval-сет, эталонная разметка и скрипты (снимки страниц, проверка меток, согласие разметчиков, отложенная часть).
- `docs/annotation_guide.md` — инструкция разметчика; `docs/annotator_b_prompt.md` — промпт для второго разметчика.
- `harness/` — система (оркестратор, тетрадь SQLite, LLM-извлечение), baseline B1 и eval-харнесс (design doc, разделы 5–6).
- `adr/` — архитектурные решения; `runs/` — сохранённые прогоны с метаданными; `tests/` — тесты без сети.

## Прогон eval (КТ3)

```bash
python -m harness run --system b1 --suite extract     # baseline B1 на видимой части A2
python -m harness run --system llm --suite extract    # LLM-извлечение: нужны OPENAI_API_KEY и PRICE_IN/PRICE_OUT в .env
python -m harness scenarios                         # S1–S7, офлайн с фиксированными ответами экстрактора
python -m harness compare runs/<id1> runs/<id2>       # метрики, стоимость, время рядом
python -m unittest discover tests
```

Результаты КТ3: [baseline B1](runs/20261123-124650-424215_b1_extract), [сценарии S1–S7](runs/20261123-124651-076585_agent-replay_scenarios), [ADR-001](adr/001-notebook-levels.md).

Baseline и LLM сравниваются на одинаковых задачах A2. Сценарии проверяют оркестрацию и память на фиксированных ответах экстрактора. Живой LLM-прогон оценивает извлечение отдельно.

Каждый прогон сохраняется в `runs/<дата>_<система>_<набор>/` (`meta.json` — модель, промпт, seed, версия eval, коммит, стоимость, время).

## Разметка eval-сета

Эталонная разметка (ground truth) выполнена с помощью LLM-агента с человеческой проверкой:
- у каждой метки есть URL источника и дословная цитата со страницы, поэтому её можно проверить без знаний предметной области;
- независимая вторая разметка на подвыборке выполнена отдельным LLM-агентом, по ней посчитано согласие разметчиков;
- часть меток выборочно проверена человеком по цитатам.

Процедура описана в design doc, раздел 7.

## Запуск

```bash
uv venv .venv
uv pip install --python .venv -r requirements.txt
cp .env.example .env  # и заполнить ключи
```
