"""Offline updater regressions; downloads and input-method deployment are stubbed."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
LATEST = "20261004"
FULL = f"fuyaorime-{LATEST}.zip"
LATEST_URL = "https://github.com/skyrocketingHong/FuyaoRime/releases/latest"

BASH_RUNNER = r'''
source "$FUYAORIME_SCRIPT" "$FUYAORIME_FIXTURE/rime"
curl() {
    local url
    for url in "$@"; do :; done
    printf '%s\n' "$url" >> "$FUYAORIME_FIXTURE/lookups"
    [ "$url" = 'https://github.com/skyrocketingHong/FuyaoRime/releases/latest' ] || return 22
    [ "$(cat "$FUYAORIME_FIXTURE/lookup-status")" = 0 ] || return 22
    cat "$FUYAORIME_FIXTURE/latest-url"
}
fetch() {
    local name="${1##*/}"
    printf '%s\n' "$name" >> "$FUYAORIME_FIXTURE/requests"
    [ -f "$FUYAORIME_FIXTURE/assets/$name" ] || return 1
    cp "$FUYAORIME_FIXTURE/assets/$name" "$2"
}
redeploy() { touch "$FUYAORIME_FIXTURE/redeployed"; }
main
'''

POWERSHELL_RUNNER = r'''
. $Env:FUYAORIME_SCRIPT -RimeDir (Join-Path $Env:FUYAORIME_FIXTURE 'rime')
function Invoke-RestMethod { throw 'REST API must not be called' }
function Invoke-WebRequest {
    param([switch]$UseBasicParsing, [string]$Method, [string]$Uri, [int]$TimeoutSec)
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'lookups') $Uri
    if ($Uri -ne 'https://github.com/skyrocketingHong/FuyaoRime/releases/latest') {
        throw 'REST API must not be called'
    }
    if ((Get-Content (Join-Path $Env:FUYAORIME_FIXTURE 'lookup-status')) -ne '0') {
        throw 'Release page unavailable'
    }
    $url = [Uri](Get-Content (Join-Path $Env:FUYAORIME_FIXTURE 'latest-url'))
    [PSCustomObject]@{ BaseResponse = [PSCustomObject]@{
        RequestMessage = [PSCustomObject]@{ RequestUri = $url }
    } }
}
function Save-Asset([string]$Url, [string]$Dest) {
    $name = ($Url -split '/')[-1]
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'requests') $name
    Copy-Item (Join-Path $Env:FUYAORIME_FIXTURE "assets/$name") $Dest -ErrorAction Stop
}
function Invoke-Redeploy {
    New-Item (Join-Path $Env:FUYAORIME_FIXTURE 'redeployed') -ItemType File | Out-Null
}
Update-FuyaoRime
'''


class UpdaterCases:
    platform = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fuyaorime-test-")
        self.addCleanup(self.temp.cleanup)
        self.fixture = Path(self.temp.name)
        self.rime = self.fixture / "rime"
        self.rime.mkdir()
        self.assets = self.fixture / "assets"
        self.assets.mkdir()
        self.marker = self.rime / "fuyaorime-version.txt"
        self.marker.write_text("20261003\n")
        (self.rime / "config.yaml").write_text("old")
        (self.rime / "obsolete.yaml").write_text("old")
        (self.rime / "personal.userdb").write_text("user data")
        self.archive(FULL, {"config.yaml": "full", "added.yaml": "new"})
        self.latest_url = LATEST_URL.replace('/latest', f'/tag/v{LATEST}')
        self.lookup_status = 0

    def archive(self, name, files):
        with zipfile.ZipFile(self.assets / name, "w", zipfile.ZIP_DEFLATED) as package:
            for path, content in files.items():
                package.writestr(path, content)

    def diff(self, base="20261003", target=LATEST, metadata=None):
        if metadata is None:
            metadata = f"适用版本: {base} -> {target}"
        readme = (
            f"FuyaoRime 增量更新包\n\n{metadata}\n\n"
            "以下 1 个文件已从配置包移除，可手动删除（不删除一般不影响使用）:\n"
            "  - obsolete.yaml\n"
        )
        name = f"fuyaorime-{target}-diff-from-{base}.zip"
        self.archive(name, {"INCREMENTAL-README.txt": readme, "config.yaml": "diff"})
        return name

    def run_update(self, success=True):
        (self.fixture / "requests").unlink(missing_ok=True)
        (self.fixture / "redeployed").unlink(missing_ok=True)
        (self.fixture / "lookups").unlink(missing_ok=True)
        (self.fixture / "latest-url").write_text(self.latest_url)
        (self.fixture / "lookup-status").write_text(str(self.lookup_status))
        env = dict(os.environ, FUYAORIME_FIXTURE=str(self.fixture))
        extension = "ps1" if self.platform == "windows" else "sh"
        env["FUYAORIME_SCRIPT"] = str(ROOT / "updater" / f"fuyaorime-update-{self.platform}.{extension}")
        if self.platform == "windows":
            runner = self.fixture / "runner.ps1"
            runner.write_text(POWERSHELL_RUNNER, encoding="utf-8-sig")
            command = [shutil.which("pwsh"), "-NoProfile", "-File", str(runner)]
        else:
            command = ["/bin/bash", "-c", BASH_RUNNER]
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        requests = self.fixture / "requests"
        return requests.read_text().splitlines() if requests.exists() else []

    def assert_installed(self, source):
        self.assertEqual((self.rime / "config.yaml").read_text(), source)
        self.assertEqual(self.marker.read_text().strip(), LATEST)
        self.assertEqual((self.rime / "personal.userdb").read_text(), "user data")
        self.assertTrue((self.fixture / "redeployed").exists())

    def test_missing_or_invalid_marker_uses_full(self):
        for value in (None, "", "unknown"):
            with self.subTest(marker=value):
                if value is None:
                    self.marker.unlink(missing_ok=True)
                else:
                    self.marker.write_text(value)
                requests = self.run_update()
                self.assertEqual(requests[-1], FULL)
                self.assert_installed("full")

    def test_matching_base_uses_diff_and_deletions(self):
        name = self.diff()
        self.assertEqual(self.run_update(), [name])
        self.assert_installed("diff")
        self.assertFalse((self.rime / "obsolete.yaml").exists())
        self.assertFalse((self.rime / "INCREMENTAL-README.txt").exists())

    def test_skipped_releases_use_full_without_chaining(self):
        self.marker.write_text("20261001\n")
        first = self.diff(base="20261001", target="20261002")
        self.diff(base="20261002", target="20261003")
        self.diff()
        requests = self.run_update()
        self.assertNotIn(first, requests)
        self.assertIn(FULL, requests)
        self.assert_installed("full")

    def test_release_gap_uses_declared_base_not_calendar_day(self):
        self.marker.write_text("20261001\n")
        name = self.diff(base="20261001")
        self.assertEqual(self.run_update(), [name])
        self.assert_installed("diff")

    def test_bad_metadata_is_rejected_before_writing(self):
        for metadata in ("适用版本: 20261002 -> 20261004", "适用版本: 20261003 -> 20261005", ""):
            with self.subTest(metadata=metadata):
                self.marker.write_text("20261003\n")
                (self.rime / "obsolete.yaml").write_text("keep")
                self.diff(metadata=metadata)
                self.assertIn(FULL, self.run_update())
                self.assert_installed("full")
                self.assertEqual((self.rime / "obsolete.yaml").read_text(), "keep")

    def test_missing_or_corrupt_diff_uses_full(self):
        for content in (None, b"invalid zip"):
            with self.subTest(content=content):
                self.marker.write_text("20261003\n")
                if content is not None:
                    (self.assets / f"fuyaorime-{LATEST}-diff-from-20261003.zip").write_bytes(content)
                self.assertIn(FULL, self.run_update())
                self.assert_installed("full")

    def test_current_or_newer_version_is_not_overwritten(self):
        for version in (LATEST, "20261005"):
            with self.subTest(version=version):
                self.marker.write_text(version + "\n")
                self.assertEqual(self.run_update(), [])
                self.assertEqual(self.marker.read_text().strip(), version)
                self.assertEqual((self.rime / "config.yaml").read_text(), "old")
                self.assertFalse((self.fixture / "redeployed").exists())

    def test_full_download_failure_preserves_old_version(self):
        (self.assets / FULL).unlink()
        self.run_update(success=False)
        self.assertEqual(self.marker.read_text().strip(), "20261003")
        self.assertEqual((self.rime / "config.yaml").read_text(), "old")
        self.assertFalse((self.fixture / "redeployed").exists())

    def test_latest_version_lookup_does_not_require_api(self):
        self.marker.write_text(LATEST + "\n")
        self.assertEqual(self.run_update(), [])
        self.assertEqual((self.fixture / "lookups").read_text().splitlines(), [LATEST_URL])

    def test_invalid_release_redirect_leaves_configuration_untouched(self):
        for url in (LATEST_URL, LATEST_URL.replace('/latest', '/tag/nightly'),
                    self.latest_url.replace('FuyaoRime', 'OtherRepo')):
            with self.subTest(url=url):
                self.latest_url = url
                self.assertEqual(self.run_update(success=False), [])
                self.assertEqual(self.marker.read_text().strip(), "20261003")
                self.assertEqual((self.rime / "config.yaml").read_text(), "old")

    def test_release_lookup_failure_leaves_configuration_untouched(self):
        self.lookup_status = 22
        self.assertEqual(self.run_update(success=False), [])
        self.assertEqual(self.marker.read_text().strip(), "20261003")
        self.assertEqual((self.rime / "config.yaml").read_text(), "old")

    def test_interrupted_write_invalidates_marker(self):
        if self.platform == "windows":
            self.skipTest("Unix unzip conflict fixture")
        self.diff()
        (self.rime / "config.yaml").unlink()
        (self.rime / "config.yaml").mkdir()
        self.run_update(success=False)
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.fixture / "redeployed").exists())


class MacOSUpdaterTests(UpdaterCases, unittest.TestCase):
    platform = "macos"


class LinuxUpdaterTests(UpdaterCases, unittest.TestCase):
    platform = "linux"


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell is not installed")
class WindowsUpdaterTests(UpdaterCases, unittest.TestCase):
    platform = "windows"


if __name__ == "__main__":
    unittest.main()
