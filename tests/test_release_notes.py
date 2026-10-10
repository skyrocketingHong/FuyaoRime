"""Release revision selection, package-derived file changes and source links."""

from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('release_notes', ROOT / 'scripts/release_notes.py')
NOTES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NOTES)


class ReleaseNotesTests(unittest.TestCase):
    def test_previous_release_uses_revision_order_and_excludes_unpublished(self):
        releases = [{'tag_name': tag} for tag in ('v20261009', 'v20261010-v2', 'v20261010',
                                                'v20261010-v10', 'v20261011', 'nightly')]
        releases += [{'tag_name': 'v20261010-v11', 'draft': True},
                     {'tag_name': 'v20261010-v12', 'prerelease': True}]
        self.assertEqual(NOTES.previous_release(releases, '20261010-v2'), 'v20261010')
        self.assertEqual(NOTES.previous_release(releases, '20261011'), 'v20261010-v10')

    def test_diff_classifies_added_modified_deleted_and_release_uses_same_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'output'
            output.mkdir()
            (output / 'same.yaml').write_text('same')
            (output / 'changed.yaml').write_text('new')
            (output / 'added.lua').write_text('added')
            previous = root / 'previous.zip'
            with zipfile.ZipFile(previous, 'w') as archive:
                for name, text in [('same.yaml', 'same'), ('changed.yaml', 'old'), ('deleted.yaml', 'old')]:
                    archive.writestr(name, text)
            diff = root / 'diff.zip'
            report = root / 'summary.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/make_diff_package.py'), str(output),
                            str(previous), str(diff), '20261010', '20261010-v2', '--summary', str(report)],
                           check=True, capture_output=True)
            summary = json.loads(report.read_text())
            self.assertEqual(summary['added'], ['added.lua'])
            self.assertEqual(summary['modified'], ['changed.yaml'])
            self.assertEqual(summary['deleted'], ['deleted.yaml'])
            with zipfile.ZipFile(diff) as archive:
                self.assertEqual(set(archive.namelist()), {'INCREMENTAL-README.txt', 'added.lua', 'changed.yaml'})
                text = archive.read('INCREMENTAL-README.txt').decode()
                self.assertIn('适用版本: 20261010 -> 20261010-v2', text)
                self.assertIn('新增文件（1 个）:', text)
                self.assertIn('修改文件（1 个）:', text)
                self.assertIn('以下 1 个文件已从配置包移除', text)
            notes = NOTES.render(output, '20261010-v2', summary, '全拼增加拆字候选和带调注音。')
            self.assertIn('新增 1 个、修改 1 个、删除 1 个', notes)
            self.assertIn('fuyaorime-20261010-v2-diff-from-20261010.zip', notes)
            for name in ('added.lua', 'changed.yaml', 'deleted.yaml'):
                self.assertIn(f'`{name}`', notes)
            self.assertNotIn('—', notes)

    def test_every_dictionary_has_a_source_and_actual_version(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            for folder in ('custom_dicts', 'cn_dicts', 'en_dicts'):
                (output / folder).mkdir()
            for key in NOTES.EXTRA_SOURCES:
                (output / 'custom_dicts' / f'{key}.dict.yaml').write_text('---\nversion: "20261001"\n...\n')
            (output / 'cn_dicts/base.dict.yaml').write_text('---\nversion: "2026.10.01"\n...\n')
            (output / 'en_dicts/cn_en.txt').write_text('fixture')
            rows = NOTES.source_rows(output)
            self.assertEqual(len(rows), len(NOTES.EXTRA_SOURCES) + 2)
            self.assertTrue(all(url.startswith('https://') for _, url, _ in rows))
            self.assertIn('2026.10.01', [version for _, _, version in rows])
            (output / 'custom_dicts/unknown.dict.yaml').write_text('---\nversion: "1"\n...\n')
            with self.assertRaises(ValueError):
                NOTES.source_rows(output)

    def test_mismatched_diff_metadata_is_not_published(self):
        with self.assertRaises(ValueError):
            NOTES.render(Path('.'), '20261010-v2', {'from': '20261009', 'to': '20261010'})

    def test_version_can_follow_a_long_dictionary_header(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'base.dict.yaml'
            path.write_text('# source notes\n' * 3300 + '---\nversion: "2026-09-20"\n...\n')
            self.assertEqual(NOTES.dictionary_version(path), '2026-09-20')


if __name__ == '__main__':
    unittest.main()
