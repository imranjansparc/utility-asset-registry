"""Simple operator commands: load, start, run, setup, check, rejects."""

from __future__ import annotations

from pathlib import Path
from urllib.error import URLError

from typer.testing import CliRunner

from factories import VALID_ROW, make_row, write_survey_csv
from utility_asset_registry.cli import operator_app

runner = CliRunner()


class TestOperatorHelp:
    def test_help_lists_the_six_words(self):
        result = runner.invoke(operator_app, ["--help"])
        assert result.exit_code == 0
        for word in ("load", "start", "run", "setup", "check", "rejects"):
            assert word in result.stdout


class TestLoad:
    def test_missing_default_csv_explains_where_to_put_it(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(operator_app, ["load"])
        assert result.exit_code == 1
        assert "Put the CSV file here first" in result.stdout
        assert "survey_export.csv" in result.stdout

    def test_loads_a_given_csv(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        csv_path = write_survey_csv(
            tmp_path / "survey.csv",
            [VALID_ROW, make_row(asset_id="BAD", name="x")],
        )
        result = runner.invoke(operator_app, ["load", str(csv_path)])
        assert result.exit_code == 0
        assert "Rows read:      2" in result.stdout
        assert "Rows accepted:  1" in result.stdout
        assert "Rows rejected:  1" in result.stdout


class TestSetup:
    def test_creates_env_and_prints_next_steps(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".env.example").write_text("JWT_SECRET=change-me\n", encoding="utf-8")
        monkeypatch.setattr("utility_asset_registry.cli.project_root", lambda: tmp_path)
        monkeypatch.setattr("utility_asset_registry.cli._install_project", lambda root: None)
        result = runner.invoke(operator_app, ["setup"])
        assert result.exit_code == 0
        assert (tmp_path / ".env").exists()
        assert "Done." in result.stdout
        assert "admin password" in result.stdout.lower()

    def test_install_failure_is_plain_language(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("utility_asset_registry.cli.project_root", lambda: tmp_path)

        def boom(root: Path) -> None:
            raise OSError("pip failed")

        monkeypatch.setattr("utility_asset_registry.cli._install_project", boom)
        result = runner.invoke(operator_app, ["setup"])
        assert result.exit_code == 1
        assert "Install failed" in result.stdout


class TestCheck:
    def test_not_running_tells_operator_to_start(self, monkeypatch):
        def down(url: str, timeout: float = 3.0) -> tuple[int, str]:
            raise URLError("connection refused")

        monkeypatch.setattr("utility_asset_registry.cli._fetch_health", down)
        result = runner.invoke(operator_app, ["check"])
        assert result.exit_code == 1
        assert "not running" in result.stdout.lower()
        assert "start" in result.stdout.lower()

    def test_running_prints_the_browser_page(self, monkeypatch):
        monkeypatch.setattr(
            "utility_asset_registry.cli._fetch_health",
            lambda url, timeout=3.0: (200, '{"status": "ok"}'),
        )
        result = runner.invoke(operator_app, ["check"])
        assert result.exit_code == 0
        assert "The system is running." in result.stdout
        assert "http://127.0.0.1:8000/docs" in result.stdout


class TestRejects:
    def test_missing_file_tells_operator_to_load(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        opened: list[Path] = []
        monkeypatch.setattr("utility_asset_registry.cli._open_path", opened.append)
        result = runner.invoke(operator_app, ["rejects"])
        assert result.exit_code == 1
        assert "No rejects file yet." in result.stdout
        assert "load" in result.stdout.lower()
        assert opened == []

    def test_existing_file_is_opened(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rejects = tmp_path / "outputs" / "rejects.csv"
        rejects.parent.mkdir()
        rejects.write_text("reason\nbad coordinates\n", encoding="utf-8")
        opened: list[Path] = []
        monkeypatch.setattr("utility_asset_registry.cli._open_path", opened.append)
        result = runner.invoke(operator_app, ["rejects"])
        assert result.exit_code == 0
        assert opened == [rejects]
        assert "reason" in result.stdout.lower()


class TestRunMenu:
    def test_choice_three_exits(self):
        result = runner.invoke(operator_app, ["run"], input="3\n")
        assert result.exit_code == 0
        assert "1 = Start the system" in result.stdout
