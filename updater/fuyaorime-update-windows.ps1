<#
.SYNOPSIS
增量更新 FuyaoRime 并重新部署小狼毫（Weasel）。

.DESCRIPTION
仅在本地版本与最新增量包基线一致时使用 diff，否则下载最新全量包。
写入前校验 INCREMENTAL-README.txt 中的适用版本，不跨版串联增量包。
适用于 Windows PowerShell 5.1 及以上，可用任务计划程序每日运行。

.PARAMETER RimeDir
Rime 配置目录，默认 %APPDATA%\Rime。

.PARAMETER GitHubProxy
可选的 GitHub 下载代理前缀，默认直连。仅用于配置包下载。

.EXAMPLE
.\fuyaorime-update-windows.ps1
#>
param(
    [string]$RimeDir = (Join-Path $Env:APPDATA 'Rime'),
    # ASVS 1.2.2、2.2.1：代理前缀仅接受不含查询串、片段及空白的 HTTP(S) 地址。
    [ValidatePattern('^$|^https?://[^/?#\s]+(/[^?#\s]*)?$')]
    [string]$GitHubProxy = ''
)

$ErrorActionPreference = 'Stop'
$Repo = 'skyrocketingHong/FuyaoRime'
$GitHubProxy = $GitHubProxy.TrimEnd('/')
$Marker = Join-Path $RimeDir 'fuyaorime-version.txt'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Write-Log([string]$Message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
}

