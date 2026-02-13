# -*- coding: utf-8 -*-
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()

VALID_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
]

IMPERATIVE_WORDS = [
    "add",
    "fix",
    "update",
    "remove",
    "delete",
    "change",
    "create",
    "implement",
    "improve",
    "refactor",
    "move",
    "rename",
    "merge",
    "release",
    "revert",
    "bump",
    "upgrade",
    "downgrade",
    "enable",
    "disable",
    "configure",
    "setup",
    "init",
    "introduce",
    "extract",
    "simplify",
    "optimize",
    "handle",
    "support",
    "allow",
    "prevent",
    "ensure",
    "validate",
    "check",
    "clean",
    "format",
    "lint",
]


@dataclass
class ScoreResult:
    commit_hash: str
    message: str
    score: int
    max_score: int = 100
    checks: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)

    @property
    def grade(self) -> str:
        if self.score >= 90:
            return "A"
        elif self.score >= 80:
            return "B"
        elif self.score >= 70:
            return "C"
        elif self.score >= 60:
            return "D"
        else:
            return "F"

    @property
    def grade_color(self) -> str:
        colors = {
            "A": "green",
            "B": "bright_green",
            "C": "yellow",
            "D": "orange1",
            "F": "red",
        }
        return colors.get(self.grade, "white")

    def to_dict(self) -> dict:
        return {
            "commit_hash": self.commit_hash,
            "message": self.message,
            "score": self.score,
            "max_score": self.max_score,
            "grade": self.grade,
            "checks": self.checks,
            "suggestions": self.suggestions,
        }


