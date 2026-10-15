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
DOWNLOAD_URL = f"https://github.com/skyrocketingHong/FuyaoRime/releases/download/v{LATEST}/"
POWERSHELL = (shutil.which("powershell") if os.name == "nt" else None) or shutil.which("pwsh")

BASH_RUNNER = r'''
args=("$FUYAORIME_FIXTURE/rime")
if [ -n "$FUYAORIME_PROXY" ]; then args+=(--github-proxy "$FUYAORIME_PROXY"); fi
source "$FUYAORIME_SCRIPT" "${args[@]}"
curl() {
    local url='' dest='' name
    while [ "$#" -gt 0 ]; do
        case "$1" in
            -o) dest="$2"; shift ;;
            https://*) url="$1" ;;
        esac
        shift
    done
    if [ "$url" = 'https://github.com/skyrocketingHong/FuyaoRime/releases/latest' ]; then
        printf '%s\n' "$url" >> "$FUYAORIME_FIXTURE/lookups"
        [ "$(cat "$FUYAORIME_FIXTURE/lookup-status")" = 0 ] || return 22
        cat "$FUYAORIME_FIXTURE/latest-url"
        return
    fi
    printf '%s\n' "$url" >> "$FUYAORIME_FIXTURE/downloads"
    name="${url##*/}"
    printf '%s\n' "$name" >> "$FUYAORIME_FIXTURE/requests"
    [ -f "$FUYAORIME_FIXTURE/assets/$name" ] || return 1
    cp "$FUYAORIME_FIXTURE/assets/$name" "$dest"
}
redeploy() { touch "$FUYAORIME_FIXTURE/redeployed"; }
main
'''

ANDROID_RUNNER = r'''
args=("$FUYAORIME_FIXTURE/rime" --rish "$FUYAORIME_FIXTURE/rish" --staging-root "$FUYAORIME_FIXTURE/staging")
if [ -n "$FUYAORIME_PROXY" ]; then args+=(--github-proxy "$FUYAORIME_PROXY"); fi
source "$FUYAORIME_SCRIPT" "${args[@]}"
curl() {
    local url='' dest='' name
    while [ "$#" -gt 0 ]; do
        case "$1" in
            -o) dest="$2"; shift ;;
            https://*) url="$1" ;;
        esac
        shift
    done
    if [ "$url" = 'https://github.com/skyrocketingHong/FuyaoRime/releases/latest' ]; then
        printf '%s\n' "$url" >> "$FUYAORIME_FIXTURE/lookups"
        [ "$(cat "$FUYAORIME_FIXTURE/lookup-status")" = 0 ] || return 22
        cat "$FUYAORIME_FIXTURE/latest-url"
        return
    fi
    printf '%s\n' "$url" >> "$FUYAORIME_FIXTURE/downloads"
    name="${url##*/}"
    printf '%s\n' "$name" >> "$FUYAORIME_FIXTURE/requests"
    [ -f "$FUYAORIME_FIXTURE/assets/$name" ] || return 1
    cp "$FUYAORIME_FIXTURE/assets/$name" "$dest"
}
main
'''

# 模拟 Shizuku 的 rish：以 -c 执行单条命令，am 调用映射为重启标记。
RISH_STUB = '''#!/usr/bin/env bash
if [ "$#" -ne 2 ] || [ "$1" != "-c" ]; then
    echo "rish stub: expected -c <command>" >&2
    exit 2
fi
am() {
    touch "$FUYAORIME_FIXTURE/redeployed"
    printf 'am %s\\n' "$*" >> "$FUYAORIME_FIXTURE/am-calls"
}
eval "$2"
'''

