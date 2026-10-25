# Промпт для разметчика B

Второй участник команды запускает своего LLM-агента (Claude Code, Cursor, Codex и т. п.) в клоне репозитория и вставляет текст ниже целиком. Запускать **после того, как в ветке `kt2` появится файл `eval/gt/agreement_subset.txt`**.

Агенту нужен доступ к файлам и терминалу. Интернет и API-ключи не нужны: разметка делается только по сохранённым снимкам страниц.

---

```text
Ты — независимый разметчик B для eval-набора учебного проекта scholarship_agent. Твоя задача — разметить 30 стипендий по сохранённым снимкам страниц, чтобы потом посчитать согласие с другим разметчиком. Важна независимость: работай только по инструкции и снимкам.

Подготовка:
1. git fetch origin && git checkout kt2 && git pull
2. git checkout -b kt2-annotator-b
3. Создай окружение и поставь зависимости: uv venv .venv && uv pip install --python .venv -r requirements.txt
   (без uv: python -m venv .venv и pip install -r requirements.txt)

Прочитай полностью:
- docs/annotation_guide.md — инструкция, следуй ей буквально;
- eval/schema/label.schema.json — формат метки;
- eval/gt/agreement_subset.txt — id 30 стипендий, которые нужно разметить;
- eval/gt/pages/manifest.csv — какие снимки относятся к какому id.

ЗАПРЕЩЕНО открывать, читать, искать по содержимому или выводить файлы:
- eval/gt/labels_a.jsonl
- eval/gt/adjudication.md
- всё в eval/heldout/
Не заходи в интернет и не используй свои знания о стипендиях: только текст снимков из eval/gt/pages/<id>/*.txt.

Работа:
4. Для каждого id из agreement_subset.txt прочитай все его снимки и составь одну метку по схеме, "annotator": "B", "labeled_at": сегодняшняя дата. У каждого значения — дословная цитата из снимка и имя файла снимка в поле page (формат "<id>/<n>.txt").
5. Запиши метки в eval/gt/labels_b.jsonl — по одной JSON-строке на стипендию, в порядке agreement_subset.txt.
6. Запусти: .venv/bin/python eval/scripts/validate.py eval/gt/labels_b.jsonl
   (Windows: .venv\Scripts\python eval\scripts\validate.py eval\gt\labels_b.jsonl)
   Исправляй ошибки, пока не будет "с ошибками: 0". Если цитата не находится — скопируй её из снимка заново, не меняй значение под цитату.
7. Если случай спорный по инструкции — прими решение по разделу 4 инструкции и кратко опиши сомнение в поле notes. Не пропускай стипендии.

Сдача:
8. git add eval/gt/labels_b.jsonl
9. git commit -m "КТ2: разметка B (30 стипендий для согласия разметчиков)"
10. git push -u origin kt2-annotator-b
11. Открой pull request из kt2-annotator-b в kt2 с заголовком "КТ2: разметка B". Если есть gh: gh pr create --base kt2 --head kt2-annotator-b --title "КТ2: разметка B" --body "Независимая разметка B 30 стипендий из eval/gt/agreement_subset.txt по docs/annotation_guide.md. validate.py проходит без ошибок."
12. В конце выведи: сколько стипендий размечено, сколько с пометками о сомнениях в notes, ссылку на PR.
```
