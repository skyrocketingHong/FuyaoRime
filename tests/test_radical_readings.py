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

    def test_merge_preserves_all_double_pinyin_schemas_and_packages_readings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("scripts", "upstream/rime-ice", "upstream/radical-readings", "overlay/lua"):
                (root / name).mkdir(parents=True)
            (root / "scripts/merge.sh").write_bytes((ROOT / "scripts/merge.sh").read_bytes())
            upstream = root / "upstream/rime-ice"
            for name in ("cn_dicts", "en_dicts", "opencc", "lua"):
                (upstream / name).mkdir()
            (upstream / "LICENSE").write_text("fixture license\n")
            schemas = ["double_pinyin" + suffix for suffix in ("", "_abc", "_flypy", "_mspy", "_sogou", "_ziguang", "_jiajia")]
            for name in schemas + ["rime_ice", "radical_pinyin"]:
                (upstream / f"{name}.schema.yaml").write_text(f"schema:\n  schema_id: {name}\n")
            readings = root / "upstream/radical-readings/zdict.reverse.bin"
            readings.write_bytes(DATA)
            patch = ROOT / "overlay/rime_ice.custom.yaml"
            (root / "overlay/rime_ice.custom.yaml").write_bytes(patch.read_bytes())
            lua = ROOT / "overlay/lua/fuyao_radical.lua"
            (root / "overlay/lua/fuyao_radical.lua").write_bytes(lua.read_bytes())
            subprocess.run(["bash", str(root / "scripts/merge.sh")], check=True, capture_output=True)
            output = root / "output"
            self.assertEqual((output / "build/zdict.reverse.bin").read_bytes(), DATA)
            self.assertEqual((output / "lua/fuyao_radical.lua").read_bytes(), lua.read_bytes())
            self.assertEqual((output / patch.name).read_bytes(), patch.read_bytes())
            for name in schemas:
                filename = f"{name}.schema.yaml"
                self.assertEqual((output / filename).read_bytes(), (upstream / filename).read_bytes())
                self.assertFalse((output / f"{name}.custom.yaml").exists())
            # Missing resources must stop before removing the last usable output.
            readings.unlink()
            result = subprocess.run(["bash", str(root / "scripts/merge.sh")], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((output / "build/zdict.reverse.bin").read_bytes(), DATA)


if __name__ == "__main__":
    unittest.main()
