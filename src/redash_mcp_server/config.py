from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "redash-mcp" / "config.json"


@dataclass(frozen=True)
class RedashSettings:
    base_url: str
    api_key: str
    timeout_seconds: int = 300
    max_rows: int = 200


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def get_config_path() -> Path:
    configured = os.environ.get("REDASH_MCP_CONFIG") or os.environ.get("REDASH_EXPORTS_CONFIG")
    return Path(configured).expanduser() if configured else DEFAULT_CONFIG_PATH


def load_settings() -> RedashSettings:
    stored = load_json_file(get_config_path())
    base_url = os.environ.get("REDASH_URL") or stored.get("base_url")
    if not base_url:
        raise RuntimeError(
            "Missing Redash URL. Set REDASH_URL or populate "
            f"{get_config_path()}."
        )

    base_url = str(base_url).rstrip("/")
    api_key = os.environ.get("REDASH_API_KEY") or stored.get("api_key")
    if not api_key:
        raise RuntimeError(
            "Missing Redash API key. Set REDASH_API_KEY or populate "
            f"{get_config_path()}."
        )

    timeout_seconds = int(os.environ.get("REDASH_TIMEOUT_SECONDS", "300"))
    max_rows = int(os.environ.get("REDASH_MCP_MAX_ROWS", "200"))
    return RedashSettings(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        max_rows=max_rows,
    )
