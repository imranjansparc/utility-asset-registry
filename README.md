# Utility Asset Registry

Backend for a state electricity distribution utility in Bhubaneswar. It takes a daily handheld GPS export, cleans and validates the rows, stores accepted assets in a database, and serves them to authorised staff and to the utility web map.

This repository is the **back-end only**. There is no map UI in this project.

## Status (16 Sep 2026) — Phase 1

Project skeleton and environment-based configuration. Ingestion, API, and tests follow in later phases before the 22 Sep submission.

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

- CLI ingest: one command, CSV path as the argument
- Web service: FastAPI, with OpenAPI docs at `/docs`
- Tests: `pytest`
