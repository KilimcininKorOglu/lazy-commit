# lazy-commit

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
- Project Configuration: Customize behavior with .lazy-commit.yaml
- History Rewrite: Rewrite old commit messages with AI
- Multi-Language: Generate commit messages in 10 different languages

## Installation

### Using uv (recommended)

```bash
uv tool install lazy-commit
```

```bash
uv tool upgrade lazy-commit
```

### From source

```bash
git clone https://github.com/QIN2DIM/lazy-commit.git
cd lazy-commit
uv sync
```

## Configuration

Set the required environment variables:

```bash
# For OpenAI API
export LAZY_COMMIT_OPENAI_BASE_URL="https://api.openai.com/v1"
export LAZY_COMMIT_OPENAI_API_KEY="your-openai-api-key"
export LAZY_COMMIT_OPENAI_MODEL_NAME="gpt-4o-mini"

# For free models via OpenRouter
export LAZY_COMMIT_OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export LAZY_COMMIT_OPENAI_API_KEY="sk-or-v1-xxx"
export LAZY_COMMIT_OPENAI_MODEL_NAME="moonshotai/kimi-k2:free"

# For Chinese users - free models via ModelScope
export LAZY_COMMIT_OPENAI_BASE_URL="https://api-inference.modelscope.cn/v1"
export LAZY_COMMIT_OPENAI_API_KEY="ms-xxx"
export LAZY_COMMIT_OPENAI_MODEL_NAME="Qwen/Qwen3-30B-A3B-Instruct-2507"

# Optional: Set maximum context size (default: 32000)
export LAZY_COMMIT_MAX_CONTEXT_SIZE=32000

# Optional: Bypass system proxy for LAN endpoints (default: false)
# Useful when accessing internal model endpoints via VPN
export LAZY_COMMIT_BYPASS_PROXY=true
```

### Environment File

You can also create a `.env` file in your project root:

**For OpenRouter (free models):**
```env
LAZY_COMMIT_OPENAI_BASE_URL=https://openrouter.ai/api/v1
LAZY_COMMIT_OPENAI_API_KEY=sk-or-v1-xxx
LAZY_COMMIT_OPENAI_MODEL_NAME=moonshotai/kimi-k2:free
```

