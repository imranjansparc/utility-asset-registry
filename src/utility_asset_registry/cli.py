"""Simple operator commands: load, start, run, setup, check, rejects."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from shutil import copyfile
from urllib.error import URLError
from urllib.request import urlopen

import typer

from utility_asset_registry.geo import nearest_asset
from utility_asset_registry.ingest import resolve_paths, run_ingest
from utility_asset_registry.reports import surveyors_on

DEFAULT_CSV = Path("data") / "survey_export.csv"
DEFAULT_REJECTS = Path("outputs") / "rejects.csv"
DOCS_URL = "http://127.0.0.1:8000/docs"
HEALTH_URL = "http://127.0.0.1:8000/health"
OPERATOR_COMMANDS = ("load", "start", "run", "setup", "check", "rejects")


def _parse_near(value: str | None) -> tuple[float, float] | None:
    if value is None:
        return None
    parts = [item.strip() for item in value.split(",")]
    if len(parts) != 2:
        raise typer.BadParameter("Use --near LATITUDE,LONGITUDE")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise typer.BadParameter("Use --near LATITUDE,LONGITUDE") from exc


def _parse_on_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise typer.BadParameter("Use --on-date YYYY-MM-DD") from exc


def ingest(
    csv_path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path of the handheld GPS CSV export.",
    ),
    rejects: Path | None = typer.Option(
        None,
        "--rejects",
        help="Where to write the rejects file (original columns plus reason).",
    ),
    map_file: Path | None = typer.Option(
        None,
        "--map",
        help="Where to write the GeoJSON map file of accepted assets.",
    ),
    summary: Path | None = typer.Option(
        None,
        "--summary",
        help="Where to write the printable summary report.",
    ),
    log_file: Path | None = typer.Option(
        None,
        "--log",
        help="Log file to which this run appends one dated line.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Abort the whole run if any row is rejected (for already-cleaned files).",
    ),
    near: str | None = typer.Option(
        None,
        "--near",
        help="LATITUDE,LONGITUDE — print the nearest accepted asset in kilometres.",
    ),
    on_date: str | None = typer.Option(
        None,
        "--on-date",
        help="YYYY-MM-DD — list distinct surveyors who worked that day.",
    ),
) -> None:
    """Load one day's field export, clean it, and write rejects, map and summary."""
    paths = resolve_paths(
        csv_path,
        rejects=rejects,
        map_file=map_file,
        summary=summary,
        log_file=log_file,
    )
    outcome = run_ingest(csv_path, paths, strict=strict)

    if outcome.missing_columns:
        missing = ", ".join(outcome.missing_columns)
        typer.echo(f"CSV is missing required column(s): {missing}")
        raise typer.Exit(code=1)

    result = outcome.result
    typer.echo(f"Rows read:      {result.rows_read}")
    typer.echo(f"Rows accepted:  {len(result.accepted)}")
    typer.echo(f"Rows rejected:  {len(result.rejected)}")
    typer.echo(f"Rejects file:   {paths.rejects}")

    if outcome.aborted_strict:
        typer.echo(
            "Strict mode: a rejected row aborted the whole run. "
            "Map and summary were not written."
        )
        raise typer.Exit(code=1)

    typer.echo(f"Map file:       {paths.map_file}")
    typer.echo(f"Summary report: {paths.summary}")

    position = _parse_near(near)
    if position is not None:
        found = nearest_asset(result.accepted, position[0], position[1])
        if found is None:
            typer.echo("Nearest asset:  none (no accepted rows)")
        else:
            asset, km = found
            typer.echo(f"Nearest asset:  {asset.asset_id} ({asset.name}) at {km:.3f} km")

    day = _parse_on_date(on_date)
    if day is not None:
        names = surveyors_on(result.accepted, day)
        listed = ", ".join(names) if names else "(none)"
        typer.echo(f"Surveyors on {day.isoformat()}: {listed}")


def project_root() -> Path:
    here = Path(__file__).resolve().parent.parent.parent
    if (here / "pyproject.toml").exists():
        return here
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists():
        return cwd
    return cwd


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def _install_project(root: Path) -> None:
    venv_py = _venv_python(root)
    if not venv_py.exists():
        subprocess.run(
            [sys.executable, "-m", "venv", str(root / ".venv")],
            check=True,
        )
    subprocess.run(
        [str(venv_py), "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
    )
    requirements = root / "requirements.txt"
    if requirements.exists():
        subprocess.run(
            [str(venv_py), "-m", "pip", "install", "-r", str(requirements)],
            check=True,
        )
    subprocess.run(
        [str(venv_py), "-m", "pip", "install", "-e", ".[dev]"],
        cwd=str(root),
        check=True,
    )


def _ensure_env_file(root: Path) -> None:
    env_path = root / ".env"
    example = root / ".env.example"
    if env_path.exists():
        return
    if example.exists():
        copyfile(example, env_path)
        typer.echo("Created .env for you.")


def _fetch_health(url: str, timeout: float = 3.0) -> tuple[int, str]:
    with urlopen(url, timeout=timeout) as response:
        return int(response.status), response.read().decode("utf-8")


def _open_path(path: Path) -> None:
    resolved = str(path.resolve())
    if os.name == "nt":
        os.startfile(resolved)
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, resolved], check=False)