POWERSHELL_RUNNER = r'''
$ErrorActionPreference = 'Stop'
. $Env:FUYAORIME_SCRIPT -RimeDir (Join-Path $Env:FUYAORIME_FIXTURE 'rime') -GitHubProxy $Env:FUYAORIME_PROXY
function Invoke-RestMethod { throw 'REST API must not be called' }
function Invoke-WebRequest {
    param([switch]$UseBasicParsing, [string]$Method, [string]$Uri, [int]$TimeoutSec, [string]$OutFile)
    if ($OutFile) {
        Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'downloads') $Uri
        $name = ($Uri -split '/')[-1]
        Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'requests') $name
        Microsoft.PowerShell.Management\Copy-Item (Join-Path $Env:FUYAORIME_FIXTURE "assets/$name") $OutFile -ErrorAction Stop
        return
    }
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
function Enter-WeaselUpdateLock {
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'lifecycle') 'lock'
    if (Test-Path (Join-Path $Env:FUYAORIME_FIXTURE 'deployment-active')) {
        throw 'Another deployment is active'
    }
    $lock = [PSCustomObject]@{}
    $lock | Add-Member -MemberType ScriptMethod -Name Dispose -Value {
        Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'lifecycle') 'unlock'
    }
    return $lock
}
function Get-WeaselServerState {
    if (-not (Test-Path (Join-Path $Env:FUYAORIME_FIXTURE 'server-running'))) { return $null }
    return [PSCustomObject]@{
        Process = [PSCustomObject]@{ HasExited = $false }
        ExecutablePath = Join-Path $Env:FUYAORIME_FIXTURE 'weasel/WeaselServer.exe'
        InstallDir = Join-Path $Env:FUYAORIME_FIXTURE 'weasel'
    }
}
function Stop-WeaselServer($State) {
    if (-not $State) { return }
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'lifecycle') 'stop'
    if (Test-Path (Join-Path $Env:FUYAORIME_FIXTURE 'stop-fails')) { throw 'Server did not exit' }
    Remove-Item (Join-Path $Env:FUYAORIME_FIXTURE 'server-running')
    $State.Process.HasExited = $true
}
$copyPackageFiles = ${function:Copy-PackageFiles}
function Copy-PackageFiles([string]$Source, [string]$RelativePath = '') {
    if (-not $RelativePath) { Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'lifecycle') 'copy' }
    & $copyPackageFiles $Source $RelativePath
}
function Copy-Item {
    [CmdletBinding()]
    param([string]$LiteralPath, [string]$Destination, [switch]$Force)
    if ((Test-Path (Join-Path $Env:FUYAORIME_FIXTURE 'copy-fails')) -and
        $Destination -eq (Join-Path $Env:FUYAORIME_FIXTURE 'rime/config.yaml')) {
        throw 'The requested operation cannot be performed on a file with a user-mapped section open.'
    }
    Microsoft.PowerShell.Management\Copy-Item @PSBoundParameters
}
function Invoke-Redeploy([string]$InstallDir) {
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'lifecycle') 'deploy'
    Set-Content (Join-Path $Env:FUYAORIME_FIXTURE 'deploy-install-dir') $InstallDir
    Copy-Item -LiteralPath $Marker -Destination (Join-Path $Env:FUYAORIME_FIXTURE 'deploy-version')
    New-Item (Join-Path $Env:FUYAORIME_FIXTURE 'redeployed') -ItemType File | Out-Null
}
function Restore-WeaselServer($State) {
    if (-not $State) { return }
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'lifecycle') 'restore'
    New-Item (Join-Path $Env:FUYAORIME_FIXTURE 'server-running') -ItemType File -Force | Out-Null
}
Update-FuyaoRime
'''


