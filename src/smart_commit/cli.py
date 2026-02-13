from typing import Optional

import typer

from smart_commit.changelog import ChangelogGenerator
from smart_commit.config import init_config, show_config
from smart_commit.git_commit_generator import GitCommitGenerator
from smart_commit.hooks import HookManager
from smart_commit.rewrite import CommitRewriter
from smart_commit.scoring import CommitScorer
from smart_commit.statistics import StatisticsAnalyzer
from smart_commit.versioning import VersionCalculator


app = typer.Typer()
hook_app = typer.Typer(help="Manage git hooks")
app.add_typer(hook_app, name="hook")


@app.command()
def main(
    push: bool = typer.Option(False, "--push", "-p", help="Auto-push after commit"),
    add: bool = typer.Option(False, "--add", "-a", help="Stage and commit changes"),
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        "-l",
        help="Language for commit message (en, tr, ja, zh, de, fr, es, pt, ko, ru)",
    ),
    hook_mode: bool = typer.Option(
        False, "--hook-mode", hidden=True, help="Output message only for git hook"
    ),
):
    """
    Generate smart git commit messages with AI.

    \b
    Usage modes:
      commit         Generate message only (copy to clipboard)
      commit --add   Stage and commit changes
      commit --push  Stage, commit and push changes
      commit --lang tr  Generate in Turkish
    """
    if push:
        add = True
    generator = GitCommitGenerator(
        auto_push=push, auto_add=add, hook_mode=hook_mode, language=lang
    )
    generator.run()


@hook_app.command("install")
def hook_install(
    hook_type: str = typer.Option(
        "prepare-commit-msg", "--type", "-t", help="Hook type to install"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing hook"),
):
    """Install lazy-commit as a git hook."""
    manager = HookManager()
    manager.install(hook_type=hook_type, force=force)


@hook_app.command("uninstall")
def hook_uninstall(
    hook_type: str = typer.Option(
        "prepare-commit-msg", "--type", "-t", help="Hook type to uninstall"
    ),
):
    """Remove lazy-commit git hook."""
    manager = HookManager()
    manager.uninstall(hook_type=hook_type)


@hook_app.command("status")
def hook_status(
    hook_type: str = typer.Option(
        "prepare-commit-msg", "--type", "-t", help="Hook type to check"
    ),
):
    """Check git hook installation status."""
    manager = HookManager()
    manager.status(hook_type=hook_type)


@app.command()
def changelog(
    from_version: Optional[str] = typer.Option(
        None, "--from", "-f", help="Starting version/tag"
    ),
    next_version: Optional[str] = typer.Option(
        None, "--next-version", "-n", help="Next version name"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Only display, don't write to file"
    ),
    output: str = typer.Option(
        "CHANGELOG.md", "--output", "-o", help="Output file path"
    ),
):
    """
    Generate changelog from conventional commits.

    \b
    Usage:
      commit changelog                    Generate changelog from latest tag
      commit changelog --from v0.1.0      Generate from specific version
      commit changelog --next-version v0.2.0  Set next version name
      commit changelog --dry-run          Preview without writing
    """
    generator = ChangelogGenerator()
    generator.run(
        from_version=from_version,
        next_version=next_version,
        dry_run=dry_run,
        output=output,
    )


@app.command()
def version(
    bump: bool = typer.Option(False, "--bump", "-b", help="Apply version bump"),
    version_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Force version type: major/minor/patch"
    ),
    pre: Optional[str] = typer.Option(
        None, "--pre", help="Pre-release label (alpha, beta, rc)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show changes without applying"
    ),
):
    """
    Calculate and bump semantic version based on commits.

    \b
    Usage:
      commit version                  Show next version
      commit version --bump           Apply version bump and create tag
      commit version --bump --type minor  Force minor version bump
      commit version --bump --pre alpha   Create pre-release version
      commit version --bump --dry-run     Preview without applying
    """
    calculator = VersionCalculator()
    calculator.run(
        bump=bump,
        version_type=version_type,
        prerelease=pre,
        dry_run=dry_run,
    )


@app.command()
def score(
    commit_ref: Optional[str] = typer.Argument(
        None, help="Commit hash or ref to analyze"
    ),
    count: int = typer.Option(1, "-n", "--count", help="Number of commits to analyze"),
    all_commits: bool = typer.Option(False, "--all", help="Analyze all commits"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze commit message quality and provide a score.

    \b
    Usage:
      commit score              Analyze last commit
      commit score -n 10        Analyze last 10 commits
      commit score --all        Analyze all commits
      commit score abc123       Analyze specific commit
      commit score --json       Output as JSON
    """
    scorer = CommitScorer()
    scorer.run(
        commit_ref=commit_ref,
        count=count,
        all_commits=all_commits,
        json_output=json_output,
    )


@app.command("init")
def init_command(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing config"
    ),
):
    """
    Create a .lazy-commit.yaml configuration file.

    \b
    Usage:
      commit init           Create config file
      commit init --force   Overwrite existing config
    """
    init_config(force=force)


@app.command("config")
def config_command(
    show: bool = typer.Option(True, "--show", help="Show current configuration"),
):
    """
    Show current configuration.

    \b
    Usage:
      commit config         Show merged configuration
    """
    if show:
        show_config()


@app.command()
def rewrite(
    count: int = typer.Option(1, "-n", "--count", help="Number of commits to rewrite"),
    from_commit: Optional[str] = typer.Option(
        None, "--from", help="Rewrite from this commit"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without applying"),
    interactive: bool = typer.Option(
        False, "-i", "--interactive", help="Confirm each commit"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Allow rewriting pushed commits"
    ),
):
    """
    Rewrite commit messages using AI.

    \b
    Usage:
      commit rewrite              Rewrite last commit
      commit rewrite -n 5         Rewrite last 5 commits
      commit rewrite --dry-run    Preview without applying
      commit rewrite -i           Interactive mode (confirm each)

    WARNING: This rewrites git history. Use with caution!
    """
    rewriter = CommitRewriter()
    rewriter.run(
        count=count,
        from_commit=from_commit,
        dry_run=dry_run,
        interactive=interactive,
        force=force,
    )


@app.command()
def stats(
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed report"
    ),
    since: Optional[str] = typer.Option(
        None, "--since", help="Start date (YYYY-MM-DD)"
    ),
    until: Optional[str] = typer.Option(None, "--until", help="End date (YYYY-MM-DD)"),
    by_author: bool = typer.Option(False, "--by-author", help="Show contributor stats"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Save report to file"
    ),
):
    """
    Show commit statistics and analysis.

    \b
    Usage:
      commit stats                  Basic statistics
      commit stats --detailed       Detailed report
      commit stats --by-author      Contributor breakdown
      commit stats --since 2025-01-01  Filter by date
      commit stats --json           JSON output
      commit stats -o report.md     Save as markdown
    """
    analyzer = StatisticsAnalyzer()
    analyzer.run(
        detailed=detailed,
        since=since,
        until=until,
        by_author=by_author,
        json_output=json_output,
        output=output,
    )


if __name__ == "__main__":
    app()
