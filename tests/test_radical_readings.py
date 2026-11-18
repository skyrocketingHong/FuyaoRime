"""Validate tone resources and their inclusion in generated configuration packages."""

from io import BytesIO
from pathlib import Path
import importlib.util
import stat
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("readings", ROOT / "scripts/fetch_radical_readings.py")
READINGS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READINGS)
DATA = b"Rime::Reverse/3.1" + b"\0" * 80


def archive_bytes(entries):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return stream.getvalue()


class ReadingResourceTests(unittest.TestCase):
    def test_only_requested_dictionary_is_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "data/zdict.reverse.bin"
            data = archive_bytes([(READINGS.MEMBER, DATA), ("../../escape.lua", b"unrelated")])
            READINGS.install_dictionary(data, dest)
            self.assertEqual(dest.read_bytes(), DATA)
            self.assertEqual([p.name for p in Path(temp).rglob("*") if p.is_file()], [dest.name])

    def test_invalid_resource_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "zdict.reverse.bin"
            dest.write_bytes(DATA)
            for entries in ([], [(READINGS.MEMBER, b"not a Rime dictionary")]):
                with self.subTest(entries=entries), self.assertRaises(ValueError):
                    READINGS.install_dictionary(archive_bytes(entries), dest)
                self.assertEqual(dest.read_bytes(), DATA)

    def test_symlinks_and_oversized_members_are_rejected(self):
        info = zipfile.ZipInfo(READINGS.MEMBER)
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(ValueError):
            READINGS.read_dictionary(archive_bytes([(info, DATA)]))
        with self.assertRaises(ValueError):
            READINGS.read_dictionary(archive_bytes([(READINGS.MEMBER, DATA * 100000)]))

    def test_merge_renames_base_configuration_and_retains_schemes_and_words(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("scripts", "upstream/base", "upstream/radical-readings", "overlay/lua"):
                (root / name).mkdir(parents=True)
            for script in ("merge.sh", "stage_base.py"):
                (root / "scripts" / script).write_bytes((ROOT / "scripts" / script).read_bytes())
            upstream = root / "upstream/base"
            for name in ("cn_dicts", "en_dicts", "opencc", "lua"):
                (upstream / name).mkdir()
            (upstream / "LICENSE").write_text("fixture license\n")
            schemas = ["double_pinyin" + suffix for suffix in ("", "_abc", "_flypy", "_mspy", "_sogou", "_ziguang", "_jiajia")]
            dual = ("schema:\n  schema_id: {name}\n  description: |\n"
                    "    雾凇拼音 - 双拼\n    https://github.com/iDvel/rime-ice\n"
                    "translator:\n  dictionary: rime_ice\n  prism: {name}\n")
            for name in schemas:
                (upstream / f"{name}.schema.yaml").write_text(dual.format(name=name), encoding="utf-8")
            radical = "speller:\n  algebra:\n    __include: algebra_rime_ice\nalgebra_rime_ice: []\n"
            (upstream / "radical_pinyin.schema.yaml").write_text(radical)
            pinyin = "schema:\n  schema_id: rime_ice\n  name: 雾凇拼音\npin_cand_filter:\n  - d\t的\n"
            t9 = "__include: rime_ice.schema.yaml:/\nschema:\n  schema_id: t9\ntranslator:\n  prism: t9\n"
            (upstream / "rime_ice.schema.yaml").write_text(pinyin, encoding="utf-8")
            vocabulary = "雾凇\twu song\t2\n"
            dictionary = "# https://github.com/iDvel/rime-ice\n---\nname: rime_ice\n...\n" + vocabulary
            (upstream / "rime_ice.dict.yaml").write_text(dictionary, encoding="utf-8")
            (upstream / "t9.schema.yaml").write_text(t9)
            (upstream / "default.yaml").write_text("schema_list:\n  - schema: rime_ice\n  - schema: t9\n")
            (upstream / "recipe.yaml").write_text("install_files: >-\n  rime_ice.schema.yaml\n  rime_ice.dict.yaml\n")
            readings = root / "upstream/radical-readings/zdict.reverse.bin"
            readings.write_bytes(DATA)
            patch = ROOT / "overlay/fuyao_rime.custom.yaml"
            (root / "overlay" / patch.name).write_bytes(patch.read_bytes())
            lua = ROOT / "overlay/lua/fuyao_radical.lua"
            (root / "overlay/lua/fuyao_radical.lua").write_bytes(lua.read_bytes())
            subprocess.run(["bash", str(root / "scripts/merge.sh")], check=True, capture_output=True)
            output = root / "output"
            self.assertEqual((output / "build/zdict.reverse.bin").read_bytes(), DATA)
            self.assertEqual((output / "lua/fuyao_radical.lua").read_bytes(), lua.read_bytes())
            self.assertEqual((output / patch.name).read_bytes(), patch.read_bytes())
            self.assertFalse(list(output.glob("rime_ice*")))
            self.assertEqual((output / "fuyao_rime.schema.yaml").read_text(),
                             pinyin.replace("schema_id: rime_ice", "schema_id: fuyao_rime")
                             .replace("name: 雾凇拼音", "name: Fuyao Rime"))
            self.assertEqual((output / "t9.schema.yaml").read_text(),
                             t9.replace("rime_ice.schema.yaml", "fuyao_rime.schema.yaml"))
            self.assertEqual((output / "fuyao_rime.dict.yaml").read_text(), "---\nname: fuyao_rime\n...\n" + vocabulary)
            self.assertEqual((upstream / "rime_ice.dict.yaml").read_text(), dictionary)
            self.assertEqual((output / "radical_pinyin.schema.yaml").read_text(),
                             radical.replace("algebra_rime_ice", "algebra_fuyao_rime"))
            self.assertIn("- schema: fuyao_rime", (output / "default.yaml").read_text())
            self.assertIn("  fuyao_rime.schema.yaml\n  fuyao_rime.dict.yaml", (output / "recipe.yaml").read_text())
            self.assertIn(b'"translator/user_dict": fuyao_rime', (output / patch.name).read_bytes())
            for name in schemas:
                expected = (f"schema:\n  schema_id: {name}\n  description: |\n    Fuyao Rime - 双拼\n"
                            f"translator:\n  dictionary: fuyao_rime\n  prism: {name}\n")
                self.assertEqual((output / f"{name}.schema.yaml").read_text(), expected)
                self.assertFalse((output / f"{name}.custom.yaml").exists())
            # Missing resources must stop before removing the last usable output.
            readings.unlink()
            result = subprocess.run(["bash", str(root / "scripts/merge.sh")], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((output / "build/zdict.reverse.bin").read_bytes(), DATA)
            # A changed upstream reference must also leave the previous output intact.
            readings.write_bytes(DATA)
            (upstream / "t9.schema.yaml").write_text(t9.replace("rime_ice.schema.yaml", "other.yaml"))
            result = subprocess.run(["bash", str(root / "scripts/merge.sh")], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((output / "build/zdict.reverse.bin").read_bytes(), DATA)


if __name__ == "__main__":
    unittest.main()
