# Stored procedures — design standard (SQL Server and DB2 z/OS)

A stored procedure is a **public API** of the database. Design it like one.

## Before writing or changing a procedure
1. Get the current definition and parameters from the catalog (MCP) — never from memory.
2. Find all callers: catalog dependencies + search in source code (C#, Python, Node, COBOL,
   Natural, SSIS/jobs). Changing a signature or result set breaks callers silently.
3. Decide what belongs in the procedure: **data access and data integrity rules**. Orchestration,
   external calls, formatting, and complex business workflows belong in the application layer.

## Contract
Document at the top (Hebrew comment block):
- Purpose (one sentence), owner/system.
- Parameters: meaning, allowed values, NULL handling.
- Result sets: exact columns and order — **stable**; never return different shapes depending
  on parameters.
- Errors: which error numbers / SQLSTATEs it raises and when.
- Side effects: tables modified, transaction behavior (does it open its own transaction? may it
  be called inside the caller's transaction?).

## Rules
1. **Single responsibility.** One procedure = one operation. No "mode" parameter that switches
   between unrelated behaviours (`@Action = 'I'/'U'/'D'`) — create separate procedures.
2. **Validate inputs first**, raise a clear business error, then do work.
3. **Set-based body**, no cursors for set logic.
4. **Explicit transactions with full error handling** (SQL Server: `XACT_ABORT` + `TRY/CATCH`
   + `THROW`; DB2: handlers + `SIGNAL`). Never leave an open transaction on error.
   Nested calls: if a caller's transaction is already open (`@@TRANCOUNT > 0`), do not
   commit/rollback it from inside without a defined convention.
5. **Backward-compatible changes**: add new parameters at the end **with defaults**; add new
   result columns at the end only if all callers read by name; otherwise create a new version
   (`..._v2`) and migrate callers.
6. **Dynamic SQL**: only when unavoidable, parameterized (`sp_executesql` / parameter markers),
   identifiers via whitelist / `QUOTENAME`. Document why.
7. **Parameter sniffing (SQL Server)**: when parameter values have very different
   selectivity, choose deliberately: `OPTION (RECOMPILE)` on the sensitive statement, local
   variables (generic plan), `OPTIMIZE FOR`, or rely on 2022 PSP. Write the choice in a comment.
8. **No `SELECT *`, no `sp_` prefix (SQL Server), schema-qualified everything.**
9. **Security**: callers get `EXECUTE` on the procedure, not table permissions. No secrets.
10. **Logging**: if the project has an audit/error-log table, use the project's standard
    procedure for it — consistently.

## SQL Server skeleton
```sql
CREATE OR ALTER PROCEDURE dbo.Order_Cancel
    @OrderId     int,
    @CancelledBy nvarchar(50),
    @Reason      nvarchar(200) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- ולידציה של קלט לפני כל עבודה
    IF @OrderId IS NULL OR @CancelledBy IS NULL
        THROW 50001, N'OrderId and CancelledBy are required', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE dbo.Orders
        SET    Status = 'CANCELLED', CancelledBy = @CancelledBy, CancelledAt = SYSUTCDATETIME()
        WHERE  OrderId = @OrderId
          AND  Status IN ('NEW', 'APPROVED');          -- רק הזמנות שעדיין ניתנות לביטול

        IF @@ROWCOUNT = 0
            THROW 50002, N'Order not found or not cancellable', 1;

        INSERT dbo.OrderHistory (OrderId, Action, ActionBy, Reason, ActionAt)
        VALUES (@OrderId, 'CANCEL', @CancelledBy, @Reason, SYSUTCDATETIME());

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
```

## DB2 z/OS native SQL procedure skeleton
```sql
CREATE PROCEDURE APP.ORDER_CANCEL
  ( IN P_ORDER_ID     INTEGER
  , IN P_CANCELLED_BY VARCHAR(50)
  , IN P_REASON       VARCHAR(200) )
  LANGUAGE SQL
  VERSION V1
  ISOLATION LEVEL CS
BEGIN
  DECLARE V_ROWS INTEGER DEFAULT 0;

  IF P_ORDER_ID IS NULL OR P_CANCELLED_BY IS NULL THEN
    SIGNAL SQLSTATE '75001' SET MESSAGE_TEXT = 'ORDER_ID AND CANCELLED_BY ARE REQUIRED';
  END IF;

  UPDATE APP.ORDERS
     SET STATUS = 'CANCELLED', CANCELLED_BY = P_CANCELLED_BY, CANCELLED_AT = CURRENT TIMESTAMP
   WHERE ORDER_ID = P_ORDER_ID
     AND STATUS IN ('NEW', 'APPROVED');

  GET DIAGNOSTICS V_ROWS = ROW_COUNT;
  IF V_ROWS = 0 THEN
    SIGNAL SQLSTATE '75002' SET MESSAGE_TEXT = 'ORDER NOT FOUND OR NOT CANCELLABLE';
  END IF;

  INSERT INTO APP.ORDER_HISTORY (ORDER_ID, ACTION, ACTION_BY, REASON, ACTION_AT)
  VALUES (P_ORDER_ID, 'CANCEL', P_CANCELLED_BY, P_REASON, CURRENT TIMESTAMP);
END
```
(Commit scope on z/OS follows the caller / `COMMIT ON RETURN` option — state which one is used.)
Hebrew comments in DB2 sources only if the source encoding supports it (see CORE rules).

## Review checklist for a procedure
- [ ] Contract documented; result set shape stable.
- [ ] Inputs validated; business errors with documented codes.
- [ ] Transaction scope correct; no open transaction on any error path.
- [ ] Set-based; SARGable; types match columns.
- [ ] Callers identified; change is backward compatible or versioned.
- [ ] Parameter sniffing considered for skewed data.
- [ ] Deployment script idempotent (`CREATE OR ALTER` / versioning) with rollback.
