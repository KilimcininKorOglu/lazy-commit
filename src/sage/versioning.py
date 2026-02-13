# -*- coding: utf-8 -*-
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class BumpType(Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass
class Version:
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        version_str = version_str.lstrip("v")
        pre = None
        if "-" in version_str:
            version_str, pre = version_str.split("-", 1)
        parts = version_str.split(".")
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 0,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
            prerelease=pre,
        )

    def bump(self, bump_type: BumpType, prerelease: Optional[str] = None) -> "Version":
        if bump_type == BumpType.MAJOR:
            return Version(self.major + 1, 0, 0, prerelease)
        elif bump_type == BumpType.MINOR:
            return Version(self.major, self.minor + 1, 0, prerelease)
        else:
            return Version(self.major, self.minor, self.patch + 1, prerelease)

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        return base


class VersionCalculator:
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
        except subprocess.CalledProcessError:
            return ""

    def get_latest_tag(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf8",
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def get_commits_since_tag(self, tag: Optional[str] = None) -> list[str]:
        if tag:
            range_spec = f"{tag}..HEAD"
        else:
            range_spec = "HEAD"
        output = self._run_command(["git", "log", range_spec, "--pretty=format:%s"])
        if not output:
            return []
        return [line.strip() for line in output.split("\n") if line.strip()]

    def analyze_commits(self, commits: list[str]) -> tuple[BumpType, list[dict]]:
        analysis = []
        has_breaking = False
        has_feat = False

        for commit in commits:
            bump = BumpType.PATCH
            reason = "other"

            if "BREAKING CHANGE" in commit or re.match(r"^\w+!:", commit):
                has_breaking = True
                bump = BumpType.MAJOR
                reason = "breaking change"
            elif commit.startswith("feat"):
                has_feat = True
                bump = BumpType.MINOR
                reason = "new feature"
            elif commit.startswith(("fix", "perf")):
                bump = BumpType.PATCH
                reason = "bug fix/performance"

            analysis.append({"commit": commit, "bump": bump, "reason": reason})

        if has_breaking:
            return BumpType.MAJOR, analysis
        elif has_feat:
            return BumpType.MINOR, analysis
        else:
            return BumpType.PATCH, analysis

    def update_pyproject_version(self, new_version: str) -> bool:
        pyproject_path = self.repo_path / "pyproject.toml"
        if not pyproject_path.exists():
            return False

        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = r'(version\s*=\s*["\'])[\d.]+(-[\w.]+)?(["\'])'
        new_content = re.sub(pattern, rf"\g<1>{new_version}\g<3>", content)

        if new_content == content:
            return False

        with open(pyproject_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True

    def create_tag(self, version: str) -> bool:
        tag_name = f"v{version}" if not version.startswith("v") else version
        try:
            subprocess.run(
                ["git", "tag", tag_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def run(
        self,
        bump: bool = False,
        version_type: Optional[str] = None,
        prerelease: Optional[str] = None,
        dry_run: bool = False,
    ) -> Optional[str]:
        console.print("[bold blue]Calculating version...[/bold blue]")

        latest_tag = self.get_latest_tag()
        if latest_tag:
            current_version = Version.parse(latest_tag)
            console.print(f"Current version: [cyan]{latest_tag}[/cyan]")
        else:
            current_version = Version(0, 0, 0)
            console.print("[dim]No tags found, starting from 0.0.0[/dim]")

        commits = self.get_commits_since_tag(latest_tag)
        if not commits:
            console.print("[yellow]No commits since last tag.[/yellow]")
            return None

        console.print(f"[dim]Found {len(commits)} commits since last tag[/dim]")

        if version_type:
            bump_type = BumpType(version_type.lower())
            analysis = []
        else:
            bump_type, analysis = self.analyze_commits(commits)

        new_version = current_version.bump(bump_type, prerelease)

        console.print()
        console.print("[bold]Commits since last tag:[/bold]")
        for item in analysis[:10]:
            bump_label = item["bump"].value.upper()
            console.print(f"  - {item['commit'][:60]} ([dim]{bump_label}[/dim])")
        if len(analysis) > 10:
            console.print(f"  ... and {len(analysis) - 10} more")

        console.print()
        console.print(
            f"Calculated next version: [bold green]{new_version}[/bold green]"
        )
        console.print(f"Reason: {bump_type.value} bump")

        if not bump:
            console.print("\n[dim]Run with --bump to apply this version.[/dim]")
            return str(new_version)

        if dry_run:
            console.print("\n[yellow]Dry run - no changes made.[/yellow]")
            return str(new_version)

        if self.update_pyproject_version(str(new_version)):
            console.print(f"[green]Updated pyproject.toml to {new_version}[/green]")

        if self.create_tag(str(new_version)):
            console.print(f"[green]Created tag v{new_version}[/green]")
        else:
            console.print("[red]Failed to create tag[/red]")
            return None

        console.print("[bold green]Version bump completed![/bold green]")
        return str(new_version)
