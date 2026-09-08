"""起源引擎(Source Engine)模组解析器。

负责扫描 Steam 目录，解析并校验三类内容：
- sourcemods 目录下的起源引擎模组（HL2 模组、GMod 基础模组、CS:S 模组等）
- Garry's Mod 的附加组件（目录型 addon 与 .gma 打包）
- 各游戏安装目录下的 .bsp 地图
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量：引擎定义
# ---------------------------------------------------------------------------
# engine 标识 -> 安装信息（Steam AppID / 安装目录名 / 可执行文件名）
ENGINE_CFG = {
    "hl2":  {"appid": 220,  "dir": "Half-Life 2",           "exe": "hl2"},
    "gmod": {"appid": 4000, "dir": "GarrysMod",             "exe": "garrysmod"},
    "css":  {"appid": 240,  "dir": "Counter-Strike Source", "exe": "hl2"},
}

# engine 标识 -> 地图目录（相对游戏安装目录）
ENGINE_MAPS_DIR = {
    "hl2":  "hl2/maps",
    "gmod": "garrysmod/maps",
    "css":  "cstrike/maps",
}

# 从 gameinfo.txt 内容中识别引擎的关键字（按优先级排序）
ENGINE_MARKERS = [
    ("gmod",    ("garrysmod", "gmod")),
    ("css",     ("cstrike", "counter-strike source")),
    ("tf2",     ("team fortress", "tf\\")),
    ("portal",  ("portal",)),
    ("ep2",     ("ep2", "episode two")),
    ("episodic", ("episodic", "episode one")),
    ("hl2",     ("hl2", "half-life 2")),
]

SOURCEMODS_REL = Path("steamapps") / "sourcemods"
COMMON_REL     = Path("steamapps") / "common"

ADDON_CONTENT_DIRS = (
    "lua", "materials", "models", "maps", "sound",
    "gamemodes", "resource", "scripts",
)


@dataclass
class SourceMod:
    """一个被解析出的模组 / 附加组件 / 地图条目。"""

    name: str
    path: Path
    kind: str                 # sourcemod / gmod_addon / gma_addon / map_file
    engine: str = "unknown"   # hl2 / gmod / css / tf2 / ...
    meta: dict = field(default_factory=dict)
    valid: bool = True
    issues: List[str] = field(default_factory=list)
    size_mb: float = 0.0

    @property
    def kind_label(self) -> str:
        return {
            "sourcemod":  "起源引擎模组",
            "gmod_addon": "GMod 附加组件(目录)",
            "gma_addon":  "GMod 附加组件(.gma)",
            "map_file":   "地图(.bsp)",
        }.get(self.kind, self.kind)

    @property
    def summary(self) -> str:
        flag = "OK" if self.valid else "无效"
        return (f"{self.name} | {self.kind_label} | 引擎:{self.engine} "
                f"| {self.size_mb:.1f}MB | {flag}")


# ---------------------------------------------------------------------------
# Steam 目录定位
# ---------------------------------------------------------------------------
def find_steam_path(override: Optional[Path] = None) -> Optional[Path]:
    """定位 Steam 安装目录：优先手动指定，其次注册表 / 常见路径。"""
    if override is not None:
        return override if (override / "steamapps").exists() else None

    candidates: List[Path] = []
    if sys.platform == "win32":
        try:
            import winreg
        except ImportError:  # 极少数环境无 winreg
            winreg = None
        if winreg is not None:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, r"SOFTWARE\Valve\Steam") as key:
                        value, _ = winreg.QueryValueEx(key, "SteamPath")
                        if value:
                            candidates.append(Path(value).resolve())
                except OSError:
                    continue
        pf = os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"
        pf2 = os.environ.get("ProgramFiles") or r"C:\Program Files"
        candidates += [Path(pf) / "Steam", Path(pf2) / "Steam"]
    else:
        candidates += [
            Path.home() / ".steam" / "steam",
            Path.home() / ".local" / "share" / "Steam",
            Path.home() / "Steam",
            Path("/usr/lib/steam"),
        ]

    for cand in candidates:
        if (cand / "steamapps").exists():
            return cand
    return None


# ---------------------------------------------------------------------------
# gameinfo.txt 解析
# ---------------------------------------------------------------------------
def _extract_braced_block(text: str, header: str) -> str:
    """从 text 中提取 'header { ... }' 块的内容（用于 SearchPaths / FileSystem）。

    兼容带引号与不带引号的键名（不同模组的 gameinfo.txt 写法不一）。
    """
    key = header.strip('"')
    m = re.search(r'"?' + re.escape(key) + r'"?\s*\{', text, re.I)
    if not m:
        return ""
    i = m.end()
    depth = 1
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[m.end():i - 1]


def parse_gameinfo(text: str) -> Tuple[dict, str]:
    """解析 gameinfo.txt 文本，返回 (字段dict, 引擎标识)。

    兼容带引号 / 不带引号的键与值（如 SteamAppId 220 与 "SteamAppId" "220"）。
    """
    info: dict = {}

    m = re.search(r'"?SteamAppId"?\s*"?(\d+)"?', text)
    if m:
        info["steam_appid"] = m.group(1)

    m = re.search(r'"Game"\s*"([^"]+)"', text)
    if m:
        info["game"] = m.group(1)
    m = re.search(r'\bgame\s+"([^"]+)"', text)
    if m and "game" not in info:
        info["game"] = m.group(1)

    search_paths = _extract_braced_block(text, '"SearchPaths"')
    filesystem = _extract_braced_block(text, '"FileSystem"')
    m = re.search(r'"?SteamAppId"?\s*"?(\d+)"?', filesystem)
    if m and "steam_appid" not in info:
        info["steam_appid"] = m.group(1)
    info["has_search_paths"] = bool(search_paths.strip())

    haystack = " ".join([search_paths, text]).lower()
    engine = "unknown"
    for eng, markers in ENGINE_MARKERS:
        if any(mk in haystack for mk in markers):
            engine = eng
            break
    return info, engine


# ---------------------------------------------------------------------------
# 扫描
# ---------------------------------------------------------------------------
def _dir_size_mb(path: Path) -> float:
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except OSError:
        pass
    return round(total / 1048576.0, 2)


def scan_sourcemods(steam: Path) -> List[SourceMod]:
    """扫描 <steam>/steamapps/sourcemods 下的起源引擎模组。"""
    out: List[SourceMod] = []
    base = steam / SOURCEMODS_REL
    if not base.is_dir():
        return out

    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        gi = child / "gameinfo.txt"
        if not gi.exists():
            out.append(SourceMod(
                name=child.name, path=child, kind="sourcemod", engine="unknown",
                valid=False, issues=["缺少 gameinfo.txt，不是有效的起源引擎模组"],
                size_mb=_dir_size_mb(child),
            ))
            continue
        try:
            text = gi.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            out.append(SourceMod(
                name=child.name, path=child, kind="sourcemod", valid=False,
                issues=[f"无法读取 gameinfo.txt: {exc}"], size_mb=_dir_size_mb(child),
            ))
            continue

        info, engine = parse_gameinfo(text)
        issues: List[str] = []
        if not info.get("has_search_paths"):
            issues.append("gameinfo.txt 缺少 SearchPaths 定义，可能无法加载内容")
        if engine == "unknown":
            issues.append("未能识别引擎类型，将按 HL2 引擎处理")
        out.append(SourceMod(
            name=child.name, path=child, kind="sourcemod", engine=engine,
            meta=info, valid=not issues, issues=issues, size_mb=_dir_size_mb(child),
        ))
    return out


def scan_gmod_addons(steam: Path) -> List[SourceMod]:
    """扫描 <steam>/steamapps/common/GarrysMod/garrysmod/addons 下的附加组件。"""
    out: List[SourceMod] = []
    addons_dir = steam / COMMON_REL / "GarrysMod" / "garrysmod" / "addons"
    if not addons_dir.is_dir():
        return out

    for child in sorted(addons_dir.iterdir()):
        if child.is_dir():
            has_content = any((child / sub).exists() for sub in ADDON_CONTENT_DIRS)
            out.append(SourceMod(
                name=child.name, path=child, kind="gmod_addon", engine="gmod",
                valid=has_content,
                issues=[] if has_content else
                ["目录中未发现可加载内容（lua/materials/models/maps 等）"],
                size_mb=_dir_size_mb(child),
            ))
        elif child.suffix.lower() == ".gma":
            try:
                size = round(child.stat().st_size / 1048576.0, 2)
            except OSError:
                size = 0.0
            out.append(SourceMod(
                name=child.name, path=child, kind="gma_addon", engine="gmod",
                meta={"gma": True}, size_mb=size,
            ))
    return out


def scan_maps(steam: Path) -> List[SourceMod]:
    """扫描 HL2 / GMod / CS:S 安装目录中的 .bsp 地图。"""
    out: List[SourceMod] = []
    for engine, rel in ENGINE_MAPS_DIR.items():
        maps_dir = steam / COMMON_REL / ENGINE_CFG[engine]["dir"] / rel
        if not maps_dir.is_dir():
            continue
        for bsp in sorted(maps_dir.glob("*.bsp")):
            try:
                size = round(bsp.stat().st_size / 1048576.0, 2)
            except OSError:
                size = 0.0
            out.append(SourceMod(
                name=bsp.stem, path=bsp, kind="map_file", engine=engine,
                meta={"maps_dir": str(maps_dir)}, size_mb=size,
            ))
    return out


def scan_all(steam: Path) -> dict:
    """执行全量扫描，返回按类型分组的解析结果。"""
    return {
        "steam": str(steam),
        "sourcemods": scan_sourcemods(steam),
        "gmod_addons": scan_gmod_addons(steam),
        "maps": scan_maps(steam),
    }


def find_mod(steam: Path, name: str, kinds: Optional[Tuple[str, ...]] = None) -> Optional[SourceMod]:
    """按名称查找模组（不区分大小写；自动剥离 .bsp / .gma 后缀）。"""
    name_l = name.lower()
    if name_l.endswith(".bsp"):
        name_l = name_l[:-4]
    elif name_l.endswith(".gma"):
        name_l = name_l[:-4]
    for group in scan_all(steam).values():
        if not isinstance(group, list):
            continue
        for mod in group:
            if kinds and mod.kind not in kinds:
                continue
            if mod.name.lower() == name_l:
                return mod
    return None
