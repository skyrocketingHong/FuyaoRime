<h1 align="center">FuyaoRime</h1>

<p align="center">
  自动同步雾凇拼音与万象拼音的 Rime 输入法配置，每日更新词库与语言模型
</p>

<p align="center">
  <a href="https://github.com/skyrocketingHong/FuyaoRime/actions/workflows/sync.yml"><img src="https://img.shields.io/github/actions/workflow/status/skyrocketingHong/FuyaoRime/sync.yml?branch=main&label=Sync" alt="Sync workflow status"></a>
  <a href="https://github.com/skyrocketingHong/FuyaoRime/releases/latest"><img src="https://img.shields.io/github/v/release/skyrocketingHong/FuyaoRime?label=Release" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue" alt="GPL-3.0"></a>
</p>

## 简介

FuyaoRime 是一个自动更新的 Rime 输入法配置仓库。它从上游 [雾凇拼音（rime-ice）](https://github.com/iDvel/rime-ice) 拉取最新配置与词库，下载 [万象拼音](https://github.com/amzxyz/rime_wanxiang) 语言模型（发布于 [RIME-LMDG](https://github.com/amzxyz/RIME-LMDG)），更新额外词库，叠加自定义皮肤与配置后，生成可直接使用的配置包 `fuyaorime-*.zip`，见 [Releases](https://github.com/skyrocketingHong/FuyaoRime/releases)。

仓库不裁剪雾凇拼音的输入方案：全拼、七种主流双拼与九键方案全部保留，可通过 Rime 方案选单（F4 或 Control+grave）切换。

## 声明

本仓库为作者个人使用的输入法配置，一切取舍以个人习惯为准，不承诺对第三方需求提供适配。不接受功能建议与定制类请求；仅接受可复现的同步失败或配置错误报告，相关 Issue 与 Pull Request 可能不予回应或合入。

## 输入方案

| 输入方案 | schema_id | 状态 |
| :--- | :--- | :--- |
| 雾凇拼音（全拼） | `rime_ice` | 默认启用 |
| 自然码双拼 | `double_pinyin` | 默认启用 |
| 智能 ABC 双拼 | `double_pinyin_abc` | 默认启用 |
| 微软双拼 | `double_pinyin_mspy` | 默认启用 |
| 搜狗双拼 | `double_pinyin_sogou` | 默认启用 |
| 小鹤双拼 | `double_pinyin_flypy` | 默认启用 |
| 紫光双拼 | `double_pinyin_ziguang` | 默认启用 |
| 拼音加加双拼 | `double_pinyin_jiajia` | 默认启用 |
| 中文九键 | `t9` | 默认注释，面向仓输入法与元书输入法（移动端） |
| 部件拆字 | `radical_pinyin` | 作为部首反查与辅码挂载于拼音方案 |
| Easy English Nano | `melt_eng` | 作为次翻译器挂载于拼音方案 |

启用或停用方案：编辑 `overlay/default.custom.yaml` 的 `schema_list`。

额外词库、语言模型、模糊音等定制通过 `overlay/rime_ice.custom.yaml` 作用于全拼主方案；切换到双拼方案后使用上游默认配置，如需定制双拼，可按 `rime_ice.custom.yaml` 的写法新增对应的 `overlay/<schema_id>.custom.yaml`（注意不要把全拼的模糊音拼写规则套用到双拼方案）。

## 包含内容

### 来自雾凇拼音

- 全部输入方案（全拼、七种双拼、九键、部件拆字、英文）
- 中文词库（8105 字表、41448 大字表、基础词库、扩展词库、腾讯词向量、杂项）
- 英文词库与各输入方案对应的中英混合词库（`en_dicts/cn_en*.txt`）
- OpenCC 映射（简繁转换、Emoji 等）
- Lua 扩展脚本

### 来自万象拼音

- 语言模型 `wanxiang-lts-zh-hans.gram`

### 自定义内容

- macOS 与 Windows 皮肤（薄荷绿、柑橘黄，均含明暗两套）
- 额外词库：
  - 中文维基百科（`zhwiki`）
  - 维基文库（`zhwikisource`）
  - 维基词典（`zhwiktionary`）
  - 萌娘百科（`moegirl`）
  - 网络俚语（`web-slang`）
  - 中国地名（`cn_places`）
  - 流行新词（`popular_new_words`）
  - 中文人名（`chinese_names`，姓氏与名字，由语料自动生成）
  - 成语俗语（`chengyu_suyu`）
  - 古诗词名句（`gushi_mingju`）
  - 唐诗三百首（`tangshi_300`）

## 使用方法

### 方法一：下载 Release 包（推荐）

1. 前往 [Releases](https://github.com/skyrocketingHong/FuyaoRime/releases) 页面；
2. 下载最新的 `fuyaorime-*.zip`；
3. 解压全部内容到 Rime 配置目录：
   - macOS：`~/Library/Rime/`
   - Windows：`%APPDATA%\Rime\`
   - Linux：`~/.config/rime/`
4. 重新部署 Rime（鼠须管、小狼毫在输入法菜单中选择「重新部署」）。

### 方法二：手动同步

```bash
# 克隆本仓库
git clone https://github.com/skyrocketingHong/FuyaoRime.git
cd FuyaoRime

# 克隆雾凇拼音上游
git clone --depth 1 https://github.com/iDvel/rime-ice.git upstream/rime-ice

# 下载万象拼音语言模型
mkdir -p upstream/wanxiang
curl -L -o upstream/wanxiang/wanxiang-lts-zh-hans.gram \
  "https://github.com/amzxyz/RIME-LMDG/releases/download/LTS/wanxiang-lts-zh-hans.gram"

# 更新额外词库
python3 scripts/update_dicts.py

# 合并配置
bash scripts/merge.sh

# 复制到 Rime 配置目录（以 macOS 为例）
cp -r output/* ~/Library/Rime/
```

## 目录结构

```text
FuyaoRime/
├── .github/workflows/sync.yml    # 自动同步工作流
├── custom_dicts/                 # 额外词库，由 update_dicts.py 生成与更新
├── overlay/                      # 自定义配置，合并时叠加到上游文件
│   ├── default.custom.yaml       # 方案列表
│   ├── rime_ice.custom.yaml      # 全拼方案定制（语言模型、模糊音等）
│   ├── rime_ice.custom.dict.yaml # 自定义词库挂载
│   ├── squirrel.custom.yaml      # macOS 皮肤
│   └── weasel.custom.yaml        # Windows 皮肤
├── scripts/
│   ├── merge.sh                  # 合并脚本
│   ├── update_dicts.py           # 额外词库更新脚本
│   └── .rime_ice_hash            # 上游 commit 记录
├── AGENTS.md                     # 项目约定
├── LICENSE                       # GPL-3.0 许可证
└── README.md
```

## 自动同步

仓库配置了 GitHub Actions，每日北京时间 05:00 自动执行：

1. 拉取雾凇拼音最新版本；
2. 下载万象拼音语言模型；
3. 更新额外词库；
4. 合并所有文件，保留全部输入方案与自定义配置；
5. 发布 `fuyaorime-*.zip` 到 Releases。

也可以在 [Actions](https://github.com/skyrocketingHong/FuyaoRime/actions/workflows/sync.yml) 页面手动触发。

## 自定义

### 修改皮肤

编辑 `overlay/squirrel.custom.yaml`（macOS）或 `overlay/weasel.custom.yaml`（Windows）。内置薄荷绿与柑橘黄两套皮肤（各含明暗变体），可在输入法外观设置中切换。

### 添加词库

1. 将词库文件（`.dict.yaml`）放入 `custom_dicts/` 目录；
2. 在 `overlay/rime_ice.custom.dict.yaml` 的 `import_tables` 中添加引用。

### 修改方案配置

全拼方案编辑 `overlay/rime_ice.custom.yaml`；其他方案按相同写法新增 `overlay/<schema_id>.custom.yaml`。

### 标点行为

已关闭「数字、字母后标点自动半角」，标点一律按全角映射处理：数字后的逗号、句号、冒号不再作为数字分隔符（`3.14`、`1,000` 不会整体上屏）；`www.`、`https:` 等前缀与 `abc_`、`name@site` 等写法中的标点也不再保持半角。输入网址、邮箱或代码标识符时，可按 Shift 临时切换英文模式。相关补丁位于 `overlay/default.custom.yaml`（`punctuator/digit_separators` 与 `recognizer/patterns`）。

## 致谢

- [iDvel/rime-ice](https://github.com/iDvel/rime-ice)：雾凇拼音
- [amzxyz/rime_wanxiang](https://github.com/amzxyz/rime_wanxiang)：万象拼音
- [amzxyz/RIME-LMDG](https://github.com/amzxyz/RIME-LMDG)：万象拼音语言模型发布仓库
- [felixonmars/fcitx5-pinyin-zhwiki](https://github.com/felixonmars/fcitx5-pinyin-zhwiki)：维基百科、维基文库、维基词典、网络俚语词库
- [outloudvi/mw2fcitx](https://github.com/outloudvi/mw2fcitx)：萌娘百科词库
- [搜狗词库](https://pinyin.sogou.com)：中国地名、流行新词、成语俗语、古诗词名句、唐诗三百首词库
- [studyzy/imewlconverter](https://github.com/studyzy/imewlconverter)：深蓝词库转换工具
- [wainshine/Chinese-Names-Corpus](https://github.com/wainshine/Chinese-Names-Corpus)：中文人名语料库
- [pypinyin](https://github.com/mozillazg/pypinyin)：人名词库拼音标注

## 许可

本仓库再分发 [雾凇拼音](https://github.com/iDvel/rime-ice) 的配置与词库，整体遵循 [GPL-3.0](LICENSE) 许可证，与上游一致。
