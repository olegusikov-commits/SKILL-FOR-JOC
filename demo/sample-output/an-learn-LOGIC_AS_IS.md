# Текущая логика решения

Точка входа: `src/chequeflow/service.py:9` `process_cheque` → `repository.py:17` load → `rules.py:12` `decide` → `repository.py:45` `save_decision` (INSERT в `auto_decisions`). Пороги: `src/chequeflow/config.py`. Первое сработавшее условие возвращает TO_CLERK (`rules.py:3`).

| # | Условие → TO_CLERK | Порог | Reason code | Тип | Где |
|---|---|---|---|---|---|
| 1 | `account.status != 'ACTIVE'` | BLOCKED и CLOSED | ACCOUNT_BLOCKED | жёсткий стоп | rules.py:14-15 |
| 2 | `is_duplicate_suspect` | флаг | DUPLICATE_SUSPECT | жёсткий стоп | rules.py:16-17 |
| 3 | `channel not in {BRANCH_SCAN, ATM}` | MOBILE запрещён | CHANNEL_NOT_ALLOWED | мягкое | rules.py:19-20, config:19 |
| 4 | `ocr_amount > 1000` | строго больше | AMOUNT_LIMIT | мягкое | rules.py:21-22, config:4 |
| 5 | `ocr_amount_conf < 0.95` | | LOW_OCR_AMOUNT | мягкое | rules.py:23-24, config:7 |
| 6 | `ocr_date_conf < 0.90` | | LOW_OCR_DATE | мягкое | rules.py:25-26, config:10 |
| 7 | `ocr_signature_score < 0.85` | | LOW_SIGNATURE | мягкое | rules.py:27-28, config:13 |
| 8 | `payer_prev_cheques < 3` | 3 проходит | NEW_PAYER | мягкое | rules.py:29-30, config:16 |
| – | иначе | | OK → AUTO_APPROVED | | rules.py:32 |

Решение сохраняет только result, reason_code, decided_at. Версия правил и применённые пороги не пишутся.

**Не используются в `decide`:** `segment`, `payer_type`, `bank_code`, `branch_id`, `received_at`, `ocr_engine_version`, `risk_flag`. `payer` передаётся, но не читается (задел под CHQ-512).

## Расхождения и странности
1. Пороги OCR одинаковы для v2.4 и v3.1, хотя docs говорят, что у v2.4 уверенность завышена. Код смену движка не учитывает.
2. `reports.py:23` использует 0,9 для `ocr_amount_conf`, а правило — 0,95; `reports.py:21` хардкодит 1000. Метрика «low OCR» в отчёте ≠ LOW_OCR_AMOUNT.
3. Логики spot-check в коде нет (вне `decide`), 3% выбираются неизвестным способом.
4. Расчёта `payer_prev_cheques` и `is_duplicate_suspect` в репозитории нет, значения приходят готовыми.
5. Жёсткие/мягкие условия различаются только комментарием и порядком.
6. CHQ-512 (`AUTO_RECURRING_PAYER`: COMPANY/GOVERNMENT, `payer_prev_cheques >= 6`, сумма ≤5000) в коде не реализовано.
7. Тесты покрывают 5 из 9 исходов, граничных значений нет.
