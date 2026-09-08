"""地图安装器：把 .bsp 地图复制到目标游戏 / 模组的地图目录。"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .detector import COMMON_REL, ENGINE_CFG, ENGINE_MAPS_DIR, SourceMod


@dataclass
class InstallTarget:
    key: str
    label: str
    path: Path


def list_install_targets(steam: Path, sourcemods: Optional[List[SourceMod]] = None) -> List[InstallTarget]:
    """列出可安装地图的目标目录（各游戏 + 已发现的模组）。"""
    targets: List[InstallTarget] = []
    for engine, rel in ENGINE_MAPS_DIR.items():
        game_dir = steam / COMMON_REL / ENGINE_CFG[engine]["dir"]
        if game_dir.is_dir():
            targets.append(InstallTarget(
                key=engine,
                label=f"{ENGINE_CFG[engine]['dir']} / {rel}",
                path=game_dir / rel,
            ))
    for mod in (sourcemods or []):
        if mod.kind == "sourcemod" and mod.valid:
            targets.append(InstallTarget(
                key=f"mod:{mod.name}",
                label=f"模组 {mod.name} / maps",
                path=mod.path / "maps",
            ))
    return targets


def install_map(bsp: Path, target: InstallTarget, force: bool = False) -> Path:
    """把 bsp 安装到目标目录，返回最终路径。

    目标目录已存在同名文件且 force=False 时抛出 FileExistsError。
    """
    if not bsp.is_file():
        raise FileNotFoundError(f"地图文件不存在: {bsp}")
    target.path.mkdir(parents=True, exist_ok=True)
    dest = target.path / bsp.name
    if dest.exists() and not force:
        raise FileExistsError(f"目标目录已存在同名地图: {dest}")
    shutil.copy2(bsp, dest)
    return dest
