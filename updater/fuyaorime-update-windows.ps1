<#
.SYNOPSIS
增量更新 FuyaoRime 并重新部署小狼毫（Weasel）。

.DESCRIPTION
首次运行（无版本标记）下载全量包，此后只下载增量包；跨多天时按发布链
逐个应用，任一环缺失即回退全量包，避免跳版漏文件。删除清单从增量包内
INCREMENTAL-README.txt 解析（格式由 make_diff_package.py 固定）。
适用于 Windows PowerShell 5.1 及以上，可用任务计划程序每日运行。

.PARAMETER RimeDir
Rime 配置目录，默认 %APPDATA%\Rime。

.EXAMPLE
.\fuyaorime-update-windows.ps1
#>
param([string]$RimeDir = (Join-Path $Env:APPDATA 'Rime'))

$ErrorActionPreference = 'Stop'
$Repo = 'skyrocketingHong/FuyaoRime'
$Marker = Join-Path $RimeDir 'fuyaorime-version.txt'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Write-Log([string]$Message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
}

function Get-Releases {
    # 匿名限频 60 次/小时；设置环境变量 GITHUB_TOKEN 可解除限制
    $headers = @{ 'User-Agent' = 'FuyaoRime-Updater' }
    if ($Env:GITHUB_TOKEN) { $headers['Authorization'] = "Bearer $Env:GITHUB_TOKEN" }
    Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases?per_page=100" `
        -Headers $headers
}

function Get-DiffAsset($Releases, [string]$Tag, [string]$FromVersion) {
    $Releases | Where-Object { $_.tag_name -eq "v$Tag" } |
        ForEach-Object { $_.assets } |
        Where-Object { $_.name -eq "fuyaorime-$Tag-diff-from-$FromVersion.zip" } |
        Select-Object -First 1
}

function Save-Asset([string]$Url, [string]$Dest) {
    Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing
}

function Remove-DeletedFiles([string]$ReadmePath) {
    # 删除清单固定在「已从配置包移除」段，条目形如「  - 相对路径」
    $inDeleted = $false
    foreach ($line in Get-Content $ReadmePath -Encoding UTF8) {
        if (-not $inDeleted) {
            if ($line -match '已从配置包移除') { $inDeleted = $true }
        } elseif ($line -match '^  - (.+)$') {
            Remove-Item -LiteralPath (Join-Path $RimeDir $Matches[1]) -Force -ErrorAction SilentlyContinue
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
        Write-Log '未找到 WeaselDeployer.exe，请在小狼毫菜单手动选择「重新部署」'
    }
}

function Update-FuyaoRime {
    $releases = Get-Releases
    $tags = @($releases | ForEach-Object { $_.tag_name.TrimStart('v') } | Sort-Object -Unique)
    if ($tags.Count -eq 0) {
        throw '未解析到任何 release'
    }
    $latest = $tags[-1]

    New-Item -ItemType Directory -Path $RimeDir -Force | Out-Null
    $current = if (Test-Path $Marker) { (Get-Content $Marker -Raw).Trim() } else { '' }
    if ($current -eq $latest) {
        Write-Log "已是最新版本 $latest"
        return
    }

    $workDir = Join-Path ([IO.Path]::GetTempPath()) ("fuyaorime-update-" + [IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    try {
        if ($current -notmatch '^\d{8}$') {
            Write-Log "未检测到本地版本标记，执行全量安装 $latest"
            $zip = Join-Path $workDir 'full.zip'
            Save-Asset "https://github.com/$Repo/releases/download/v$latest/fuyaorime-$latest.zip" $zip
            Expand-Archive -Path $zip -DestinationPath $RimeDir -Force
        } else {
            Write-Log "本地版本 $current，开始增量更新到 $latest"
            foreach ($tag in ($tags | Where-Object { $_ -gt $current })) {
                $asset = Get-DiffAsset $releases $tag $current
                if (-not $asset) { break }
                $zip = Join-Path $workDir 'diff.zip'
                Save-Asset $asset.browser_download_url $zip
                Expand-Archive -Path $zip -DestinationPath $RimeDir -Force
                $readme = Join-Path $RimeDir 'INCREMENTAL-README.txt'
                if (Test-Path $readme) {
                    Remove-DeletedFiles $readme
                    Remove-Item $readme -Force
                }
                $current = $tag
            }
            if ($current -ne $latest) {
                Write-Log '增量链中断，回退全量包'
                $zip = Join-Path $workDir 'full.zip'
                Save-Asset "https://github.com/$Repo/releases/download/v$latest/fuyaorime-$latest.zip" $zip
                Expand-Archive -Path $zip -DestinationPath $RimeDir -Force
            }
        }
    } finally {
        Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    Set-Content -Path $Marker -Value $latest -Encoding ASCII
    Invoke-Redeploy
}

Update-FuyaoRime
