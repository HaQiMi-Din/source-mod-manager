"""启动器命令组装与地图安装器单元测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from source_mod_manager.detector import find_mod, scan_all, scan_sourcemods
from source_mod_manager.installer import install_map, list_install_targets
from source_mod_manager.launcher import LaunchError, build_command, engine_exe

from fixtures import make_steam_tree


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.steam = make_steam_tree(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_engine_exe_found(self):
        for engine in ("hl2", "gmod", "css"):
            exe = engine_exe(self.steam, engine)
            self.assertIsNotNone(exe, f"{engine} 应找到可执行文件")
            self.assertTrue(exe.exists())

    def test_engine_exe_missing(self):
        steam2 = self._tmp.name and self.steam.parent / "other"
        (steam2 / "steamapps" / "common").mkdir(parents=True)
        self.assertIsNone(engine_exe(steam2, "gmod"))

    def test_sourcemod_command(self):
        mod = find_mod(self.steam, "my_hl2_mod")
        cmd = build_command(self.steam, mod)
        self.assertTrue(cmd[0].endswith(("hl2.exe", "hl2_linux", "hl2")), cmd[0])
        self.assertIn("-game", cmd)
        self.assertEqual(cmd[cmd.index("-game") + 1], "my_hl2_mod")

    def test_gmod_addon_command(self):
        mod = find_mod(self.steam, "cool_addon")
        cmd = build_command(self.steam, mod)
        self.assertTrue(cmd[0].endswith(("garrysmod.exe", "garrysmod_linux", "garrysmod")), cmd[0])

    def test_map_command(self):
        mod = find_mod(self.steam, "de_dust2.bsp")
        cmd = build_command(self.steam, mod)
        self.assertIn("+map", cmd)
        self.assertEqual(cmd[cmd.index("+map") + 1], "de_dust2")

    def test_missing_engine_raises(self):
        steam2 = self.steam.parent / "naked"
        (steam2 / "steamapps" / "sourcemods" / "x").mkdir(parents=True)
        (steam2 / "steamapps" / "sourcemods" / "x" / "gameinfo.txt").write_text(
            '"GameInfo" { FileSystem { SteamAppId 9999 SearchPaths { Game |gameinfo_path|. } } }')
        mod = scan_sourcemods(steam2)[0]
        with self.assertRaises(LaunchError):
            build_command(steam2, mod, engine="hl2")


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.steam = make_steam_tree(Path(self._tmp.name))
        self.maps = scan_all(self.steam)["maps"]

    def tearDown(self):
        self._tmp.cleanup()

    def test_list_install_targets(self):
        sourcemods = scan_sourcemods(self.steam)
        targets = list_install_targets(self.steam, sourcemods)
        keys = {t.key for t in targets}
        self.assertIn("hl2", keys)
        self.assertIn("gmod", keys)
        self.assertIn("css", keys)
        self.assertIn("mod:my_hl2_mod", keys)

    def test_install_map_into_gmod(self):
        dust = next(m for m in self.maps if m.name == "de_dust2")
        target = next(t for t in list_install_targets(self.steam) if t.key == "gmod")
        dest = install_map(dust.path, target)
        self.assertTrue(dest.exists())
        self.assertEqual(dest.name, "de_dust2.bsp")

    def test_install_duplicate_raises(self):
        dust = next(m for m in self.maps if m.name == "de_dust2")
        target = next(t for t in list_install_targets(self.steam) if t.key == "hl2")
        install_map(dust.path, target)  # 首次安装成功
        with self.assertRaises(FileExistsError):
            install_map(dust.path, target)  # 重复安装报错
        install_map(dust.path, target, force=True)  # --force 覆盖成功


if __name__ == "__main__":
    unittest.main()
