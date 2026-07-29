# rtac_modbus_server (pae-rtac-server)

Owns: polling Modbus TCP devices (SEL RTACs) on a schedule and storing their
register/point readings as time-series in TimescaleDB, plus the sites → devices →
device-points CRUD, live register streaming, and CSV export API (all under `/api`).
Does NOT own: the upstream Modbus aggregator/RTAC itself (external, `AGGREGATOR_MODBUS_HOST`),
the DAS data-acquisition API (`pae-das-api`), or any downstream dashboard/analytics.

## This repo diverges from the standard Python setup — read this
- No uv. Deps install via `pip install -e .` (Docker) against pyproject; a stale
  `requirements.txt` also exists. Types are checked with **mypy, not pyright**;
  formatting is **black + ruff** (line-length 100). `uv run` / pyright do not apply here.
- Imports are flat and require `PYTHONPATH=src` — modules import as `from config import ...`,
  `from db.connection import ...`, NOT a package. Bare `pytest` and bare `python main.py` fail.
- There is no auth layer at all yet; every endpoint is unauthenticated. `/api/healthz`
  must stay that way — the Docker HEALTHCHECK and k8s probes hit it.

## Commands (need Docker running first)
- Setup / dev: `make up-build` (Windows: `.\make.ps1 up-build`) — builds & starts
  postgres, redis, app; migrations auto-run in the container entrypoint.
- Run outside Docker: `make run` (= `cd src && python -m main`, needs pg+redis reachable).
- Test: `make test` (brings up redis, then `PYTHONPATH=src pytest tests/ -v`).
  Integration tests (`tests/integration/`) also need postgres up.
- Single test: `PYTHONPATH=src pytest tests/unit/test_sanitize.py::TestSanitize::test_x -v`.
- Lint/format: `make lint` (ruff + mypy) / `make format` (black + ruff).
- Migrate manually: `make migrate` (= `python scripts/migrate_db.py`).

## Linting is CI-enforced — every change must leave `ruff check` clean
`.github/workflows/ci.yml` runs `ruff check src/ tests/` and **fails the build on any
error** (mypy also runs but is currently non-blocking). Before finishing any Python
change, make sure ruff passes with zero errors. Config lives in `pyproject.toml` under
`[tool.ruff.lint]` (line-length 100; rule sets `E,W,F,I,B,C4,UP`; `E501`/`B008` ignored).
Concretely, write code that already satisfies these:
- **Modern typing (UP):** use built-in generics and unions — `list[int]`, `dict[str, X]`,
  `X | None` — NOT `typing.List`/`Dict`/`Optional`/`Union`. Don't import those from `typing`.
- **Sorted imports (I001):** stdlib → third-party → first-party, each group alphabetized.
- **Exception chaining (B904):** inside an `except`, always chain — `raise HTTPException(...)
  from err` when the caught exception is meaningful, or `... from None` for a deliberate
  translation (e.g. converting a lookup miss to a 404). Never a bare `raise X(...)` in `except`.
- **No trailing/blank-line whitespace (W29x)**, files end with a newline, no unused imports (F401).
- If a rule genuinely shouldn't apply, add a scoped `# noqa: <CODE>` with a reason — don't
  broaden the global ignore list without asking.
- No local Python here (the `.venv` is a broken shim). Use the Docker-backed make
  targets: `make lint` / `.\make.ps1 lint` (check) and `make lint-fix` /
  `.\make.ps1 lint-fix` (auto-fix imports/typing/whitespace; B904 must be fixed by hand).
- A pre-commit hook (`.githooks/pre-commit`) runs ruff in Docker and blocks commits with
  lint errors. Enable it once per clone: `git config core.hooksPath .githooks` (needs
  Docker running; bypass in emergencies with `git commit --no-verify`).

## What this service owns
- Postgres/TimescaleDB tables: `sites`, `devices`, `device_points`, `point_readings`,
  `register_readings_translated`, `schema_migrations`. (`device_register_map` and the
  `*_configs` tables were dropped in migrations 022/042 — don't reference them.)
- Redis: read-through cache + APScheduler leader-election / job locks (not a message bus).
- Publishes no events to any broker; DAS_API_BASE_URL is configured but nothing calls it yet.

## Gotchas
- Host ports are remapped: app 8000, **postgres 5435→5432, redis 6380→6379**. A local
  `.env` for tests/tools must target 5435/6380, not the defaults.
- Migrations are raw numbered SQL in `src/db/migrations/NNN_*.sql`, applied and tracked in
  `schema_migrations` by `scripts/migrate_db.py`. No Alembic — add a new `NNN_*.sql` to change schema.
- Scheduler uses Redis leader election: only ONE replica polls (job `modbus_poll`, every
  `POLL_INTERVAL_SECONDS`, default 10). It won't start if Redis is down; `SCHEDULER_ENABLED=false`
  disables it. Polling targets are read from the DB (sites → devices → device-points).
- A global `validate_time_range` middleware (`src/api/middleware/`) runs on every request
  and rejects bad start/end query params.
- `main.py` hardcodes `reload=True`; the Dockerfile runs a single uvicorn process
  (the gunicorn config exists but is commented out).

## Output style (keep token usage down)
- Keep responses short. Lead with the answer; no recap tables or restated diffs unless asked.
- Don't re-print file contents you just edited.
