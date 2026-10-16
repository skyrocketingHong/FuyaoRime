# 字体清单与元书配置

本文记录 [macOS 皮肤](overlay/squirrel.custom.yaml)和 [Windows 皮肤](overlay/weasel.custom.yaml)中引用的字体，并说明在 iPhone 元书输入法中的对应方式。字体名称出现在配置中，不代表设备已经安装该字体，也不代表字体覆盖全部字符。字体文件不随 FuyaoRime 配置包分发。

macOS 使用普通文字字体作为主字体，保留正常的文字和空格宽度；彩色 Emoji 使用 `AppleColorEmoji`，单色符号和扩展汉字由其他后备字体补充，`Unifont` 放在最后。Windows 保留 `Noto Color Emoji Flags`、`Apple Color Emoji`、`Segoe UI Emoji` 原有的 Emoji 优先顺序，实际命中取决于已安装字体；系统自带的彩色 Emoji 字体为 `Segoe UI Emoji`。字体调整只影响显示，不改写候选或上屏字符。

## Apple 系统字体

| 配置中的名称 | 桌面用途 | iPhone 元书对应方式 |
| --- | --- | --- |
| `SF Pro Display` | 正文主字体 | 优先保留元书默认系统字体；不能假定 macOS 的同名字串等价于 iOS 系统字体接口。 |
| `SF Compact Display` | 候选编号主字体 | 优先使用元书默认系统字体。SF Compact 是 watchOS 默认字体，不作为 iPhone 必装字体。 |
| `PingFang SC` | 简体中文后备 | 可引用系统字体名 `PingFangSC-Regular`，无需从 Mac 复制字体文件。 |
| `AppleColorEmoji`、`Apple Color Emoji` | 彩色 Emoji 后备 | 可引用系统字体名 `AppleColorEmoji`。 |
| `Zapf Dingbats`（PostScript 名 `ZapfDingbatsITC`） | 勾号等单色符号后备 | 元书可引用系统字体名 `ZapfDingbatsITC`。其字符覆盖范围不等于整个 Dingbats 区块。 |

