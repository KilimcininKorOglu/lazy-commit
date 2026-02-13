from typing import Optional

import typer

from sage.changelog import ChangelogGenerator
from sage.config import init_config, show_config
from sage.git_commit_generator import GitCommitGenerator
from sage.hooks import HookManager
from sage.rewrite import CommitRewriter
from sage.scoring import CommitScorer
from sage.statistics import StatisticsAnalyzer
from sage.versioning import VersionCalculator


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
      sage         Generate message only (copy to clipboard)
      sage --add   Stage and commit changes
      sage --push  Stage, commit and push changes
      sage --lang tr  Generate in Turkish
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
    """Install sage as a git hook."""
    manager = HookManager()
    manager.install(hook_type=hook_type, force=force)


@hook_app.command("uninstall")
def hook_uninstall(
    hook_type: str = typer.Option(
        "prepare-commit-msg", "--type", "-t", help="Hook type to uninstall"
    ),
):
    """Remove sage git hook."""
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
      sage changelog                    Generate changelog from latest tag
      sage changelog --from v0.1.0      Generate from specific version
      sage changelog --next-version v0.2.0  Set next version name
      sage changelog --dry-run          Preview without writing
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
      sage version                  Show next version
      sage version --bump           Apply version bump and create tag
      sage version --bump --type minor  Force minor version bump
      sage version --bump --pre alpha   Create pre-release version
      sage version --bump --dry-run     Preview without applying
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
      sage score              Analyze last commit
      sage score -n 10        Analyze last 10 commits
      sage score --all        Analyze all commits
      sage score abc123       Analyze specific commit
      sage score --json       Output as JSON
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
    Create a .sage.yaml configuration file.

    \b
    Usage:
      sage init           Create config file
      sage init --force   Overwrite existing config
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
      sage config         Show merged configuration
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
      sage rewrite              Rewrite last commit
      sage rewrite -n 5         Rewrite last 5 commits
      sage rewrite --dry-run    Preview without applying
      sage rewrite -i           Interactive mode (confirm each)

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
      sage stats                  Basic statistics
      sage stats --detailed       Detailed report
      sage stats --by-author      Contributor breakdown
      sage stats --since 2025-01-01  Filter by date
      sage stats --json           JSON output
      sage stats -o report.md     Save as markdown
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
