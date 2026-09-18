# Utility Asset Registry

Backend for a state electricity distribution utility in Bhubaneswar. It takes a daily handheld GPS export, cleans and validates the rows, stores accepted assets in a database, and serves them to authorised staff and to the utility web map.

This repository is the **back-end only**. There is no map UI in this project.

## Status (18 Sep 2026) — Phase 4

Accepted assets are stored in a database and served over HTTP. Sign-in and bulk upload follow in the next phase.

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

Place the supplied field export at `data/survey_export.csv` when you have it.

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

Open http://127.0.0.1:8000/docs to see every operation and try it. The monitoring check is `GET /health` and does not require a login.

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Confirms the application is running |
| GET | `/assets` | List a page of assets (`limit` default 25, max 100; `offset`; filters `asset_type`, `status`, `surveyor`, `condition_min`, `condition_max`; search `q`) |
| GET | `/assets/{code}` | Fetch one asset |
| POST | `/assets` | Add a new asset |
| PUT | `/assets/{code}` | Replace an asset in full |
| PATCH | `/assets/{code}` | Correct selected fields |
| DELETE | `/assets/{code}` | Remove an asset and its visit history |
| GET | `/assets/{code}/visits` | Visit history for one asset |
| GET | `/reports/summary` | Counts, averages, worst asset, map extent |
| GET | `/reports/repairs` | In-service assets with condition below 5 |
| GET | `/reports/most-visited` | Assets visited most often |
| GET | `/reports/nearest?latitude=&longitude=` | Nearest surveyed asset in kilometres |
| GET | `/reports/surveyors?date=YYYY-MM-DD` | Distinct surveyors that day |

A request never returns every asset at once. Outcomes are labelled: `created`, `deleted`, `not_found`, `invalid`.

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

## What will run later

- Sign-in (surveyor vs administrator), bulk CSV upload, cache and request limits
