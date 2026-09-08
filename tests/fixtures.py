"""测试夹具：在临时目录构造一个模拟的 Steam 目录树。"""

from __future__ import annotations

from pathlib import Path

HL2_GAMEINFO = '''"GameInfo"
{
\tgame\t"My HL2 Mod"
\tFileSystem
\t{
\t\tSteamAppId\t\t\t\t220
\t\tSearchPaths
\t\t{
\t\t\tGame\t|gameinfo_path|.
\t\t\tGame\thl2
\t\t\tMod\t|all_source_engine_paths|hl2
\t\t}
\t}
}
'''

GMOD_GAMEINFO = '''"GameInfo"
{
\tgame\t"GMod Base Mod"
\tFileSystem
\t{
\t\tSteamAppId\t\t\t\t4000
\t\tSearchPaths
\t\t{
\t\t\tGame\t|gameinfo_path|.
\t\t\tGame\tgarrysmod
\t\t}
\t}
}
'''

CSS_GAMEINFO = '''"GameInfo"
{
\tgame\t"CS:S Base Mod"
\tFileSystem
\t{
\t\tSteamAppId\t\t\t\t240
\t\tSearchPaths
\t\t{
\t\t\tGame\t|gameinfo_path|.
\t\t\tGame\tcstrike
\t\t}
\t}
}
'''


def make_steam_tree(root: Path) -> Path:
    """构造模拟 Steam 目录，返回 steam 根目录。"""
    steam = root / "steam"

    # ---- sourcemods：起源引擎模组 ----
    sourcemods = steam / "steamapps" / "sourcemods"

    (sourcemods / "my_hl2_mod").mkdir(parents=True)
    (sourcemods / "my_hl2_mod" / "gameinfo.txt").write_text(HL2_GAMEINFO, encoding="utf-8")
    (sourcemods / "my_hl2_mod" / "maps").mkdir()

    (sourcemods / "gmod_base").mkdir(parents=True)
    (sourcemods / "gmod_base" / "gameinfo.txt").write_text(GMOD_GAMEINFO, encoding="utf-8")

    (sourcemods / "css_base").mkdir(parents=True)
    (sourcemods / "css_base" / "gameinfo.txt").write_text(CSS_GAMEINFO, encoding="utf-8")

    (sourcemods / "broken_mod").mkdir()
    (sourcemods / "broken_mod" / "readme.txt").write_text("not a mod", encoding="utf-8")

    # ---- GMod 附加组件 ----
    gmod = steam / "steamapps" / "common" / "GarrysMod" / "garrysmod"
    addons = gmod / "addons"
    (addons / "cool_addon" / "lua" / "autorun").mkdir(parents=True)
    (addons / "cool_addon" / "lua" / "autorun" / "init.lua").write_text(
        "print('hello')", encoding="utf-8")
    (addons / "empty_addon").mkdir()
    (addons / "pack.gma").write_bytes(b"GMA" + b"\x00" * 100)

    # ---- HL2 ----
    hl2 = steam / "steamapps" / "common" / "Half-Life 2"
    (hl2 / "hl2" / "maps").mkdir(parents=True)
    (hl2 / "hl2" / "maps" / "d1_trainstation_01.bsp").write_bytes(b"\x00" * 2048)

    # ---- CS:S ----
    css = steam / "steamapps" / "common" / "Counter-Strike Source"
    (css / "cstrike" / "maps").mkdir(parents=True)
    (css / "cstrike" / "maps" / "de_dust2.bsp").write_bytes(b"\x00" * 1024)

    # ---- 可执行文件（两种平台变体，保证任意平台都能被 engine_exe 找到） ----
    (hl2 / "hl2.exe").write_bytes(b"MZ")
    (hl2 / "hl2_linux").write_bytes(b"ELF")
    (gmod / "garrysmod.exe").write_bytes(b"MZ")
    (gmod / "garrysmod_linux").write_bytes(b"ELF")
    (css / "hl2.exe").write_bytes(b"MZ")
    (css / "hl2_linux").write_bytes(b"ELF")

    return steam
