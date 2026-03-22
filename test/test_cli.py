from typer.testing import CliRunner
import os
import pytest

from cli.main import app

def test_cli_help(cli_runner: CliRunner):
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init-db" in result.stdout
    assert "add" in result.stdout

def test_cli_init_db(cli_runner: CliRunner):
    result = cli_runner.invoke(app, ["init-db"])
    assert result.exit_code == 0
    assert "Database initialized" in result.stdout

def test_cli_add_blocked_without_override(cli_runner: CliRunner):
    # Depending on ALLOW_DIRECT_DB_CLI, add might fail or succeed. 
    # Let's ensure it's not set.
    if "ALLOW_DIRECT_DB_CLI" in os.environ:
        del os.environ["ALLOW_DIRECT_DB_CLI"]
        
    result = cli_runner.invoke(app, ["add", "TestCliFood", "100", "0", "10", "1"])
    assert result.exit_code == 2
    assert "Direct 'add' CLI access is disabled" in result.stderr
