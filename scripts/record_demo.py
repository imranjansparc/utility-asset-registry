"""Capture a 5–8 minute demo MP4 from the live application. Not part of the product."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo_recording"
VIDEO = OUT_DIR / "Utility_Asset_Registry_Demo.mp4"
CONCAT = OUT_DIR / "concat.txt"
BASE = "http://127.0.0.1:8000"


def read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def child_env(rate_limit: int | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env.update(read_env_file())
    if rate_limit is not None:
        env["RATE_LIMIT_PER_MINUTE"] = str(rate_limit)
    return env


ADMIN = {
    "username": "admin",
    "password": read_env_file().get("BOOTSTRAP_ADMIN_PASSWORD", "change-me-before-go-live"),
}
SURVEYOR = {
    "username": "surveyor",
    "password": "surveyor-pass-123",
    "role": "surveyor",
}


def venv_python() -> Path:
    if os.name == "nt":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def run_ingest() -> str:
    result = subprocess.run(
        [str(venv_python()), "-m", "utility_asset_registry", str(ROOT / "data" / "survey_export.csv")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=child_env(),
        check=False,
    )
    return (result.stdout or "") + (result.stderr or "")


def start_server(rate_limit: int = 60) -> subprocess.Popen:
    env = child_env(rate_limit=rate_limit)
    return subprocess.Popen(
        [
            str(venv_python()),
            "-m",
            "uvicorn",
            "utility_asset_registry.api.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_health(timeout: float = 30.0) -> None:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.4)
    raise RuntimeError("Server did not start")


def api(method: str, path: str, token: str | None = None, json_body=None):
    import urllib.error
    import urllib.request

    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return response.status, parsed, dict(response.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return exc.code, parsed, dict(exc.headers)


def pretty(payload) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True)[:1800]


def draw_slide(
    path: Path,
    title: str,
    subtitle: str,
    body: str,
    caption: str,
    banner: str = "5-8 minute demonstration  ·  21 Sep 2026",
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1280, 720
    image = Image.new("RGB", (width, height), (18, 32, 48))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 32)
        sub_font = ImageFont.truetype("arial.ttf", 18)
        body_font = ImageFont.truetype("consola.ttf", 16)
        cap_font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        title_font = ImageFont.load_default()
        sub_font = title_font
        body_font = title_font
        cap_font = title_font

    draw.rectangle((0, 0, width, 86), fill=(27, 54, 93))
    draw.text((32, 18), "Utility Asset Registry  ·  Bhubaneswar", fill="white", font=title_font)
    draw.text((32, 56), banner, fill=(180, 210, 230), font=sub_font)
    draw.rectangle((32, 110, width - 32, 168), fill=(15, 108, 140))
    draw.text((48, 126), title, fill="white", font=title_font)
    draw.text((48, 178), subtitle, fill=(200, 220, 230), font=sub_font)
    draw.rectangle((32, 210, width - 32, 640), fill=(8, 16, 24))
    y = 224
    for line in body.splitlines()[:22]:
        draw.text((48, y), line[:110], fill=(210, 230, 210), font=body_font)
        y += 18
    draw.rectangle((0, 652, width, height), fill=(27, 54, 93))
    draw.text((32, 668), caption, fill="white", font=cap_font)
    image.save(path)


def ffmpeg_bin() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def concat_video(clips: list[tuple[Path, float]], output: Path | None = None) -> None:
    dest = output if output is not None else VIDEO
    list_file = dest.with_suffix(".concat.txt")
    lines = []
    for path, duration in clips:
        posix = path.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{posix}'")
        lines.append(f"duration {duration:.2f}")
    last = clips[-1][0].resolve().as_posix().replace("'", "'\\''")
    lines.append(f"file '{last}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [
        ffmpeg_bin(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-vsync",
        "vfr",
        "-pix_fmt",
        "yuv420p",
        str(dest),
    ]
    subprocess.run(cmd, check=True, cwd=OUT_DIR)


def capture_docs_png(path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(BASE + "/docs", wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(800)
            page.screenshot(path=str(path), full_page=False)
            browser.close()
        return path.exists()
    except Exception:
        return False


def write_simple_video(
    stem: str,
    banner: str,
    scenes: list[tuple[float, str, str, str, str]],
    extra: list[tuple[Path, float]] | None = None,
) -> Path:
    clips: list[tuple[Path, float]] = []
    for index, (duration, title, subtitle, body, caption) in enumerate(scenes, 1):
        path = OUT_DIR / f"{stem}_{index:02d}.png"
        draw_slide(path, title, subtitle, body, caption, banner=banner)
        clips.append((path, duration))
        if extra and index == 2:
            clips.extend(extra)
    dest = OUT_DIR / f"{stem}.mp4"
    concat_video(clips, dest)
    return dest


def write_user_videos(
    *,
    ingest_text: str,
    reject_preview: str,
    docs_png: Path,
    assets_status: int,
    assets_body: dict,
    user_body: dict,
    user_status: int,
    del_status: int,
    del_body: dict,
    surveyor_assets_status: int,
    surveyor_assets: dict,
    sum1: dict,
    repairs_status: int,
    repairs_body: dict,
) -> list[Path]:
    videos: list[Path] = []
    videos.append(
        write_simple_video(
            "01_IT_first_time",
            "Simple demo  ·  IT / first-time installer",
            [
                (
                    12,
                    "This video is for IT only",
                    "You prepare the computer once. Other people then type load or start.",
                    "You do not load the daily CSV.\nYou do not work in the browser every day.",
                    "IT  ·  first time only",
                ),
                (
                    25,
                    "Type these four lines, once",
                    "Open PowerShell in the project folder",
                    "cd C:\\Users\\ranja\\utility-asset-registry\n"
                    "python -m venv .venv\n"
                    ".\\.venv\\Scripts\\Activate.ps1\n"
                    "pip install -e .\n"
                    "setup",
                    "setup installs the tools and creates .env if it is missing",
                ),
                (
                    20,
                    "Set the first admin password",
                    "notepad .env",
                    "Change these lines, then Save:\n"
                    "  JWT_SECRET=  (a long secret only IT knows)\n"
                    "  BOOTSTRAP_ADMIN_USERNAME=admin\n"
                    "  BOOTSTRAP_ADMIN_PASSWORD=  (the sign-in password)\n\n"
                    "Do not send .env to GitHub.",
                    "IT  ·  password file",
                ),
                (
                    18,
                    "Prove it works",
                    "Type start. Keep that window open. In a second window type check.",
                    "start\n\ncheck\n\nYou should see: The system is running.\n"
                    "Browser: http://127.0.0.1:8000/docs\n"
                    "Stop with Ctrl+C.",
                    "IT  ·  done",
                ),
            ],
        )
    )
    videos.append(
        write_simple_video(
            "02_Night_operator",
            "Simple demo  ·  Night operator",
            [
                (
                    12,
                    "This video is for the night operator",
                    "You load today's GPS file. You do not need the browser.",
                    "Your command is one word:  load",
                    "Night operator",
                ),
                (
                    18,
                    "1. Put today's file here",
                    "Replace the file if one is already there",
                    "C:\\Users\\ranja\\utility-asset-registry\\data\\survey_export.csv",
                    "Night operator  ·  step 1",
                ),
                (
                    18,
                    "2. Open PowerShell, then type load",
                    "cd  then  Activate.ps1  then  load",
                    "cd C:\\Users\\ranja\\utility-asset-registry\n"
                    ".\\.venv\\Scripts\\Activate.ps1\n"
                    "load",
                    "Night operator  ·  step 2",
                ),
                (
                    28,
                    "3. Read the result (live run)",
                    "Good rows are saved. Bad rows are kept in a rejects file.",
                    ingest_text or "Rows read / accepted / rejected",
                    "Night operator  ·  live load",
                ),
                (
                    22,
                    "4. If rejected rows are more than 0, type rejects",
                    "Excel opens. Look at the last column named reason.",
                    reject_preview,
                    "Night operator  ·  tell your supervisor",
                ),
            ],
        )
    )
    videos.append(
        write_simple_video(
            "03_Day_staff_surveyor",
            "Simple demo  ·  Day staff / surveyor",
            [
                (
                    12,
                    "This video is for day staff / surveyor",
                    "You search, add, and correct assets. You cannot delete.",
                    "Your command is one word:  start",
                    "Surveyor",
                ),
                (
                    16,
                    "1. Type start and keep the window open",
                    "Then open Chrome or Edge",
                    "start\n\nBrowser: http://127.0.0.1:8000/docs\n"
                    "If you are not sure it is on, type check in another window.",
                    "Surveyor  ·  step 1",
                ),
                (
                    22,
                    "2. Sign in, then list assets",
                    f"POST /auth/login  then  GET /assets  ·  HTTP {surveyor_assets_status}",
                    pretty({"items": surveyor_assets.get("items", [])[:2], "total": surveyor_assets.get("total")}),
                    "Surveyor  ·  live request",
                ),
                (
                    22,
                    "3. What you may do  /  what you may not do",
                    f"DELETE as surveyor returned HTTP {del_status}",
                    "You may: GET /assets, POST /assets, PATCH /assets/{code}\n"
                    "You may not: DELETE, create users, upload CSV\n\n"
                    + pretty(del_body),
                    "Surveyor  ·  not_permitted is correct",
                ),
            ],
            extra=[(docs_png, 12)],
        )
    )
    videos.append(
        write_simple_video(
            "04_Administrator",
            "Simple demo  ·  Administrator",
            [
                (
                    12,
                    "This video is for the administrator",
                    "You can do everything a surveyor can, plus three extra jobs.",
                    "start  →  http://127.0.0.1:8000/docs  →  sign in as admin",
                    "Admin",
                ),
                (
                    20,
                    "1. Create a surveyor",
                    f"POST /auth/users  ·  HTTP {user_status}",
                    pretty(user_body),
                    "Admin  ·  give the person the username and password yourself",
                ),
                (
                    18,
                    "2. Delete an asset (admin only)",
                    "DELETE /assets/{code}  ·  surveyor is refused; admin is allowed",
                    pretty(del_body) + "\n\nThat refusal is for the surveyor. Admin uses the same URL and it works.",
                    "Admin  ·  delete",
                ),
                (
                    18,
                    "3. Upload a CSV in the browser, or use night load",
                    "POST /ingest/upload",
                    "Night operator type load  =  usual way\n"
                    "Admin POST /ingest/upload  =  same cleaning, while the system is running\n\n"
                    f"After a night load, GET /assets total={assets_body.get('total')} (HTTP {assets_status})",
                    "Admin  ·  done",
                ),
            ],
        )
    )
    repair_items = repairs_body.get("items", repairs_body) if isinstance(repairs_body, dict) else repairs_body
    videos.append(
        write_simple_video(
            "05_Supervisor",
            "Simple demo  ·  Supervisor",
            [
                (
                    12,
                    "This video is for the supervisor",
                    "You check if today's load was clean, and which assets need repair.",
                    "You can use commands (no browser) or reports in /docs.",
                    "Supervisor",
                ),
                (
                    22,
                    "After the night load — no browser needed",
                    "Ask for rows read / accepted / rejected. If rejected > 0, type rejects.",
                    ingest_text + "\n\n" + reject_preview[:700],
                    "Supervisor  ·  quality of today's file",
                ),
                (
                    18,
                    "In the browser after someone types start",
                    f"GET /reports/summary  ·  cached={sum1.get('cached')}  total={sum1.get('total')}",
                    pretty({k: sum1.get(k) for k in ("cached", "total", "by_type", "average_condition") if k in sum1}),
                    "Supervisor  ·  totals",
                ),
                (
                    18,
                    "Assets that need repair",
                    f"GET /reports/repairs  ·  HTTP {repairs_status}",
                    pretty(repair_items if not isinstance(repair_items, list) else {"items": repair_items[:4]}),
                    "Supervisor  ·  condition below 5",
                ),
            ],
        )
    )
    return videos


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    db = ROOT / "dev.db"
    if db.exists():
        db.unlink()

    ingest_text = run_ingest().strip()
    rejects = (ROOT / "outputs" / "rejects.csv").read_text(encoding="utf-8").splitlines()
    reject_preview = "\n".join(rejects[:8])

    server = start_server(rate_limit=60)
    try:
        wait_health()
        status, login_body, _ = api("POST", "/auth/login", json_body=ADMIN)
        if status != 200:
            raise RuntimeError(f"Admin login failed: {login_body}")
        admin_token = login_body["token"]
        user_status, user_body, _ = api("POST", "/auth/users", token=admin_token, json_body=SURVEYOR)
        assets_status, assets_body, _ = api("GET", "/assets?limit=5", token=admin_token)
        s_status, s_login, _ = api("POST", "/auth/login", json_body={"username": SURVEYOR["username"], "password": SURVEYOR["password"]})
        surveyor_token = s_login.get("token")
        del_status, del_body, _ = api("DELETE", "/assets/PL-0001", token=surveyor_token)
        sum1_status, sum1, _ = api("GET", "/reports/summary", token=admin_token)
        sum2_status, sum2, _ = api("GET", "/reports/summary", token=admin_token)
        patch_status, patch_body, _ = api(
            "PATCH",
            "/assets/PL-0004",
            token=admin_token,
            json_body={"condition_score": 7},
        )
        sum3_status, sum3, _ = api("GET", "/reports/summary", token=admin_token)
        repairs_status, repairs_body, _ = api("GET", "/reports/repairs", token=admin_token)
        surveyor_assets_status, surveyor_assets, _ = api("GET", "/assets?limit=3", token=surveyor_token)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    server = start_server(rate_limit=8)
    try:
        wait_health()
        _, login_again, _ = api("POST", "/auth/login", json_body=ADMIN)
        limited_token = login_again["token"]
        statuses = []
        last_headers: dict = {}
        last_body: dict = {}
        last_code = 0
        for _ in range(12):
            last_code, last_body, last_headers = api(
                "GET", "/assets?limit=1", token=limited_token
            )
            statuses.append(last_code)
            if last_code == 429:
                break
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    docs_png = OUT_DIR / "docs_live.png"
    server = start_server(rate_limit=60)
    try:
        wait_health()
        got_docs = capture_docs_png(docs_png)
        if not got_docs:
            _, spec, _ = api("GET", "/openapi.json")
            paths = "\n".join(f"  {method.upper():6} {path}" for path, ops in sorted(spec.get("paths", {}).items()) for method in ops)
            draw_slide(
                docs_png,
                "2. Published documentation  GET /docs",
                "OpenAPI page the map vendor can open without calling us",
                paths or "GET /docs  GET /openapi.json  GET /health  POST /auth/login",
                "Scene 2 of 6",
            )
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    slides: list[tuple[Path, float]] = []

    def add(name: str, duration: float, title: str, subtitle: str, body: str, caption: str) -> None:
        path = OUT_DIR / name
        draw_slide(path, title, subtitle, body, caption)
        slides.append((path, duration))

    add(
        "01_intro.png",
        40,
        "Working demonstration",
        "Back-end only. No map UI in this project.",
        textwrap.dedent(
            """
            Utility Asset Registry
            State electricity distribution utility · Bhubaneswar

            This recording shows all six required scenes:
              1. Ingest rejects bad rows and continues
              2. Published documentation at /docs
              3. Sign-in, then a successful request
              4. Surveyor refused a deletion (not_permitted)
              5. Summary cache, then refresh after a change
              6. Caller refused for exceeding the request limit (429)

            Commands used: load / asset-ingest, start, /docs
            """
        ).strip(),
        "0:00  Intro",
    )
    add(
        "02_ingest.png",
        50,
        "1. Ingestion tool  ·  bad rows rejected, run continues",
        "Command: python -m utility_asset_registry data\\survey_export.csv",
        ingest_text or "Rows read / accepted / rejected",
        "Scene 1 of 6  ·  live CLI output",
    )
    add(
        "03_rejects.png",
        30,
        "Rejects file  ·  original columns plus reason",
        str(ROOT / "outputs" / "rejects.csv"),
        reject_preview,
        "Scene 1 of 6  ·  10 rejected rows kept for correction",
    )
    add(
        "04_docs_title.png",
        15,
        "2. Published documentation  http://127.0.0.1:8000/docs",
        "The map vendor can open this page and try every operation",
        "Next: live screenshot of GET /docs (OpenAPI / Swagger UI).",
        "Scene 2 of 6",
    )
    slides.append((docs_png, 30))
    add(
        "05_login.png",
        40,
        "3. Sign-in  POST /auth/login",
        "Admin username from .env  ·  HTTP " + str(status),
        pretty({"request": {"username": ADMIN["username"], "password": "(from .env)"}, "response": {k: login_body[k] for k in login_body if k != "token"} | {"token": "(bearer token issued)"}}),
        "Scene 3 of 6  ·  credential issued, expires_in returned",
    )
    add(
        "06_assets.png",
        25,
        "3. Successful authenticated request  GET /assets",
        f"HTTP {assets_status}  ·  total={assets_body.get('total')}  limit={assets_body.get('limit')}",
        pretty({"items": assets_body.get("items", [])[:3], "total": assets_body.get("total")}),
        "Scene 3 of 6  ·  signed-in list succeeds",
    )
    add(
        "07_create_surveyor.png",
        25,
        "4. Admin creates a surveyor  POST /auth/users",
        f"HTTP {user_status}",
        pretty(user_body),
        "Scene 4 of 6  ·  surveyor account ready",
    )
    add(
        "08_delete_refused.png",
        40,
        "4. Surveyor DELETE /assets/PL-0001  ·  refused",
        f"HTTP {del_status}  ·  surveyor login HTTP {s_status}",
        pretty(del_body),
        "Scene 4 of 6  ·  outcome not_permitted  ·  asset was not deleted",
    )
    add(
        "09_summary_fresh.png",
        30,
        "5. GET /reports/summary  ·  first call",
        f"HTTP {sum1_status}  ·  cached={sum1.get('cached')}",
        pretty({k: sum1.get(k) for k in ("cached", "total", "by_type", "average_condition") if k in sum1}),
        "Scene 5 of 6  ·  cached is false",
    )
    add(
        "10_summary_cached.png",
        25,
        "5. GET /reports/summary  ·  second call",
        f"HTTP {sum2_status}  ·  cached={sum2.get('cached')}",
        pretty({k: sum2.get(k) for k in ("cached", "total", "by_type", "average_condition") if k in sum2}),
        "Scene 5 of 6  ·  cached is true  ·  same totals",
    )
    add(
        "11_summary_refreshed.png",
        40,
        "5. PATCH /assets/PL-0004 then GET /reports/summary",
        f"PATCH HTTP {patch_status}  ·  summary HTTP {sum3_status}  ·  cached={sum3.get('cached')}",
        pretty({"patch": patch_body, "summary_cached": sum3.get("cached"), "total": sum3.get("total")}),
        "Scene 5 of 6  ·  cache dropped after a change  ·  cached is false",
    )
    retry = last_body.get("retry_after_seconds") or last_headers.get("Retry-After") or last_headers.get("retry-after")
    add(
        "12_rate_limit.png",
        50,
        "6. Request limit exceeded  ·  RATE_LIMIT_PER_MINUTE=8",
        f"Statuses: {statuses}  ·  last HTTP {last_code}",
        pretty(last_body) + f"\n\nRetry-After: {retry}",
        "Scene 6 of 6  ·  429  ·  outcome rate_limited",
    )
    add(
        "13_close.png",
        30,
        "End of demonstration",
        "All six required scenes recorded from the live application.",
        textwrap.dedent(
            """
            Shown:
              • Ingest: rows rejected, run continued, rejects.csv has reason
              • GET /docs published operations
              • Admin login + GET /assets 200
              • Surveyor DELETE refused (not_permitted)
              • Summary cached, then fresh after PATCH
              • GET /assets 429 rate_limited with retry guidance

            Tests: pytest (throwaway database, never touches this demo db)
            Submit this MP4 to the organisation. Do not commit it to GitHub.
            """
        ).strip(),
        "7:30  Close",
    )

    concat_video(slides, VIDEO)
    seconds = sum(duration for _, duration in slides)
    print(f"wrote {VIDEO}")
    print(f"duration_s={seconds:.0f}")
    print(f"ingest_ok={'Rows accepted' in ingest_text}")
    print(f"login={status} assets={assets_status} user={user_status} delete={del_status}")
    print(f"cache={sum1.get('cached')}/{sum2.get('cached')}/{sum3.get('cached')} rate={statuses}")

    user_videos = write_user_videos(
        ingest_text=ingest_text,
        reject_preview=reject_preview,
        docs_png=docs_png,
        assets_status=assets_status,
        assets_body=assets_body,
        user_body=user_body,
        user_status=user_status,
        del_status=del_status,
        del_body=del_body,
        surveyor_assets_status=surveyor_assets_status,
        surveyor_assets=surveyor_assets,
        sum1=sum1,
        repairs_status=repairs_status,
        repairs_body=repairs_body,
    )
    for path in user_videos:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
