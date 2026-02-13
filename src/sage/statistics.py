# -*- coding: utf-8 -*-
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()

CONVENTIONAL_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?:\s*.+"
)


@dataclass
class CommitStats:
    total_commits: int = 0
    date_range: tuple[str, str] = ("", "")
    type_distribution: dict[str, int] = field(default_factory=dict)
    scope_distribution: dict[str, int] = field(default_factory=dict)
    commits_per_weekday: dict[str, int] = field(default_factory=dict)
    commits_per_month: dict[str, int] = field(default_factory=dict)
    avg_title_length: float = 0.0
    commits_with_body: int = 0
    commits_with_breaking_change: int = 0
    conventional_commits: int = 0
    by_author: dict[str, dict] = field(default_factory=dict)


class StatisticsAnalyzer:
    def __init__(self):
        self.repo_path = self._find_git_root()

    @staticmethod
    def _find_git_root() -> Path:
        try:
            result = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                text=True,
                stderr=subprocess.PIPE,
            ).strip()
            return Path(result)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return Path.cwd()

    def _run_command(self, command: list[str]) -> str:
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def _get_commits(
        self, since: Optional[str] = None, until: Optional[str] = None
    ) -> list[dict]:
        cmd = ["git", "log", "--format=%H|%an|%ad|%s|%b%x00", "--date=iso"]

        if since:
            cmd.append(f"--since={since}")
        if until:
            cmd.append(f"--until={until}")

        output = self._run_command(cmd)
        if not output:
            return []

        commits = []
        for entry in output.split("\x00"):
            entry = entry.strip()
            if not entry:
                continue

            parts = entry.split("|", 4)
            if len(parts) < 4:
                continue

            commit_hash, author, date_str, subject = parts[:4]
            body = parts[4] if len(parts) > 4 else ""

            commits.append(
                {
                    "hash": commit_hash,
                    "author": author,
                    "date": date_str,
                    "subject": subject,
                    "body": body.strip(),
                }
            )

        return commits

    def _parse_commit_type(self, subject: str) -> Optional[str]:
        match = re.match(r"^(\w+)(\(.+\))?!?:", subject)
        if match:
            return match.group(1).lower()
        return None

    def _parse_scope(self, subject: str) -> Optional[str]:
        match = re.match(r"^\w+\(([^)]+)\)", subject)
        if match:
            return match.group(1)
        return None

    def _is_conventional(self, subject: str) -> bool:
        return bool(CONVENTIONAL_PATTERN.match(subject))

    def _has_breaking_change(self, subject: str, body: str) -> bool:
        if "!" in subject.split(":")[0]:
            return True
        if "BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body:
            return True
        return False

    def analyze(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        by_author: bool = False,
    ) -> CommitStats:
        commits = self._get_commits(since, until)

        if not commits:
            return CommitStats()

        stats = CommitStats()
        stats.total_commits = len(commits)

        dates = [c["date"][:10] for c in commits]
        stats.date_range = (min(dates), max(dates))

        type_counter: Counter = Counter()
        scope_counter: Counter = Counter()
        weekday_counter: Counter = Counter()
        month_counter: Counter = Counter()
        author_stats: dict[str, dict] = {}

        total_title_length = 0

        weekdays = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        for commit in commits:
            subject = commit["subject"]
            body = commit["body"]
            author = commit["author"]

            commit_type = self._parse_commit_type(subject)
            if commit_type:
                type_counter[commit_type] += 1

            scope = self._parse_scope(subject)
            if scope:
                scope_counter[scope] += 1

            try:
                dt = datetime.fromisoformat(commit["date"][:19])
                weekday_counter[weekdays[dt.weekday()]] += 1
                month_counter[dt.strftime("%Y-%m")] += 1
            except ValueError:
                pass

            total_title_length += len(subject)

            if body:
                stats.commits_with_body += 1

            if self._has_breaking_change(subject, body):
                stats.commits_with_breaking_change += 1

            if self._is_conventional(subject):
                stats.conventional_commits += 1

            if by_author:
                if author not in author_stats:
                    author_stats[author] = {"commits": 0, "types": Counter()}
                author_stats[author]["commits"] += 1
                if commit_type:
                    author_stats[author]["types"][commit_type] += 1

        stats.type_distribution = dict(type_counter.most_common())
        stats.scope_distribution = dict(scope_counter.most_common(10))
        stats.commits_per_weekday = dict(weekday_counter)
        stats.commits_per_month = dict(sorted(month_counter.items()))
        stats.avg_title_length = total_title_length / len(commits) if commits else 0

        if by_author:
            stats.by_author = {
                author: {
                    "commits": data["commits"],
                    "top_type": (
                        data["types"].most_common(1)[0][0] if data["types"] else None
                    ),
                }
                for author, data in sorted(
                    author_stats.items(), key=lambda x: x[1]["commits"], reverse=True
                )
            }

        return stats

    def _create_bar(self, value: int, max_value: int, width: int = 20) -> str:
        if max_value == 0:
            return ""
        bar_length = int((value / max_value) * width)
        return "█" * bar_length

    def _print_stats(self, stats: CommitStats, detailed: bool = False) -> None:
        console.print("\n[bold blue]Commit Statistics[/bold blue]")
        console.print("=" * 40)

        console.print(f"\nRepository: [cyan]{self.repo_path.name}[/cyan]")
        if stats.date_range[0]:
            console.print(f"Period: {stats.date_range[0]} to {stats.date_range[1]}")
        console.print(f"Total Commits: [bold]{stats.total_commits}[/bold]")

        if stats.total_commits == 0:
            console.print("\n[yellow]No commits found.[/yellow]")
            return

        conv_ratio = (stats.conventional_commits / stats.total_commits) * 100
        console.print(f"Conventional Commits: [green]{conv_ratio:.0f}%[/green]")

        if stats.type_distribution:
            console.print("\n[bold]Type Distribution[/bold]")
            console.print("-" * 30)
            max_count = max(stats.type_distribution.values())
            for commit_type, count in stats.type_distribution.items():
                pct = (count / stats.total_commits) * 100
                bar = self._create_bar(count, max_count)
                console.print(f"{commit_type:10} {bar} {count} ({pct:.0f}%)")

        if stats.scope_distribution:
            console.print("\n[bold]Top Scopes[/bold]")
            console.print("-" * 30)
            max_count = max(stats.scope_distribution.values())
            for scope, count in list(stats.scope_distribution.items())[:5]:
                bar = self._create_bar(count, max_count, 15)
                console.print(f"{scope:12} {bar} {count}")

        console.print("\n[bold]Quality Metrics[/bold]")
        console.print("-" * 30)
        body_pct = (stats.commits_with_body / stats.total_commits) * 100
        console.print(f"With Body: {body_pct:.0f}%")
        console.print(f"Breaking Changes: {stats.commits_with_breaking_change}")
        console.print(f"Avg Title Length: {stats.avg_title_length:.0f} chars")

        if detailed and stats.commits_per_weekday:
            console.print("\n[bold]Activity by Weekday[/bold]")
            console.print("-" * 30)
            max_count = (
                max(stats.commits_per_weekday.values())
                if stats.commits_per_weekday
                else 1
            )
            for day in [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]:
                count = stats.commits_per_weekday.get(day, 0)
                bar = self._create_bar(count, max_count, 15)
                console.print(f"{day:10} {bar} {count}")

        if stats.by_author:
            console.print("\n[bold]Contributors[/bold]")
            table = Table()
            table.add_column("Author", style="cyan")
            table.add_column("Commits", justify="right")
            table.add_column("Top Type")

            for author, data in list(stats.by_author.items())[:10]:
                table.add_row(
                    author[:20],
                    str(data["commits"]),
                    data["top_type"] or "-",
                )
            console.print(table)

    def _to_json(self, stats: CommitStats) -> str:
        return json.dumps(
            {
                "repository": self.repo_path.name,
                "period": {"from": stats.date_range[0], "to": stats.date_range[1]},
                "total_commits": stats.total_commits,
                "conventional_ratio": (
                    stats.conventional_commits / stats.total_commits
                    if stats.total_commits
                    else 0
                ),
                "type_distribution": stats.type_distribution,
                "scope_distribution": stats.scope_distribution,
                "quality": {
                    "with_body_ratio": (
                        stats.commits_with_body / stats.total_commits
                        if stats.total_commits
                        else 0
                    ),
                    "breaking_changes": stats.commits_with_breaking_change,
                    "avg_title_length": round(stats.avg_title_length, 1),
                },
                "by_author": stats.by_author if stats.by_author else None,
            },
            indent=2,
        )

    def _to_markdown(self, stats: CommitStats) -> str:
        lines = [
            "# Commit Statistics Report",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d')}",
            f"Repository: {self.repo_path.name}",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Commits | {stats.total_commits} |",
            (
                f"| Conventional Commits | {stats.conventional_commits / stats.total_commits * 100:.0f}% |"
                if stats.total_commits
                else ""
            ),
            (
                f"| With Body | {stats.commits_with_body / stats.total_commits * 100:.0f}% |"
                if stats.total_commits
                else ""
            ),
            f"| Avg Title Length | {stats.avg_title_length:.0f} chars |",
            "",
        ]

        if stats.type_distribution:
            lines.extend(
                [
                    "## Type Distribution",
                    "",
                    "| Type | Count | Percentage |",
                    "|------|-------|------------|",
                ]
            )
            for commit_type, count in stats.type_distribution.items():
                pct = (count / stats.total_commits) * 100 if stats.total_commits else 0
                lines.append(f"| {commit_type} | {count} | {pct:.0f}% |")
            lines.append("")

        if stats.scope_distribution:
            lines.extend(
                [
                    "## Top Scopes",
                    "",
                    "| Scope | Count |",
                    "|-------|-------|",
                ]
            )
            for scope, count in list(stats.scope_distribution.items())[:10]:
                lines.append(f"| {scope} | {count} |")
            lines.append("")

        return "\n".join(lines)

    def run(
        self,
        detailed: bool = False,
        since: Optional[str] = None,
        until: Optional[str] = None,
        by_author: bool = False,
        json_output: bool = False,
        output: Optional[str] = None,
    ) -> None:
        with console.status("[bold blue]Analyzing commits..."):
            stats = self.analyze(since=since, until=until, by_author=by_author)

        if json_output:
            print(self._to_json(stats))
            return

        if output:
            markdown = self._to_markdown(stats)
            output_path = Path(output)
            output_path.write_text(markdown, encoding="utf-8")
            console.print(f"[green]Report saved to {output}[/green]")
            return

        self._print_stats(stats, detailed=detailed)
