# Utility Asset Registry

Backend for a state electricity distribution utility in Bhubaneswar. It takes a daily handheld GPS export, cleans and validates the rows, stores accepted assets in a database, and serves them to authorised staff and to the utility web map.

This repository is the **back-end only**. There is no map UI in this project.

## Status (20 Sep 2026) — Phase 5

Sign-in (JWT), surveyor vs administrator roles, admin bulk CSV upload, and CORS for the web map are in place. Cache and request limits follow in Phase 6.

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

## Ingestion tool

One command. The operator does not need to know Python.

```powershell
asset-ingest data\survey_export.csv
```

Or, from this folder:

```powershell
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

## Web service

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
| GET | `/health` | anyone | Confirms the application is running |
| POST | `/auth/login` | anyone | Sign in and receive a bearer token |
| POST | `/auth/users` | admin | Create a surveyor or administrator |
| GET | `/assets` | signed-in | List a page of assets (`limit` default 25, max 100; filters and `q`) |
| GET | `/assets/{code}` | signed-in | Fetch one asset |
| POST | `/assets` | signed-in | Add a new asset |
| PUT | `/assets/{code}` | signed-in | Replace an asset in full |
| PATCH | `/assets/{code}` | signed-in | Correct selected fields |
| DELETE | `/assets/{code}` | admin | Remove an asset and its visit history |
| GET | `/assets/{code}/visits` | signed-in | Visit history for one asset |
| GET | `/reports/summary` | signed-in | Counts, averages, worst asset, map extent |
| GET | `/reports/repairs` | signed-in | In-service assets with condition below 5 |
| GET | `/reports/most-visited` | signed-in | Assets visited most often |
| GET | `/reports/nearest?latitude=&longitude=` | signed-in | Nearest surveyed asset in kilometres |
| GET | `/reports/surveyors?date=YYYY-MM-DD` | signed-in | Distinct surveyors that day |
| POST | `/ingest/upload` | admin | Upload a day's CSV; returns accepted and rejected counts |

Outcomes are labelled: `created`, `deleted`, `not_found`, `invalid`, `unauthenticated`, `not_permitted`. CORS allows only the origins in `CORS_ORIGINS` (the web map), not every address.

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
| `RATE_LIMIT_PER_MINUTE` | Maximum requests from one caller |
| `BOOTSTRAP_ADMIN_USERNAME` | First administrator username, created on startup if missing |
| `BOOTSTRAP_ADMIN_PASSWORD` | First administrator password (never commit a real value) |

## What will run later

- Summary cache (60 seconds), 60 requests/minute rate limit, request timing in logs and responses
