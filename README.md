# Utility Asset Registry

Backend for a state electricity distribution utility in Bhubaneswar. It takes a daily handheld GPS export, cleans and validates the rows, stores accepted assets in a database, and serves them to authorised staff and to the utility web map.

This repository is the **back-end only**. There is no map UI in this project.

**How to operate this system:** see [OPERATOR_GUIDE.pdf](OPERATOR_GUIDE.pdf) (printable) or [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md). For IT, night operator, day staff, administrator, and supervisor.

## Status (20 Sep 2026) — Phase 6 complete

Ready for submission: CLI ingest, database API, JWT roles, bulk upload, CORS, 60-second summary cache, 60 requests/minute rate limit, and request timing. Sample ingest outputs are in `outputs/`.

## Setup

Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".[dev]"
copy .env.example .env
```

`requirements.txt` pins exact versions so another engineer can recreate this environment. `.env.example` lists every required setting without real secrets.

Edit `.env` and set `JWT_SECRET`, `BOOTSTRAP_ADMIN_USERNAME`, and `BOOTSTRAP_ADMIN_PASSWORD` before starting the service. The first administrator is created on startup from those values.

The representative handheld export is `data/survey_export.csv` (62 rows; about one in six is faulty, matching the assignment).

Extra test files for you (developer), not for the night operator:

| File | Purpose | How to load |
|---|---|---|
| `data/sample_correct.csv` | All clean rows | Double-click `load_correct.bat` |
| `data/sample_incorrect.csv` | Bad rows only | Double-click `load_incorrect.bat` |

`run.bat` stays for the end user only (start / load main CSV / exit).

## How to use (simple commands)

Open PowerShell, then type these three lines **once per window**:

```powershell
cd C:\Users\ranja\utility-asset-registry
.\.venv\Scripts\Activate.ps1
```

After that, use one word:

| Type this | What it does |
|---|---|
| `setup` | First time only: install tools and create `.env` |
| `load` | Load today's CSV (`data\survey_export.csv`) |
| `start` | Start the system. Then open http://127.0.0.1:8000/docs |
| `check` | Tell you if the system is running |
| `rejects` | Open the bad-rows file from the last load |
| `run` | Menu: 1 start, 2 load, 3 exit |

```powershell
setup
load
start
check
rejects
run
```

If PowerShell says `start` is the wrong command, type:

```powershell
asset start
```

`asset load`, `asset check`, and `asset rejects` work the same way.

**First time only:** `python -m venv .venv`, then `.\.venv\Scripts\Activate.ps1`, then `pip install -e .`, then type `setup` and set the admin password in `.env`.

## Ingestion tool

**Easiest:** type `load`

Or:

```powershell
asset-ingest data\survey_export.csv
```

Or, from this folder:

```powershell
python -m utility_asset_registry load
python -m utility_asset_registry data\survey_export.csv
```

Optional arguments:

```powershell
asset-ingest data\survey_export.csv --rejects outputs\rejects.csv --map outputs\assets.geojson --summary outputs\summary.txt --log outputs\ingest.log
asset-ingest data\survey_export.csv --strict
asset-ingest --help
```

`--strict` aborts the whole run if any row is rejected. Use it when loading a file that should already be clean.

On completion the tool prints rows read, accepted, rejected, and the rejects file path. Defaults (if you omit the optional paths) are `outputs/rejects.csv`, `outputs/assets.geojson`, `outputs/summary.txt`, and `outputs/ingest.log`.

Also available:

- `--near LATITUDE,LONGITUDE` — nearest accepted asset, true Earth distance in kilometres
- `--on-date YYYY-MM-DD` — distinct surveyors who worked that day

If a required CSV column is missing, the run stops at once and names the missing column.

### Sample ingest outputs

One run against `data/survey_export.csv` is committed under `outputs/`:

| File | Contents |
|---|---|
| `outputs/rejects.csv` | Refused rows with original values plus `reason` |
| `outputs/assets.geojson` | Accepted assets as a GeoJSON FeatureCollection |
| `outputs/summary.txt` | Printable supervisor summary |
| `outputs/ingest.log` | Dated line for the run |

Result of that run: **62 read, 52 accepted, 10 rejected**.

## Web service

**Easiest:** type `start`, then open http://127.0.0.1:8000/docs. Type `check` if you are not sure it is running.

Or from PowerShell:

```powershell
copy .env.example .env
uvicorn utility_asset_registry.api.app:create_app --factory --reload
```

Open http://127.0.0.1:8000/docs to see every operation and try it. The monitoring check is `GET /health` and does not require a login. Every other data route needs `Authorization: Bearer <token>` from `/auth/login`.

### Sign-in

```powershell
# POST /auth/login
# body: {"username":"admin","password":"..."}
# returns: token, token_type=bearer, expires_in, role, username
```

Roles:

- **surveyor** — read, add, and correct assets
- **admin** — all of the above, plus delete, bulk CSV upload, and creating users

### Network operations

| Method | Path | Who | What it does |
|---|---|---|---|
| GET | `/health` | anyone | Confirms the application is running (exempt from rate limit) |
| POST | `/auth/login` | anyone | Sign in and receive a bearer token |
| POST | `/auth/users` | admin | Create a surveyor or administrator |
| GET | `/assets` | signed-in | List a page of assets (`limit` default 25, max 100; filters and `q`) |
| GET | `/assets/{code}` | signed-in | Fetch one asset |
| POST | `/assets` | signed-in | Add a new asset |
| PUT | `/assets/{code}` | signed-in | Replace an asset in full |
| PATCH | `/assets/{code}` | signed-in | Correct selected fields |
| DELETE | `/assets/{code}` | admin | Remove an asset and its visit history |
| GET | `/assets/{code}/visits` | signed-in | Visit history for one asset |
| GET | `/reports/summary` | signed-in | Counts, averages, worst asset, map extent (cached up to 60 s) |
| GET | `/reports/repairs` | signed-in | In-service assets with condition below 5 |
| GET | `/reports/most-visited` | signed-in | Assets visited most often |
| GET | `/reports/nearest?latitude=&longitude=` | signed-in | Nearest surveyed asset in kilometres |
| GET | `/reports/surveyors?date=YYYY-MM-DD` | signed-in | Distinct surveyors that day |
| POST | `/ingest/upload` | admin | Upload a day's CSV; returns accepted and rejected counts |

Outcomes are labelled: `created`, `deleted`, `not_found`, `invalid`, `unauthenticated`, `not_permitted`, `rate_limited`.

### Reliability features

- **Summary cache** — `/reports/summary` is cached for up to 60 seconds. The cache is dropped immediately when any asset is added, corrected, replaced, deleted, or bulk-uploaded. The response includes `"cached": true|false`.
- **Rate limit** — each caller is limited to `RATE_LIMIT_PER_MINUTE` requests (default 60). Beyond that the API returns 429 with `retry_after_seconds` and a `Retry-After` header. `/health` is exempt.
- **Request timing** — every response includes `X-Response-Time-Ms`. The same duration is written to the application log.
- **CORS** — only origins listed in `CORS_ORIGINS` (the web map), not every address.

## Tests

```powershell
pytest
```

## Configuration

All runtime settings are read from the environment (`src/utility_asset_registry/config.py`):

| Setting | Purpose |
|---|---|
| `DATABASE_URL` | SQLite for development; point at the enterprise database later without a rewrite |
| `JWT_SECRET` | Signing secret for login credentials (never commit a real value) |
| `JWT_EXPIRE_MINUTES` | How long a sign-in credential lasts |
| `CORS_ORIGINS` | Comma-separated addresses allowed to call the API (the web map) |
| `RATE_LIMIT_PER_MINUTE` | Maximum requests from one caller per minute |
| `BOOTSTRAP_ADMIN_USERNAME` | First administrator username, created on startup if missing |
| `BOOTSTRAP_ADMIN_PASSWORD` | First administrator password (never commit a real value) |

## Demo checklist (5–8 minutes)

1. CLI ingest rejects bad rows and continues (`asset-ingest data\survey_export.csv`).
2. Open `/docs` and show the published operations.
3. Sign in, then make a successful authenticated request.
4. Sign in as a surveyor and show delete refused (`not_permitted`).
5. Call `/reports/summary` twice (second shows `"cached": true`), then change an asset and show the next summary is fresh.
6. Lower `RATE_LIMIT_PER_MINUTE` (or hammer the API) and show a 429 with retry guidance.