Apple 的[系统字体表](https://developer.apple.com/fonts/system-fonts/)列出了 PingFang SC、Apple Color Emoji 和 Zapf Dingbats 的 iOS 支持；[字体名称说明](https://developer.apple.com/documentation/applenews/applying-apple-news-format-fonts)列出上述 PostScript 名称。SF Pro 和 SF Compact 应按平台使用系统字体接口，不将 Apple 提供的设计用字体文件打包给输入法。[Apple 字体使用说明](https://developer.apple.com/documentation/technologyoverviews/fonts)

## 可另外获取的字体

| 配置中的名称 | 用途 | 官方来源及 iPhone 使用说明 |
| --- | --- | --- |
| `Noto Sans` | 西文及其他文字后备 | [Google Fonts 字体文件](https://github.com/google/fonts/tree/main/ofl/notosans)。可选合适字重的 TTF；当前目录提供可变字体，导入后以元书识别出的名称和字重为准。 |
| `Noto Sans SC` | 简体中文后备 | [官方静态 Regular OTF](https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf)。可作为额外中文字体，不能据此宣称包含全部新增 CJK 字符。 |
| `MiSans L3` | 生僻汉字补充 | [小米官方介绍](https://hyperos.mi.com/font/zh/rare-word/)和[官方下载包](https://hyperos.mi.com/font-download/MiSans_L3.zip)。包内包含 TTF 和 OTF；L3 不替代常用汉字字体。 |
| `Noto Sans Symbols 2` | 单色符号补充，例如 U+2700 黑色安全剪刀 | [官方 TTF](https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssymbols2/NotoSansSymbols2-Regular.ttf)：`NotoSansSymbols2-Regular.ttf`；PostScript 名为 `NotoSansSymbols2-Regular`。不是彩色 Emoji 字体或 CJK 字体。 |
| `Noto Sans Symbols` | 常用杂项符号、圈号、编号等补充 | [官方可变 TTF](https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssymbols/NotoSansSymbols%5Bwght%5D.ttf)：`NotoSansSymbols[wght].ttf`；默认 Regular 的 PostScript 名为 `NotoSansSymbols-Regular`。与 Symbols 2 分工补字。 |
| `Catrinity` | 技术、数学、箭头及较新 Unicode 符号补充 | [官方 OTF](https://catrinity-font.de/downloads/Catrinity.otf)：`Catrinity.otf`。采用 2.250 版；[官方更新记录](https://catrinity-font.de/versions.html)包含 Unicode 17 新增符号等扩展，不等于覆盖整个 Unicode。保留在系统 Emoji 和前序符号字体之后。 |
| `Noto Sans Bengali` | 孟加拉文字及 U+09F3 孟加拉塔卡货币符号补充 | [官方可变 TTF](https://raw.githubusercontent.com/google/fonts/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf)：`NotoSansBengali[wdth,wght].ttf`；默认 Regular 的 PostScript 名为 `NotoSansBengali-Regular`。 |
| `Unifont` | 最终缺字兜底 | [GNU Unifont 官方入口](https://www.unifoundry.com/unifont/index.html)。在元书中可通过字符范围限制其参与 CJK 补字；具体覆盖取决于下载文件和版本。 |
| `Noto Color Emoji Flags` | Windows 配置中的旗帜 Emoji 后备 | Google Noto Emoji 官方提供[旗帜专用 TTF](https://github.com/googlefonts/noto-emoji/blob/main/2D/fonts/NotoColorEmoji-flagsonly.ttf)，[命名脚本](https://github.com/googlefonts/noto-emoji/blob/main/update_flag_name.py)确认字体名为 `Noto Color Emoji Flags`。iPhone 优先使用系统 `AppleColorEmoji`，未验证该旗帜字体在元书中的彩色格式支持，不列为手机必装项。 |

Noto 字体和 Catrinity 采用 SIL OFL 1.1；再分发字体时保留对应版权和许可文件。Noto Emoji 的字体许可与其工具、图片资源许可不同，以具体文件目录为准。[Noto Sans 许可](https://github.com/google/fonts/blob/main/ofl/notosans/OFL.txt)、[Noto Sans Symbols 2 许可](https://github.com/google/fonts/blob/main/ofl/notosanssymbols2/OFL.txt)、[Catrinity 许可](https://catrinity-font.de/downloads/Catrinity-OFL.txt)、[Noto Emoji 字体许可](https://github.com/googlefonts/noto-emoji/blob/main/2D/fonts/LICENSE)

MiSans L3 使用免费商用的专有许可，不能按 OFL 字体处理。建议直接从小米官网下载并按协议使用，不把它作为独立字体包再分发。[小米字体 FAQ](https://hyperos.mi.com/font/zh/faq/)、[许可协议](https://hyperos.mi.com/font-download/MiSans%E5%AD%97%E4%BD%93%E7%9F%A5%E8%AF%86%E4%BA%A7%E6%9D%83%E8%AE%B8%E5%8F%AF%E5%8D%8F%E8%AE%AE.pdf)

GNU Unifont 的基础字体覆盖基本多文种平面（BMP）；官方另有 Upper 字体处理扩展平面。基础文件、Upper 文件和具体版本不能互相替代，也不能仅凭 `Unifont` 名称推断覆盖全部新增 CJK。当前官方字体提供 OFL 1.1 与 GPL 2+ 字体嵌入例外双重许可，实际采用文件的说明应一并保留。

## Windows 随附字体

下列字体出现在现有桌面配置中，但不作为 iPhone 通用导入包的组成部分。

| 配置中的名称 | 用途 | 官方来源与限制 |
| --- | --- | --- |
| macOS：`SimSun-ExtB-Regular`；Windows：`SimSun-ExtB` | 扩展汉字后备 | [Microsoft 字体说明](https://learn.microsoft.com/en-us/typography/font-list/simsun)，随 Windows 提供，文件名为 `simsunb.ttf`。鼠须管使用完整的族名和字形写法，避免把 `SimSun-ExtB` 误拆为普通 SimSun 与 ExtB 字形；小狼毫仍使用字体族名。 |
| `SimSun-ExtG` | 较新扩展汉字后备 | [Windows 官方发布说明](https://blogs.windows.com/windows-insider/2025/01/21/releasing-windows-11-build-26100-3025-to-the-release-preview-channel/)，随 Windows 更新提供；该说明列出扩展 G、H、I 支持。macOS 同样应核对完整名称，例如 `SimSun-ExtG-Regular`；未安装及验证时，不将该条目算作有效覆盖。 |
| `Segoe UI Symbol` | 单色符号后备 | [Microsoft 字体说明](https://learn.microsoft.com/en-us/typography/font-list/segoe-ui-symbol)，随 Windows 提供，文件名为 `seguisym.ttf`。 |
| `Segoe UI Emoji` | Windows 彩色 Emoji 后备 | [Microsoft 字体说明](https://learn.microsoft.com/en-us/typography/font-list/segoe-ui-emoji)，随 Windows 提供，文件名为 `seguiemj.ttf`。iPhone 使用系统 `AppleColorEmoji`。 |

能够从 Windows 找到或复制字体文件，不等于取得跨平台使用或再分发许可；Office 中能够调用某款字体也不代表可以导出给其他应用。需要扩展使用时按具体字体和产品的许可核对。[Microsoft 字体许可 FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)

## 在 iPhone 元书中配置

元书的皮肤和字体配置独立于桌面的 `squirrel.custom.yaml`、`weasel.custom.yaml`。复制 Rime 输入方案不会自动应用桌面字体链。

元书提供两种方式：应用中的字体设置可对全部键盘生效；皮肤 `config.yaml` 设置 `fontFace` 后，该皮肤使用自己的字体配置，覆盖应用字体设置。外部字体可放在皮肤的 `fonts/` 目录，皮肤按官方结构打包成 `.cskin` 后由元书导入。[元书皮肤结构与字体设置](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/structure/#fontface)

`fontFace` 是数组，顺序决定优先级。每个条目的已支持字段如下：

| 字段 | 含义 |
| --- | --- |
| `name` | 系统内置字体名称，例如 `PingFangSC-Regular`。 |
| `url` | 皮肤 `fonts/` 目录中的字体文件名，包含后缀。 |
| `ranges` | 可选数组，限制该字体的 Unicode 生效范围。 |
| `location` | `ranges` 条目中的起始码位，整数。 |
| `length` | `ranges` 条目中的码位数量，整数。 |

同一条目同时包含 `name` 和 `url` 时，`name` 优先。字体的 `fontWeight` 设置会影响优先级及范围效果；使用指定字重时应配合相应字重的字体文件。

以下示例以苹方作为主要文字字体，展示系统字体和外部字体的引用方式。文件名必须与 `fonts/` 中实际保存的文件一致；应用前保留现有皮肤副本，并按自己的主字体选择调整顺序。

```yaml
fontFace:
  - name: PingFangSC-Regular
  - name: AppleColorEmoji
  - name: ZapfDingbatsITC
  - url: NotoSansSymbols2-Regular.ttf
  - url: NotoSansSymbols[wght].ttf
  - url: Catrinity.otf
  - url: NotoSansBengali[wdth,wght].ttf
```

### 将 Unifont 放在 CJK 范围的末尾

建议从[完整字体配置片段](updater/ios-fonts.example.yaml)开始：它包含四款开放符号字体，并将 Unifont 基础字体和 Upper 字体分别限定到 BMP CJK、扩展 B 至 J、兼容表意文字及汉字结构描述符范围。该文件需要合并到已有皮肤的 `config.yaml`，不是独立的 `.cskin`，其中未准备的字体条目应删除。

在前面的正常文字、Emoji、符号和汉字字体之后，将下面条目追加到已有 `fontFace` 数组末尾。示例假定已把所选 GNU Unifont 基础 OTF 保存为 `fonts/unifont.otf`。

```yaml
  - url: unifont.otf
    ranges:
      - location: 13312
        length: 6592
      - location: 19968
        length: 20992
```

| Unicode 区间（含两端） | `location` | `length` | 范围 |
| --- | ---: | ---: | --- |
| U+3400–U+4DBF | 13312 | 6592 | CJK 统一表意文字扩展 A |
| U+4E00–U+9FFF | 19968 | 20992 | CJK 统一表意文字 |

这里的长度按“结束码位 − 起始码位 + 1”计算。例如第一项的结束位置为 `13312 + 6592 - 1 = 19903`，即 U+4DBF。[Unicode 17 官方区块表](https://www.unicode.org/Public/17.0.0/ucd/Blocks.txt)

此示例仅覆盖两个 BMP 区块，不是完整 CJK 配置。需要扩展其他区块时，应先确认对应字体文件确实包含目标字符，再添加相应范围；扩大范围本身不会为字体补出缺失字形。不要直接把整个 Unicode 空间交给 Unifont，否则常用符号仍可能回退到它。

## 常用符号核对结果

2026-10-16 在 macOS 上按鼠须管 1.1.2 的字体解析方式构造 CoreText 字体链，检查 9,080 条唯一文本：其中 7,862 条为符号及完整组合序列，1,218 条为 Rime 符号表提供的扩展字母。范围包括 Unicode 17 的常用标点、货币、箭头、数学、技术、制表、几何、音乐、编号和现代图符，以及当前上游 `symbols_v.yaml`、`symbols_caps_v.yaml`、Emoji 映射、OpenCC 和标点配置中的候选；保留原始 VS、ZWJ 和组合序列，不追加显示选择符。检查集包含 551 条完整 Emoji 序列，其中有 258 条旗帜序列。

| 字体链 | 非 CJK 文本回退到 Unifont | CJK 结构描述符回退到 Unifont | LastResort 或单码点零字形 |
| --- | ---: | ---: | ---: |
| 正文 `font_face` | 0 | 4 | 0 |
| 注释 `comment_font_face` | 0 | 4 | 0 |
| 编号 `label_font_face` | 0 | 0 | 0 |
| 预编辑配置 `preedit_font_face` | 0 | 4 | 0 |

四个 CJK 结构描述符是 U+2FFC、U+2FFD、U+2FFE、U+2FFF。16 pt 正文的双空格宽度为约 6.56 pt。鼠须管 1.1.2 实际不读取独立的 `preedit_font_face`，预编辑继承正文；表中该项核对的是预留配置字体链，不能视为此版本具有独立预编辑字体能力。

本机 `SimSun-ExtG-Regular` 和 `Segoe UI Symbol` 未能解析，以上结果不依赖这两款字体。字体选择和字形存在性检查不等于逐字视觉检查，也不保证检查集之外的所有非 CJK 字符永远不会使用 Unifont。Windows 和 iPhone 元书尚未执行平台实测；桌面同步的是共用字体与回退顺序，平台 Emoji、SimSun 和 Zapf 的名称保留必要差异。

### 重新核对

在 macOS 上准备 Swift 和现有 Python 环境中的 PyYAML，并确保 `upstream/rime-ice` 已存在：

```bash
python3 scripts/build_font_audit_corpus.py --download
swift scripts/audit_macos_fonts.swift \
  dist/font-audit/corpus.style.json \
  dist/font-audit/corpus.json \
  dist/font-audit/result.json
```

第一个命令下载并校验固定 Unicode 17 数据，提取当前上游候选，记录输入及语料哈希；第二个命令使用本机已安装字体，输出实际命中的字体与回退计数。源候选更新后，检查集数量可以变化。缺字体时先安装清单中的对应文件；Unicode 数据哈希不符时应停止并核对来源，不绕过校验。命令不修改输入法配置，生成物都在 `dist/font-audit/`，按需删除该目录即可清理。

## 平台验收范围

本文的系统字体名称、元书字段和外部字体来源已经按官方资料核对。macOS 字体探针的结果不能代替 iPhone 键盘验证。手机上仍需确认导入后的字体名称、所用字重、范围优先级、常用符号、扩展汉字、Emoji 组合、空格宽度和键盘运行是否符合预期。

配置范围只约束字体选择，不改变字符本身。应保留输入方案中的原始文本，不为修复显示而替换相似符号、追加 VS16 或改写上屏内容。
