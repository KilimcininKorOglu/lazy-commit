from typing import Optional

import typer

from smart_commit.changelog import ChangelogGenerator
from smart_commit.git_commit_generator import GitCommitGenerator
from smart_commit.versioning import VersionCalculator


app = typer.Typer()


@app.command()
def main(
    push: bool = typer.Option(False, "--push", "-p", help="Auto-push after commit"),
    add: bool = typer.Option(False, "--add", "-a", help="Stage and commit changes"),
):
    """
    Generate smart git commit messages with AI.

    \b
    Usage modes:
      commit         Generate message only (copy to clipboard)
      commit --add   Stage and commit changes
      commit --push  Stage, commit and push changes
    """
    if push:
        add = True
    generator = GitCommitGenerator(auto_push=push, auto_add=add)
    generator.run()


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


if __name__ == "__main__":
    app()
