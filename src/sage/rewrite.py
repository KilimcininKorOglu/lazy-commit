# -*- coding: utf-8 -*-
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from sage.models import CommitMessage
from sage.prompts import SYSTEM_INSTRUCTIONS
from sage.settings import settings
from sage._tun import get_lan_http_client

console = Console()

REWRITE_PROMPT = """Analyze the following git diff and generate a better commit message.
The original commit message was: "{original_message}"

Git diff:
{diff}

Generate a proper conventional commit message that accurately describes these changes."""


@dataclass
class CommitInfo:
    hash: str
    message: str
    diff: str
    is_merge: bool = False
    is_pushed: bool = False
    new_message: Optional[str] = None


class CommitRewriter:
    def __init__(self):
        self.repo_path = self._find_git_root()
        base_url = settings.SAGE_OPENAI_BASE_URL
        self._client = OpenAI(
            api_key=settings.SAGE_OPENAI_API_KEY.get_secret_value(),
            base_url=base_url,
            http_client=get_lan_http_client(base_url) if base_url else None,
        )
        self._model = settings.SAGE_OPENAI_MODEL_NAME

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

    def _run_command(self, command: list[str], check: bool = True) -> str:
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=check,
                encoding="utf8",
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            if check:
                raise
            return ""

    def _check_working_tree(self) -> bool:
        status = self._run_command(["git", "status", "--porcelain"])
        if status:
            console.print(
                "[red]Working tree is not clean. Please commit or stash changes first.[/red]"
            )
            return False
        return True

    def _is_merge_commit(self, commit_hash: str) -> bool:
        parents = self._run_command(
            ["git", "rev-parse", f"{commit_hash}^@"], check=False
        )
        return len(parents.split("\n")) > 1

    def _is_pushed(self, commit_hash: str) -> bool:
        result = self._run_command(
            ["git", "branch", "-r", "--contains", commit_hash], check=False
        )
        return bool(result.strip())

    def _get_commits(
        self, count: int, from_commit: Optional[str] = None
    ) -> list[CommitInfo]:
        if from_commit:
            range_spec = f"{from_commit}^..HEAD"
        else:
            range_spec = f"-{count}"

        output = self._run_command(["git", "log", range_spec, "--pretty=format:%H|%s"])

        if not output:
            return []

        commits = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 1)
            if len(parts) != 2:
                continue

            commit_hash, message = parts
            diff = self._run_command(
                ["git", "show", commit_hash, "--format=", "--patch"]
            )

            commits.append(
                CommitInfo(
                    hash=commit_hash,
                    message=message,
                    diff=diff,
                    is_merge=self._is_merge_commit(commit_hash),
                    is_pushed=self._is_pushed(commit_hash),
                )
            )

        return commits

    def _generate_new_message(self, commit: CommitInfo) -> Optional[str]:
        prompt = REWRITE_PROMPT.format(
            original_message=commit.message,
            diff=commit.diff[:8000],
        )

        messages = [
            ChatCompletionSystemMessageParam(
                role="system", content=SYSTEM_INSTRUCTIONS
            ),
            ChatCompletionUserMessageParam(role="user", content=prompt),
        ]

        try:
            completion = self._client.chat.completions.parse(
                model=self._model,
                messages=messages,
                response_format=CommitMessage,
                temperature=0,
                timeout=50,
            )
            result = completion.choices[0].message.parsed
            return result.to_git_message() if result else None
        except Exception as e:
            console.print(f"[red]Failed to generate message: {e}[/red]")
            return None

    def _create_backup(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_branch = f"backup-rewrite-{timestamp}"
        self._run_command(["git", "branch", backup_branch])
        return backup_branch

    def _display_comparison(self, commit: CommitInfo) -> None:
        console.print(f"\n[bold]Commit:[/bold] {commit.hash[:7]}")
        console.print(Panel(commit.message, title="Original", border_style="red"))
        if commit.new_message:
            console.print(Panel(commit.new_message, title="New", border_style="green"))

    def _apply_rewrite(self, commits: list[CommitInfo]) -> bool:
        commits_to_rewrite = [c for c in commits if c.new_message and not c.is_merge]

        if not commits_to_rewrite:
            console.print("[yellow]No commits to rewrite.[/yellow]")
            return False

        oldest_commit = commits_to_rewrite[-1]

        env_script = "#!/bin/sh\ncat << 'EOF'\n"
        for c in commits_to_rewrite:
            env_script += f"{c.hash}|{c.new_message}\n"
        env_script += "EOF\n"

        try:
            for commit in reversed(commits_to_rewrite):
                (
                    self._run_command(
                        ["git", "commit", "--amend", "-m", commit.new_message]
                    )
                    if commit == commits_to_rewrite[0]
                    else None
                )

            if len(commits_to_rewrite) == 1:
                self._run_command(
                    [
                        "git",
                        "commit",
                        "--amend",
                        "-m",
                        commits_to_rewrite[0].new_message,
                    ]
                )
            else:
                console.print(
                    "[yellow]Multiple commit rewrite requires interactive rebase.[/yellow]"
                )
                console.print(
                    f"[dim]Run: git rebase -i {oldest_commit.hash}^ and change 'pick' to 'reword'[/dim]"
                )
                return False

            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Rewrite failed: {e}[/red]")
            return False

    def run(
        self,
        count: int = 1,
        from_commit: Optional[str] = None,
        dry_run: bool = False,
        interactive: bool = False,
        force: bool = False,
    ) -> None:
        console.print("[bold blue]Analyzing commits for rewrite...[/bold blue]")

        if not self._check_working_tree():
            return

        commits = self._get_commits(count, from_commit)

        if not commits:
            console.print("[yellow]No commits found.[/yellow]")
            return

        warnings = []
        for commit in commits:
            if commit.is_pushed and not force:
                warnings.append(f"Commit {commit.hash[:7]} has been pushed to remote")
            if commit.is_merge:
                warnings.append(
                    f"Commit {commit.hash[:7]} is a merge commit (will be skipped)"
                )

        if warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for w in warnings:
                console.print(f"  [yellow]![/yellow] {w}")

            if any(c.is_pushed for c in commits) and not force:
                console.print("\n[red]Use --force to rewrite pushed commits.[/red]")
                return

        backup_branch = None
        if not dry_run:
            backup_branch = self._create_backup()
            console.print(f"[dim]Created backup branch: {backup_branch}[/dim]")

        console.print(f"\n[bold]Processing {len(commits)} commit(s)...[/bold]")

        for i, commit in enumerate(commits):
            if commit.is_merge:
                console.print(f"\n[dim]Skipping merge commit {commit.hash[:7]}[/dim]")
                continue

            console.print(
                f"\n[bold]Commit {i+1}/{len(commits)}:[/bold] {commit.hash[:7]}"
            )

            with console.status("[bold blue]Generating new message..."):
                commit.new_message = self._generate_new_message(commit)

            if not commit.new_message:
                console.print(
                    "[yellow]Could not generate new message, skipping.[/yellow]"
                )
                continue

            self._display_comparison(commit)

            if interactive and not dry_run:
                choice = Prompt.ask(
                    "[A]ccept / [S]kip / [Q]uit",
                    choices=["a", "s", "q"],
                    default="a",
                )
                if choice == "q":
                    console.print("[yellow]Aborted by user.[/yellow]")
                    return
                elif choice == "s":
                    commit.new_message = None
                    continue

        if dry_run:
            console.print("\n[yellow]Dry run - no changes made.[/yellow]")
            return

        self._apply_rewrite(commits)

        console.print("\n[bold]Rewrite Summary[/bold]")
        console.print("=" * 40)
        if backup_branch:
            console.print(f"Backup branch: [cyan]{backup_branch}[/cyan]")

        rewritten = sum(1 for c in commits if c.new_message and not c.is_merge)
        skipped = sum(1 for c in commits if c.is_merge)

        console.print(f"Commits rewritten: {rewritten}")
        if skipped:
            console.print(f"Commits skipped (merge): {skipped}")

        if backup_branch:
            console.print(f"\n[dim]To undo: git reset --hard {backup_branch}[/dim]")