class UpdaterCases:
    platform = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fuyaorime test-")
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
        self.protected = {
            "installation.yaml": "local installation",
            "rime_ice.userdb/CURRENT": "local database head",
            "rime_ice.userdb/000001.ldb": "local learned words",
            "double_pinyin.userdb/CURRENT": "other schema database",
            "userdb/records": "local database container",
            "nested/installation.yaml": "nested installation",
            "nested/another.userdb/data": "nested learned words",
        }
        for name, value in self.protected.items():
            target = self.rime / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value)
        self.archive(FULL, {"config.yaml": "full", "added.yaml": "new"})
        self.latest_url = LATEST_URL.replace('/latest', f'/tag/v{LATEST}')
        self.lookup_status = 0
        self.proxy = ""

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
        (self.fixture / "downloads").unlink(missing_ok=True)
        (self.fixture / "redeployed").unlink(missing_ok=True)
        (self.fixture / "lookups").unlink(missing_ok=True)
        (self.fixture / "lifecycle").unlink(missing_ok=True)
        (self.fixture / "latest-url").write_text(self.latest_url)
        (self.fixture / "lookup-status").write_text(str(self.lookup_status))
        env = dict(os.environ, FUYAORIME_FIXTURE=str(self.fixture), FUYAORIME_PROXY=self.proxy)
        extension = "ps1" if self.platform == "windows" else "sh"
        env["FUYAORIME_SCRIPT"] = str(ROOT / "updater" / f"fuyaorime-update-{self.platform}.{extension}")
        if self.platform == "windows":
            runner = self.fixture / "runner.ps1"
            runner.write_text(POWERSHELL_RUNNER, encoding="utf-8-sig")
            command = [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(runner)]
        elif self.platform == "android":
            command = ["/bin/bash", "-c", ANDROID_RUNNER]
        else:
            command = ["/bin/bash", "-c", BASH_RUNNER]
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
        self.result = result
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
        for name, value in self.protected.items():
            self.assertEqual((self.rime / name).read_text(), value, name)

    def test_full_update_preserves_installation_and_databases(self):
        self.marker.unlink()
        files = {name: "incoming user data" for name in self.protected}
        files.update({"config.yaml": "full", "INSTALLATION.YAML": "wrong identity",
                      "UPPER.USERDB/data": "wrong database", "new.userdb/data": "foreign database"})
        self.archive(FULL, files)
        self.run_update()
        self.assert_installed("full")
        self.assertFalse((self.rime / "new.userdb").exists())
        self.assertFalse((self.rime / "UPPER.USERDB").exists())

    def test_diff_cannot_overwrite_or_delete_user_data(self):
        readme = "适用版本: 20261003 -> 20261004\n\n已从配置包移除\n"
        readme += "".join(f"  - {name}\n" for name in [*self.protected, "rime_ice.userdb", "obsolete.yaml"])
        files = {name: "incoming user data" for name in self.protected}
        files.update({"config.yaml": "diff", "INCREMENTAL-README.txt": readme})
        self.archive(f"fuyaorime-{LATEST}-diff-from-20261003.zip", files)
        self.run_update()
        self.assert_installed("diff")
        self.assertFalse((self.rime / "obsolete.yaml").exists())

    def test_diff_does_not_delete_parent_directories(self):
        readme = "适用版本: 20261003 -> 20261004\n\n已从配置包移除\n  - nested\n"
        self.archive(f"fuyaorime-{LATEST}-diff-from-20261003.zip",
                     {"config.yaml": "diff", "INCREMENTAL-README.txt": readme})
        self.run_update()
        self.assert_installed("diff")

    def test_diff_rejects_deletion_outside_configuration(self):
        outside = self.fixture / "outside.yaml"
        outside.write_text("keep")
        readme = "适用版本: 20261003 -> 20261004\n\n已从配置包移除\n  - ../outside.yaml\n"
        self.archive(f"fuyaorime-{LATEST}-diff-from-20261003.zip",
                     {"config.yaml": "diff", "INCREMENTAL-README.txt": readme})
        self.run_update(success=False)
        self.assertEqual(outside.read_text(), "keep")

    def test_update_rejects_link_to_user_data(self):
        alias = self.rime / "alias.yaml"
        try:
            alias.symlink_to(self.rime / "installation.yaml")
        except OSError:
            self.skipTest("Symbolic links are unavailable")
        self.archive(FULL, {"config.yaml": "full", "alias.yaml": "wrong identity"})
        self.run_update(success=False)
        self.assertEqual((self.rime / "installation.yaml").read_text(), "local installation")
        self.assertFalse((self.fixture / "redeployed").exists())

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
        self.assertEqual((self.fixture / "downloads").read_text().splitlines(), [DOWNLOAD_URL + name])
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

    def test_same_day_revision_uses_matching_diff(self):
        target = LATEST + "-v2"
        self.latest_url = LATEST_URL.replace('/latest', f'/tag/v{target}')
        self.marker.write_text(LATEST + "\n")
        name = self.diff(base=LATEST, target=target)
        self.assertEqual(self.run_update(), [name])
        self.assertEqual(self.marker.read_text().strip(), target)
        self.assertEqual((self.rime / "config.yaml").read_text(), "diff")

    def test_revision_comparison_is_numeric_and_date_takes_precedence(self):
        self.marker.write_text(LATEST + "-v10\n")
        self.latest_url = LATEST_URL.replace('/latest', f'/tag/v{LATEST}-v2')
        self.assertEqual(self.run_update(), [])
        self.assertEqual(self.marker.read_text().strip(), LATEST + "-v10")
        target = "20261005"
        self.latest_url = LATEST_URL.replace('/latest', f'/tag/v{target}')
        name = self.diff(base=LATEST + "-v10", target=target)
        self.assertEqual(self.run_update(), [name])
        self.assertEqual(self.marker.read_text().strip(), target)

    def test_revision_two_can_update_to_revision_ten(self):
        self.marker.write_text(LATEST + "-v2\n")
        target = LATEST + "-v10"
        self.latest_url = LATEST_URL.replace('/latest', f'/tag/v{target}')
        name = self.diff(base=LATEST + "-v2", target=target)
        self.assertEqual(self.run_update(), [name])
        self.assertEqual(self.marker.read_text().strip(), target)

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
                    self.latest_url + '-v0', self.latest_url + '-v02', self.latest_url + '-v10000',
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

    def test_download_proxy_routes_full_and_diff(self):
        self.proxy = "https://downloads.example/forward/"
        name = self.diff()
        for version, asset, content in (("", FULL, "full"), ("20261003", name, "diff")):
            with self.subTest(version=version):
                self.marker.write_text(version)
                self.assertEqual(self.run_update(), [asset])
                self.assert_installed(content)
                self.assertEqual((self.fixture / "downloads").read_text().splitlines(),
                                 [self.proxy + DOWNLOAD_URL + asset])
                self.assertEqual((self.fixture / "lookups").read_text().splitlines(), [LATEST_URL])

    def test_proxy_missing_diff_falls_back_to_proxied_full(self):
        self.proxy = "https://downloads.example"
        name = f"fuyaorime-{LATEST}-diff-from-20261003.zip"
        self.assertEqual(self.run_update(), [name, FULL])
        self.assert_installed("full")
        self.assertEqual((self.fixture / "downloads").read_text().splitlines(),
                         [self.proxy + '/' + DOWNLOAD_URL + asset for asset in (name, FULL)])

    def test_invalid_proxy_fails_before_any_request(self):
        for proxy in ("file:///tmp/proxy", "https://", "https://bad host", "https://downloads.example/?token=x"):
            with self.subTest(proxy=proxy):
                self.proxy = proxy
                self.assertEqual(self.run_update(success=False), [])
                self.assertFalse((self.fixture / "lookups").exists())
                self.assertEqual(self.marker.read_text().strip(), "20261003")

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


