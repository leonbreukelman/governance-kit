"""Governance-enhanced Spec Kit CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click

from .overlay import apply_governance_overlay, check_governance_overlay


def find_specify_executable() -> str | None:
    """Find the specify executable, checking common install locations.

    Returns:
        Path to specify executable or None if not found.
    """
    # First check if it's in PATH
    specify_path = shutil.which("specify")
    if specify_path:
        return specify_path

    return None


def is_constitution_customized(constitution_path: Path) -> bool:
    """Check if constitution.md has been filled in with custom content.

    A constitution is considered customized if it exists and does NOT contain
    template placeholders like [PROJECT_NAME] or [PRINCIPLE_1_NAME].

    Args:
        constitution_path: Path to constitution.md file

    Returns:
        True if constitution has custom content, False if it's still a template
    """
    if not constitution_path.exists():
        return False

    try:
        content = constitution_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, OSError):
        # If we can't read the file, assume it's customized to be safe
        return True

    # Check for common template placeholders
    template_markers = [
        "[PROJECT_NAME]",
        "[PRINCIPLE_1_NAME]",
        "[PRINCIPLE_2_NAME]",
        "[YOUR_PROJECT]",
        "[TEAM_NAME]",
        "TODO:",
        "FIXME:",
    ]

    # If any template marker is found, it's still a template
    for marker in template_markers:
        if marker in content:
            return False

    # Check if file has meaningful content (not just whitespace/headers)
    # Strip common markdown headers and whitespace
    lines = [
        line.strip()
        for line in content.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]

    # If there's actual content beyond headers, consider it customized
    return len(lines) > 0


def backup_specify_directory(specify_dir: Path) -> Path:
    """Create a timestamped backup of the .specify directory.

    Args:
        specify_dir: Path to .specify directory

    Returns:
        Path to the backup directory

    Raises:
        OSError: If backup cannot be created due to filesystem issues
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = specify_dir.parent / f".specify-backup-{timestamp}"

    # Check if backup path already exists
    if backup_path.exists():
        # Add a suffix to make it unique
        import time

        suffix = int(time.time() * 1000) % 1000
        backup_path = specify_dir.parent / f".specify-backup-{timestamp}-{suffix}"

    try:
        shutil.copytree(specify_dir, backup_path)
    except (OSError, PermissionError) as e:
        msg = f"Failed to create backup: {e}"
        raise OSError(msg) from e

    return backup_path


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
@click.option(
    "--ai",
    type=str,
    default="copilot",
    help="AI assistant (claude, gemini, copilot, etc.)",
)
@click.option(
    "--destroy-content",
    is_flag=True,
    help="Allow overwriting customized constitution.md (DANGEROUS - data loss!)",
)
def init(
    dry_run: bool, force: bool, skip_speckit: bool, ai: str, destroy_content: bool
) -> None:
    """Initialize repository with Spec Kit + Governance overlay.

    This command will:
    1. Run 'specify init --here --ai <ai>' if not skipped
    2. Copy governance rules to .specify/memory/governance/
    3. Append rules to constitution.md
    """
    specify_dir = Path(".specify")

    # Step 1: Run Spec Kit init if needed
    if not skip_speckit:
        if specify_dir.exists() and not force:
            click.echo("ℹ️  .specify/ already exists. Use --force to reinitialize.")
        else:
            # CRITICAL: Check for customized constitution before destructive operation
            constitution = specify_dir / "memory" / "constitution.md"
            if specify_dir.exists() and is_constitution_customized(constitution):
                if not destroy_content:
                    click.echo(
                        "⚠️  WARNING: Existing constitution.md detected with custom content!",
                        err=True,
                    )
                    click.echo(
                        "   Running 'specify init --force' would DESTROY your filled-in "
                        "constitution.",
                        err=True,
                    )
                    click.echo("", err=True)
                    click.echo("Options:", err=True)
                    click.echo(
                        "  1. Use 'governance init --skip-speckit' to apply overlay only "
                        "(RECOMMENDED)",
                        err=True,
                    )
                    click.echo(
                        "  2. Use '--destroy-content --force' to overwrite (DATA LOSS!)",
                        err=True,
                    )
                    click.echo("", err=True)
                    click.echo(
                        "💡 Tip: If you want to preserve your content, use --skip-speckit",
                        err=True,
                    )
                    sys.exit(1)
                else:
                    # User explicitly requested to destroy content - create backup first
                    click.echo(
                        "⚠️  --destroy-content flag detected. Creating backup...",
                        err=True,
                    )
                    if not dry_run:
                        try:
                            backup_path = backup_specify_directory(specify_dir)
                            click.echo(f"📦 Backed up .specify/ to {backup_path}")
                        except OSError as e:
                            click.echo(f"❌ Failed to create backup: {e}", err=True)
                            click.echo(
                                "   Cannot proceed without backup. Aborting.", err=True
                            )
                            sys.exit(1)

            click.echo(f"📦 Running Spec Kit initialization (AI: {ai})...")
            if not dry_run:
                specify_exe = find_specify_executable()
                cmd: list[str]

                if specify_exe:
                    cmd = [
                        specify_exe,
                        "init",
                        "--here",
                        "--force",
                        "--ai",
                        ai,
                        "--ignore-agent-tools",
                    ]
                else:
                    # Fallback to uvx
                    click.echo("   (specify not found, using uvx...)")
                    cmd = [
                        "uvx",
                        "--from",
                        "git+https://github.com/github/spec-kit.git",
                        "specify",
                        "init",
                        "--here",
                        "--force",
                        "--ai",
                        ai,
                        "--ignore-agent-tools",
                    ]

                # Run without capturing output to preserve TTY for interactive prompts
                result = subprocess.run(cmd, check=False)

                if result.returncode != 0:
                    click.echo("❌ Spec Kit init failed.", err=True)
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
