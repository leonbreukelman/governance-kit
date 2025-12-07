"""Governance overlay application logic."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.abc import Traversable

# Marker to detect if overlay is already applied
OVERLAY_MARKER = "# --- 🏛️ GOVERNANCE OVERLAY ---"


def get_rules_dir() -> Traversable:
    """Get the bundled rules directory.

    Returns:
        Path-like object to the bundled rules directory.
    """
    return files("governance") / "rules"


def apply_governance_overlay(specify_dir: Path) -> bool:
    """Apply governance rules to a Spec Kit initialized repository.

    Copies bundled governance rules to .specify/memory/governance/
    and appends them to constitution.md.

    Args:
        specify_dir: Path to .specify/ directory

    Returns:
        True if overlay was applied, False if already present.

    Raises:
        FileNotFoundError: If constitution.md doesn't exist
    """
    memory_dir = specify_dir / "memory"
    constitution = memory_dir / "constitution.md"
    gov_dir = memory_dir / "governance"

    # Validate constitution exists
    if not constitution.exists():
        msg = f"{constitution} not found. Run '/speckit.constitution' first."
        raise FileNotFoundError(msg)

    # Check if already applied (idempotent)
    content = constitution.read_text()
    if OVERLAY_MARKER in content:
        return False  # Already applied

    # Create governance directory
    gov_dir.mkdir(exist_ok=True)

    # Copy rule files from bundled package data
    rules_source = get_rules_dir()
    rule_files = ["architecture.md", "stack.md", "process.md"]

    for rule_name in rule_files:
        source = rules_source / rule_name
        # Check if source exists (as Traversable)
        try:
            source_content = source.read_text()
            (gov_dir / rule_name).write_text(source_content)
        except FileNotFoundError:
            # Rule file not bundled, skip
            pass

    # Build governance section content
    sections = []
    for rule_name in rule_files:
        rule_path = gov_dir / rule_name
        if rule_path.exists():
            rule_content = rule_path.read_text().strip()
            section_name = rule_name.replace(".md", "").title()
            sections.append(f"## {section_name} Governance\n\n{rule_content}")

    if not sections:
        # No rules to add, create placeholder
        sections.append(
            "## Governance Rules\n\n"
            "*Add rules to `.specify/memory/governance/` directory.*"
        )

    governance_section = f"""

{OVERLAY_MARKER}

The following governance rules are **non-negotiable** and apply to all development phases.

{chr(10).join(sections)}

---
*Governance overlay applied by governance-kit*
"""

    # Append to constitution
    with open(constitution, "a") as f:
        f.write(governance_section)

    return True


def check_governance_overlay(specify_dir: Path) -> list[str]:
    """Check if governance overlay is properly configured.

    Args:
        specify_dir: Path to .specify/ directory

    Returns:
        List of issues found (empty if all good).
    """
    issues: list[str] = []
    constitution = specify_dir / "memory" / "constitution.md"
    gov_dir = specify_dir / "memory" / "governance"

    if not constitution.exists():
        issues.append("constitution.md not found")
    elif OVERLAY_MARKER not in constitution.read_text():
        issues.append("Governance overlay not in constitution.md")

    if not gov_dir.exists():
        issues.append("governance/ directory not found")
    else:
        for rule in ["architecture.md", "stack.md", "process.md"]:
            if not (gov_dir / rule).exists():
                issues.append(f"Missing rule: {rule}")

    return issues