class AndroidUpdaterTests(UpdaterCases, unittest.TestCase):
    platform = "android"

    def setUp(self):
        super().setUp()
        stub = self.fixture / "rish"
        stub.write_text(RISH_STUB)
        stub.chmod(0o755)

    def test_update_rejects_link_to_user_data(self):
        # 写入端先删后拷：同名符号链接被替换为普通文件，不跟随链接改写用户数据。
        alias = self.rime / "alias.yaml"
        try:
            alias.symlink_to(self.rime / "installation.yaml")
        except OSError:
            self.skipTest("Symbolic links are unavailable")
        self.archive(FULL, {"config.yaml": "full", "alias.yaml": "wrong identity"})
        self.run_update()
        self.assert_installed("full")
        self.assertFalse(alias.is_symlink())
        self.assertEqual((self.rime / "alias.yaml").read_text(), "wrong identity")
        self.assertEqual((self.rime / "installation.yaml").read_text(), "local installation")

    def test_restart_targets_configured_ime_package(self):
        self.diff()
        self.run_update()
        self.assertEqual((self.fixture / "am-calls").read_text().splitlines(),
                         ["am force-stop org.fcitx.fcitx5.android"])

    def test_staging_directory_is_cleaned_after_run(self):
        self.run_update()
        self.assertFalse((self.fixture / "staging" / "fuyaorime-update-staging").exists())


