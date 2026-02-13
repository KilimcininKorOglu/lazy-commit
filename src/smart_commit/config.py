# -*- coding: utf-8 -*-
import subprocess
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from rich.console import Console
from rich.syntax import Syntax

console = Console()

CONFIG_FILENAME = ".lazy-commit.yaml"
GLOBAL_CONFIG_PATH = Path.home() / CONFIG_FILENAME

DEFAULT_TEMPLATE = """# lazy-commit configuration
# Documentation: https://github.com/QIN2DIM/lazy-commit

version: 1

format:
  # Uncomment to restrict allowed types
  # types: [feat, fix, docs, style, refactor, perf, test, build, ci, chore]
  
  # Uncomment to define allowed scopes
  # scopes: [api, ui, db, core]
  
  require_scope: false
  require_body: false
  max_title_length: 72
  require_issue_ref: false
  # issue_pattern: "(JIRA-\\d+|#\\d+)"

ai:
  language: en
  # instructions: |
  #   - Custom instruction 1
  #   - Custom instruction 2

exclude:
  - "*.lock"
  - "*.ipynb"
"""


class FormatConfig(BaseModel):
    types: Optional[list[str]] = None
    scopes: Optional[list[str]] = None
    require_scope: bool = False
    require_body: bool = False
    max_title_length: int = 72
    require_issue_ref: bool = False
    issue_pattern: str = r"(#\d+|[A-Z]+-\d+)"


class AIConfig(BaseModel):
    language: str = "en"
    instructions: Optional[str] = None


class LazyCommitConfig(BaseModel):
    version: int = 1
    format: FormatConfig = FormatConfig()
    ai: AIConfig = AIConfig()
    exclude: list[str] = ["*.lock", "*.ipynb"]


def find_git_root() -> Path:
    try:
        git_root_str = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.PIPE,
            cwd=Path.cwd(),
        ).strip()
        return Path(git_root_str)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def load_config() -> LazyCommitConfig:
    config = LazyCommitConfig()

    if GLOBAL_CONFIG_PATH.exists():
        try:
            with open(GLOBAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                global_data = yaml.safe_load(f) or {}
            config = _merge_config(config, global_data)
        except Exception:
            pass

    project_config_path = find_git_root() / CONFIG_FILENAME
    if project_config_path.exists():
        try:
            with open(project_config_path, "r", encoding="utf-8") as f:
                project_data = yaml.safe_load(f) or {}
            config = _merge_config(config, project_data)
        except Exception:
            pass

    return config


def _merge_config(base: LazyCommitConfig, data: dict) -> LazyCommitConfig:
    if "format" in data:
        format_data = data["format"]
        base.format = FormatConfig(
            types=format_data.get("types", base.format.types),
            scopes=format_data.get("scopes", base.format.scopes),
            require_scope=format_data.get("require_scope", base.format.require_scope),
            require_body=format_data.get("require_body", base.format.require_body),
            max_title_length=format_data.get(
                "max_title_length", base.format.max_title_length
            ),
            require_issue_ref=format_data.get(
                "require_issue_ref", base.format.require_issue_ref
            ),
            issue_pattern=format_data.get("issue_pattern", base.format.issue_pattern),
        )

    if "ai" in data:
        ai_data = data["ai"]
        base.ai = AIConfig(
            language=ai_data.get("language", base.ai.language),
            instructions=ai_data.get("instructions", base.ai.instructions),
        )

    if "exclude" in data:
        base.exclude = data["exclude"]

    return base


def init_config(force: bool = False) -> bool:
    config_path = find_git_root() / CONFIG_FILENAME

    if config_path.exists() and not force:
        console.print(f"[yellow]Config file already exists at {config_path}[/yellow]")
        console.print("[dim]Use --force to overwrite[/dim]")
        return False

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_TEMPLATE)

    console.print(f"[green]Created config file at {config_path}[/green]")
    return True


def show_config() -> None:
    config = load_config()

    console.print("[bold]Current Configuration:[/bold]\n")

    global_exists = GLOBAL_CONFIG_PATH.exists()
    project_path = find_git_root() / CONFIG_FILENAME
    project_exists = project_path.exists()

    console.print(
        f"Global config ({GLOBAL_CONFIG_PATH}): {'[green]exists[/green]' if global_exists else '[dim]not found[/dim]'}"
    )
    console.print(
        f"Project config ({project_path}): {'[green]exists[/green]' if project_exists else '[dim]not found[/dim]'}"
    )
    console.print()

    config_dict = {
        "version": config.version,
        "format": {
            "types": config.format.types,
            "scopes": config.format.scopes,
            "require_scope": config.format.require_scope,
            "require_body": config.format.require_body,
            "max_title_length": config.format.max_title_length,
            "require_issue_ref": config.format.require_issue_ref,
            "issue_pattern": config.format.issue_pattern,
        },
        "ai": {
            "language": config.ai.language,
            "instructions": config.ai.instructions,
        },
        "exclude": config.exclude,
    }

    yaml_str = yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)
    console.print(syntax)


def build_config_prompt(config: LazyCommitConfig) -> str:
    parts = []

    if config.format.types:
        parts.append(f"Allowed commit types: {', '.join(config.format.types)}")

    if config.format.scopes:
        parts.append(f"Allowed scopes: {', '.join(config.format.scopes)}")

    if config.format.require_scope:
        parts.append("A scope is REQUIRED for all commits.")

    if config.format.require_body:
        parts.append("A body/description is REQUIRED for all commits.")

    if config.format.max_title_length != 72:
        parts.append(
            f"Maximum title length: {config.format.max_title_length} characters"
        )

    if config.format.require_issue_ref:
        parts.append(
            f"An issue reference is REQUIRED (pattern: {config.format.issue_pattern})"
        )

    if config.ai.language != "en":
        lang_instruction = get_language_instruction(config.ai.language)
        parts.append(lang_instruction)

    if config.ai.instructions:
        parts.append(f"Additional instructions:\n{config.ai.instructions}")

    return "\n".join(parts) if parts else ""


LANGUAGE_INSTRUCTIONS = {
    "en": "Write the commit message in English.",
    "tr": "Commit mesajini Turkce yaz. Type ve scope Ingilizce kalsin.",
    "ja": "コミットメッセージを日本語で書いてください。TypeとScopeは英語のままにしてください。",
    "zh": "用中文写提交信息。Type和Scope保持英文。",
    "de": "Schreibe die Commit-Nachricht auf Deutsch. Type und Scope bleiben auf Englisch.",
    "fr": "Écrivez le message de commit en français. Type et scope restent en anglais.",
    "es": "Escribe el mensaje de commit en español. Type y scope permanecen en inglés.",
    "pt": "Escreva a mensagem de commit em português. Type e scope permanecem em inglês.",
    "ko": "커밋 메시지를 한국어로 작성하세요. Type과 Scope는 영어로 유지하세요.",
    "ru": "Напишите сообщение коммита на русском языке. Type и scope остаются на английском.",
}


def get_language_instruction(lang: str) -> str:
    return LANGUAGE_INSTRUCTIONS.get(lang, LANGUAGE_INSTRUCTIONS["en"])
