<h1 align="center">FuyaoRime</h1>

<p align="center">
  基于雾凇拼音、万象语言模型与扩展词库的 Rime 配置，每日自动同步发布
</p>

<p align="center">
  <a href="https://github.com/skyrocketingHong/FuyaoRime/actions/workflows/sync.yml"><img src="https://img.shields.io/github/actions/workflow/status/skyrocketingHong/FuyaoRime/sync.yml?branch=main&label=Sync" alt="Sync workflow status"></a>
  <a href="https://github.com/skyrocketingHong/FuyaoRime/releases/latest"><img src="https://img.shields.io/github/v/release/skyrocketingHong/FuyaoRime?label=Release" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue" alt="GPL-3.0"></a>
</p>

FuyaoRime 将[雾凇拼音](https://github.com/iDvel/rime-ice)的配置与词库、[万象语言模型](https://github.com/amzxyz/RIME-LMDG)及额外词库合并为配置包，供鼠须管、小狼毫和 Linux Rime 客户端使用。

- 保留雾凇拼音的全拼、七种双拼、九键、部件拆字与英文方案。
- 为全拼配置万象语言模型、额外词库和模糊音。
- 提供 macOS 与 Windows 的薄荷绿、柑橘黄皮肤，均含明暗变体。
- 每日计划于北京时间 05:00 触发同步，完成后发布全量包和增量包；GitHub Actions 的实际运行与发布时间可能延迟。

## 安装配置

先安装对应平台的 Rime 客户端，再从 [Releases](https://github.com/skyrocketingHong/FuyaoRime/releases/latest) 下载配置包。

| 配置包 | 使用条件 |
| :--- | :--- |
| `fuyaorime-YYYYMMDD.zip` | 全量包。首次安装、跨版更新或无法确认本地版本时使用 |
| `fuyaorime-YYYYMMDD-diff-from-YYYYMMDD.zip` | 增量包。仅适用于已安装版本与 `from` 后日期完全一致的配置 |

例如，`fuyaorime-20261004-diff-from-20261003.zip` 只能用于从 `20261003` 更新到 `20261004`；本地若是 `20261001`，应下载全量包。

1. 备份现有配置。使用增量包时，先核对包内 `INCREMENTAL-README.txt` 的适用版本与本地版本是否一致。
2. 将包内文件解压覆盖到客户端实际使用的 Rime 配置目录；使用增量包时按其中的删除清单移除旧文件。
3. 在输入法菜单中重新部署 Rime。

| 平台 | 更新脚本的默认配置目录 |
| :--- | :--- |
| macOS | `~/Library/Rime/` |
| Windows | `%APPDATA%\Rime\` |
| Linux | `${XDG_CONFIG_HOME:-$HOME/.config}/rime/` |

不同 Linux 客户端可能使用不同目录，请以客户端的实际设置为准。自动更新脚本也支持传入自定义目录。

`fuyaorime-version.txt` 由更新脚本维护。手动覆盖配置后应删除旧标记，让脚本下次以全量包重新建立版本基线；不要仅修改标记来跳过安装。

## 自动更新

[`updater/`](updater/) 中的脚本通过 GitHub `/releases/latest` 的公开跳转查询最新版本，下载配置并尝试重新部署输入法。客户端更新无需 GitHub Token，也不依赖 REST API 的匿名请求额度。

| 本地状态 | 更新方式 |
| :--- | :--- |
| 无版本标记或标记无效 | 安装最新全量包 |
| 与最新版本一致 | 跳过更新 |
| 比远端版本更新 | 保留本地配置，不降级 |
| 最新 diff 包的基线与本地版本一致，且包内适用版本校验通过 | 应用该增量包及删除清单 |
| 跨版、没有匹配的 diff 包，或增量包下载、校验失败 | 下载最新全量包 |

脚本不会串联历史增量包。写入配置前会使旧版本标记失效，全部文件处理成功后再记录新版本；写入失败后的下一次运行使用全量包。

全量安装采用覆盖方式，不会清空配置目录，也不会自动清理历史版本遗留的全部文件。自行修改的同名配置会被覆盖，请保留备份。

桌面脚本会跳过 `installation.yaml`、`userdb` 和所有 `*.userdb` 数据库及其内部文件，更新包覆盖与增量删除清单均不能修改这些路径；其他目录也不会因删除清单而被整目录删除。此保护针对更新器的文件操作，输入法重新部署时仍按自身规则处理用户数据。

### macOS

依赖系统自带的 Bash、`curl` 和 `unzip`，重新部署使用鼠须管的 `--reload`。

```bash
mkdir -p "$HOME/bin" "$HOME/Library/Logs"
curl -fsSL -o "$HOME/bin/fuyaorime-update-macos.sh" \
  https://raw.githubusercontent.com/skyrocketingHong/FuyaoRime/main/updater/fuyaorime-update-macos.sh
bash "$HOME/bin/fuyaorime-update-macos.sh"
```

### Linux

需要 Bash、`curl` 和 `unzip`。脚本会尝试重启正在运行的 fcitx5，或执行 `ibus restart`。

```bash
mkdir -p "$HOME/bin" "$HOME/.local/state"
curl -fsSL -o "$HOME/bin/fuyaorime-update-linux.sh" \
  https://raw.githubusercontent.com/skyrocketingHong/FuyaoRime/main/updater/fuyaorime-update-linux.sh
bash "$HOME/bin/fuyaorime-update-linux.sh"
```

配置目录不同时，将实际路径作为第一个参数传入：

```bash
bash "$HOME/bin/fuyaorime-update-linux.sh" "/path/to/rime"
```

macOS 脚本接受相同参数。Linux 定时任务缺少图形会话环境时，可能需要在更新后手动重新部署。

### Windows

使用 Windows PowerShell 5.1 或更高版本。脚本会在 Rime 安装目录中查找 `WeaselDeployer.exe` 并执行 `/deploy`；找不到时会提示手动部署。

```powershell
Invoke-WebRequest -UseBasicParsing `
  -Uri https://raw.githubusercontent.com/skyrocketingHong/FuyaoRime/main/updater/fuyaorime-update-windows.ps1 `
  -OutFile "$env:USERPROFILE\fuyaorime-update-windows.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\fuyaorime-update-windows.ps1"
```

自定义目录可通过 `-RimeDir 'D:\Rime'` 传入。更新脚本不包含在配置包中，需要升级脚本时重新执行对应平台的下载命令。

### 可选下载代理

默认直连 GitHub，不预设代理网站。需要通过 GitHub 下载转发服务获取配置包时，可传入以下参数：

| 平台 | 参数 |
| :--- | :--- |
| macOS、Linux | `--github-proxy <代理前缀>` |
| Windows | `-GitHubProxy <代理前缀>` |

代理前缀为完整的 HTTP(S) 地址，可包含服务路径，不含查询串或片段。脚本按“代理前缀 + `/` + 原始 GitHub 下载地址”拼接，仅影响全量包和 diff 包下载；版本查询仍直连 GitHub。省略参数即恢复直连，定时任务可在脚本命令后添加同一参数。

### iOS：元书输入法

提供一体更新快捷指令的[生成脚本](updater/build_ios_shortcut.py)和[使用说明](updater/IOS.md)，依次完成版本查询、全量包下载、解压覆盖和请求元书部署。下载代理前缀可选，保存时跳过方案根目录的安装信息和用户数据库；iPhone 端的运行行为需在首次使用时确认。

### 每日定时

以下示例按本机时区在 09:00 运行。GitHub Actions 的定时任务可能延迟，请根据 Release 的实际发布时间安排客户端更新；运行时新包尚未发布，脚本会使用最近已发布的版本。先手动执行一次脚本，确认日志中的安装结果与版本标记，再添加定时任务。

macOS：执行 `crontab -e`，添加一行：

```cron
0 9 * * * /bin/bash "$HOME/bin/fuyaorime-update-macos.sh" >> "$HOME/Library/Logs/fuyaorime-update.log" 2>&1
```

Linux：执行 `crontab -e`，添加一行，配置目录不同时在命令后补充实际路径：

```cron
0 9 * * * /bin/bash "$HOME/bin/fuyaorime-update-linux.sh" >> "$HOME/.local/state/fuyaorime-update.log" 2>&1
```

Windows：在命令提示符中创建任务：

```bat
schtasks /Create /SC DAILY /ST 09:00 /TN "FuyaoRime Update" ^
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"%USERPROFILE%\fuyaorime-update-windows.ps1\""
```

停用时删除对应的 crontab 行，或执行 `schtasks /Delete /TN "FuyaoRime Update" /F`。版本查询或下载失败时，检查网络能否访问 GitHub Release 页面及其下载资源。

## 输入方案与词库

| 输入方案 | `schema_id` | 默认状态 |
| :--- | :--- | :--- |
| 雾凇拼音（全拼） | `rime_ice` | 启用 |
| 自然码双拼 | `double_pinyin` | 启用 |
| 智能 ABC 双拼 | `double_pinyin_abc` | 启用 |
| 微软双拼 | `double_pinyin_mspy` | 启用 |
| 搜狗双拼 | `double_pinyin_sogou` | 启用 |
| 小鹤双拼 | `double_pinyin_flypy` | 启用 |
| 紫光双拼 | `double_pinyin_ziguang` | 启用 |
| 拼音加加双拼 | `double_pinyin_jiajia` | 启用 |
| 中文九键 | `t9` | 注释，按需启用 |
| 部件拆字 | `radical_pinyin` | 作为反查与辅码使用 |
| Easy English Nano | `melt_eng` | 作为英文次翻译器使用 |

配置包包含雾凇拼音的中文词库、英文及中英混合词库、OpenCC 映射和 Lua 扩展。额外词库包括中文维基百科、维基文库、维基词典、萌娘百科、网络俚语、中国地名、流行新词、中文人名、成语俗语、古诗词名句和唐诗三百首。

语言模型、额外词库和模糊音默认仅作用于全拼；双拼保持上游配置。英文方案另有三字母全小写派生补丁，例如输入 `ios` 可匹配 `iOS`，全拼和双拼均可使用。

标点按全角映射处理，包括数字和字母后的标点。输入网址、邮箱或代码时可切换英文模式。

## 自定义配置

在仓库中修改以下文件后重新合并配置；直接修改已安装配置时，使用配置目录下对应的文件名。

| 配置项 | 源文件 |
| :--- | :--- |
| 启用方案、标点规则 | [`overlay/default.custom.yaml`](overlay/default.custom.yaml) |
| 全拼语言模型、模糊音及其他设置 | [`overlay/rime_ice.custom.yaml`](overlay/rime_ice.custom.yaml) |
| 额外词库引用 | [`overlay/rime_ice.custom.dict.yaml`](overlay/rime_ice.custom.dict.yaml) |
| 英文拼写派生 | [`overlay/melt_eng.custom.yaml`](overlay/melt_eng.custom.yaml) |
| macOS 皮肤 | [`overlay/squirrel.custom.yaml`](overlay/squirrel.custom.yaml) |
| Windows 皮肤 | [`overlay/weasel.custom.yaml`](overlay/weasel.custom.yaml) |

添加词库时，将 `.dict.yaml` 文件放入 `custom_dicts/`，并在 `rime_ice.custom.dict.yaml` 的 `import_tables` 中添加引用。定制其他方案时新增对应的 `<schema_id>.custom.yaml`，不要直接复制全拼的模糊音拼写规则到双拼方案。

## 同步与构建

[`sync.yml`](.github/workflows/sync.yml) 使用 `0 21 * * *`，计划每天 UTC 21:00（北京时间次日 05:00）触发。GitHub Actions 不保证准点运行，负载较高时可能延后，详见[官方调度说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

工作流同步雾凇拼音、万象语言模型和额外词库，再叠加 `overlay/` 生成配置包。维基百科、维基文库和维基词典另按月从 Wikimedia 标题数据构建，网络俚语每日检查页面变化。同步也可在 [Actions](https://github.com/skyrocketingHong/FuyaoRime/actions/workflows/sync.yml) 中手动触发。

<details>
<summary>手动构建配置包</summary>

在已有 Python 环境中安装脚本依赖后运行：

```bash
git clone https://github.com/skyrocketingHong/FuyaoRime.git
cd FuyaoRime
git clone --depth 1 https://github.com/iDvel/rime-ice.git upstream/rime-ice

mkdir -p upstream/wanxiang
curl -fL -o upstream/wanxiang/wanxiang-lts-zh-hans.gram \
  https://github.com/amzxyz/RIME-LMDG/releases/download/LTS/wanxiang-lts-zh-hans.gram

python3 -m pip install pypinyin opencc regex more-itertools
python3 scripts/update_dicts.py
python3 scripts/build_zhwiki.py
bash scripts/merge.sh
```

合并结果位于 `output/`。复制到客户端配置目录后重新部署；自行构建的配置没有 Release 版本基线，接入自动更新时应删除旧的 `fuyaorime-version.txt`。

</details>

主要目录：

```text
FuyaoRime/
├── .github/workflows/sync.yml   # 每日同步与发布
├── overlay/                    # 自定义配置和皮肤
├── scripts/                    # 词库获取、生成、合并及增量打包
├── updater/                    # 三平台客户端更新脚本
├── tests/                      # 更新逻辑的离线回归测试
├── custom_dicts/               # 构建时生成的额外词库
├── upstream/                   # 构建时下载的上游文件
└── output/                     # 合并后的配置
```

## 使用与反馈

本仓库为作者个人使用的输入法配置，不接受功能建议与定制请求；问题反馈限于可复现的同步失败或配置错误。

## 致谢与许可

- [iDvel/rime-ice](https://github.com/iDvel/rime-ice)：雾凇拼音配置与词库。
- [amzxyz/rime_wanxiang](https://github.com/amzxyz/rime_wanxiang) 和 [amzxyz/RIME-LMDG](https://github.com/amzxyz/RIME-LMDG)：万象拼音与语言模型。
- [felixonmars/fcitx5-pinyin-zhwiki](https://github.com/felixonmars/fcitx5-pinyin-zhwiki) 和 [Wikimedia Dumps](https://dumps.wikimedia.org/)：维基系词库与条目标题数据。
- [outloudvi/mw2fcitx](https://github.com/outloudvi/mw2fcitx)：萌娘百科词库。
- [搜狗词库](https://pinyin.sogou.com)和[深蓝词库转换工具](https://github.com/studyzy/imewlconverter)：分类词库及格式转换。
- [wainshine/Chinese-Names-Corpus](https://github.com/wainshine/Chinese-Names-Corpus) 和 [pypinyin](https://github.com/mozillazg/pypinyin)：中文人名语料与拼音标注。

本仓库再分发雾凇拼音的配置与词库，整体遵循 [GPL-3.0](LICENSE) 许可证。

## AI 辅助开发

本项目在开发过程中使用生成式 AI 协助编码。

[![Vibe PR](https://raw.githubusercontent.com/fenxer/llm-things/main/stickers/vibe-pr.svg)](https://github.com/fenxer/llm-things/blob/main/stickers/vibe-pr.svg)
