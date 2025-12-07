"""Tests for governance overlay logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from governance.overlay import (
    OVERLAY_MARKER,
    apply_governance_overlay,
    check_governance_overlay,
)


@pytest.fixture
def mock_specify_dir(tmp_path: Path) -> Path:
    """Create a mock .specify directory with constitution.md."""
    specify_dir = tmp_path / ".specify"
    memory_dir = specify_dir / "memory"
    memory_dir.mkdir(parents=True)

    # Create a mock constitution.md
    constitution = memory_dir / "constitution.md"
    constitution.write_text("""# Project Constitution

## Core Principles

### I. Quality First
All code must be tested.
""")

    return specify_dir


class TestApplyGovernanceOverlay:
    """Tests for apply_governance_overlay function."""

    def test_applies_overlay_successfully(self, mock_specify_dir: Path) -> None:
        """Test that overlay is applied to constitution.md."""
        result = apply_governance_overlay(mock_specify_dir)

        assert result is True

        # Check constitution was updated
        constitution = mock_specify_dir / "memory" / "constitution.md"
        content = constitution.read_text()
        assert OVERLAY_MARKER in content
        assert "Architecture Governance" in content

    def test_creates_governance_directory(self, mock_specify_dir: Path) -> None:
        """Test that governance directory is created with rule files."""
        apply_governance_overlay(mock_specify_dir)

        gov_dir = mock_specify_dir / "memory" / "governance"
        assert gov_dir.exists()
        assert (gov_dir / "architecture.md").exists()
        assert (gov_dir / "stack.md").exists()
        assert (gov_dir / "process.md").exists()

    def test_idempotent_no_duplicate(self, mock_specify_dir: Path) -> None:
        """Test that running twice doesn't duplicate content."""
        apply_governance_overlay(mock_specify_dir)
        result = apply_governance_overlay(mock_specify_dir)

        assert result is False

        constitution = mock_specify_dir / "memory" / "constitution.md"
        content = constitution.read_text()
        # Should only have one marker
        assert content.count(OVERLAY_MARKER) == 1

    def test_raises_if_no_constitution(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised if constitution.md missing."""
        specify_dir = tmp_path / ".specify"
        memory_dir = specify_dir / "memory"
        memory_dir.mkdir(parents=True)
        # No constitution.md created

        with pytest.raises(FileNotFoundError, match="constitution.md not found"):
            apply_governance_overlay(specify_dir)


class TestCheckGovernanceOverlay:
    """Tests for check_governance_overlay function."""

    def test_returns_empty_when_valid(self, mock_specify_dir: Path) -> None:
        """Test that no issues are returned for valid overlay."""
        apply_governance_overlay(mock_specify_dir)

        issues = check_governance_overlay(mock_specify_dir)
        assert issues == []

    def test_detects_missing_overlay(self, mock_specify_dir: Path) -> None:
        """Test that missing overlay marker is detected."""
        issues = check_governance_overlay(mock_specify_dir)

        assert "Governance overlay not in constitution.md" in issues
        assert "governance/ directory not found" in issues

    def test_detects_missing_constitution(self, tmp_path: Path) -> None:
        """Test that missing constitution.md is detected."""
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir(parents=True)

        issues = check_governance_overlay(specify_dir)
        assert "constitution.md not found" in issues
