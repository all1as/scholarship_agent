# Разбор расхождений разметчиков A и B

Подвыборка: 30 стипендий (`eval/gt/agreement_subset.txt`). Разметчик A — LLM-агент (Claude, Claude Code), разметчик B — независимый LLM-агент второго участника команды (отдельная сессия Claude Code, только инструкция и снимки). Скрипт: `eval/scripts/agreement.py`. Дата: 25.10.2026.

## Согласие (до разбора)

| Поле | Значение | Цель |
|---|---|---|
| дедлайны подачи (дата + точность + область), полное совпадение | 29/30 = 97 % | ≥90 % |
| основная выплата (сумма + валюта + период + полное покрытие) | 28/30 = 93 % | ≥85 % |
| статус цикла, κ Коэна | 1,00 | ≥0,8 |
| `open_to_ru`, κ Коэна | 0,84 | ≥0,8 |

Все показатели выше целей — эталон принимается. Эти значения — потолок M4 и M5 (раздел 7.4 design doc).

## Решения по расхождениям

| id | Поле | A | B | Решение | Почему |
|---|---|---|---|---|---|
| eiffel | open_to_ru | unknown | yes | **B** — A исправлен | «encourages applicants from foreign countries»: открыто для иностранцев, Россия не исключена — по инструкции 2.8 это `yes` |
| boell_international | open_to_ru | unknown | yes | **B** — A исправлен | «International students … can apply»; приоритет странам DAC — не исключение остальных |
| kas_international | open_to_ru | unknown | yes | **B** — A исправлен | «aimed at international students … from non-EU countries» — `yes` по инструкции 2.8 |
| commonwealth_masters | amount.full_coverage | true | null | **A** | «covers fees, approved fares, and personal maintenance» — полное покрытие сказано явно |
| master_mind | amount.full_coverage | null | false | **A**, инструкция уточнена | о полном покрытии страница ничего не говорит → `null`; `false` — только если страница прямо говорит о частичном покрытии |
| dk_government_scholarship_au | scope дедлайнов | global | program | **A**, инструкция уточнена | «летний / зимний набор» — общий раунд приёма, а не дедлайн конкретной программы |

**Вывод.** У разметчика A систематическая ошибка — излишняя осторожность в `open_to_ru` (ставил `unknown` там, где инструкция требует `yes`). Все остальные метки A2 с `unknown` перепроверены поиском формулировок «non-EU / international / foreign / Ausländer / all nationalities» в снимках. Исправлены ещё две: `hss_international` (программа «Internationale Studierende und Promovierende (Ausländer)») и `fes_international` (отложенная часть; «Grundförderung für Ausländer:innen»). Остальные `unknown` оставлены: у Chevening, DAAD, Rhodes, Stipendium Hungaricum, MAECI, MMEG список стран вынесен на другую страницу; у Oulu и Tampere «для иностранцев» относится к плате за обучение, а не к условиям стипендии; у прочих фраза описывает аудиторию, а не условие.

## Выборочная проверка человеком

Ожидается: 20 случайных меток A + все расхождения выше. Записывать сюда: id, поле, было, стало, кто проверял.
