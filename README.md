<h1 align="center">FuyaoRime</h1>

<p align="center">
  基于雾凇拼音、万象语言模型与扩展词库的 Rime 配置，每日自动同步发布
</p>

<p align="center">
  <a href="https://github.com/skyrocketingHong/FuyaoRime/actions/workflows/sync.yml"><img src="https://img.shields.io/github/actions/workflow/status/skyrocketingHong/FuyaoRime/sync.yml?branch=main&label=Sync" alt="Sync workflow status"></a>
  <a href="https://github.com/skyrocketingHong/FuyaoRime/releases/latest"><img src="https://img.shields.io/github/v/release/skyrocketingHong/FuyaoRime?label=Release" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue" alt="GPL-3.0"></a>
</p>

FuyaoRime 将[雾凇拼音](https://github.com/iDvel/rime-ice)、[万象语言模型](https://github.com/amzxyz/RIME-LMDG)和扩展词库合并为配置包，供鼠须管、小狼毫、Linux Rime、小企鹅输入法及元书使用。

- 保留全拼、七种双拼、九键、部件拆字和英文方案。
- 全拼加入万象语言模型、扩展词库、模糊音，以及带调注音的拆字混输。
- macOS 和 Windows 提供薄荷绿、柑橘黄皮肤，含明暗变体。
- 提供四平台更新脚本和元书快捷指令。

## 安装

安装对应平台的 Rime 客户端，从 [Releases](https://github.com/skyrocketingHong/FuyaoRime/releases/latest) 下载配置包。

| 文件 | 用途 |
| --- | --- |
| `fuyaorime-YYYYMMDD.zip` | 首次安装、跨版更新或无法确认本地版本时使用 |
| `fuyaorime-YYYYMMDD-diff-from-YYYYMMDD.zip` | 仅用于从 `from` 后的版本更新到目标版本 |

同日修订带 `-vN` 后缀，例如 `v20261010-v2`；下载包使用相同版本名。

1. 备份现有配置，将包内文件覆盖到下表目录。
2. 使用增量包时，先核对 `INCREMENTAL-README.txt` 的适用版本，再按删除清单移除旧文件。
3. 从输入法菜单重新部署。Android 可使用下方脚本，元书见 [iOS 使用说明](updater/IOS.md)。

| 平台 | 默认配置目录 |
| --- | --- |
| macOS | `~/Library/Rime/` |
| Windows | `%APPDATA%\Rime\` |
| Linux | `${XDG_CONFIG_HOME:-$HOME/.config}/rime/`，以客户端设置为准 |
| Android | `/storage/emulated/0/Android/data/org.fcitx.fcitx5.android/files/data/rime/` |

手动覆盖配置后删除 `fuyaorime-version.txt`，让更新脚本下次使用全量包重建版本基线。

## 自动更新

脚本优先使用与本地版本匹配的增量包；无有效标记、跨版或增量包不可用时下载全量包。已是最新版本时跳过，本地版本较新时不降级。

更新保留 `installation.yaml`、`userdb` 和所有 `*.userdb`；同名配置会被覆盖，全量更新不清空目录。写入失败后，下次运行会使用全量包。

下载有进度和阶段提示。版本查询直连 GitHub，无需 Token。脚本不在配置包中，升级脚本需重新执行下载命令。

### macOS

使用系统自带的 Bash、`curl` 和 `unzip`。

```bash
mkdir -p "$HOME/bin" "$HOME/Library/Logs"
curl -fL -o "$HOME/bin/fuyaorime-update-macos.sh" \
  https://raw.githubusercontent.com/skyrocketingHong/FuyaoRime/main/updater/fuyaorime-update-macos.sh
bash "$HOME/bin/fuyaorime-update-macos.sh"
```

### Linux

需要 Bash、`curl` 和 `unzip`。脚本会尝试重启 fcitx5 或 ibus；定时任务中无法自动部署时，手动重新部署一次。

```bash
mkdir -p "$HOME/bin" "$HOME/.local/state"
curl -fL -o "$HOME/bin/fuyaorime-update-linux.sh" \
  https://raw.githubusercontent.com/skyrocketingHong/FuyaoRime/main/updater/fuyaorime-update-linux.sh
bash "$HOME/bin/fuyaorime-update-linux.sh"
```

macOS 和 Linux 均可将自定义配置目录作为第一个参数：

```bash
bash "$HOME/bin/fuyaorime-update-linux.sh" "/path/to/rime"
```

### Windows

使用 Windows PowerShell 5.1 或更高版本。更新前会退出小狼毫，完成后部署并恢复服务，更新期间请暂停输入。找不到部署器时按提示手动部署。

```powershell
Invoke-WebRequest -UseBasicParsing `
  -Uri https://raw.githubusercontent.com/skyrocketingHong/FuyaoRime/main/updater/fuyaorime-update-windows.ps1 `
  -OutFile "$env:USERPROFILE\fuyaorime-update-windows.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\fuyaorime-update-windows.ps1"
```

自定义目录使用 `-RimeDir 'D:\Rime'`。

### Android：小企鹅输入法

需要 [Termux](https://termux.dev)、[Shizuku](https://github.com/RikkaApps/Shizuku) 和 `rish`。

1. 在 Termux 执行 `termux-setup-storage`，再安装依赖：`pkg install curl unzip cronie termux-services`。
2. 启动 Shizuku，导出 `rish` 和 `rish_shizuku.dex`。将两者放到 Termux 私有目录；Android 14 起不能从共享存储直接运行 dex。
3. 下载并运行脚本：

```bash
mkdir -p "$HOME/bin"
cp /storage/emulated/0/Download/rish /storage/emulated/0/Download/rish_shizuku.dex "$HOME/bin/"
chmod 755 "$HOME/bin/rish"
curl -fL -o "$HOME/bin/fuyaorime-update-android.sh" \
  https://raw.githubusercontent.com/skyrocketingHong/FuyaoRime/main/updater/fuyaorime-update-android.sh
bash "$HOME/bin/fuyaorime-update-android.sh"
```

脚本通过 Shizuku 写入配置，随后强制停止输入法；再次启用输入法时会自动部署。手机重启后需重新启动 Shizuku。

| 参数 | 用途 |
| --- | --- |
| 第一个位置参数 | 自定义 Rime 配置目录 |
| `--ime-package` | 指定输入法包名，例如 fxliang 改版的 `org.fcitx.fcitx5.android.fx` |
| `--rish` | 指定 rish 路径 |
| `--staging-root` | 指定共享暂存目录，默认为 `Download`，结束后清理 |

### iOS：元书

使用一体更新快捷指令，见[导入与使用说明](updater/IOS.md)。字体设置见[字体清单](FONTS.md)。

### 下载代理

| 平台 | 参数 |
| --- | --- |
| macOS、Linux、Android | `--github-proxy <代理前缀>` |
| Windows | `-GitHubProxy <代理前缀>` |

默认直连。代理前缀使用完整 HTTP(S) 地址，不含查询串或片段；仅影响配置包下载，版本查询仍直连 GitHub。定时任务可追加相同参数。

<details>
<summary>每日定时更新</summary>

以下示例在本机时间 09:00 运行，添加前先手动运行成功。新 Release 尚未发布时，脚本会使用最近已发布的版本。

macOS：执行 `crontab -e`，添加：

```cron
0 9 * * * /bin/bash "$HOME/bin/fuyaorime-update-macos.sh" >> "$HOME/Library/Logs/fuyaorime-update.log" 2>&1
```

Linux：执行 `crontab -e`，添加：

```cron
0 9 * * * /bin/bash "$HOME/bin/fuyaorime-update-linux.sh" >> "$HOME/.local/state/fuyaorime-update.log" 2>&1
```

Termux：先执行 `sv-enable crond`，再执行 `crontab -e` 添加：

```cron
0 9 * * * /data/data/com.termux/files/usr/bin/bash "$HOME/bin/fuyaorime-update-android.sh" >> "$HOME/fuyaorime-update.log" 2>&1
```

休眠可能延迟任务，可使用 `termux-wake-lock` 或调整电池优化。

Windows：在命令提示符中执行：

```bat
schtasks /Create /SC DAILY /ST 09:00 /TN "FuyaoRime Update" ^
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"%USERPROFILE%\fuyaorime-update-windows.ps1\""
```

停用时删除对应 crontab 行，或执行 `schtasks /Delete /TN "FuyaoRime Update" /F`。

</details>

## 输入方案与自定义

| 方案 | `schema_id` |
| --- | --- |
| 雾凇拼音全拼 | `rime_ice` |
| 自然码双拼 | `double_pinyin` |
| 智能 ABC 双拼 | `double_pinyin_abc` |
| 微软双拼 | `double_pinyin_mspy` |
| 搜狗双拼 | `double_pinyin_sogou` |
| 小鹤双拼 | `double_pinyin_flypy` |
| 紫光双拼 | `double_pinyin_ziguang` |
| 拼音加加双拼 | `double_pinyin_jiajia` |
| 中文九键（默认注释） | `t9` |
| 部件拆字 | `radical_pinyin` |
| Easy English Nano | `melt_eng` |

额外词库包括中文维基百科、维基文库、维基词典、萌娘百科、网络俚语、中国地名、流行新词、中文人名、成语俗语、古诗词名句和唐诗三百首。

语言模型、额外词库、模糊音和拆字混输用于全拼，双拼保持上游配置。英文方案共用三字母小写派生，例如输入 `ios` 可匹配 `iOS`。标点按全角处理，输入网址或代码时可切换英文模式。

全拼可直接输入部件拼音，例如 `mamama` 得到骉、驫及词典收录的带调读音，也支持 `ma'ma'ma` 和原有的 `uUmamama` 反查。普通候选前三项优先，随后最多插入两个完整匹配的拆字候选；同码先排有注音的字，再优先基本汉字区，结果去重。不做拆字补全、造句或用户词频学习，未收录读音时标注“拆字”。

| 配置项 | 源文件 |
| --- | --- |
| 启用方案、标点 | [default.custom.yaml](overlay/default.custom.yaml) |
| 全拼模型、模糊音、拆字设置 | [rime_ice.custom.yaml](overlay/rime_ice.custom.yaml) |
| 额外词库引用 | [rime_ice.custom.dict.yaml](overlay/rime_ice.custom.dict.yaml) |
| 英文派生 | [melt_eng.custom.yaml](overlay/melt_eng.custom.yaml) |
| 拆字混输实现 | [fuyao_radical.lua](overlay/lua/fuyao_radical.lua) |
| macOS 皮肤 | [squirrel.custom.yaml](overlay/squirrel.custom.yaml) |
| Windows 皮肤 | [weasel.custom.yaml](overlay/weasel.custom.yaml) |

字体顺序、下载和元书对应设置见 [FONTS.md](FONTS.md)。添加词库时，将 `.dict.yaml` 放入 `custom_dicts/`，并在 `rime_ice.custom.dict.yaml` 的 `import_tables` 中引用；其他方案使用各自的 `<schema_id>.custom.yaml`。

## 同步与构建

[同步工作流](.github/workflows/sync.yml)每日计划在北京时间 05:00 运行，GitHub Actions 可能延迟。也可在 [Actions](https://github.com/skyrocketingHong/FuyaoRime/actions/workflows/sync.yml) 手动触发；`revision=2` 生成当天的 `-v2` 修订版，`release_note` 填写主要变化。增量基线取目标版本之前最近的稳定版。

<details>
<summary>手动构建</summary>

在已有 Python 环境中安装依赖并运行：

```bash
git clone https://github.com/skyrocketingHong/FuyaoRime.git
cd FuyaoRime
git clone --depth 1 https://github.com/iDvel/rime-ice.git upstream/rime-ice
python3 scripts/fetch_radical_readings.py

mkdir -p upstream/wanxiang
curl -fL -o upstream/wanxiang/wanxiang-lts-zh-hans.gram \
  https://github.com/amzxyz/RIME-LMDG/releases/download/LTS/wanxiang-lts-zh-hans.gram

python3 -m pip install pypinyin opencc regex more-itertools
python3 scripts/update_dicts.py
python3 scripts/build_zhwiki.py
bash scripts/merge.sh
```

结果位于 `output/`，复制到配置目录后重新部署。自行构建的配置没有 Release 基线，使用更新脚本前删除旧版本标记。

`fetch_radical_readings.py` 获取 `build/zdict.reverse.bin` 带调注音词典，资源缺失时构建会停止。已有资源包可使用 `--archive /path/to/extra.zip`。离线检查：

```bash
python3 -m unittest discover -s tests -p 'test_radical_readings.py' -v
```

真实引擎测试见 [test_radical_engine.py](tests/test_radical_engine.py)，需 PyYAML、Rime 探针、引擎及 Lua 插件，并设置 `RIME_PROBE`、`RIME_LIBRARY`、`RIME_LUA_PLUGIN`。

</details>

## 来源与许可

- [雾凇拼音](https://github.com/iDvel/rime-ice)：基础配置和词库。
- [部件拆字](https://github.com/mirtlecn/rime-radical-pinyin)：拆字词库与带调注音。
- [万象拼音](https://github.com/amzxyz/rime_wanxiang)、[万象语言模型](https://github.com/amzxyz/RIME-LMDG)。
- [fcitx5-pinyin-zhwiki](https://github.com/felixonmars/fcitx5-pinyin-zhwiki)、[Wikimedia Dumps](https://dumps.wikimedia.org/)：维基系词库。
- [萌娘百科词库](https://github.com/outloudvi/mw2fcitx)。
- [搜狗词库](https://pinyin.sogou.com)、[深蓝词库转换](https://github.com/studyzy/imewlconverter)。
- [中文姓名语料](https://github.com/wainshine/Chinese-Names-Corpus)、[pypinyin](https://github.com/mozillazg/pypinyin)。

配置包遵循 [GPL-3.0](LICENSE)。本项目主要供作者个人使用，不接受功能建议与定制请求，仅接受可复现的同步失败或配置错误报告。

## AI 辅助开发

本项目在开发过程中使用生成式 AI 协助编码。

[![Vibe PR](https://raw.githubusercontent.com/fenxer/llm-things/main/stickers/vibe-pr.svg)](https://github.com/fenxer/llm-things/blob/main/stickers/vibe-pr.svg)
