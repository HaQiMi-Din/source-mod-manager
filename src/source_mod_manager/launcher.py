"""模组启动器：根据模组类型组装命令并调用正确的引擎可执行文件运行。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .detector import COMMON_REL, ENGINE_CFG, SourceMod


class LaunchError(RuntimeError):
    """启动失败。"""


def _exe_names(exe: str) -> List[str]:
    if sys.platform == "win32":
        return [exe + ".exe"]
    if sys.platform == "darwin":
        return [exe + "_osx"]
    return [exe + "_linux", exe]


def engine_exe(steam: Path, engine: str) -> Optional[Path]:
    """返回指定引擎的可执行文件绝对路径；未安装返回 None。"""
    cfg = ENGINE_CFG.get(engine)
    if cfg is None:
        return None
    game_dir = steam / COMMON_REL / cfg["dir"]
    for name in _exe_names(cfg["exe"]):
        cand = game_dir / name
        if cand.exists():
            return cand
    return None


def _need_exe(steam: Path, engine: str) -> Path:
    exe = engine_exe(steam, engine)
    if exe is None:
        label = ENGINE_CFG.get(engine, {}).get("dir", engine)
        raise LaunchError(f"未找到 {engine} 引擎的可执行文件，请确认已在 Steam 安装 {label}")
    return exe


def build_command(steam: Path, mod: SourceMod, engine: Optional[str] = None,
                  map_name: Optional[str] = None) -> List[str]:
    """组装启动命令（不执行），供测试与启动共用。

    - sourcemod:    <引擎exe> -game <模组名> [+map <图>]
    - gmod 组件:    <garrysmod.exe> [+map <图>]
    - 地图:         <引擎exe> +map <地图名>
    """
    if mod.kind == "sourcemod":
        eng = engine or mod.engine
        if eng == "unknown":
            eng = "hl2"
        exe = _need_exe(steam, eng)
        args = ["-game", mod.name]
        if map_name:
            args += ["+map", map_name]
        return [str(exe)] + args

    if mod.kind in ("gmod_addon", "gma_addon"):
        exe = _need_exe(steam, "gmod")
        args: List[str] = []
        if map_name:
            args += ["+map", map_name]
        return [str(exe)] + args

    if mod.kind == "map_file":
        eng = engine or mod.engine or "hl2"
        exe = _need_exe(steam, eng)
        return [str(exe), "+map", map_name or mod.name]

    raise LaunchError(f"不支持的模组类型: {mod.kind}")


def launch(steam: Path, mod: SourceMod, engine: Optional[str] = None,
           map_name: Optional[str] = None) -> subprocess.Popen:
    """启动模组并返回进程句柄。"""
    cmd = build_command(steam, mod, engine, map_name)
    exe = Path(cmd[0])
    try:
        return subprocess.Popen(cmd, cwd=str(exe.parent))
    except OSError as exc:
        raise LaunchError(f"启动失败: {exe} - {exc}") from exc
