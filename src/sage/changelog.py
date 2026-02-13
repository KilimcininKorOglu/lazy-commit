# -*- coding: utf-8 -*-
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

COMMIT_TYPE_SECTIONS = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "style": "Styles",
    "refactor": "Refactoring",
    "perf": "Performance",
    "test": "Tests",
    "build": "Build",
    "ci": "CI/CD",
    "chore": "Chores",
    "revert": "Reverts",
}


@dataclass
class ParsedCommit:
    hash: str
    type: str
    scope: Optional[str]
    title: str
    body: Optional[str] = None
    is_breaking: bool = False


@dataclass
class ChangelogVersion:
    version: str
    date: str
    commits: list[ParsedCommit] = field(default_factory=list)


class ChangelogGenerator:
    def __init__(self):
        self.repo_path = self._find_git_root()

    @staticmethod
    def _find_git_root() -> Path:
        try:
            git_root_str = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                text=True,
                stderr=subprocess.PIPE,
                cwd=Path.cwd(),
            ).strip()
            return Path(git_root_str)
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(
                "[red]Fatal: Not a git repository (or any of the parent directories).[/red]"
            )
            raise ValueError("This script must be run from within a Git repository.")

    def _run_command(self, command: list[str]) -> str:
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf8",
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            console.print(
                f"[red]Command '{' '.join(command)}' failed: {e.stderr}[/red]"
            )
            raise

    def get_tags(self) -> list[str]:
        try:
            output = self._run_command(["git", "tag", "--list", "--sort=-v:refname"])
            return [tag.strip() for tag in output.split("\n") if tag.strip()]
        except subprocess.CalledProcessError:
            return []

    def get_commits(
        self, from_ref: Optional[str] = None, to_ref: str = "HEAD"
    ) -> list[str]:
        if from_ref:
            range_spec = f"{from_ref}..{to_ref}"
        else:
            range_spec = to_ref

        try:
            output = self._run_command(
                ["git", "log", range_spec, "--pretty=format:%H|%s|%b%x00"]
            )
            if not output:
                return []
            return [c.strip() for c in output.split("\x00") if c.strip()]
        except subprocess.CalledProcessError:
            return []

    def parse_commit(self, raw_commit: str) -> Optional[ParsedCommit]:
        parts = raw_commit.split("|", 2)
        if len(parts) < 2:
            return None

        commit_hash = parts[0]
        subject = parts[1]
        body = parts[2] if len(parts) > 2 else None

        pattern = r"^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$"
        match = re.match(pattern, subject)

        if not match:
            return None

        commit_type = match.group(1).lower()
        scope = match.group(2)
        is_breaking = match.group(3) == "!"
        title = match.group(4)

        if body and "BREAKING CHANGE:" in body:
            is_breaking = True

        return ParsedCommit(
            hash=commit_hash[:7],
            type=commit_type,
            scope=scope,
            title=title,
            body=body,
            is_breaking=is_breaking,
        )

    def group_commits(
        self, commits: list[ParsedCommit]
    ) -> tuple[list[ParsedCommit], dict[str, list[ParsedCommit]]]:
        breaking_changes: list[ParsedCommit] = []
        grouped: dict[str, list[ParsedCommit]] = {}

        for commit in commits:
            if commit.is_breaking:
                breaking_changes.append(commit)

            if commit.type not in grouped:
                grouped[commit.type] = []
            grouped[commit.type].append(commit)

        return breaking_changes, grouped

    def generate_markdown(
        self,
        version: str,
        commits: list[ParsedCommit],
        date: Optional[str] = None,
    ) -> str:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        breaking_changes, grouped = self.group_commits(commits)

        lines = [f"## [{version}] - {date}", ""]

        if breaking_changes:
            lines.append("### BREAKING CHANGES")
            for commit in breaking_changes:
                scope_str = f"**{commit.scope}**: " if commit.scope else ""
                lines.append(f"- {scope_str}{commit.title}")
            lines.append("")

        for commit_type, section_name in COMMIT_TYPE_SECTIONS.items():
            if commit_type in grouped:
                lines.append(f"### {section_name}")
                for commit in grouped[commit_type]:
                    scope_str = f"**{commit.scope}**: " if commit.scope else ""
                    lines.append(f"- {scope_str}{commit.title}")
                lines.append("")

        return "\n".join(lines)

    def run(
        self,
        from_version: Optional[str] = None,
        next_version: Optional[str] = None,
        dry_run: bool = False,
        output: str = "CHANGELOG.md",
    ) -> str:
        console.print("[bold blue]Generating changelog...[/bold blue]")

        tags = self.get_tags()

        if from_version is None and tags:
            from_version = tags[0]
            console.print(
                f"[dim]Using latest tag as starting point: {from_version}[/dim]"
            )

        if next_version is None:
            next_version = "Unreleased"

        raw_commits = self.get_commits(from_ref=from_version)

        if not raw_commits:
            console.print("[yellow]No commits found in the specified range.[/yellow]")
            return ""

        console.print(f"[dim]Found {len(raw_commits)} commits[/dim]")

        parsed_commits = []
        for raw in raw_commits:
            parsed = self.parse_commit(raw)
            if parsed:
                parsed_commits.append(parsed)

        if not parsed_commits:
            console.print(
                "[yellow]No conventional commits found. Make sure commits follow the format: type(scope): title[/yellow]"
            )
            return ""

        console.print(f"[dim]Parsed {len(parsed_commits)} conventional commits[/dim]")

        changelog_content = self.generate_markdown(next_version, parsed_commits)

        if dry_run:
            console.print("\n[bold]Generated Changelog:[/bold]\n")
            console.print(changelog_content)
        else:
            output_path = self.repo_path / output
            existing_content = ""

            if output_path.exists():
                with open(output_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()

            if existing_content.startswith("# Changelog"):
                header_end = existing_content.find("\n\n")
                if header_end != -1:
                    new_content = (
                        existing_content[: header_end + 2]
                        + changelog_content
                        + "\n"
                        + existing_content[header_end + 2 :]
                    )
                else:
                    new_content = existing_content + "\n\n" + changelog_content
            else:
                new_content = "# Changelog\n\n" + changelog_content
                if existing_content:
                    new_content += "\n" + existing_content

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            console.print(f"[green]Changelog written to {output}[/green]")

        console.print("[bold green]Changelog generation completed![/bold green]")
        return changelog_content
