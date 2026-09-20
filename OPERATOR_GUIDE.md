# How to operate the Utility Asset Registry

This system stores electricity assets in Bhubaneswar (poles, transformers, valves, manholes). Field staff send a CSV file. The system cleans it, saves good rows, and keeps bad rows for correction.

You do **not** need to know Python. You type short words in PowerShell.

**Project folder:** `C:\Users\ranja\utility-asset-registry`

Read only the section for your job:

| If you are | Read |
|---|---|
| IT / first-time installer | Section A |
| Night operator (load today’s file) | Section B |
| Day staff / surveyor | Section C |
| Administrator | Section D |
| Supervisor (check quality) | Section E |

Everyone should also read **Commands** and **If something goes wrong**.

---

## Open PowerShell (every user, every time)

1. Press the **Windows** key.
2. Type **PowerShell**.
3. Press **Enter**.
4. Type these two lines, then press **Enter** after each:

```powershell
cd C:\Users\ranja\utility-asset-registry
.\.venv\Scripts\Activate.ps1
```

**What this means:** go to the project folder, then turn on the project tools. You must do this **once in each new PowerShell window** before `load`, `start`, `check`, or the other words will work.

If PowerShell asks about running scripts, type:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then try `.\.venv\Scripts\Activate.ps1` again.

---

## Commands (one word each)

| Type this | Who uses it | What it does |
|---|---|---|
| `setup` | IT, first time only | Installs the tools and creates the password file `.env` |
| `load` | Night operator | Reads `data\survey_export.csv`, saves good rows, writes bad rows to a rejects file |
| `start` | Day staff, admin | Starts the system. Keep that window open. Then open http://127.0.0.1:8000/docs |
| `check` | Anyone | Tells you if the system is running |
| `rejects` | Night operator, supervisor | Opens the bad-rows file from the last `load` |
| `run` | Anyone who wants a menu | Shows: 1 = start, 2 = load, 3 = exit |

If PowerShell treats `start` as a Windows command instead of this system, type:

```powershell
asset start
```

`asset load`, `asset check`, `asset rejects`, `asset setup`, and `asset run` work the same way.

---

## A. IT / first-time installer

**Your job:** prepare the computer once. Other people then use `load` and `start` every day.

### 1. Install Python

Install **Python 3.11 or newer** if it is not already installed. During install, tick **Add Python to PATH**.

### 2. Open PowerShell and go to the folder

```powershell
cd C:\Users\ranja\utility-asset-registry
```

