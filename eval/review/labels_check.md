# Проверка меток A2 человеком

Как проверять: открыть файл снимка по ссылке, найти цитату поиском (Ctrl+F) и решить, следует ли значение из цитаты. Знание предметной области не нужно. В колонку «✔/✘» поставить ✔ или ✘; при ✘ — записать в `eval/gt/adjudication.md`: id, поле, было, стало, почему.

Выборка: 20 случайных видимых меток (seed 2027) + 6 стипендий, где расходились разметчики A и B.

## Случайная выборка

### Amsterdam Merit Scholarship (University of Amsterdam) (`amsterdam_excellence`)

Примечание разметчика: На обзорной странице нет ни дедлайна, ни суммы; подробности — на отдельной странице стипендии и страницах факультетов. Название в A1 (Amsterdam Excellence Scholarships) — прежнее.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | who plan to do a Master's programme at the University of Amsterdam. | [amsterdam_excellence/1.txt](../gt/pages/amsterdam_excellence/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | yes | The Amsterdam Merit Scholarship is for outstanding students from outside the EU/EEA | [amsterdam_excellence/1.txt](../gt/pages/amsterdam_excellence/1.txt) | |

### Chevening Scholarships (`chevening`)

Примечание разметчика: Точный дедлайн подачи — на странице страны; 8 July 2027 — дедлайн оффера от вуза, не подачи. Список стран-участниц на отдельной странице.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | pursue one-year master’s degrees in the UK | [chevening/1.txt](../gt/pages/chevening/1.txt) | |
| статус цикла 2027/28 | published | — | — | |
| дедлайн подачи | 2026-10 (month), цикл 2027/28, область country — exact date and time on each country/territory page | October 2026 Applications close Please refer to your country page for the deadline. | [chevening/2.txt](../gt/pages/chevening/2.txt) | |
| другая дата: opening | 2026-08 (month) | August 2026 Applications open | [chevening/2.txt](../gt/pages/chevening/2.txt) | |
| другая дата: results | 2027-06 (month) | Mid-June 2027 Results | [chevening/2.txt](../gt/pages/chevening/2.txt) | |
| другая дата: offer_or_documents | 2027-07-08 (day) | The deadline to receive and submit at least one unconditional UK university offer is 17:00 BST (UK time) on 8 July 2027. | [chevening/2.txt](../gt/pages/chevening/2.txt) | |
| сумма | сумма не указана; полное покрытие: да | Chevening Scholarships are fully-funded | [chevening/1.txt](../gt/pages/chevening/1.txt) | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | unknown | — | — | |

### European Master in Embedded Computing Systems (EMECS), Erasmus Mundus (`em_emecs`)