@unittest.skipUnless(POWERSHELL, "PowerShell is not installed")
class WindowsUpdaterTests(UpdaterCases, unittest.TestCase):
    platform = "windows"

    def lifecycle(self):
        path = self.fixture / "lifecycle"
        return path.read_text().splitlines() if path.exists() else []

    def test_server_stops_before_writing_and_restores_after_deployment(self):
        (self.fixture / "server-running").touch()
        self.diff()
        self.run_update()
        self.assertEqual(self.lifecycle(), ["lock", "stop", "copy", "unlock", "deploy", "restore"])
        self.assert_installed("diff")
        self.assertEqual((self.fixture / "deploy-version").read_text().strip(), LATEST)
        self.assertEqual((self.fixture / "deploy-install-dir").read_text().strip(), str(self.fixture / "weasel"))
        self.assertTrue((self.fixture / "server-running").exists())

    def test_interrupted_write_invalidates_marker_and_restores_server(self):
        (self.fixture / "server-running").touch()
        (self.fixture / "copy-fails").touch()
        self.diff()
        self.run_update(success=False)
        self.assertEqual(self.lifecycle(), ["lock", "stop", "copy", "unlock", "restore"])
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.fixture / "redeployed").exists())
        self.assertTrue((self.fixture / "server-running").exists())
        self.assertIn("config.yaml", self.result.stdout + self.result.stderr)

    def test_failed_stop_preserves_old_version_and_configuration(self):
        (self.fixture / "server-running").touch()
        (self.fixture / "stop-fails").touch()
        self.diff()
        self.run_update(success=False)
        self.assertEqual(self.lifecycle(), ["lock", "stop", "unlock", "restore"])
        self.assertEqual(self.marker.read_text().strip(), "20261003")
        self.assertEqual((self.rime / "config.yaml").read_text(), "old")
        self.assertTrue((self.fixture / "server-running").exists())
        self.assertFalse((self.fixture / "redeployed").exists())

    def test_active_deployment_blocks_update_before_stopping_or_writing(self):
        (self.fixture / "server-running").touch()
        (self.fixture / "deployment-active").touch()
        self.diff()
        self.run_update(success=False)
        self.assertEqual(self.lifecycle(), ["lock"])
        self.assertEqual(self.marker.read_text().strip(), "20261003")
        self.assertEqual((self.rime / "config.yaml").read_text(), "old")
        self.assertTrue((self.fixture / "server-running").exists())

    def test_download_failure_does_not_stop_server(self):
        (self.fixture / "server-running").touch()
        (self.assets / FULL).unlink()
        self.run_update(success=False)
        self.assertEqual(self.lifecycle(), [])
        self.assertTrue((self.fixture / "server-running").exists())
        self.assertEqual(self.marker.read_text().strip(), "20261003")

    def test_current_version_does_not_stop_server(self):
        (self.fixture / "server-running").touch()
        self.marker.write_text(LATEST + "\n")
        self.assertEqual(self.run_update(), [])
        self.assertEqual(self.lifecycle(), [])
        self.assertTrue((self.fixture / "server-running").exists())

    def test_previously_stopped_server_is_not_started(self):
        self.diff()
        self.run_update()
        self.assertEqual(self.lifecycle(), ["lock", "copy", "unlock", "deploy"])
        self.assertFalse((self.fixture / "server-running").exists())


