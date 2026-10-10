"""Exercise real Rime/Lua with upstream schemas and synthetic personal data.

Set RIME_PROBE, RIME_LIBRARY and RIME_LUA_PLUGIN to run this integration suite.
The probe is built from rime_probe.cc using the engine's public rime_api.h.
"""

from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = [os.environ.get(key) for key in ("RIME_PROBE", "RIME_LIBRARY", "RIME_LUA_PLUGIN")]
INPUTS = ["mamama", "ma'ma'ma", "huohuohuo", "shuishuishui", "mumumu", "jinjinjin",
          "ma", "mamam", "hello", "ios", "uUmamama", "uUhuohuohuo", "mumu"]


@unittest.skipUnless(all(RUNTIME), "Set RIME_PROBE, RIME_LIBRARY and RIME_LUA_PLUGIN")
class RadicalEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import yaml

        upstream = ROOT / "upstream/rime-ice"
        if not (upstream / "rime_ice.schema.yaml").exists():
            raise unittest.SkipTest("Fetch upstream/rime-ice before running engine tests")
        cls.temp = tempfile.TemporaryDirectory(prefix="fuyaorime-engine-")
        cls.addClassCleanup(cls.temp.cleanup)
        shared = Path(cls.temp.name) / "shared"
        cls.user = Path(cls.temp.name) / "user"
        shared.mkdir()
        cls.user.mkdir()
        for path in upstream.glob("*.yaml"):
            shutil.copy2(path, shared / path.name)
        for name in ("lua", "opencc"):
            shutil.copytree(upstream / name, shared / name)
        (shared / "en_dicts").mkdir()
        (shared / "en_dicts/cn_en.txt").write_text("")
        # Small deterministic ordinary vocabulary; the real radical table is unchanged.
        (shared / "melt_eng.dict.yaml").write_text(
            "---\nname: melt_eng\nversion: '1'\nsort: by_weight\n...\nhello\thello\t10\niOS\tiOS\t10\n")
        (cls.user / "rime_ice.custom.dict.yaml").write_text(
            "---\nname: rime_ice.custom\nversion: '1'\nsort: by_weight\n...\n"
            "妈\tma\t100\n马\tma\t90\n嘛\tma\t80\n"
            "妈妈妈\tma ma ma\t10000\n妈妈马\tma ma ma\t9000\n"
            "妈妈嘛\tma ma ma\t8000\n马妈妈\tma ma ma\t7000\n"
            "木\tmu\t100\n木木木\tmu mu mu\t1000\n林\tmu mu\t900\n"
            "火\thuo\t100\n火火火\thuo huo huo\t1000\n水\tshui\t100\n"
            "水水水\tshui shui shui\t1000\n金\tjin\t100\n金金金\tjin jin jin\t1000\n")
        (cls.user / "build").mkdir()
        shutil.copy2(ROOT / "upstream/radical-readings/zdict.reverse.bin", cls.user / "build")
        (cls.user / "lua").mkdir()
        shutil.copy2(ROOT / "overlay/lua/fuyao_radical.lua", cls.user / "lua")
        shutil.copy2(ROOT / "overlay/melt_eng.custom.yaml", cls.user)
        defaults = yaml.safe_load((ROOT / "overlay/default.custom.yaml").read_text())
        defaults["patch"]["schema_list"] = [{"schema": "rime_ice"}, {"schema": "fuyao_baseline"}]
        (cls.user / "default.custom.yaml").write_text(yaml.safe_dump(defaults, allow_unicode=True))
        patch = yaml.safe_load((ROOT / "overlay/rime_ice.custom.yaml").read_text())
        # The grammar and large extra word lists are outside this feature's scope.
        patch["patch"] = {key: value for key, value in patch["patch"].items() if not key.startswith("grammar/")}
        (cls.user / "rime_ice.custom.yaml").write_text(yaml.safe_dump(patch, allow_unicode=True))
        # Keep upstream syntax intact: yaml-cpp accepts tabs in its pin-candidate scalars.
        baseline = (shared / "rime_ice.schema.yaml").read_text()
        assert baseline.count("schema_id: rime_ice") == 1
        (shared / "fuyao_baseline.schema.yaml").write_text(
            baseline.replace("schema_id: rime_ice", "schema_id: fuyao_baseline", 1))
        del patch["patch"]["engine/filters/+"]
        del patch["patch"]["fuyao_radical"]
        (cls.user / "fuyao_baseline.custom.yaml").write_text(yaml.safe_dump(patch, allow_unicode=True))
        cls.command = RUNTIME + [str(shared), str(cls.user)]
        cls.baseline = cls.query("fuyao_baseline", INPUTS)
        cls.results = cls.query("rime_ice", INPUTS)

    @classmethod
    def query(cls, schema, inputs):
        result = subprocess.run(cls.command + [schema] + inputs, text=True, capture_output=True, timeout=120)
        if result.returncode != 0 or "Lua" in result.stderr:
            raise AssertionError(f"Rime probe failed ({result.returncode}):\n{result.stderr}\n{result.stdout}")
        return [json.loads(line) for line in result.stdout.splitlines() if line]

    def candidates(self, input_text, baseline=False):
        rows = self.baseline if baseline else self.results
        return next(row["candidates"] for row in rows if row.get("input") == input_text)

    def test_mamama_keeps_top_three_and_inserts_tone_marked_radicals(self):
        before = self.candidates("mamama", baseline=True)
        after = self.candidates("mamama")
        self.assertEqual(after[:3], before[:3])
        self.assertEqual({item["text"] for item in after[3:5]}, {"骉", "驫"})
        for item in after[3:5]:
            self.assertIn("biāo", item["comment"])

    def test_complete_component_matches_and_explicit_separators(self):
        for code, character, reading in [("ma'ma'ma", "骉", "biāo"), ("huohuohuo", "焱", "yàn"),
                                          ("shuishuishui", "淼", "miǎo"), ("mumumu", "森", "sēn"),
                                          ("jinjinjin", "鑫", "xīn")]:
            with self.subTest(code=code):
                match = next(item for item in self.candidates(code) if item["text"] == character)
                self.assertIn(reading, match["comment"])

    def test_single_component_incomplete_input_and_english_are_unchanged(self):
        for code in ("ma", "mamam", "hello", "ios"):
            with self.subTest(code=code):
                self.assertEqual(self.candidates(code), self.candidates(code, baseline=True))

    def test_prefixed_reverse_lookup_remains_and_has_tone_marks(self):
        for code, character, reading in [("uUmamama", "骉", "biāo"), ("uUhuohuohuo", "焱", "yàn")]:
            with self.subTest(code=code):
                self.assertEqual(self.candidates(code), self.candidates(code, baseline=True))
                match = next(item for item in self.candidates(code) if item["text"] == character)
                self.assertIn(reading, match["comment"])

    def test_duplicate_candidates_are_not_added(self):
        candidates = self.candidates("mumu")
        self.assertEqual(sum(item["text"] == "林" for item in candidates), 1)

    def test_selecting_radical_does_not_learn_a_main_pinyin_spelling(self):
        rows = self.query("rime_ice", ["mamama", "select:3", "mamama"])
        self.assertIn(rows[1]["commit"], ("骉", "驫"))
        self.assertEqual(rows[0]["candidates"], rows[2]["candidates"])
        self.assertFalse(list(self.user.glob("radical_pinyin.userdb*")))


if __name__ == "__main__":
    unittest.main()