Примечание разметчика: На главной странице нет ни сроков, ни стипендий; последние новости — 2023–2024 гг. Данные о наборе 2027 не найдены.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | is a two-years Master’s course where each of the two academic years is spent at a different EMECS partner university. | [em_emecs/1.txt](../gt/pages/em_emecs/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | unknown | — | — | |

### IMLEX — Erasmus Mundus Master in Imaging and Light in Extended Reality (`em_imlex`)

Примечание разметчика: Полные стипендии EMJM для лучших в наборе 2027; размер ежемесячной выплаты на снятых страницах не указан. Подача через Studyinfo.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | Erasmus Mundus – Master of Science in Imaging and Light in Extended Reality (IMLEX) | [em_imlex/1.txt](../gt/pages/em_imlex/1.txt) | |
| статус цикла 2027/28 | published | — | — | |
| дедлайн подачи | 2027-01-13 (day), цикл 2027/28, область global | Next application round will be open from 2 December 2026 to 13 January 2027. | [em_imlex/2.txt](../gt/pages/em_imlex/2.txt) | |
| другая дата: opening | 2026-12-02 (day) | Next application round will be open from 2 December 2026 to 13 January 2027. | [em_imlex/2.txt](../gt/pages/em_imlex/2.txt) | |
| другая дата: results | 2027-04 (month) | inform the applicants on their admission results in April 2027, at the latest | [em_imlex/2.txt](../gt/pages/em_imlex/2.txt) | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: да, проживание: не сказано, перелёт: не сказано | EMJM scholarship holders do not pay for tuition. | [em_imlex/1.txt](../gt/pages/em_imlex/1.txt) | |
| открыта для РФ | yes | offering full scholarships with monthly allowance for all nationalities. | [em_imlex/1.txt](../gt/pages/em_imlex/1.txt) | |

### EPFL Master Excellence Fellowships (`epfl_excellence`)

Примечание разметчика: «New deadline for the 2027 EPFL Master Excellence Fellowship» — даты без года, цикл 2027/28 по контексту. Заявка — галочка в анкете на магистратуру; оплачена и подтверждена до 15 декабря. Решение — в конце марта.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | allow students to concentrate on their Master’s studies | [epfl_excellence/1.txt](../gt/pages/epfl_excellence/1.txt) | |
| статус цикла 2027/28 | published | — | — | |
| дедлайн подачи | --12-15 (day_no_year), цикл 2027/28, область applicant_group — external applicants applying via IS-Academia | – December 15 for applications submitted via IS-Academia. | [epfl_excellence/1.txt](../gt/pages/epfl_excellence/1.txt) | |
| дедлайн подачи | --01-31 (day_no_year), цикл 2027/28, область applicant_group — EPFL students applying for a consecutive Master's | – January 31 for EPFL students applying for a consecutive Master’s degree. | [epfl_excellence/1.txt](../gt/pages/epfl_excellence/1.txt) | |
| сумма | 10000 CHF / semester; полное покрытие: нет | Amount: CHF 10,000 per semester, with a maximum coverage of 4 semesters. | [epfl_excellence/2.txt](../gt/pages/epfl_excellence/2.txt) | |
| покрывает | обучение: нет, проживание: не сказано, перелёт: не сказано | Students are responsible for managing all living expenses, including tuition fees and rent. | [epfl_excellence/2.txt](../gt/pages/epfl_excellence/2.txt) | |
| открыта для РФ | yes | Anyone applying to a Master’s program at EPFL is eligible. | [epfl_excellence/2.txt](../gt/pages/epfl_excellence/2.txt) | |

### ETH Zurich Excellence Scholarship & Opportunity Programme (ESOP) (`eth_esop`)

Примечание разметчика: Подача вместе с заявкой на магистратуру через eApply в первом окне (1–30.11.2026, 11:59 CET). Решение — в конце марта (год не указан). Ставка с HS27 — 13 500 CHF за семестр.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | ETH Zurich supports excellent Master's students (no MAS) | [eth_esop/1.txt](../gt/pages/eth_esop/1.txt) | |
| статус цикла 2027/28 | published | — | — | |
| дедлайн подачи | 2026-11-30 (day), цикл 2027/28, область global | The next application window is open Nov, 1 - Nov, 30 2026, 11.59h, MEZ for a start in the Master programme in HS27. | [eth_esop/1.txt](../gt/pages/eth_esop/1.txt) | |
| другая дата: opening | 2026-11-01 (day) | International Bachelor's degrees: 1 - 30 November 2026 | [eth_esop/2.txt](../gt/pages/eth_esop/2.txt) | |
| сумма | 13500 CHF / semester; полное покрытие: да; варианты: CHF 12'000 per semester before HS27 | (CHF 12'000 per semester, from HS27 onwards 13'500 CHF) | [eth_esop/1.txt](../gt/pages/eth_esop/1.txt) | |
| покрывает | обучение: да, проживание: да, перелёт: не сказано | The Excellence Scholarship/ESOP consists of a scholarship covering living and study expenses (CHF 12'000 per semester, from HS27 onwards 13'500 CHF) as well as a tuition fee waiver. | [eth_esop/1.txt](../gt/pages/eth_esop/1.txt) | |
| открыта для РФ | unknown | — | — | |

### University of Glasgow Global Leadership Scholarship (`glasgow_leadership`)

Примечание разметчика: Россия явно в списке стран. Приём ещё не открыт («will open shortly»), решение на скользящей основе, закрытие «usually in late August» — точной даты нет.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | starting a postgraduate taught Masters programme in any discipline for Academic Session 2027/2028. | [glasgow_leadership/1.txt](../gt/pages/glasgow_leadership/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | 10000 GBP / total; полное покрытие: нет | £10,000 Tuition Fee Waiver | [glasgow_leadership/1.txt](../gt/pages/glasgow_leadership/1.txt) | |
| покрывает | обучение: да, проживание: нет, перелёт: не сказано | The scholarship is awarded as a tuition fees discount for one year only. | [glasgow_leadership/1.txt](../gt/pages/glasgow_leadership/1.txt) | |
| открыта для РФ | yes | Romania - Russia - Rwanda | [glasgow_leadership/1.txt](../gt/pages/glasgow_leadership/1.txt) | |

### University of Helsinki Scholarship Programme (tuition fee waivers) (`helsinki_scholarship`)

Примечание разметчика: Освобождение от платы на 50 % или 100 % (большинство — 50 %), подаётся в той же заявке, что и на магистратуру; дедлайн на странице не указан. Категории указаны «for application round 2025-26» — устаревшая информация.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | who want to complete a Master's programme at the University of Helsinki. | [helsinki_scholarship/1.txt](../gt/pages/helsinki_scholarship/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: да, проживание: нет, перелёт: не сказано | Please note that university of Helsinki does not offer scholarships to cover living expenses. | [helsinki_scholarship/1.txt](../gt/pages/helsinki_scholarship/1.txt) | |
| открыта для РФ | yes | Scholarships are intended for excellent tuition fee-liable students from outside the EU/EEA and Switzerland who want to complete a Master's programme at the University of Helsinki. | [helsinki_scholarship/1.txt](../gt/pages/helsinki_scholarship/1.txt) | |

### KAAD scholarship programmes (Catholic Academic Exchange Service) (`kaad_eastern_europe`)

Примечание разметчика: Снимок описывает программы 1 и 2 (приглашения для стран-партнёров, программа 2 — для студентов из стран Глобального Юга, уже обучающихся в Германии); отдельная программа для Восточной Европы на этой странице не описана. Дат и сумм нет.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master, phd, other | is aimed at postgraduates and persons with proven professional experience who are usually invited to Germany for postgraduate studies or research stays | [kaad_eastern_europe/1.txt](../gt/pages/kaad_eastern_europe/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | unknown | — | — | |

### Leiden University Excellence Scholarship (LExS) (`leiden_excellence`)

Примечание разметчика: Скидка на обучение одного из пяти уровней, период не указан. Цикл 2027/28 — по контексту (программы с началом в сентябре, дедлайн 1.12.2026). Результаты — до конца марта (год не указан).

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | For excellent students joining a full-time Leiden University Master's degree programme | [leiden_excellence/1.txt](../gt/pages/leiden_excellence/1.txt) | |
| статус цикла 2027/28 | published | — | — | |
| дедлайн подачи | 2026-12-01 (day), цикл 2027/28, область global | Deadline - 1 December 2026 | [leiden_excellence/1.txt](../gt/pages/leiden_excellence/1.txt) | |
| сумма | 10000 EUR / None; полное покрытие: нет; варианты: five award levels: €10,000 / €15,000 / €17,500 / €18,500 / €19,000 of the tuition fee | € 10,000 of the tuition fee | [leiden_excellence/1.txt](../gt/pages/leiden_excellence/1.txt) | |
| покрывает | обучение: да, проживание: не сказано, перелёт: не сказано | The LExS is not a full scholarship and does not cover the full cost of your studies. | [leiden_excellence/1.txt](../gt/pages/leiden_excellence/1.txt) | |
| открыта для РФ | yes | Applicants must have a non-EEA/non-EFTA* passport | [leiden_excellence/1.txt](../gt/pages/leiden_excellence/1.txt) | |

### NSF Graduate Research Fellowship Program (GRFP) (`nsf_grfp`)

Примечание разметчика: Только граждане, национальные подданные или постоянные жители США; иностранцы на студенческой визе явно исключены. Дедлайн зависит от области (Major Field of Study), даты — в Notice of Funding Opportunity; модуль подачи обычно открывается в июле-августе.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master, phd | Must intend to enroll or be enrolled full-time in an eligible research-based master's or doctoral degree program in an eligible field of study in STEM. | [nsf_grfp/1.txt](../gt/pages/nsf_grfp/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | no | Individuals who are not U.S. citizens, U.S. nationals, or permanent residents. | [nsf_grfp/1.txt](../gt/pages/nsf_grfp/1.txt) | |

### University of Oulu Tuition Fee Waiver Scholarships (`oulu_scholarship`)

Примечание разметчика: Частичные скидки на обучение для принятых на программы с осени 2027; отдельного дедлайна стипендии нет. Даты 7 и 21 января 2027 — окно подачи на магистратуру, не на стипендию. Суммы — по программам на другой странице.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | bachelor, master | tuition fee waiver scholarships available for international applicants to the University of Oulu's bachelor's and master's degree programmes. | [oulu_scholarship/1.txt](../gt/pages/oulu_scholarship/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| другая дата: other | 2027-01-07 (day) | 7 January 2027 at 08:00 (UTC+2) \| Application opens | [oulu_scholarship/2.txt](../gt/pages/oulu_scholarship/2.txt) | |
| другая дата: other | 2027-01-21 (day) | 21 January 2027 at 15:00 (UTC+2) \| Application closes | [oulu_scholarship/2.txt](../gt/pages/oulu_scholarship/2.txt) | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: да, проживание: нет, перелёт: не сказано | partial Tuition Fee Waiver Scholarships for students admitted to master's degree programmes starting in autumn 2027. | [oulu_scholarship/1.txt](../gt/pages/oulu_scholarship/1.txt) | |
| открыта для РФ | unknown | — | — | |

### Padua International Excellence Scholarship Programme (`padova_excellence`)

Примечание разметчика: Отдельной заявки нет — кандидат рассматривается при подаче на программу в первом окне; сроки будут в призыве, который опубликуют в ноябре 2026.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | bachelor, master | who wish to attend an English-taught first-cycle/Bachelor's degree course or master's degree. | [padova_excellence/1.txt](../gt/pages/padova_excellence/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| другая дата: other | 2026-11 (month) | More information about Padua International Excellence Scholarships will be available in the Calls for Application that will be published in November 2026. | [padova_excellence/1.txt](../gt/pages/padova_excellence/1.txt) | |
| сумма | 8000 EUR / year; полное покрытие: нет; варианты: gross, plus exemption from student fees | Scholarship amount: €8,000.00 (gross) + exemption from student fees for each academic year. | [padova_excellence/1.txt](../gt/pages/padova_excellence/1.txt) | |
| покрывает | обучение: да, проживание: да, перелёт: не сказано | Scholarship amount: €8,000.00 (gross) + exemption from student fees for each academic year. | [padova_excellence/1.txt](../gt/pages/padova_excellence/1.txt) | |
| открыта для РФ | yes | must not hold the Italian citizenship (unless it is a dual citizenship); | [padova_excellence/1.txt](../gt/pages/padova_excellence/1.txt) | |

### P.E.O. International Peace Scholarship (`peo_ips`)

Примечание разметчика: Только для женщин; нужно уже учиться (enrolled) в США/Канаде с полным годом курсов впереди. Ежегодно 15.09–15.12, объявление в мае.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master, phd | provides scholarships to international women pursuing graduate degrees in the U.S. and Canada | [peo_ips/1.txt](../gt/pages/peo_ips/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| дедлайн подачи | --12-15 (day_no_year), цикл None, область global | Applications are accepted September 15 - December 15 each year. | [peo_ips/2.txt](../gt/pages/peo_ips/2.txt) | |
| другая дата: opening | --09-15 (day_no_year) | Applications are accepted September 15 - December 15 each year. | [peo_ips/2.txt](../gt/pages/peo_ips/2.txt) | |
| сумма | 12500 USD / None; полное покрытие: нет; варианты: maximum; lesser amounts according to need | The maximum amount awarded to a student is $12,500. | [peo_ips/2.txt](../gt/pages/peo_ips/2.txt) | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | yes | is a woman outside the United States and Canada who is seeking an advanced degree from an accredited college or university in the U.S. or Canada | [peo_ips/2.txt](../gt/pages/peo_ips/2.txt) | |

### University of Sussex Chancellor's Masters Scholarship (2026) (`sussex_chancellors`)

Примечание разметчика: Набор 2026 закрыт. Требуется бакалавриат UK или Ирландии с First Class — для поступающих из России фактически недоступна, но ограничения по гражданству нет. Для Overseas — £5,000.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | have accepted an offer of a place on an eligible full time or part time Masters course to start in September 2026 | [sussex_chancellors/1.txt](../gt/pages/sussex_chancellors/1.txt) | |
| статус цикла 2027/28 | only_past_cycle | — | — | |
| дедлайн подачи | 2026-08-01 (day), цикл 2026/27, область global | 1 August 2026 23:59 | [sussex_chancellors/1.txt](../gt/pages/sussex_chancellors/1.txt) | |
| сумма | 3000 GBP / total; полное покрытие: нет; варианты: £5,000 for applicants assessed as Overseas for fees | £3,000 for applicants assessed as 'Home' for fees or £5,000 for applicants assessed as 'Overseas' for fees | [sussex_chancellors/1.txt](../gt/pages/sussex_chancellors/1.txt) | |
| покрывает | обучение: да, проживание: нет, перелёт: не сказано | Tuition fee reduction | [sussex_chancellors/1.txt](../gt/pages/sussex_chancellors/1.txt) | |
| открыта для РФ | unknown | — | — | |

### Tampere University tuition fee scholarships (`tampere_scholarship`)

Примечание разметчика: Скидка 50 % за обучение, подаётся в заявке на программу через Studyinfo.fi в период приёма (сроки не на этой странице). В приём 2026 присуждено всего 9 стипендий. Early bird (−€2,000) — не стипендия.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | bachelor, master | Tampere University tuition fee scholarships awarded at admission cover 50% of the tuition fees for the programme duration. | [tampere_scholarship/1.txt](../gt/pages/tampere_scholarship/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: да, проживание: нет, перелёт: не сказано | Tampere University tuition fee scholarships awarded at admission cover 50% of the tuition fees for the programme duration. | [tampere_scholarship/1.txt](../gt/pages/tampere_scholarship/1.txt) | |
| открыта для РФ | unknown | — | — | |

### Trinity College Dublin Global Excellence Postgraduate Scholarships (`tcd_global_excellence`)

Примечание разметчика: Набор 2026/2027 (дедлайны 2026 года). STEM-программы (инженерия, естественные науки, CS и статистика) исключены — для них отдельные стипендии; поэтому вне профиля. Студенты из Китая не допускаются.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | who have received a course offer for a full-time postgraduate taught programme at Trinity College Dublin. | [tcd_global_excellence/1.txt](../gt/pages/tcd_global_excellence/1.txt) | |
| статус цикла 2027/28 | only_past_cycle | — | — | |
| дедлайн подачи | 2026-06-15 (day), цикл 2026/27, область country — all other regions (incl. Europe outside EU) | All other regions: 15 June 2026 | [tcd_global_excellence/1.txt](../gt/pages/tcd_global_excellence/1.txt) | |
| дедлайн подачи | 2026-05-01 (day), цикл 2026/27, область country — Africa | Africa: 1 May 2026 | [tcd_global_excellence/1.txt](../gt/pages/tcd_global_excellence/1.txt) | |
| дедлайн подачи | 2026-04-01 (day), цикл 2026/27, область country — Central, North and South America | Central, North and South America: 1 April 2026 | [tcd_global_excellence/1.txt](../gt/pages/tcd_global_excellence/1.txt) | |
| дедлайн подачи | 2026-07-15 (day), цикл 2026/27, область country — South East Asia and Oceania | South East Asia and Oceania: 15 July 2026 | [tcd_global_excellence/1.txt](../gt/pages/tcd_global_excellence/1.txt) | |
| сумма | 2000 EUR / total; полное покрытие: нет; варианты: €2,000 to €5,000 depending on the region | Scholarships range in value between €2,000 and €5,000 depending on the region. | [tcd_global_excellence/1.txt](../gt/pages/tcd_global_excellence/1.txt) | |
| покрывает | обучение: да, проживание: нет, перелёт: не сказано | Scholarships are applied as a one-time reduction to the tuition fees of a full-time postgraduate taught programme. | [tcd_global_excellence/1.txt](../gt/pages/tcd_global_excellence/1.txt) | |
| открыта для РФ | yes | Applicants must have a non-EU fee status, and their tuition fees must be billed at a non-EU rate. | [tcd_global_excellence/1.txt](../gt/pages/tcd_global_excellence/1.txt) | |

### Université Grenoble Alpes master scholarships (overview, incl. GS@UGA attractiveness scholarship) (`uga_idex`)

Примечание разметчика: Обзорная страница с таблицей многих стипендий; название первой строки (вероятно, IDEX) в снимке обрезано. Сумма — для GS@UGA. Сроков нет.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | The scholarship may be allocated to students entering a first or second year of a Master’s degree | [uga_idex/1.txt](../gt/pages/uga_idex/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | 14500 EUR / total; полное покрытие: нет; варианты: GS@UGA attractiveness scholarship over two years; other UGA scholarships differ | Students applying to one of the 18 programs at Graduate School@UGA are eligible for the GS@UGA attractiveness scholarship worth €14,500 over the two years of the master's degree. | [uga_idex/1.txt](../gt/pages/uga_idex/1.txt) | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | unknown | — | — | |

### Universität Hamburg Merit Scholarships for International Students (`uhh_merit`)

Примечание разметчика: Снимок — только FAQ: для иностранцев, уже обучающихся в Гамбурге, не для докторантов; дедлайн и сумма — в разделе «Application», которого нет в снимке. Раунды подачи — апрель и октябрь (по статистике прошлых раундов). Уровень обучения явно не указан.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | не указан | — | — | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | unknown | — | — | |

### Vanier Canada Graduate Scholarships (`vanier`)

Примечание разметчика: Только PhD; программа больше не принимает заявки («We are no longer accepting applications»), заменена Canada Graduate Research Scholarship – Doctoral.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | phd | helps Canadian institutions attract highly qualified doctoral students. | [vanier/1.txt](../gt/pages/vanier/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | 50000 CAD / year; полное покрытие: не сказано | Valued at $50,000 per year for three years during doctoral studies | [vanier/1.txt](../gt/pages/vanier/1.txt) | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | yes | Canadian citizens, permanent residents of Canada and foreign citizens are eligible to be nominated for a Vanier CGS. | [vanier/2.txt](../gt/pages/vanier/2.txt) | |

## Расхождения A и B (решение уже принято — проверить, согласен ли)

### France Excellence Eiffel Scholarship Program (`eiffel`)

Примечание разметчика: Подаёт не студент, а французский вуз («Only applications submitted by French higher education institutions are accepted»); дедлайн 6 января — для вузов, у вузов внутренние дедлайны раньше. Возраст: до 29 лет для магистратуры. Суммы на странице нет. [Исправлено после сверки с разметчиком B: open_to_ru = yes.]

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master, phd | to enroll in their masters and PhD programs | [eiffel/1.txt](../gt/pages/eiffel/1.txt) | |
| статус цикла 2027/28 | published | — | — | |
| дедлайн подачи | 2027-01-06 (day), цикл 2027/28, область global | Deadline for the reception of applications by Campus France: January 6, 2027 included. | [eiffel/1.txt](../gt/pages/eiffel/1.txt) | |
| другая дата: opening | 2026-10 (month) | Opening of the call for applications: October 2026 | [eiffel/1.txt](../gt/pages/eiffel/1.txt) | |
| другая дата: results | 2027-04-12 (day) | Publication of results: from the 12th of April, 2027 | [eiffel/1.txt](../gt/pages/eiffel/1.txt) | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | yes | encourages applicants from foreign countries up to 29 years old at master’s level | [eiffel/1.txt](../gt/pages/eiffel/1.txt) | |

### Heinrich Böll Foundation scholarships for international graduates and PhD students (`boell_international`)

Примечание разметчика: Периоды подачи: 15.01–01.03.2027 и 15.07–01.09.2027; 15.01 и 15.07 — открытие портала, не дедлайн. Приоритет — заявители из стран DAC; список стран на странице не приведён, поэтому open_to_ru = unknown. Цикл 2027/28 — по контексту раундов 2027 года. [Исправлено после сверки с разметчиком B: open_to_ru = yes.]

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master, phd | who intend to pursue a Master's degree or PhD in Germany. | [boell_international/1.txt](../gt/pages/boell_international/1.txt) | |
| статус цикла 2027/28 | published | — | — | |
| дедлайн подачи | 2027-03-01 (day), цикл 2027/28, область global — spring 2027 round | Spring 2027: 15 January 2027 until 1 March 2027 | [boell_international/1.txt](../gt/pages/boell_international/1.txt) | |
| дедлайн подачи | 2027-09-01 (day), цикл 2027/28, область global — fall 2027 round | Fall 2027: 15 July 2027 until 1 September 2027 | [boell_international/1.txt](../gt/pages/boell_international/1.txt) | |
| другая дата: opening | 2027-01-15 (day) | The online application portal opens on January 15, 2027, and closes on March 1, 2027. | [boell_international/1.txt](../gt/pages/boell_international/1.txt) | |
| другая дата: opening | 2027-07-15 (day) | Fall 2027: 15 July 2027 until 1 September 2027 | [boell_international/1.txt](../gt/pages/boell_international/1.txt) | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: не сказано, проживание: не сказано, перелёт: не сказано | — | — | |
| открыта для РФ | yes | International students who have completed their first degree abroad can apply prior to starting a Master's degree program in Germany. | [boell_international/1.txt](../gt/pages/boell_international/1.txt) | |

### Konrad-Adenauer-Stiftung International Scholarship Program (`kas_international`)

Примечание разметчика: Два пути: внутри Германии — ежегодно до 15 июля; из-за рубежа — через участвующие офисы KAS (список меняется ежегодно, на странице нет). Требуется немецкий не ниже B2. Программа для граждан стран вне ЕС, но участие России не указано. [Исправлено после сверки с разметчиком B: open_to_ru = yes.]

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | bachelor, master, phd | pursue a Bachelor’s degree (from the second semester onward), a Master’s degree, or a doctorate at a German university. | [kas_international/2.txt](../gt/pages/kas_international/2.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| дедлайн подачи | --07-15 (day_no_year), цикл None, область applicant_group — applicants already living in Germany (domestic selection procedure) | The application deadline for the domestic selection procedure is July 15 at 12:00 noon (CET) each year. | [kas_international/2.txt](../gt/pages/kas_international/2.txt) | |
| сумма | 992 EUR / month; полное покрытие: нет; варианты: doctoral candidates €1,400 per month | Students enrolled in a Master's or postgraduate program receive a monthly scholarship of €992. | [kas_international/1.txt](../gt/pages/kas_international/1.txt) | |
| покрывает | обучение: не сказано, проживание: да, перелёт: не сказано | For Bachelor's, Master's, or Postgraduate programs, recipients can receive up to €992 per month in scholarship funding. | [kas_international/2.txt](../gt/pages/kas_international/2.txt) | |
| открыта для РФ | yes | The International Scholarship Program is primarily aimed at international students and doctoral candidates from non-EU countries | [kas_international/2.txt](../gt/pages/kas_international/2.txt) | |

### Commonwealth Master's Scholarships (`commonwealth_masters`)

Примечание разметчика: Дедлайн указан без года, цикл 2027/28 следует из контекста; приём уже закрыт. Номинирующие организации могут ставить свои более ранние дедлайны. Россия не входит в закрытый список стран Содружества.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | to undertake full-time taught Master’s study at a UK university. | [commonwealth_masters/1.txt](../gt/pages/commonwealth_masters/1.txt) | |
| статус цикла 2027/28 | published | — | — | |
| дедлайн подачи | --10-20 (day_no_year), цикл 2027/28, область global | The closing date for applications was 16:00 BST on Tuesday 20 October. | [commonwealth_masters/1.txt](../gt/pages/commonwealth_masters/1.txt) | |
| другая дата: other | 2026-12 (month) | They will nominate candidates to the CSC by December 2026. | [commonwealth_masters/1.txt](../gt/pages/commonwealth_masters/1.txt) | |
| другая дата: results | 2027-07 (month) | Applicants can expect to hear the outcome of their applications by July 2027. | [commonwealth_masters/1.txt](../gt/pages/commonwealth_masters/1.txt) | |
| сумма | 1712 GBP / month; полное покрытие: да; варианты: £2,000 per month at universities in the London metropolitan area | Stipend (living allowance) at the rate of £1,712 per month, or £2,000 per month for those at universities in the London metropolitan area | [commonwealth_masters/1.txt](../gt/pages/commonwealth_masters/1.txt) | |
| покрывает | обучение: да, проживание: да, перелёт: да | A Commonwealth Scholarship covers fees, approved fares, and personal maintenance. | [commonwealth_masters/1.txt](../gt/pages/commonwealth_masters/1.txt) | |
| открыта для РФ | no | Please note that only candidates from the eligible countries listed below can apply for Commonwealth Master’s Scholarships. | [commonwealth_masters/1.txt](../gt/pages/commonwealth_masters/1.txt) | |

### Master Mind Scholarships (Flanders) (`master_mind`)

Примечание разметчика: Граждане России явно исключены. Набор 2026-2027 закрыт, условия 2027-2028 пересматриваются. Дедлайн задаёт каждый вуз (подача через вуз). «€10.225» — европейская запись, 10 225 евро.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | awards scholarships for master's programmes in Flanders and Brussels to outstanding students from around the world. | [master_mind/1.txt](../gt/pages/master_mind/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| сумма | 10225 EUR / year; полное покрытие: не сказано; варианты: may change for 2027-2028 (scholarship under review) | A Master Mind Scholarship includes a grant of €10.225 and a tuition fee waiver per academic year. | [master_mind/1.txt](../gt/pages/master_mind/1.txt) | |
| покрывает | обучение: да, проживание: да, перелёт: не сказано | A Master Mind Scholarship includes a grant of €10.225 and a tuition fee waiver per academic year. | [master_mind/1.txt](../gt/pages/master_mind/1.txt) | |
| открыта для РФ | no | All nationalities can apply, with the exception of Russian nationals | [master_mind/3.txt](../gt/pages/master_mind/3.txt) | |

### Aarhus University Danish State Scholarships (tuition waivers) (`dk_government_scholarship_au`)

Примечание разметчика: Отдельной заявки нет: стипендия рассматривается автоматически при подаче на программу до 15 января (летний набор). Для естественных и технических наук — только освобождение от платы. На странице также «applicants from outside Europe» — формулировки расходятся.

| Поле | Значение | Цитата | Снимок | ✔/✘ |
|---|---|---|---|---|
| уровень | master | typically but not always for the duration of your Master’s degree programme. | [dk_government_scholarship_au/1.txt](../gt/pages/dk_government_scholarship_au/1.txt) | |
| статус цикла 2027/28 | not_found | — | — | |
| дедлайн подачи | --01-15 (day_no_year), цикл None, область global — summer intake; programme application deadline (scholarship assessed automatically) | Only applicants who have applied for a Master’s degree programme no later than 15 January (summer admission) and 15 September (winter admission) will be considered for a tuition waiver/scholarship. | [dk_government_scholarship_au/1.txt](../gt/pages/dk_government_scholarship_au/1.txt) | |
| дедлайн подачи | --09-15 (day_no_year), цикл None, область global — winter intake (limited number of programmes) | Only applicants who have applied for a Master’s degree programme no later than 15 January (summer admission) and 15 September (winter admission) will be considered for a tuition waiver/scholarship. | [dk_government_scholarship_au/1.txt](../gt/pages/dk_government_scholarship_au/1.txt) | |
| другая дата: opening | --11-01 (day_no_year) | The application round opens 1 November. | [dk_government_scholarship_au/2.txt](../gt/pages/dk_government_scholarship_au/2.txt) | |
| другая дата: offer_or_documents | --04-01 (day_no_year) | you should not decline your offer of admission until the final deadline 1 April (summer admission) | [dk_government_scholarship_au/1.txt](../gt/pages/dk_government_scholarship_au/1.txt) | |
| сумма | нет на странице | — | — | |
| покрывает | обучение: да, проживание: не сказано, перелёт: не сказано | Aarhus University has a limited number of scholarships (100% tuition fee waivers) available. | [dk_government_scholarship_au/1.txt](../gt/pages/dk_government_scholarship_au/1.txt) | |
| открыта для РФ | yes | Aarhus University offers a limited number of Danish state scholarships for non-EU students. | [dk_government_scholarship_au/1.txt](../gt/pages/dk_government_scholarship_au/1.txt) | |
