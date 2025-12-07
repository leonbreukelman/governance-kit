# Governance-Kit

Governance overlay for [GitHub Spec Kit](https://github.com/github/spec-kit). Injects organizational governance rules into Spec Kit's constitution for automated enforcement across all development phases.

## Installation

```bash
# Global installation (recommended)
uv tool install git+https://github.com/your-org/governance-kit.git

# Or project-local
uv pip install git+https://github.com/your-org/governance-kit.git
```

## Usage

### Initialize a New Repository

```bash
# Creates .specify/ and applies governance overlay
governance init
```

### Apply to Existing Spec Kit Repository

```bash
# Skip Spec Kit init, just apply overlay
governance init --skip-speckit
```

### Verify Configuration

```bash
governance check
```

## How It Works

1. `governance init` runs `specify init --here` (if needed)
2. Copies governance rules to `.specify/memory/governance/`
3. Appends rules to `.specify/memory/constitution.md`
4. Spec Kit commands (`/speckit.plan`, `/speckit.analyze`, etc.) automatically enforce the rules

## Customizing Rules

Edit the files in `.specify/memory/governance/`:

- `architecture.md` - Architectural constraints
- `stack.md` - Technology stack rules
- `process.md` - Development process requirements

## Development

```bash
git clone https://github.com/your-org/governance-kit
cd governance-kit
uv sync
uv run pytest tests/ -v
```

## License

Apache-2.0