@unittest.skipUnless(POWERSHELL, "PowerShell is not installed")
class WindowsWeaselHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fuyaorime process test-")
        self.addCleanup(self.temp.cleanup)
        self.fixture = Path(self.temp.name)
        (self.fixture / "weasel").mkdir()
        (self.fixture / "weasel" / "WeaselServer.exe").touch()
        (self.fixture / "weasel" / "WeaselDeployer.exe").touch()

    def run_helper(self, body, success=True, variables=None):
        runner = self.fixture / "runner.ps1"
        runner.write_text(
            "$ErrorActionPreference = 'Stop'\n"
            ". $Env:FUYAORIME_SCRIPT -RimeDir (Join-Path $Env:FUYAORIME_FIXTURE 'rime')\n" + body,
            encoding="utf-8-sig",
        )
        env = dict(os.environ, FUYAORIME_FIXTURE=str(self.fixture),
                   FUYAORIME_SCRIPT=str(ROOT / "updater" / "fuyaorime-update-windows.ps1"))
        env.update(variables or {})
        result = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(runner)],
                                env=env, capture_output=True, text=True, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_launcher_preserves_exact_argument_string(self):
        executable = shutil.which("where.exe" if os.name == "nt" else "true")
        if not executable:
            self.skipTest("No suitable system process fixture is available")
        self.run_helper(r'''
foreach ($arguments in @('/quit', '/deploy', '')) {
    $process = Start-WeaselProcess $Env:FUYAORIME_CHILD_EXE $arguments
    try {
        if ($process.StartInfo.Arguments -cne $arguments) { throw 'Argument string was changed' }
        if ($process.StartInfo.FileName -cne $Env:FUYAORIME_CHILD_EXE) { throw 'Executable path was changed' }
        if ($process.StartInfo.UseShellExecute) { throw 'Shell execution must be disabled' }
        if ($process.StartInfo.WorkingDirectory -cne (Split-Path -Parent $Env:FUYAORIME_CHILD_EXE)) {
            throw 'Unexpected working directory'
        }
        if (-not $process.WaitForExit(5000)) { $process.Kill(); throw 'Process fixture did not exit' }
    } finally {
        $process.Dispose()
    }
}
''', variables={"FUYAORIME_CHILD_EXE": executable})

    def test_quit_waits_for_original_process_and_rejects_timeout(self):
        body = r'''
$originalExited = $true
$controllerExited = $true
$process = [PSCustomObject]@{ HasExited = $false }
$process | Add-Member -MemberType ScriptMethod -Name WaitForExit -Value {
    param($Timeout)
    if ($Timeout -le 0) { throw 'Expected a bounded wait' }
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'events') 'wait-original'
    return $originalExited
}
$controller = [PSCustomObject]@{}
$controller | Add-Member -MemberType ScriptMethod -Name WaitForExit -Value {
    param($Timeout)
    if ($Timeout -le 0) { throw 'Expected a bounded wait' }
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'events') 'wait-controller'
    return $controllerExited
}
function Start-WeaselProcess {
    param($ExecutablePath, $Arguments)
    if ($Arguments -cne '/quit') { throw 'Expected an exact quit argument' }
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'events') 'quit'
    return $controller
}
Stop-WeaselServer ([PSCustomObject]@{
    Process = $process
    ExecutablePath = Join-Path $Env:FUYAORIME_FIXTURE 'weasel/WeaselServer.exe'
})
'''
        for original_exited, controller_exited in ((True, True), (False, True), (True, False)):
            with self.subTest(original_exited=original_exited, controller_exited=controller_exited):
                (self.fixture / "events").unlink(missing_ok=True)
                scenario = body
                if not original_exited:
                    scenario = scenario.replace("$originalExited = $true", "$originalExited = $false")
                if not controller_exited:
                    scenario = scenario.replace("$controllerExited = $true", "$controllerExited = $false")
                self.run_helper(scenario, success=original_exited and controller_exited)
                events = ["quit", "wait-original"]
                if original_exited:
                    events.append("wait-controller")
                self.assertEqual((self.fixture / "events").read_text().splitlines(), events)

    def test_restore_starts_only_previously_running_missing_server(self):
        self.run_helper(r'''
$session = (Get-Process -Id $PID).SessionId
$servers = @()
function Get-Process {
    [CmdletBinding()]
    param($Name, $Id)
    if ($Id) { return [PSCustomObject]@{ SessionId = $session } }
    return $servers
}
function Start-WeaselProcess {
    param($ExecutablePath, $Arguments = '')
    if ($Arguments -cne '') { throw 'Restore must not supply command arguments' }
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'starts') $ExecutablePath
}
$state = [PSCustomObject]@{
    Process = [PSCustomObject]@{ HasExited = $false }
    ExecutablePath = Join-Path $Env:FUYAORIME_FIXTURE 'weasel/WeaselServer.exe'
}
Restore-WeaselServer $null
Restore-WeaselServer $state
$state.Process.HasExited = $true
$servers = @([PSCustomObject]@{ SessionId = $session })
Restore-WeaselServer $state
if (Test-Path (Join-Path $Env:FUYAORIME_FIXTURE 'starts')) { throw 'Unexpected server start' }
$servers = @([PSCustomObject]@{ SessionId = $session + 1 })
Restore-WeaselServer $state
$servers = @([PSCustomObject]@{ SessionId = $session })
Restore-WeaselServer $state
''')
        self.assertEqual((self.fixture / "starts").read_text().splitlines(),
                         [str(self.fixture / "weasel" / "WeaselServer.exe")])

    def test_server_detection_uses_current_session_and_rejects_ambiguity(self):
        self.run_helper(r'''
$session = (Get-Process -Id $PID).SessionId
$path = Join-Path $Env:FUYAORIME_FIXTURE 'weasel/WeaselServer.exe'
$current = [PSCustomObject]@{ SessionId = $session; Path = $path }
$other = [PSCustomObject]@{ SessionId = $session + 1; Path = $path }
$servers = @($other, $current)
function Get-Process {
    [CmdletBinding()]
    param($Name, $Id)
    if ($Id) { return [PSCustomObject]@{ SessionId = $session } }
    return $servers
}
$state = Get-WeaselServerState
if ($state.Process -ne $current -or $state.ExecutablePath -ne $path -or
    $state.InstallDir -ne (Split-Path -Parent $path)) { throw 'Wrong server selected' }
$servers = @($other)
if ($null -ne (Get-WeaselServerState)) { throw 'Other session must not be selected' }
foreach ($ambiguous in @($true, $false)) {
    $servers = if ($ambiguous) { @($current, $current) } else {
        @([PSCustomObject]@{ SessionId = $session; Path = '' })
    }
    $rejected = $false
    try { Get-WeaselServerState | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw 'Unsafe server state must be rejected' }
}
''')

    def test_deployment_mutex_rejects_existing_holder_and_releases(self):
        self.run_helper(r'''
$held = Enter-WeaselUpdateLock
try {
    $rejected = $false
    try { $second = Enter-WeaselUpdateLock } catch { $rejected = $true }
    if (-not $rejected) { $second.Dispose(); throw 'Existing deployment was not rejected' }
} finally {
    $held.Dispose()
}
$next = Enter-WeaselUpdateLock
$next.Dispose()
''')

    def test_deployment_waits_and_reports_unsuccessful_exit(self):
        body = r'''
function Start-WeaselProcess {
    param($ExecutablePath, $Arguments)
    if ($Arguments -cne '/deploy') { throw 'Expected an exact deploy argument' }
    Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'deployers') $ExecutablePath
    $process = [PSCustomObject]@{ ExitCode = $null }
    $process | Add-Member -MemberType ScriptMethod -Name WaitForExit -Value {
        Add-Content (Join-Path $Env:FUYAORIME_FIXTURE 'deployers') 'wait-deployment'
        $this.ExitCode = 0
    }
    return $process
}
Invoke-Redeploy (Join-Path $Env:FUYAORIME_FIXTURE 'weasel')
'''
        for succeeded in (True, False):
            with self.subTest(succeeded=succeeded):
                (self.fixture / "deployers").unlink(missing_ok=True)
                self.run_helper(body if succeeded else body.replace("ExitCode = 0", "ExitCode = 1"),
                                success=succeeded)
                self.assertEqual((self.fixture / "deployers").read_text().splitlines(),
                                 [str(self.fixture / "weasel" / "WeaselDeployer.exe"), "wait-deployment"])


if __name__ == "__main__":
    unittest.main()
