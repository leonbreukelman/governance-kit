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


class TestConstitutionProtection:
    """Tests for constitution.md data loss protection."""

    def test_detects_customized_constitution(self, tmp_path: Path) -> None:
        """Test that customized constitution is detected."""
        from governance.cli import is_constitution_customized

        constitution = tmp_path / "constitution.md"
        
        # Empty file is not customized
        constitution.write_text("")
        assert not is_constitution_customized(constitution)

        # File with template placeholders is not customized
        constitution.write_text("# [PROJECT_NAME]\n\n## [PRINCIPLE_1_NAME]")
        assert not is_constitution_customized(constitution)

        # File with actual content is customized
        constitution.write_text("# My Project\n\n## Core Values\n\nWe value quality.")
        assert is_constitution_customized(constitution)

    def test_prevents_overwriting_customized_constitution(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init refuses to overwrite customized constitution without --destroy-content."""
        import os

        # Setup: create .specify with customized constitution
        specify_dir = tmp_path / ".specify"
        memory_dir = specify_dir / "memory"
        memory_dir.mkdir(parents=True)

        constitution = memory_dir / "constitution.md"
        constitution.write_text("# My Project\n\n## Core Values\n\nWe value quality.")

        os.chdir(tmp_path)

        # Try to run init with --force (should fail with protection)
        result = runner.invoke(main, ["init", "--force"])

        assert result.exit_code == 1
        assert "WARNING" in result.output
        assert "custom content" in result.output
        assert "--skip-speckit" in result.output

    def test_allows_overwrite_with_destroy_content_flag(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that --destroy-content flag allows overwrite with backup."""
        import os

        # Setup: create .specify with customized constitution
        specify_dir = tmp_path / ".specify"
        memory_dir = specify_dir / "memory"
        memory_dir.mkdir(parents=True)

        constitution = memory_dir / "constitution.md"
        original_content = "# My Project\n\n## Core Values\n\nWe value quality."
        constitution.write_text(original_content)

        os.chdir(tmp_path)

        # Run with --destroy-content flag (should create backup)
        # Note: This will fail to actually run specify, but we're testing the backup logic
        runner.invoke(main, ["init", "--force", "--destroy-content"])

        # Check that backup was created
        backup_dirs = list(tmp_path.glob(".specify-backup-*"))
        assert len(backup_dirs) == 1
        
        # Verify backup contains original content
        backup_constitution = backup_dirs[0] / "memory" / "constitution.md"
        assert backup_constitution.read_text() == original_content

    def test_skip_speckit_bypasses_protection(
        self, runner: CliRunner, mock_specify_with_constitution: Path
    ) -> None:
        """Test that --skip-speckit bypasses the protection check."""
        import os
        os.chdir(mock_specify_with_constitution)

        # Add custom content to constitution
        constitution = mock_specify_with_constitution / ".specify" / "memory" / "constitution.md"
        constitution.write_text("# My Project\n\n## Core Values\n\nWe value quality.")

        # Should succeed with --skip-speckit
        result = runner.invoke(main, ["init", "--skip-speckit"])

        assert result.exit_code == 0
        assert "Governance overlay applied" in result.output

    def test_handles_unreadable_constitution_safely(self, tmp_path: Path) -> None:
        """Test that unreadable constitution is treated as customized for safety."""
        from governance.cli import is_constitution_customized

        # Create a constitution file
        constitution = tmp_path / "constitution.md"
        constitution.write_text("# My Project")

        # Make it unreadable (simulate permission error)
        import os
        os.chmod(constitution, 0o000)

        try:
            # Should return True (assume customized) for safety
            result = is_constitution_customized(constitution)
            assert result is True
        finally:
            # Restore permissions for cleanup
            os.chmod(constitution, 0o644)