class CommitScorer:
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

    def get_commits(
        self, count: int = 1, commit_ref: Optional[str] = None
    ) -> list[tuple[str, str]]:
        if commit_ref:
            output = self._run_command(
                ["git", "log", commit_ref, "-1", "--pretty=format:%H|%s%n%b"]
            )
            if output:
                parts = output.split("|", 1)
                if len(parts) == 2:
                    return [(parts[0], parts[1])]
            return []

        output = self._run_command(
            ["git", "log", f"-{count}", "--pretty=format:%H|%s%n%b%x00"]
        )
        if not output:
            return []

        commits = []
        for entry in output.split("\x00"):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split("|", 1)
            if len(parts) == 2:
                commits.append((parts[0][:7], parts[1]))
        return commits

    def score_commit(self, commit_hash: str, message: str) -> ScoreResult:
        score = 0
        checks = []
        suggestions = []

        lines = message.strip().split("\n")
        title = lines[0] if lines else ""
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        # Type check (20 points)
        type_match = re.match(r"^(\w+)(?:\(.*?\))?!?:", title)
        if type_match:
            commit_type = type_match.group(1).lower()
            score += 20
            checks.append(("Type present", True, f"Found: {commit_type}"))

            # Valid type (10 points)
            if commit_type in VALID_TYPES:
                score += 10
                checks.append(
                    (
                        "Valid type",
                        True,
                        f"{commit_type} is a valid conventional commit type",
                    )
                )
            else:
                checks.append(
                    ("Valid type", False, f"{commit_type} is not a standard type")
                )
                suggestions.append(
                    f"Use a standard type: {', '.join(VALID_TYPES[:5])}..."
                )
        else:
            checks.append(("Type present", False, "No commit type found"))
            suggestions.append("Start with a type: feat:, fix:, docs:, etc.")

        # Scope check (10 points)
        scope_match = re.match(r"^\w+\(([^)]+)\)", title)
        if scope_match:
            score += 10
            checks.append(("Scope present", True, f"Found: {scope_match.group(1)}"))
        else:
            checks.append(("Scope present", False, "No scope specified"))
            suggestions.append("Add a scope: feat(api): or fix(auth):")

        # Title length (15 points)
        title_after_type = re.sub(r"^\w+(?:\(.*?\))?!?:\s*", "", title)
        title_len = len(title_after_type)
        if 10 <= title_len <= 72:
            score += 15
            checks.append(
                ("Title length", True, f"{title_len} chars (10-72 recommended)")
            )
        elif title_len < 10:
            checks.append(("Title length", False, f"Too short: {title_len} chars"))
            suggestions.append("Make the title more descriptive (at least 10 chars)")
        else:
            checks.append(("Title length", False, f"Too long: {title_len} chars"))
            suggestions.append("Shorten the title to 72 chars or less")

        # Imperative mood (15 points)
        first_word = (
            title_after_type.split()[0].lower() if title_after_type.split() else ""
        )
        if first_word in IMPERATIVE_WORDS:
            score += 15
            checks.append(("Imperative mood", True, f"Starts with '{first_word}'"))
        elif first_word.endswith(("ed", "ing", "s")):
            checks.append(
                ("Imperative mood", False, f"'{first_word}' is not imperative")
            )
            suggestions.append(
                "Use imperative mood: 'add' not 'added', 'fix' not 'fixed'"
            )
        else:
            score += 10  # Partial credit for unknown words
            checks.append(("Imperative mood", None, f"Could not verify '{first_word}'"))

        # Body present (10 points)
        if body:
            score += 10
            checks.append(("Body present", True, f"{len(body)} chars"))
        else:
            checks.append(("Body present", False, "No description body"))
            suggestions.append("Add a body explaining why the change was made")

        # Breaking change (10 points)
        has_breaking = "!" in title.split(":")[0] if ":" in title else False
        has_breaking = has_breaking or "BREAKING CHANGE" in message
        if has_breaking:
            score += 10
            checks.append(("Breaking change marked", True, "Breaking change indicated"))
        else:
            checks.append(("Breaking change marked", None, "Not applicable"))

        # Issue reference (10 points)
        issue_pattern = r"(#\d+|[A-Z]+-\d+)"
        if re.search(issue_pattern, message):
            score += 10
            checks.append(("Issue reference", True, "Found issue reference"))
        else:
            checks.append(("Issue reference", False, "No issue reference"))
            suggestions.append("Reference related issues: #123 or JIRA-456")

        return ScoreResult(
            commit_hash=commit_hash,
            message=title,
            score=score,
            checks=checks,
            suggestions=suggestions,
        )

    def display_result(self, result: ScoreResult) -> None:
        console.print()
        console.print(f"[bold]Commit:[/bold] {result.commit_hash}")
        console.print(f"[bold]Message:[/bold] {result.message}")
        console.print()
        console.print(
            f"[bold]Score:[/bold] [{result.grade_color}]{result.score}/{result.max_score} ({result.grade})[/{result.grade_color}]"
        )
        console.print()

        for check_name, passed, detail in result.checks:
            if passed is True:
                icon = "[green]✓[/green]"
            elif passed is False:
                icon = "[red]✗[/red]"
            else:
                icon = "[dim]-[/dim]"
            console.print(f"  {icon} {check_name}: [dim]{detail}[/dim]")

        if result.suggestions:
            console.print()
            console.print("[bold]Suggestions:[/bold]")
            for suggestion in result.suggestions:
                console.print(f"  [yellow]•[/yellow] {suggestion}")

    def display_summary(self, results: list[ScoreResult]) -> None:
        if not results:
            console.print("[yellow]No commits to analyze.[/yellow]")
            return

        total_score = sum(r.score for r in results)
        avg_score = total_score // len(results)

        grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for r in results:
            grade_counts[r.grade] += 1

        console.print()
        console.print("[bold]Commit Quality Report[/bold]")
        console.print("=" * 40)
        console.print()
        console.print(f"Total commits analyzed: {len(results)}")
        console.print(f"Average score: {avg_score}/100")
        console.print()

        console.print("[bold]Grade Distribution:[/bold]")
        for grade in ["A", "B", "C", "D", "F"]:
            count = grade_counts[grade]
            pct = (count * 100) // len(results) if results else 0
            bar = "█" * (count * 2)
            console.print(f"  {grade}: {bar} {count} ({pct}%)")

    def run(
        self,
        commit_ref: Optional[str] = None,
        count: int = 1,
        all_commits: bool = False,
        json_output: bool = False,
    ) -> None:
        console.print("[bold blue]Analyzing commit quality...[/bold blue]")

        if all_commits:
            count = 1000

        commits = self.get_commits(count=count, commit_ref=commit_ref)

        if not commits:
            console.print("[yellow]No commits found.[/yellow]")
            return

        results = [self.score_commit(h, m) for h, m in commits]

        if json_output:
            output = [r.to_dict() for r in results]
            print(json.dumps(output, indent=2))
            return

        if len(results) == 1:
            self.display_result(results[0])
        else:
            self.display_summary(results)
            console.print()
            table = Table(title="Commit Scores")
            table.add_column("Hash", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Grade")
            table.add_column("Message")

            for r in results[:20]:
                table.add_row(
                    r.commit_hash,
                    f"{r.score}",
                    f"[{r.grade_color}]{r.grade}[/{r.grade_color}]",
                    r.message[:50] + "..." if len(r.message) > 50 else r.message,
                )

            if len(results) > 20:
                table.add_row("...", "...", "...", f"... and {len(results) - 20} more")

            console.print(table)