### 3. Create the tool folder and install once

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
setup
```

| Line | Meaning |
|---|---|
| `python -m venv .venv` | Makes a private folder of tools for this project |
| `Activate.ps1` | Turns those tools on |
| `pip install -e .` | Installs this system so `load` and `start` work |
| `setup` | Installs packages and creates `.env` if it is missing |

### 4. Set the first administrator password

```powershell
notepad .env
```

Change these three lines, then **Save** and close Notepad:

- `JWT_SECRET=` a long secret sentence that only IT knows  
- `BOOTSTRAP_ADMIN_USERNAME=admin` (or another username)  
- `BOOTSTRAP_ADMIN_PASSWORD=` the password staff will use to sign in the first time  

Do not share this file. Do not put a real password in any file that is sent to GitHub.

### 5. Prove it works

```powershell
start
```

Keep that window open. In a **second** PowerShell window (same `cd` and `Activate` steps), type:

```powershell
check
```

You should see: **The system is running.**

Open a browser: **http://127.0.0.1:8000/docs**

To stop the system, click the first window and press **Ctrl+C**.

---

## B. Night operator

**Your job:** at the end of the shift, load today’s handheld GPS file. You do **not** need the browser for this.

### 1. Put today’s file in the right place

Copy the CSV to:

`C:\Users\ranja\utility-asset-registry\data\survey_export.csv`

If a file is already there, replace it.

The file must have these column names:

`asset_id`, `name`, `asset_type`, `latitude`, `longitude`, `elevation_m`, `surveyed_on`, `surveyor`, `status`, `condition_score`, `attribute_json`

### 2. Open PowerShell (see the top of this document)

### 3. Load the file

```powershell
load
```

**Meaning:** read the CSV, clean each row, save good assets, write bad rows to `outputs\rejects.csv`.

### 4. Read the result on the screen

Example:

```text
Rows read:      62
Rows accepted:  52
Rows rejected:  10
Rejects file:   outputs\rejects.csv
```

| Line | Meaning |
|---|---|
| Rows read | How many rows were in the file |
| Rows accepted | Good rows saved in the system |
| Rows rejected | Bad rows **not** saved |
| Rejects file | Where the bad rows were written |

Good rows are already saved. Bad rows are not thrown away.

### 5. If rejected rows are more than 0

```powershell
rejects
```

**Meaning:** opens the bad-rows file (usually in Excel). Look at the last column named **`reason`**. Tell your supervisor. After the file is corrected, put it back as `data\survey_export.csv` and type `load` again.

### Optional: menu instead of `load`

```powershell
run
```

Then press **2** and Enter.

---

## C. Day staff / surveyor

**Your job:** search assets, add a missing one, or correct a field. You cannot delete assets, create users, or upload a CSV in the browser. That is for an administrator.

### 1. Start the system

Open PowerShell (see the top of this document), then:

```powershell
start
```

**Meaning:** turns the system on. **Keep this window open.** If you close it, the browser will stop working.

If you are not sure it is on, open a second PowerShell window and type `check`.

### 2. Open the work page

In Chrome or Edge open:

**http://127.0.0.1:8000/docs**

This page lists every action. It is not a map. The map is a separate program that talks to this system.

### 3. Sign in

1. Open **POST /auth/login**.
2. Click **Try it out**.
3. Put your username and password:

```json
{"username":"your-username","password":"your-password"}
```

4. Click **Execute**.
5. Copy the **token** from the response.
6. Click **Authorize** at the top of the page.
7. Paste: `Bearer` then a space then the token.
8. Click **Authorize**, then **Close**.

**Meaning:** the system now knows who you are. The token expires after about 60 minutes. Sign in again if work stops.

### 4. Daily work (after you are signed in)

| What you want | Where on the page |
|---|---|
| List assets | GET `/assets` |
| Find one asset by code | GET `/assets/PL-0001` (use the real code, like `PL-0142`) |
| Search by name or text | GET `/assets` and fill in `q` |
| Filter by type, status, or surveyor | GET `/assets` and fill in those boxes |
| Add an asset | POST `/assets` |
| Correct some fields | PATCH `/assets/{code}` |
| Replace all fields | PUT `/assets/{code}` |
| See visit history | GET `/assets/{code}/visits` |
| Counts for the map | GET `/reports/summary` |
| Assets that need repair | GET `/reports/repairs` |
| Nearest asset to a point | GET `/reports/nearest` |

Asset codes look like **`PL-0142`**: two letters, a hyphen, four digits.

Allowed types: `pole`, `valve`, `manhole`, `transformer`.  
Allowed status: `active`, `decommissioned`, `proposed`.  
Condition score: **0 to 10**. A decommissioned asset cannot have a score above 2.

### 5. Stop the system

Click the PowerShell window that is running `start`, then press **Ctrl+C**.

---

## D. Administrator

**Your job:** everything a surveyor can do, plus delete assets, create users, and upload a CSV in the browser.

### 1. Start and sign in

Same as day staff: type `start`, open **http://127.0.0.1:8000/docs**, sign in with the **admin** username and password.

The first admin account comes from `.env` (`BOOTSTRAP_ADMIN_USERNAME` and `BOOTSTRAP_ADMIN_PASSWORD`). Change that password with IT. Do not leave `change-me-before-go-live` in use.

### 2. Extra actions only an admin may do

| What you want | Where on the page |
|---|---|
| Create a surveyor or another admin | POST `/auth/users` |
| Delete an asset (and its visit history) | DELETE `/assets/{code}` |
| Upload a day’s CSV from the browser | POST `/ingest/upload` |

When you create a user, choose role **`surveyor`** or **`admin`**. Give the person the username and password yourself. This system does not send email.

If a surveyor tries to delete or upload, the system answers: **Only an administrator may do that.**

### 3. Upload in the browser vs night `load`

- Night operator `load` is the usual way: file goes in `data\survey_export.csv`.
- **POST `/ingest/upload`** is the same cleaning, used when an admin already has the CSV and the system is running.

Both save good rows and report rejected rows.

---

## E. Supervisor

**Your job:** see whether today’s load was clean, and see which assets need repair.

You can use commands (no browser) or the reports page (browser).

### After the night load (no browser)

1. Ask the night operator for the counts (read, accepted, rejected).
2. If rejected is more than 0, type `rejects` (after the usual PowerShell steps).
3. Open **`reason`** in Excel. Send the bad rows back to the field team.
4. After they fix the file, the night operator types `load` again.

Also look in the `outputs` folder:

| File | What it is |
|---|---|
| `outputs\rejects.csv` | Bad rows plus a **reason** |
| `outputs\summary.txt` | Short printable summary |
| `outputs\assets.geojson` | Good assets for a map |
| `outputs\ingest.log` | One dated line per load |

### In the browser (after someone types `start` and you sign in)

| What you want | Where |
|---|---|
| Totals and map extent | GET `/reports/summary` |
| In-service assets with condition below 5 | GET `/reports/repairs` |
| Assets visited most often | GET `/reports/most-visited` |
| Who surveyed on a date | GET `/reports/surveyors` |

---

## If something goes wrong

| What you see | Meaning | What to do |
|---|---|---|
| `Put the CSV file here first` | `data\survey_export.csv` is missing | Copy today’s file to that path, then `load` |
| `Please run setup` / command not found | Tools are not installed, or you skipped Activate | IT: run Section A. You: run the two lines at the top |
| `CSV is missing required column(s)` | Header names are wrong | Fix the CSV column names, then `load` |
| `The system is not running` | `start` is not open | Type `start` in a window and leave it open |
| Username or password is wrong | Sign-in failed | Check `.env` with IT, or ask admin for your account |
| Sign in is required | No token, or token expired | Sign in again and click Authorize |
| Only an administrator may do that | Surveyor tried admin work | Ask an admin |
| Too many requests / 429 | You clicked too fast | Wait one minute and try again |
| `start` opens a new Windows window | PowerShell used the Windows `start` word | Type `asset start` instead |

---

## What you should never do

- Do not close the `start` window while people are using the browser.
- Do not delete `.env` or share the admin password.
- Do not change `run.bat` for developer tests. Night staff may still use the menu (`run` or `run.bat`).
- Do not send `dev.db` or `.env` to people outside the team.

---

## Quick cards (print these)

### Night operator

```powershell
cd C:\Users\ranja\utility-asset-registry
.\.venv\Scripts\Activate.ps1
load
```

If rejected rows > 0, type `rejects`.

### Day staff

```powershell
cd C:\Users\ranja\utility-asset-registry
.\.venv\Scripts\Activate.ps1
start
```

Keep the window open. Browser: http://127.0.0.1:8000/docs  
Sign in → Authorize → do your work. Stop with **Ctrl+C**.