function Get-LatestVersion {
    # 公开 Release 跳转不依赖 REST API 的匿名请求额度。
    $response = Invoke-WebRequest -UseBasicParsing -Method Head `
        -Uri "https://github.com/$Repo/releases/latest" -TimeoutSec 45
    $uri = $response.BaseResponse.ResponseUri
    if (-not $uri) { $uri = $response.BaseResponse.RequestMessage.RequestUri }
    $pattern = '^https://github\.com/' + [regex]::Escape($Repo) + '/releases/tag/v([0-9]{8})$'
    if ([string]$uri.AbsoluteUri -cnotmatch $pattern) {
        throw 'Release 页面未返回有效的 FuyaoRime 日期版本'
    }
    return $Matches[1]
}

function Save-Asset([string]$Url, [string]$Dest) {
    if ($GitHubProxy) { $Url = "$GitHubProxy/$Url" }
    Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing
}

function Test-DiffVersion([string]$ReadmePath, [string]$FromVersion, [string]$ToVersion) {
    if (-not (Test-Path -LiteralPath $ReadmePath -PathType Leaf)) { return $false }
    $versions = @(Get-Content -LiteralPath $ReadmePath -Encoding UTF8 |
        Where-Object { $_ -cmatch '^适用版本:' })
    return ($versions.Count -eq 1 -and $versions[0] -ceq "适用版本: $FromVersion -> $ToVersion")
}

function Test-ProtectedPath([string]$Path) {
    foreach ($part in ($Path -split '[/\\]')) {
        if ($part.TrimEnd(' ', '.') -imatch '^(installation\.yaml|userdb|.*\.userdb)$') { return $true }
    }
    return $false
}

function Get-SafeTarget([string]$RelativePath) {
    if (-not $RelativePath -or [IO.Path]::IsPathRooted($RelativePath) -or $RelativePath.Contains(':')) {
        throw '拒绝不安全的更新路径'
    }
    $target = $RimeDir
    foreach ($part in ($RelativePath -split '[/\\]')) {
        if ($part.TrimEnd(' ') -eq '..') { throw '拒绝越出配置目录的路径' }
        if (-not $part -or $part -eq '.') { continue }
        $target = Join-Path $target $part
        if (Test-Path -LiteralPath $target) {
            $item = Get-Item -LiteralPath $target -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw '更新路径包含符号链接或目录联接，已停止'
            }
        }
    }
    return $target
}

function Copy-PackageFiles([string]$Source, [string]$RelativePath = '') {
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        $relative = if ($RelativePath) { "$RelativePath/$($item.Name)" } else { $item.Name }
        if (Test-ProtectedPath $relative) { continue }
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw '配置包包含符号链接或目录联接，已停止'
        }
        $target = Get-SafeTarget $relative
        if ($item.PSIsContainer) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
            Copy-PackageFiles $item.FullName $relative
        } else {
            if (Test-Path -LiteralPath $target -PathType Container) { throw '无法用配置文件替换已有目录' }
            Copy-Item -LiteralPath $item.FullName -Destination $target -Force
        }
    }
}

function Remove-DeletedFiles([string]$ReadmePath) {
    # 删除清单固定在"已从配置包移除"段，条目形如 "  - 相对路径"
    $inDeleted = $false
    foreach ($line in Get-Content -LiteralPath $ReadmePath -Encoding UTF8) {
        if (-not $inDeleted) {
            if ($line -match '已从配置包移除') { $inDeleted = $true }
        } elseif ($line -match '^  - (.+)$') {
            $relative = $Matches[1]
            if (Test-ProtectedPath $relative) {
                Write-Log '已忽略用户数据的删除请求'
                continue
            }
            $path = Get-SafeTarget $relative
            if (Test-Path -LiteralPath $path -PathType Leaf) { Remove-Item -LiteralPath $path -Force }
        } else {
            $inDeleted = $false
        }
    }
}

function Invoke-Redeploy {
    $roots = @("$Env:ProgramFiles\Rime", "${Env:ProgramFiles(x86)}\Rime") |
        Where-Object { $_ -and (Test-Path $_) }
    $deployer = $roots | ForEach-Object {
        Get-ChildItem -Path $_ -Recurse -Filter 'WeaselDeployer.exe' -ErrorAction SilentlyContinue
    } | Select-Object -First 1
    if ($deployer) {
        Start-Process -FilePath $deployer.FullName -ArgumentList '/deploy'
        Write-Log '已通知小狼毫重新部署'
    } else {
        Write-Log '未找到 WeaselDeployer.exe，请在小狼毫菜单手动选择"重新部署"'
    }
}

function Update-FuyaoRime {
    $latest = Get-LatestVersion

    New-Item -ItemType Directory -Path $RimeDir -Force | Out-Null
    $current = if (Test-Path -LiteralPath $Marker) { ([string](Get-Content -LiteralPath $Marker -Raw)).Trim() } else { '' }
    if ($current -eq $latest) {
        Write-Log "已是最新版本 $latest"
        return
    }
    if ($current -cmatch '^[0-9]{8}$' -and $current -gt $latest) {
        Write-Log "本地版本 $current 新于远端 $latest，跳过更新"
        return
    }

    $workDir = Join-Path ([IO.Path]::GetTempPath()) ("fuyaorime-update-" + [IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    try {
        $packageDir = Join-Path $workDir 'package'
        $useDiff = $false
        if ($current -cmatch '^[0-9]{8}$') {
            try {
                $zip = Join-Path $workDir 'diff.zip'
                Save-Asset "https://github.com/$Repo/releases/download/v$latest/fuyaorime-$latest-diff-from-$current.zip" $zip
                Expand-Archive -Path $zip -DestinationPath $packageDir -Force
                $useDiff = Test-DiffVersion (Join-Path $packageDir 'INCREMENTAL-README.txt') $current $latest
            } catch {
                Write-Log '增量包下载或解压失败，使用全量包'
            }
            if (-not $useDiff) {
                Write-Log "无匹配本地版本 $current 的有效增量包，使用全量包 $latest"
            }
        } else {
            Write-Log "未检测到本地版本标记，执行全量安装 $latest"
        }

        if (-not $useDiff) {
            if (Test-Path -LiteralPath $packageDir) {
                Remove-Item -LiteralPath $packageDir -Recurse -Force
            }
            $zip = Join-Path $workDir 'full.zip'
            Save-Asset "https://github.com/$Repo/releases/download/v$latest/fuyaorime-$latest.zip" $zip
            Expand-Archive -Path $zip -DestinationPath $packageDir -Force
        }

        # 写入中断后无法再信任旧基线，下次运行须使用全量包。
        if (Test-Path -LiteralPath $Marker) { Remove-Item -LiteralPath $Marker -Force }
        Copy-PackageFiles $packageDir
        if ($useDiff) {
            Remove-DeletedFiles (Join-Path $packageDir 'INCREMENTAL-README.txt')
            Remove-Item -LiteralPath (Join-Path $RimeDir 'INCREMENTAL-README.txt') -Force
            Write-Log "已应用增量包 $current -> $latest"
        } else {
            Write-Log "已应用全量包 $latest"
        }
        Set-Content -Path $Marker -Value $latest -Encoding ASCII
    } finally {
        Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    Invoke-Redeploy
}

if ($MyInvocation.InvocationName -ne '.') {
    Update-FuyaoRime
}