**For Chinese users - [ModelScope](https://www.modelscope.cn/models/Qwen/Qwen3-30B-A3B-Instruct-2507) (free models):**
```env
LAZY_COMMIT_OPENAI_BASE_URL="https://api-inference.modelscope.cn/v1"
LAZY_COMMIT_OPENAI_API_KEY="ms-xxx"
LAZY_COMMIT_OPENAI_MODEL_NAME="Qwen/Qwen3-30B-A3B-Instruct-2507"
```

## Usage

### Basic Usage

Generate a commit message only (display message without applying):

```bash
commit
```

or if installed from source:

```bash
uv run commit
```

### Stage and Commit

Generate commit message, stage files, and apply commit (without push):

```bash
commit --add
```

### Auto-push After Commit

Generate commit message, stage files, apply commit, and push to remote:

```bash
commit --push
```

Note: When `--push` is enabled, `--add` is automatically enabled.

### Generate Changelog

Generate a changelog from conventional commits:

```bash
commit changelog
```

Options:
- `--from`, `-f`: Starting version/tag (default: latest tag)
- `--next-version`, `-n`: Next version name (default: "Unreleased")
- `--dry-run`: Preview without writing to file
- `--output`, `-o`: Output file path (default: CHANGELOG.md)

Examples:

```bash
# Generate changelog from latest tag
commit changelog

# Generate from specific version
commit changelog --from v0.1.0

# Set next version name
commit changelog --next-version v0.2.0

# Preview without writing
commit changelog --dry-run
```

### Semantic Versioning

Calculate and bump version based on conventional commits:

```bash
commit version
```

Options:
- `--bump`, `-b`: Apply version bump and create git tag
- `--type`, `-t`: Force version type (major/minor/patch)
- `--pre`: Pre-release label (alpha, beta, rc)
- `--dry-run`: Preview without applying

Examples:

```bash
# Show next version
commit version

# Apply version bump and create tag
commit version --bump

# Force minor version bump
commit version --bump --type minor

# Create pre-release version
commit version --bump --pre alpha
```

Version bump rules:
- Breaking changes (`!` or `BREAKING CHANGE:`) -> Major
- New features (`feat:`) -> Minor
- Bug fixes and others -> Patch

### Git Hooks

Install lazy-commit as a git hook for automatic commit message generation:

```bash
# Install hook
commit hook install

# Uninstall hook
commit hook uninstall

# Check hook status
commit hook status
```

Options:
- `--type`, `-t`: Hook type (default: prepare-commit-msg)
- `--force`, `-f`: Overwrite existing hook

### Quality Scoring

Analyze commit message quality:

```bash
commit score
```

Options:
- `-n`, `--count`: Number of commits to analyze
- `--all`: Analyze all commits
- `--json`: Output as JSON

Examples:

```bash
# Analyze last commit
commit score

# Analyze last 10 commits
commit score -n 10

# Analyze specific commit
commit score abc123

# Output as JSON
commit score --json
```

Scoring criteria (100 points):
- Type present and valid (30 points)
- Scope present (10 points)
- Title length 10-72 chars (15 points)
- Imperative mood (15 points)
- Body present (10 points)
- Breaking change marked (10 points)
- Issue reference (10 points)

### Project Configuration

Create a `.lazy-commit.yaml` file to customize behavior:

```bash
# Create config file
commit init

# Show current configuration
commit config
```

Example `.lazy-commit.yaml`:

```yaml
version: 1

format:
  # Restrict allowed types
  types: [feat, fix, docs, style, refactor, perf, test, build, ci, chore]
  
  # Define allowed scopes
  scopes: [api, ui, db, core]
  
  require_scope: false
  require_body: false
  max_title_length: 72
  require_issue_ref: false

ai:
  language: en
  # instructions: |
  #   - Custom instruction 1
  #   - Custom instruction 2

exclude:
  - "*.lock"
  - "*.ipynb"
```

Configuration loading order (later overrides earlier):
1. Default values
2. Global config: `~/.lazy-commit.yaml`
3. Project config: `.lazy-commit.yaml`

### Multi-Language Support

Generate commit messages in different languages:

```bash
# Turkish
commit --lang tr

# Japanese
commit --lang ja

# German
commit --lang de
```

Supported languages: `en`, `tr`, `ja`, `zh`, `de`, `fr`, `es`, `pt`, `ko`, `ru`

You can also set the default language in `.lazy-commit.yaml`:

```yaml
ai:
  language: tr
```

Note: Type and scope always remain in English (conventional commits standard).

### Rewrite Commit History

Rewrite old commit messages using AI:

```bash
commit rewrite
```

Options:
- `-n`, `--count`: Number of commits to rewrite
- `--from`: Rewrite from specific commit
- `--dry-run`: Preview without applying
- `-i`, `--interactive`: Confirm each commit
- `--force`, `-f`: Allow rewriting pushed commits

Examples:

```bash
# Rewrite last commit
commit rewrite

# Rewrite last 5 commits
commit rewrite -n 5

# Preview without applying
commit rewrite --dry-run

# Interactive mode
commit rewrite -n 3 -i
```

WARNING: This rewrites git history. A backup branch is created automatically.

## How It Works

1. **Repository Detection**: Automatically detects git repository root
2. **File Analysis**: Scans for modified, staged, and untracked files
3. **Smart Filtering**: Excludes files like `*.lock`, `*.ipynb` from AI analysis but includes them in commits
4. **Diff Generation**: Creates comprehensive diffs for all relevant changes
5. **Context Management**: Compresses large diffs to fit within AI model context limits
6. **AI Generation**: Uses AI to generate a structured commit message following Conventional Commits
7. **Display Message**: Always displays the generated commit message
8. **Optional Staging & Commit**: If `--add` is used, stages all changes and applies the generated commit message
9. **Optional Push**: If `--push` is used, pushes changes to remote repository after commit

## Commit Message Format

The tool generates commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Commit Types

- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions or modifications
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Maintenance tasks

## Examples

### Feature Addition
```
feat(api): add user authentication endpoint

Implements JWT-based authentication with login and logout functionality.
Includes input validation and error handling for invalid credentials.
```

### Bug Fix
```
fix(payment): correct tax calculation error

Fixed off-by-one error in tax calculation loop that was causing
incorrect tax amounts for orders with multiple items.
```

### Documentation
```
docs(README): update installation and configuration instructions

Added detailed setup guide for environment variables and
included examples for different AI providers.
```

## Requirements

- Python 3.12+
- Git repository
- OpenAI-compatible API access (OpenAI, local models, etc.)

## Dependencies

- `typer`: Command-line interface
- `openai`: OpenAI API client
- `pydantic-settings`: Configuration management
- `rich`: Beautiful terminal output
- `loguru`: Logging
- `tiktoken`: Token counting

## Development

### Setup Development Environment

```bash
git clone https://github.com/QIN2DIM/lazy-commit.git
cd lazy-commit
uv sync --group dev
```

### Code Quality

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run code quality checks
6. Submit a pull request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
