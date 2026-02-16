# sage

A smart git commit message generator that uses AI to create high-quality commit messages following the Conventional Commits specification. It analyzes your git changes and automatically generates descriptive commit messages.

## Features

- AI-Powered: Uses OpenAI-compatible APIs to generate intelligent commit messages
- Conventional Commits: Follows the Conventional Commits specification format
- Smart File Analysis: Automatically analyzes changed files and generates appropriate diffs
- Intelligent Filtering: Excludes lock files and binary files from analysis while still including them in commits
- Context Compression: Automatically compresses large diffs to fit within token limits
- Auto-Push Support: Optional automatic push to remote repository after commit
- Rich UI: Beautiful command-line interface with progress bars and status indicators
- File Status Display: Shows modified, added, and deleted files with clear indicators
- Changelog Generation: Automatically generate CHANGELOG.md from conventional commits
- Semantic Versioning: Calculate and bump versions based on commit types
- Git Hooks: Install as a git hook for automatic commit message generation
- Quality Scoring: Analyze commit message quality with detailed feedback
- Project Configuration: Customize behavior with .sage.yaml
- History Rewrite: Rewrite old commit messages with AI
- Multi-Language: Generate commit messages in 10 different languages
- Statistics: Analyze commit patterns and generate reports

## Installation

### Using uv (recommended)

```bash
uv tool install sage-commit
```

```bash
uv tool upgrade sage-commit
```

### From source

```bash
git clone https://github.com/QIN2DIM/sage-commit.git
cd sage-commit
uv sync
```

## Configuration

Set the required environment variables:

```bash
# For OpenAI API
export SAGE_OPENAI_BASE_URL="https://api.openai.com/v1"
export SAGE_OPENAI_API_KEY="your-openai-api-key"
export SAGE_OPENAI_MODEL_NAME="gpt-4o-mini"

# For free models via OpenRouter
export SAGE_OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export SAGE_OPENAI_API_KEY="sk-or-v1-xxx"
export SAGE_OPENAI_MODEL_NAME="moonshotai/kimi-k2:free"

# Optional: Set maximum context size (default: 32000)
export SAGE_MAX_CONTEXT_SIZE=32000

# Optional: Bypass system proxy for LAN endpoints (default: false)
export SAGE_BYPASS_PROXY=true
```

### Environment File

You can also create a `.env` file in your project root:

```env
SAGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1
SAGE_OPENAI_API_KEY=sk-or-v1-xxx
SAGE_OPENAI_MODEL_NAME=moonshotai/kimi-k2:free
```

## Usage

### Basic Usage

Generate a commit message only (display message without applying):

```bash
sage
```

### Stage and Commit

Generate commit message, stage files, and apply commit:

```bash
sage --add
```

### Auto-push After Commit

Generate commit message, stage files, apply commit, and push to remote:

```bash
sage --push
```

### Generate Changelog

```bash
sage changelog
sage changelog --from v0.1.0
sage changelog --dry-run
```

### Semantic Versioning

```bash
sage version
sage version --bump
sage version --bump --type minor
sage version --bump --pre alpha
```

### Git Hooks

```bash
sage hook install
sage hook uninstall
sage hook status
```

### Quality Scoring

```bash
sage score
sage score -n 10
sage score --json
```

### Project Configuration

Create a `.sage.yaml` file:

```bash
sage init
sage config
```

Example `.sage.yaml`:

```yaml
version: 1

format:
  types: [feat, fix, docs, style, refactor, perf, test, build, ci, chore]
  scopes: [api, ui, db, core]
  require_scope: false
  require_body: false
  max_title_length: 72

ai:
  language: en
  # instructions: |
  #   - Custom instruction 1

exclude:
  - "*.lock"
  - "*.ipynb"
```

Configuration loading order:
1. Default values
2. Global config: `~/.sage.yaml`
3. Project config: `.sage.yaml`

### Multi-Language Support

```bash
sage --lang tr    # Turkish
sage --lang ja    # Japanese
sage --lang de    # German
```

Supported: `en`, `tr`, `ja`, `zh`, `de`, `fr`, `es`, `pt`, `ko`, `ru`

### Rewrite Commit History

```bash
sage rewrite
sage rewrite -n 5
sage rewrite --dry-run
sage rewrite -i
```

WARNING: This rewrites git history. A backup branch is created automatically.

### Commit Statistics

```bash
sage stats
sage stats --detailed --by-author
sage stats --since 2025-01-01
sage stats --json
sage stats -o report.md
```

## Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Commit Types

- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Maintenance tasks

## Requirements

- Python 3.12+
- Git repository
- OpenAI-compatible API access

## Development

```bash
git clone https://github.com/QIN2DIM/sage-commit.git
cd sage-commit
uv sync --group dev

# Format and lint
uv run black src/
uv run ruff check src/
```

## License

MIT License. See [LICENSE](LICENSE) for details.
