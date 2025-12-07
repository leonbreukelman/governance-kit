"""Governance-enhanced Spec Kit CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from .overlay import apply_governance_overlay, check_governance_overlay


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Governance-enhanced Spec Kit CLI.

    Wraps GitHub Spec Kit with organizational governance rules.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.option("--dry-run", is_flag=True, help="Simulate without making changes")
@click.option("--force", is_flag=True, help="Force reinitialize even if .specify exists")
@click.option(
    "--skip-speckit",
    is_flag=True,
    help="Skip Spec Kit init (apply overlay only to existing .specify)",
)
def init(dry_run: bool, force: bool, skip_speckit: bool) -> None:
    """Initialize repository with Spec Kit + Governance overlay.

    This command will:
    1. Run 'specify init --here' if not skipped
    2. Copy governance rules to .specify/memory/governance/
    3. Append rules to constitution.md
    """
    specify_dir = Path(".specify")

    # Step 1: Run Spec Kit init if needed
    if not skip_speckit:
        if specify_dir.exists() and not force:
            click.echo("ℹ️  .specify/ already exists. Use --force to reinitialize.")
        else:
            click.echo("📦 Running Spec Kit initialization...")
            if not dry_run:
                # Try direct specify command first
                result = subprocess.run(
                    ["specify", "init", "--here", "--force"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    # Fallback to uvx if specify not in PATH
                    click.echo("   (specify not in PATH, trying uvx...)")
                    result = subprocess.run(
                        [
                            "uvx",
                            "--from",
                            "git+https://github.com/github/spec-kit.git",
                            "specify",
                            "init",
                            "--here",
                            "--force",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        click.echo(f"❌ Spec Kit init failed: {result.stderr}", err=True)
                        sys.exit(1)
                click.echo("✅ Spec Kit initialized.")

    # Step 2: Validate .specify exists
    if not specify_dir.exists():
        click.echo(
            "❌ .specify/ not found. Run 'specify init --here' first or remove --skip-speckit.",
            err=True,
        )
        sys.exit(1)

    # Step 3: Check if constitution.md exists
    constitution = specify_dir / "memory" / "constitution.md"
    if not constitution.exists():
        click.echo(
            "⚠️  constitution.md not found. Run '/speckit.constitution' in your AI agent first.",
            err=True,
        )
        click.echo("   Then run 'governance init --skip-speckit' to apply the overlay.")
        sys.exit(1)

    # Step 4: Apply governance overlay
    click.echo("🛡️  Applying Governance Overlay...")
    if not dry_run:
        try:
            applied = apply_governance_overlay(specify_dir)
            if applied:
                click.echo("✅ Governance overlay applied successfully.")
            else:
                click.echo("ℹ️  Governance overlay already present, skipping.")
        except FileNotFoundError as e:
            click.echo(f"❌ {e}", err=True)
            sys.exit(1)
    else:
        click.echo("   (dry-run: no changes made)")


@main.command()
def check() -> None:
    """Check if governance overlay is applied correctly.

    Validates that:
    - constitution.md exists and contains overlay marker
    - governance/ directory exists with rule files
    """
    specify_dir = Path(".specify")

    if not specify_dir.exists():
        click.echo("❌ .specify/ not found. Run 'governance init' first.", err=True)
        sys.exit(1)

    issues = check_governance_overlay(specify_dir)

    if issues:
        click.echo("Governance overlay issues found:")
        for issue in issues:
            click.echo(f"  ⚠️  {issue}")
        sys.exit(1)
    else:
        click.echo("✅ Governance overlay is properly configured.")


if __name__ == "__main__":
    main()
