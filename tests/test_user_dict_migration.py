"""Verify migration preserves backup data and writes a separate Rime snapshot."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "updater/migrate_user_dict.py"
SNAPSHOT = ("\ufeff#@/db_name\trime_ice\r\n#@/db_type\tuserdb\r\n#@/tick\t24\r\n"
            "ce shi \t测试 rime_ice\tc=12 d=0.8 t=24\r\n").encode("utf-8")


class UserDictMigrationTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="fuyaorime migration test ")
        self.addCleanup(workspace.cleanup)
        self.folder = Path(workspace.name)
        self.source = self.folder / "rime_ice.userdb.txt"

    def convert(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.source)],
                              capture_output=True, text=True)

    def test_conversion_preserves_entries_and_existing_snapshots(self):
        self.source.write_bytes(SNAPSHOT)
        existing = self.folder / "fuyao_rime.userdb.txt"
        existing.write_bytes(b"existing snapshot")
        results = [self.convert(), self.convert()]
        outputs = []
        for result in results:
            self.assertEqual(result.returncode, 0, result.stderr)
            output = Path(result.stdout.rstrip("\n"))
            self.assertEqual(output.name, "fuyao_rime.userdb.txt")
            self.assertEqual(output.parent.parent, self.folder)
            self.assertEqual(output.read_bytes(),
                             SNAPSHOT.replace(b"/db_name\trime_ice", b"/db_name\tfuyao_rime"))
            outputs.append(output)
        self.assertNotEqual(*outputs)
        self.assertEqual(self.source.read_bytes(), SNAPSHOT)
        self.assertEqual(existing.read_bytes(), b"existing snapshot")

    def test_invalid_snapshot_does_not_create_output(self):
        cases = [
            SNAPSHOT.replace(b"/db_name\trime_ice", b"/db_name\tfuyao_rime"),
            SNAPSHOT + b"#@/db_name\trime_ice\r\n",
            SNAPSHOT.replace(b"/db_type\tuserdb", b"/db_type\tother"),
            b"not a snapshot",
        ]
        for content in cases:
            with self.subTest(content=content):
                self.source.write_bytes(content)
                result = self.convert()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(list(self.folder.iterdir()), [self.source])
