"""配置读写：保存用户手动指定的 Steam 路径。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".source_mod_manager"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_steam_override() -> Optional[Path]:
    value = load_config().get("steam_path")
    return Path(value) if value else None
