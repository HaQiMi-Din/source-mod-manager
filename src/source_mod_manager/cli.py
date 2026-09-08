"""命令行入口：scan / launch / install-map / gui / steam。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .config import get_steam_override, save_config
from .detector import SourceMod, find_mod, find_steam_path, scan_all
from .installer import install_map, list_install_targets
from .launcher import LaunchError, launch

EXIT_NO_STEAM = """错误：无法定位 Steam 安装目录。
请用 --steam 参数手动指定，例如：
  python -m source_mod_manager scan --steam "C:/Program Files (x86)/Steam"
  SourceModManagerCLI.exe scan --steam "D:/Steam"
"""


def _resolve_steam(override: Optional[str]) -> Path:
    p = Path(override) if override else get_steam_override()
    steam = find_steam_path(p)
    if steam is None:
        sys.exit(EXIT_NO_STEAM)
    if override:
        save_config({"steam_path": str(steam)})
    return steam


def _print_table(mods: List[SourceMod]) -> None:
    if not mods:
        print("  (无)")
        return
    for m in mods:
        mark = "OK " if m.valid else "!! "
        print(f"  [{mark}] {m.summary}")
        for issue in m.issues:
            print(f"        - {issue}")


def cmd_scan(args: argparse.Namespace) -> int:
    steam = _resolve_steam(args.steam)
    result = scan_all(steam)

    if args.json:

        def dump(mod: SourceMod) -> dict:
            return {
                "name": mod.name, "path": str(mod.path), "kind": mod.kind,
                "engine": mod.engine, "valid": mod.valid, "issues": mod.issues,
                "size_mb": mod.size_mb, "meta": mod.meta,
            }

        print(json.dumps({
            "steam": str(steam),
            "sourcemods": [dump(m) for m in result["sourcemods"]],
            "gmod_addons": [dump(m) for m in result["gmod_addons"]],
            "maps": [dump(m) for m in result["maps"]],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"Steam 目录: {steam}\n")
    print("== 起源引擎模组 (sourcemods) ==")
    _print_table(result["sourcemods"])
    print("\n== GMod 附加组件 (addons) ==")
    _print_table(result["gmod_addons"])
    print("\n== 地图 (.bsp) ==")
    _print_table(result["maps"])
    print("\n提示：使用 `python -m source_mod_manager gui` 打开图形界面。")
    return 0


def cmd_launch(args: argparse.Namespace) -> int:
    steam = _resolve_steam(args.steam)
    kinds = None
    if args.kind:
        kinds = (args.kind,)
    mod = find_mod(steam, args.name, kinds)
    if mod is None:
        sys.exit(f"未找到名为 '{args.name}' 的模组，请先运行 scan 查看全部模组。")
    if not mod.valid:
        print(f"警告：{mod.name} 解析不完整，仍尝试启动。")
    try:
        proc = launch(steam, mod, engine=args.engine, map_name=args.map)
    except LaunchError as exc:
        sys.exit(f"启动失败：{exc}")
    print(f"已启动 {mod.name}（{mod.kind_label}，引擎 {mod.engine}），PID={proc.pid}")
    print("提示：游戏启动时请保持 Steam 客户端运行（起源引擎受 Steam DRM 保护）。")
    return 0


def cmd_install_map(args: argparse.Namespace) -> int:
    steam = _resolve_steam(args.steam)
    bsp = Path(args.bsp).expanduser().resolve()
    if not bsp.is_file():
        sys.exit(f"地图文件不存在: {bsp}")

    result = scan_all(steam)
    targets = list_install_targets(steam, result["sourcemods"])
    if not targets:
        sys.exit("没有可用的安装目标：请确认已安装 HL2 / GMod / CS:S 或存在有效模组。")

    target = None
    if args.target:
        for t in targets:
            if t.key == args.target:
                target = t
                break
        if target is None:
            names = ", ".join(t.key for t in targets)
            sys.exit(f"未知目标 '{args.target}'，可选：{names}")
    else:
        if len(targets) == 1:
            target = targets[0]
        else:
            print("可用的安装目标：")
            for i, t in enumerate(targets, 1):
                print(f"  {i}. [{t.key}] {t.label}")
            choice = input("请输入编号：").strip()
            try:
                target = targets[int(choice) - 1]
            except (ValueError, IndexError):
                sys.exit("无效编号。")

    try:
        dest = install_map(bsp, target, force=args.force)
    except FileExistsError as exc:
        sys.exit(f"安装失败：{exc}（如已存在且想覆盖，请加 --force）")
    print(f"地图已安装到: {dest}")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    steam = _resolve_steam(args.steam)
    from .gui import run_gui
    run_gui(steam)
    return 0


def cmd_steam(args: argparse.Namespace) -> int:
    print(_resolve_steam(args.steam))
    return 0


def _add_steam_arg(parser: argparse.ArgumentParser) -> None:
    """为顶层与各子命令都添加 --steam，两个位置均可使用。"""
    parser.add_argument(
        "--steam",
        default=argparse.SUPPRESS,
        help="Steam 安装目录路径（首次指定后会记住）",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="source-mod-manager",
        description="起源引擎(Source Engine)模组解析与启动管理器：扫描/校验/运行 HL2、GMod、CS:S 模组与地图。",
    )
    _add_steam_arg(parser)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scan", help="扫描并解析全部模组")
    _add_steam_arg(p)
    p.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("launch", help="启动指定模组 / 附加组件 / 地图")
    _add_steam_arg(p)
    p.add_argument("name", help="模组名 / 附加组件名 / 地图名(可带 .bsp)")
    p.add_argument("--engine", choices=["hl2", "gmod", "css"], help="强制指定引擎")
    p.add_argument("--map", help="启动后进入的地图名")
    p.add_argument("--kind", choices=["sourcemod", "gmod_addon", "gma_addon", "map_file"],
                   help="限定查找类型（名称冲突时使用）")
    p.set_defaults(func=cmd_launch)

    p = sub.add_parser("install-map", help="安装 .bsp 地图到目标游戏/模组")
    _add_steam_arg(p)
    p.add_argument("bsp", help="地图文件路径")
    p.add_argument("--target", help="目标键：hl2 / gmod / css / mod:<模组名>")
    p.add_argument("--force", action="store_true", help="覆盖已存在的同名地图")
    p.set_defaults(func=cmd_install_map)

    p = sub.add_parser("gui", help="打开图形界面")
    _add_steam_arg(p)
    p.set_defaults(func=cmd_gui)

    p = sub.add_parser("steam", help="显示定位到的 Steam 目录")
    _add_steam_arg(p)
    p.set_defaults(func=cmd_steam)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
