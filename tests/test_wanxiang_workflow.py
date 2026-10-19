"""Exercise the actual Wanxiang workflow step with offline GitHub/curl fixtures."""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASSET = 'wanxiang-lts-zh-hans.gram'
STEP = (ROOT / '.github/workflows/sync.yml').read_text().split(
    '      - name: Download wanxiang grammar\n', 1)[1].split('\n      - name:', 1)[0]
SCRIPT = textwrap.dedent(STEP.split('        run: |\n', 1)[1])
STUB = '''#!/usr/bin/env python3
from pathlib import Path
import os, sys

tool = Path(sys.argv[0]).name
args = sys.argv[1:]
with open('calls.txt', 'a') as handle:
    handle.write(tool + '\\n')
if tool == 'gh':
    assert os.environ.get('GH_TOKEN') == 'fixture-token'
    assert args == ['api', 'repos/amzxyz/RIME-LMDG/releases/tags/LTS']
    if os.environ['API_FAILURE'] == '1':
        print('gh: API rate limit exceeded (HTTP 403)', file=sys.stderr)
        sys.exit(1)
    print(Path('release-fixture.json').read_text())
elif any('api.github.com' in arg for arg in args):
    print(Path('release-fixture.json').read_text())
else:
    assert '-f' in args or '-fL' in args or '--fail' in args
    destination = Path(args[args.index('-o') + 1])
    destination.write_bytes(b'' if os.environ['EMPTY_DOWNLOAD'] == '1' else b'fixture-model')
    sys.exit(int(os.environ['DOWNLOAD_EXIT']))
'''


class WanxiangWorkflowTests(unittest.TestCase):
    def run_step(self, metadata, *, api_failure=False, download_exit=0, empty=False):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binaries = directory / 'bin'
            binaries.mkdir()
            for name in ('gh', 'curl'):
                path = binaries / name
                path.write_text(STUB)
                path.chmod(0o755)
            (binaries / 'python3').symlink_to(sys.executable)
            (directory / 'release-fixture.json').write_text(json.dumps(metadata))
            environment = os.environ | {
                'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
                'GH_TOKEN': 'fixture-token',
                'API_FAILURE': str(int(api_failure)),
                'DOWNLOAD_EXIT': str(download_exit),
                'EMPTY_DOWNLOAD': str(int(empty)),
            }
            result = subprocess.run(['bash', '-eo', 'pipefail', '-c', SCRIPT],
                                    cwd=directory, env=environment, capture_output=True, text=True)
            calls = (directory / 'calls.txt').read_text().splitlines()
            output = directory / 'upstream/wanxiang'
            files = {path.name: path.read_bytes() for path in output.iterdir()}
            return result, calls, files

    def metadata(self, timestamp='2026-10-17T09:59:19Z'):
        return {'assets': [{'name': 'other.gram', 'updated_at': '2025-01-01T00:00:00Z'},
                           {'name': ASSET, 'updated_at': timestamp}]}

    def test_authenticated_metadata_precedes_download(self):
        self.assertIn('GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}', STEP)
        result, calls, files = self.run_step(self.metadata())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['gh', 'curl'])
        self.assertEqual(files[ASSET], b'fixture-model')
        self.assertEqual(files['version.txt'], b'20261017\n')

    def test_version_uses_asset_update_date_in_beijing(self):
        result, _, files = self.run_step(self.metadata('2026-10-17T20:00:00Z'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(files['version.txt'], b'20261018\n')

    def test_api_failure_stops_before_download(self):
        result, calls, files = self.run_step({'message': 'API rate limit exceeded'}, api_failure=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HTTP 403', result.stderr)
        self.assertEqual(calls, ['gh'])
        self.assertNotIn('version.txt', files)
        self.assertNotIn(ASSET, files)

    def test_invalid_metadata_stops_before_download(self):
        duplicate = self.metadata()
        duplicate['assets'].append(duplicate['assets'][-1])
        for metadata in ({'message': 'Not Found'}, [], {'assets': []},
                         {'assets': None}, duplicate, self.metadata(None),
                         self.metadata('2026-02-30T00:00:00Z')):
            with self.subTest(metadata=metadata):
                result, calls, files = self.run_step(metadata)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, ['gh'])
                self.assertNotIn('version.txt', files)
                self.assertNotIn(ASSET, files)

    def test_download_failure_does_not_record_version(self):
        for exit_code, empty in ((22, False), (18, False), (0, True)):
            with self.subTest(exit_code=exit_code, empty=empty):
                result, calls, files = self.run_step(self.metadata(), download_exit=exit_code, empty=empty)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, ['gh', 'curl'])
                self.assertNotIn('version.txt', files)


if __name__ == '__main__':
    unittest.main()