def load(
    csv_path: Path | None = typer.Argument(
        None,
        help="CSV to load. If omitted, uses data\\survey_export.csv",
    ),
) -> None:
    """Load today's survey CSV. Good rows are saved; bad rows go to outputs\\rejects.csv."""
    path = csv_path if csv_path is not None else DEFAULT_CSV
    if not path.exists():
        typer.echo("Put the CSV file here first:")
        typer.echo(f"  {path}")
        raise typer.Exit(code=1)
    ingest(csv_path=path)


def start() -> None:
    """Start the system. Keep this window open, then open the browser page."""
    env_path = Path(".env")
    example = Path(".env.example")
    if not env_path.exists():
        if example.exists():
            copyfile(example, env_path)
            typer.echo("Created .env for you.")
        typer.echo("Open .env in Notepad and set the admin password,")
        typer.echo("then type start again.")
        raise typer.Exit(code=1)

    import uvicorn

    typer.echo("Starting... Keep this window open.")
    typer.echo(f"Browser page: {DOCS_URL}")
    typer.echo("Press Ctrl+C to stop.")
    uvicorn.run(
        "utility_asset_registry.api.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
    )


def menu() -> None:
    """Show a simple menu: 1 start, 2 load, 3 exit."""
    while True:
        typer.echo("")
        typer.echo("================================")
        typer.echo(" Utility Asset Registry")
        typer.echo("================================")
        typer.echo("")
        typer.echo("  1 = Start the system")
        typer.echo("  2 = Load survey CSV")
        typer.echo("  3 = Exit")
        typer.echo("")
        choice = typer.prompt("Type 1, 2 or 3").strip()
        if choice == "1":
            start()
        elif choice == "2":
            load()
        elif choice == "3":
            raise typer.Exit(code=0)
        else:
            typer.echo("Type 1, 2 or 3")


def setup() -> None:
    """First-time prepare: install tools and create the password file."""
    root = project_root()
    typer.echo("Installing... please wait.")
    try:
        _install_project(root)
    except (OSError, subprocess.CalledProcessError):
        typer.echo("Install failed. Ask IT to run setup again.")
        raise typer.Exit(code=1)
    _ensure_env_file(root)
    typer.echo("Done.")
    typer.echo("1. Open .env in Notepad and set the admin password")
    typer.echo("2. Type start to start the system")
    typer.echo("3. Type load to load today's CSV")


def check() -> None:
    """Tell you if the system is running."""
    try:
        status, body = _fetch_health(HEALTH_URL)
    except (OSError, URLError, TimeoutError):
        typer.echo("The system is not running.")
        typer.echo("Type start, keep the window open, then try check again.")
        raise typer.Exit(code=1)
    if status != 200 or "ok" not in body.lower():
        typer.echo("The system is not running.")
        typer.echo("Type start, keep the window open, then try check again.")
        raise typer.Exit(code=1)
    typer.echo("The system is running.")
    typer.echo(f"Browser page: {DOCS_URL}")


def open_rejects() -> None:
    """Open the bad-rows file from the last load."""
    path = DEFAULT_REJECTS
    if not path.exists():
        typer.echo("No rejects file yet.")
        typer.echo("Type load first. If rows fail, they are written here:")
        typer.echo(f"  {path}")
        raise typer.Exit(code=1)
    typer.echo(f"Rejects file: {path}")
    typer.echo("Open it in Excel. Look at the last column named reason.")
    _open_path(path)


operator_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Simple commands: load, start, run, setup, check, rejects",
)
operator_app.command("load")(load)
operator_app.command("start")(start)
operator_app.command("run")(menu)
operator_app.command("setup")(setup)
operator_app.command("check")(check)
operator_app.command("rejects")(open_rejects)


def run() -> None:
    typer.run(ingest)


def operator_main() -> None:
    operator_app()


def load_main() -> None:
    typer.run(load)


def start_main() -> None:
    typer.run(start)


def menu_main() -> None:
    typer.run(menu)


def setup_main() -> None:
    typer.run(setup)


def check_main() -> None:
    typer.run(check)


def rejects_main() -> None:
    typer.run(open_rejects)
