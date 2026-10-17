# Карта данных

## Источник
`meet-chequemis`, SQLite 3.45.1, среда **TEST** (подтверждено пользователем в PROJECT_CONTEXT, 2026-10-17; в боевой системе, по docstring, SQL Server). Период 2026-01-01..2026-09-30, ровно по 4 000 чеков в месяц (данные выглядят синтетическими/выровненными).

## Таблицы и связи
| Таблица | Что хранит | Ключ | Связь | Строк | Дата (индекс) |
|---|---|---|---|---|---|
| cheques | чек, OCR-поля, канал, payer_prev_cheques, risk_flag | cheque_id | → branches, accounts, payers | 36 000 | received_at (ix_cheques_received_at) |
| auto_decisions | решение правил | cheque_id (1:1) | → cheques | 36 000 | decided_at (нет индекса) |
| clerk_reviews | проверки פקיד | review_id | N:1 → cheques | 33 575 | reviewed_at (нет индекса); ix_clerk_reviews_cheque |
| accounts | счёт: segment, status | account_id | → branches | 8 000 | – |
| payers | payer_type (PRIVATE/COMPANY/GOVERNMENT), bank_code | payer_id | | 3 000 | – |
| branches | | branch_id | | 20 | – |
Сирот и NULL в ключевых полях нет. `clerk_id` → `clerks` в meet-checkov без FK.

## Поле-эталон (outcome)
`clerk_reviews.decision` (APPROVED/REJECTED), `corrected_amount`, `reject_reason`. Финальное = последняя проверка по `reviewed_at DESC, review_id DESC` (допущение Д-3). 491 чек с двумя проверками, у 115 решения противоречат (APPROVED→REJECTED 105, REJECTED→APPROVED 10). У авто-одобренных эталон есть только у 79 spot-check (все APPROVED, без исправлений); у 2 916 эталона нет.

## Поля по времени появления
| Поле | Известно при авто-решении? | Доказательство |
|---|---|---|
| received_at, channel, account_id, payer_id, ocr_*, ocr_engine_version, is_duplicate_suspect | да | `decided_at − received_at` ≤ 40 с; их использует `decide` |
| payer_prev_cheques | заявлено «при приёме», но **не воспроизводится** | queries/005: совпадение 19,5% (счёт) / 5,5% (любой счёт) |
| payers.payer_type, bank_code | да (статичны, истории изменений нет) | ПРЕДПОЛОЖЕНИЕ |
| accounts.status, segment | **неизвестно**: нет истории, статус мог измениться после решения | |
| risk_flag | **нет** — ставится פקיד; NULL ⇔ нет проверки (2 916 из 2 916) | данные |
| corrected_amount, decision, reject_reason, clerk_id, reviewed_at, is_spot_check | **нет** — проверка начинается ≥0,04 суток после решения | данные |

## Качество данных
- Пропусков/отрицательных сумм/conf вне [0,1] нет.
- Двойные проверки: 491 чек (1,4%).
- `risk_flag` сильно связан с отказом (SUSPICIOUS+REJECTED 2 629) → использовать как признак нельзя.
- OCR: `ocr_amount_conf` упала в среднем с 0,9405 (v2.4) до 0,9223 (v3.1); date_conf и signature не изменились; доля LOW_OCR_AMOUNT 8,27% → 10,35%.
- Данные по месяцам идеально ровные (4 000) — проверить, не искусственная ли это выборка.

## Глоссарий
| Термин | Значение | Где |
|---|---|---|
| авто-разрешение / אישור אוטומטי | `auto_decisions.result = 'AUTO_APPROVED'` (reason OK) | auto_decisions |
| פקיד | сотрудник, проверяющий чек | clerk_reviews, checkov.clerks |
| spot-check | проверка ~3% авто-одобренных постфактум | clerk_reviews.is_spot_check=1 |
| risk_flag | OK/SUSPICIOUS, ставит פקיד | cheques.risk_flag |
| payer_prev_cheques | число прежних чеков плательщика на счёт (по docs) | cheques |
| מושך (payer) | плательщик по чеку | payers |
