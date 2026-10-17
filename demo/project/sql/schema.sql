-- סכמת מסד הנתונים chequemis (גרסת SQLite להדגמה)

CREATE TABLE branches (
    branch_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    region      TEXT NOT NULL
);

CREATE TABLE accounts (
    account_id  INTEGER PRIMARY KEY,
    branch_id   TEXT NOT NULL REFERENCES branches(branch_id),
    opened_at   TEXT NOT NULL,
    segment     TEXT NOT NULL,              -- private / business
    status      TEXT NOT NULL               -- ACTIVE / BLOCKED / CLOSED
);

CREATE TABLE payers (
    payer_id    INTEGER PRIMARY KEY,
    payer_type  TEXT NOT NULL,              -- PRIVATE / COMPANY / GOVERNMENT
    bank_code   TEXT NOT NULL
);

CREATE TABLE cheques (
    cheque_id            INTEGER PRIMARY KEY,
    received_at          TEXT NOT NULL,     -- ISO datetime
    branch_id            TEXT NOT NULL REFERENCES branches(branch_id),
    account_id           INTEGER NOT NULL REFERENCES accounts(account_id),
    payer_id             INTEGER NOT NULL REFERENCES payers(payer_id),
    channel              TEXT NOT NULL,     -- BRANCH_SCAN / MOBILE / ATM
    ocr_engine_version   TEXT NOT NULL,
    ocr_amount           REAL NOT NULL,
    ocr_amount_conf      REAL NOT NULL,
    ocr_date_conf        REAL NOT NULL,
    ocr_signature_score  REAL NOT NULL,
    payer_prev_cheques   INTEGER NOT NULL,  -- מחושב בעת קבלת השיק
    is_duplicate_suspect INTEGER NOT NULL,
    risk_flag            TEXT               -- OK / SUSPICIOUS
);
CREATE INDEX ix_cheques_received_at ON cheques(received_at);
CREATE INDEX ix_cheques_account ON cheques(account_id);

CREATE TABLE auto_decisions (
    cheque_id    INTEGER PRIMARY KEY REFERENCES cheques(cheque_id),
    decided_at   TEXT NOT NULL,
    result       TEXT NOT NULL,             -- AUTO_APPROVED / TO_CLERK
    reason_code  TEXT NOT NULL
);

CREATE TABLE clerk_reviews (
    review_id         INTEGER PRIMARY KEY,
    cheque_id         INTEGER NOT NULL REFERENCES cheques(cheque_id),
    reviewed_at       TEXT NOT NULL,
    clerk_id          INTEGER NOT NULL,
    decision          TEXT NOT NULL,        -- APPROVED / REJECTED
    corrected_amount  REAL,
    reject_reason     TEXT,
    is_spot_check     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_clerk_reviews_cheque ON clerk_reviews(cheque_id);
