from typer.testing import CliRunner

from screen_pilot.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_status():
    result = runner.invoke(app, ["status"])
    # Either reports running or fails gracefully
    assert "screen-pilot" in result.stdout.lower() or result.exit_code == 1
