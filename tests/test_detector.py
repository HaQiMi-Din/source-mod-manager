"""模组解析器单元测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from source_mod_manager.detector import (
    find_mod,
    find_steam_path,
    parse_gameinfo,
    scan_all,
    scan_gmod_addons,
    scan_maps,
    scan_sourcemods,
)

from fixtures import CSS_GAMEINFO, GMOD_GAMEINFO, HL2_GAMEINFO, make_steam_tree


class ParseGameInfoTest(unittest.TestCase):
    def test_hl2_gameinfo(self):
        info, engine = parse_gameinfo(HL2_GAMEINFO)
        self.assertEqual(engine, "hl2")
        self.assertEqual(info["steam_appid"], "220")
        self.assertTrue(info["has_search_paths"])

    def test_gmod_gameinfo(self):
        info, engine = parse_gameinfo(GMOD_GAMEINFO)
        self.assertEqual(engine, "gmod")
        self.assertEqual(info["steam_appid"], "4000")

    def test_css_gameinfo(self):
        info, engine = parse_gameinfo(CSS_GAMEINFO)
        self.assertEqual(engine, "css")
        self.assertEqual(info["steam_appid"], "240")

    def test_empty_text(self):
        info, engine = parse_gameinfo("")
        self.assertEqual(engine, "unknown")
        self.assertFalse(info.get("has_search_paths", False))


class ScanTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.steam = make_steam_tree(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_find_steam_path_override(self):
        found = find_steam_path(self.steam)
        self.assertEqual(found, self.steam)
        self.assertIsNone(find_steam_path(self.steam.parent / "nope"))

    def test_scan_sourcemods(self):
        mods = scan_sourcemods(self.steam)
        by_name = {m.name: m for m in mods}
        self.assertEqual(len(mods), 4)
        self.assertTrue(by_name["my_hl2_mod"].valid)
        self.assertEqual(by_name["my_hl2_mod"].engine, "hl2")
        self.assertEqual(by_name["gmod_base"].engine, "gmod")
        self.assertEqual(by_name["css_base"].engine, "css")
        self.assertFalse(by_name["broken_mod"].valid)
        self.assertTrue(any("gameinfo.txt" in i for i in by_name["broken_mod"].issues))

    def test_scan_gmod_addons(self):
        mods = scan_gmod_addons(self.steam)
        by_name = {m.name: m for m in mods}
        self.assertEqual(len(mods), 3)
        self.assertEqual(by_name["cool_addon"].kind, "gmod_addon")
        self.assertTrue(by_name["cool_addon"].valid)
        self.assertFalse(by_name["empty_addon"].valid)
        self.assertEqual(by_name["pack.gma"].kind, "gma_addon")
        self.assertTrue(by_name["pack.gma"].valid)

    def test_scan_maps(self):
        mods = scan_maps(self.steam)
        by_name = {m.name: m for m in mods}
        self.assertEqual(len(mods), 2)
        self.assertEqual(by_name["d1_trainstation_01"].engine, "hl2")
        self.assertEqual(by_name["de_dust2"].engine, "css")

    def test_scan_all_structure(self):
        result = scan_all(self.steam)
        self.assertEqual(result["steam"], str(self.steam))
        self.assertEqual(len(result["sourcemods"]), 4)
        self.assertEqual(len(result["gmod_addons"]), 3)
        self.assertEqual(len(result["maps"]), 2)

    def test_find_mod(self):
        m = find_mod(self.steam, "MY_HL2_MOD")
        self.assertIsNotNone(m)
        self.assertEqual(m.kind, "sourcemod")
        m2 = find_mod(self.steam, "de_dust2.bsp")
        self.assertIsNotNone(m2)
        self.assertEqual(m2.kind, "map_file")
        self.assertIsNone(find_mod(self.steam, "not_exist"))


if __name__ == "__main__":
    unittest.main()
