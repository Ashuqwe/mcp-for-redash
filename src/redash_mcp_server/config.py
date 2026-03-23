from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "redash-mcp" / "config.json"
DEFAULT_INSTANCE_NAME = "default"


@dataclass(frozen=True)
class RedashInstanceSettings:
    name: str
    base_url: str
    api_key: str


@dataclass(frozen=True)
class RedashSettings:
    instances: dict[str, RedashInstanceSettings]
    default_instance: str
    timeout_seconds: int = 300
    max_rows: int = 200
    read_only: bool = True
    allow_adhoc_sql: bool = False

    def get_instance(self, name: str | None = None) -> RedashInstanceSettings:
        selected = name or self.default_instance
        try:
            return self.instances[selected]
        except KeyError as exc:
            known = ", ".join(sorted(self.instances))
            raise RuntimeError(
                f"Unknown Redash instance '{selected}'. Known instances: {known}."
            ) from exc


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def get_config_path() -> Path:
    configured = os.environ.get("REDASH_MCP_CONFIG") or os.environ.get(
        "REDASH_EXPORTS_CONFIG"
    )
    return Path(configured).expanduser() if configured else DEFAULT_CONFIG_PATH


def _parse_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _build_instance(name: str, payload: dict[str, Any]) -> RedashInstanceSettings:
    base_url = payload.get("base_url")
    api_key = payload.get("api_key")
    if not base_url or not api_key:
        raise RuntimeError(
            f"Redash instance '{name}' is missing base_url or api_key."
        )
    return RedashInstanceSettings(
        name=name,
        base_url=str(base_url).rstrip("/"),
        api_key=str(api_key),
    )


def _load_instances(stored: dict[str, Any]) -> tuple[dict[str, RedashInstanceSettings], str]:
    env_base_url = os.environ.get("REDASH_URL")
    env_api_key = os.environ.get("REDASH_API_KEY")
    env_default_instance = os.environ.get("REDASH_MCP_DEFAULT_INSTANCE")

    if env_base_url or env_api_key:
        if not (env_base_url and env_api_key):
            raise RuntimeError(
                "Set both REDASH_URL and REDASH_API_KEY for environment-based "
                "configuration."
            )
        default_instance = (env_default_instance or DEFAULT_INSTANCE_NAME).strip()
        return (
            {
                default_instance: RedashInstanceSettings(
                    name=default_instance,
                    base_url=str(env_base_url).rstrip("/"),
                    api_key=str(env_api_key),
                )
            },
            default_instance,
        )

    instances_payload = stored.get("instances")
    if isinstance(instances_payload, dict) and instances_payload:
        instances: dict[str, RedashInstanceSettings] = {}
        for raw_name, raw_payload in instances_payload.items():
            if not isinstance(raw_name, str) or not raw_name.strip():
                raise RuntimeError("Every Redash instance must have a non-empty name.")
            if not isinstance(raw_payload, dict):
                raise RuntimeError(
                    f"Redash instance '{raw_name}' must be a JSON object."
                )
            instance_name = raw_name.strip()
            instances[instance_name] = _build_instance(instance_name, raw_payload)

        default_instance = (
            str(env_default_instance or stored.get("default_instance") or "").strip()
            or next(iter(instances))
        )
        if default_instance not in instances:
            known = ", ".join(sorted(instances))
            raise RuntimeError(
                f"default_instance '{default_instance}' is not defined. "
                f"Known instances: {known}."
            )
        return instances, default_instance

    legacy_base_url = stored.get("base_url")
    legacy_api_key = stored.get("api_key")
    if legacy_base_url or legacy_api_key:
        if not (legacy_base_url and legacy_api_key):
            raise RuntimeError(
                f"Missing Redash URL or API key in {get_config_path()}."
            )
        default_instance = (env_default_instance or DEFAULT_INSTANCE_NAME).strip()
        return (
            {
                default_instance: RedashInstanceSettings(
                    name=default_instance,
                    base_url=str(legacy_base_url).rstrip("/"),
                    api_key=str(legacy_api_key),
                )
            },
            default_instance,
        )

    raise RuntimeError(
        "Missing Redash configuration. Set REDASH_URL and REDASH_API_KEY, or populate "
        f"{get_config_path()} with either base_url/api_key or an instances block."
    )


def load_settings() -> RedashSettings:
    stored = load_json_file(get_config_path())
    instances, default_instance = _load_instances(stored)
    timeout_seconds = int(os.environ.get("REDASH_TIMEOUT_SECONDS", "300"))
    max_rows = int(os.environ.get("REDASH_MCP_MAX_ROWS", "200"))
    read_only = _parse_bool(
        os.environ.get("REDASH_MCP_READ_ONLY", stored.get("read_only")),
        default=True,
    )
    allow_adhoc_sql = _parse_bool(
        os.environ.get("REDASH_MCP_ALLOW_ADHOC_SQL", stored.get("allow_adhoc_sql")),
        default=False,
    )
    return RedashSettings(
        instances=instances,
        default_instance=default_instance,
        timeout_seconds=timeout_seconds,
        max_rows=max_rows,
        read_only=read_only,
        allow_adhoc_sql=allow_adhoc_sql,
    )
