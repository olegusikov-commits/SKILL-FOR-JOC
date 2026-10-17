# Python standard

Detect the version (`pyproject.toml` `requires-python`, `.python-version`, runtime) and the
tooling in use (ruff/black/flake8, mypy, pytest). Follow them.

## Structure
- A package, not a folder of scripts: `src/<package>/` (or project layout), modules by
  responsibility; entry point `main()` behind `if __name__ == "__main__":`.
- Business logic in plain functions/classes without I/O; DB/HTTP/files in adapter modules.
- Configuration from environment/config file, validated at startup (pydantic-settings or a
  dataclass), not module-level globals scattered around.
- CLI with `argparse` / `typer` / `click` per project.

## Code
- Type hints on all public functions; `mypy`/`pyright` clean if the project uses them.
- `dataclasses` (`frozen=True` for values) or pydantic models for structured data — not dicts
  passed around everywhere.
- No mutable default arguments; no wildcard imports; no `global`.
- `pathlib` for paths; context managers (`with`) for files, connections, locks.
- Specific exceptions; `raise ... from e`; never bare `except:` or `except Exception: pass`.
- `logging` module with a module logger (`logger = logging.getLogger(__name__)`), never `print`
  for diagnostics; lazy formatting (`logger.info("x=%s", x)`).
- Generators/iterators for large data; do not load whole tables into memory without reason.
- pandas: vectorized operations, no row-wise `iterrows()` on large frames; explicit dtypes.

## Data access
- DB-API with parameters — never f-strings or `%` into SQL:
  - pyodbc (SQL Server): `cursor.execute("SELECT ... WHERE Id = ?", order_id)`
  - ibm_db / ibm_db_dbi (DB2): parameter markers `?` with `ibm_db.execute(stmt, (value,))`
- Explicit transactions (`autocommit` off, commit/rollback deliberately); close cursors.
- SQLAlchemy if the project uses it — Core/ORM per project; watch N+1 (`selectinload`).

## Dependencies
Pinned versions in the project's mechanism (requirements lock / poetry / uv); no new package
without justification (LARGE task).

## Tests
pytest, fixtures for setup, `parametrize` for input tables, `tmp_path`, fake adapters for DB/HTTP;
`freezegun`/injected clock for time.
