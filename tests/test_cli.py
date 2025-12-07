"""Tests for governance CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from governance.cli import main
from governance.overlay import OVERLAY_MARKER


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_specify_with_constitution(tmp_path: Path) -> Path:
    """Create a mock .specify directory with constitution.md."""
    specify_dir = tmp_path / ".specify"
    memory_dir = specify_dir / "memory"
    memory_dir.mkdir(parents=True)

    constitution = memory_dir / "constitution.md"
    constitution.write_text("# Project Constitution\n\n## Principles\n")

    return tmp_path


class TestCheckCommand:
    """Tests for the 'governance check' command."""

    def test_check_fails_when_no_specify_dir(self, runner: CliRunner) -> None:
        """Test check fails when .specify doesn't exist."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["check"])

            assert result.exit_code == 1
            assert ".specify/ not found" in result.output

    def test_check_fails_when_no_overlay(
        self, runner: CliRunner, mock_specify_with_constitution: Path
    ) -> None:
        """Test check fails when overlay not applied."""
        import os
        os.chdir(mock_specify_with_constitution)

        result = runner.invoke(main, ["check"])

        assert result.exit_code == 1
        assert "Governance overlay not in constitution.md" in result.output

    def test_check_passes_when_overlay_applied(
        self, runner: CliRunner, mock_specify_with_constitution: Path
    ) -> None:
        """Test check passes after overlay is applied."""
        import os
        os.chdir(mock_specify_with_constitution)

        # Apply overlay first
        from governance.overlay import apply_governance_overlay
        apply_governance_overlay(mock_specify_with_constitution / ".specify")

        result = runner.invoke(main, ["check"])

        assert result.exit_code == 0
        assert "properly configured" in result.output


class TestInitCommand:
    """Tests for the 'governance init' command."""

    def test_init_dry_run_makes_no_changes(
        self, runner: CliRunner, mock_specify_with_constitution: Path
    ) -> None:
        """Test --dry-run doesn't modify files."""
        import os
        os.chdir(mock_specify_with_constitution)

        constitution = mock_specify_with_constitution / ".specify" / "memory" / "constitution.md"
        original_content = constitution.read_text()

        result = runner.invoke(main, ["init", "--skip-speckit", "--dry-run"])

        assert result.exit_code == 0
        assert "dry-run" in result.output
        assert constitution.read_text() == original_content

    def test_init_applies_overlay(
        self, runner: CliRunner, mock_specify_with_constitution: Path
    ) -> None:
        """Test init applies overlay when --skip-speckit is used."""
        import os
        os.chdir(mock_specify_with_constitution)

        result = runner.invoke(main, ["init", "--skip-speckit"])

        assert result.exit_code == 0
        assert "Governance overlay applied" in result.output

        constitution = mock_specify_with_constitution / ".specify" / "memory" / "constitution.md"
        assert OVERLAY_MARKER in constitution.read_text()

    def test_init_skips_if_already_applied(
        self, runner: CliRunner, mock_specify_with_constitution: Path
    ) -> None:
        """Test init is idempotent."""
        import os
        os.chdir(mock_specify_with_constitution)

        # Apply once
        runner.invoke(main, ["init", "--skip-speckit"])

        # Apply again
        result = runner.invoke(main, ["init", "--skip-speckit"])

        assert result.exit_code == 0
        assert "already present" in result.output


class TestMainHelp:
    """Tests for help output."""

    def test_shows_help_when_no_command(self, runner: CliRunner) -> None:
        """Test that help is shown when no subcommand given."""
        result = runner.invoke(main)

        assert result.exit_code == 0
        assert "Governance-enhanced Spec Kit CLI" in result.output
        assert "init" in result.output
        assert "check" in result.output
