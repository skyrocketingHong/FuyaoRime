# 字体

以下按配置优先级排列，未安装或缺字时使用后备字体。

## 桌面字体顺序

以下为正文和注释的实际顺序，对应 `font_face`、`comment_font_face`。

| 顺位 | macOS | Windows |
| ---: | --- | --- |
| 1 | SF Pro Display | SF Pro Display |
| 2 | Noto Sans | Noto Sans |
| 3 | PingFang SC | Noto Color Emoji Flags |
| 4 | Noto Sans SC | Apple Color Emoji |
| 5 | MiSans L3 | Segoe UI Emoji |
| 6 | SimSun-ExtB-Regular | PingFang SC |
| 7 | SimSun-ExtG-Regular | Noto Sans SC |
| 8 | Segoe UI Symbol | MiSans L3 |
| 9 | AppleColorEmoji | SimSun-ExtB |
| 10 | ZapfDingbatsITC | SimSun-ExtG |
| 11 | Noto Sans Symbols 2 | Segoe UI Symbol |
| 12 | Noto Sans Symbols | Zapf Dingbats |
| 13 | Catrinity | Noto Sans Symbols 2 |
| 14 | Unifont | Noto Sans Symbols |
| 15 | — | Catrinity |
| 16 | — | Unifont |

编号字体 `label_font_face` 从 `SF Compact Display → Noto Sans` 开始，后面依次为该平台的 Emoji 字体、Zapf、Noto Sans Symbols 2、Noto Sans Symbols、Catrinity。

macOS 的 `SimSun-ExtB-Regular` 和 `SimSun-ExtG-Regular` 对应 Windows 的 `SimSun-ExtB` 和 `SimSun-ExtG`；两端使用不同名称以适配客户端解析。

## 字体下载

| 字体 | 用途 | 来源 |
| --- | --- | --- |
| SF Pro Display、SF Compact Display | 正文、编号 | [Apple Fonts](https://developer.apple.com/fonts/)；元书可直接使用默认系统字体 |
| PingFang SC、AppleColorEmoji、ZapfDingbatsITC | 中文、Emoji、勾号等符号 | Apple 系统字体；元书可用下方示例中的名称调用 |
| Noto Sans | 西文后备 | [Google Fonts](https://github.com/google/fonts/tree/main/ofl/notosans) |
| Noto Sans SC | 中文后备 | [Regular OTF](https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf) |
| MiSans L3 | 生僻汉字 | [小米字体](https://hyperos.mi.com/font/zh/rare-word/) |
| SimSun-ExtB、SimSun-ExtG、Segoe UI Symbol、Segoe UI Emoji | Windows 扩展汉字和符号 | Windows 随附字体；元书优先使用苹方，缺字时按需添加字体 |
| Noto Color Emoji Flags | Windows 旗帜 Emoji | [旗帜专用 TTF](https://github.com/googlefonts/noto-emoji/blob/main/2D/fonts/NotoColorEmoji-flagsonly.ttf)；元书使用 AppleColorEmoji |
| Noto Sans Symbols 2 | 图形、剪刀等符号 | [TTF](https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssymbols2/NotoSansSymbols2-Regular.ttf) |
| Noto Sans Symbols | 编号和杂项符号 | [可变 TTF](https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssymbols/NotoSansSymbols%5Bwght%5D.ttf) |
| Catrinity | 数学、箭头及较新符号 | [OTF](https://catrinity-font.de/downloads/Catrinity.otf) |
| Unifont、Unifont Upper | CJK 缺字的最后兜底 | [GNU Unifont](https://www.unifoundry.com/unifont/index.html)；基础字体和 Upper 分别补充不同平面 |

三款符号字体为 Noto Sans Symbols 2、Noto Sans Symbols、Catrinity。字体包中的许可文件放在 `licenses/`。

macOS 正文和注释中的 `৳`（U+09F3）仍回退到 Unifont。鼠须管 1.1.2 无法按码位限制字体；元书可用 `ranges` 将 Unifont 限定在 CJK 范围。

## 元书配置

1. 将三款符号字体放入皮肤的 `fonts/` 目录。
2. 把[字体配置示例](updater/ios-fonts.example.yaml)合并到皮肤的 `config.yaml`，保留原键盘布局。没有准备的字体文件条目可删除。
3. 如需 Unifont 补字，准备基础字体和 Upper 文件，按示例命名为 `unifont.otf`、`unifont_upper.otf`，放在字体列表末尾。
4. 将皮肤打包成 `.cskin` 后导入元书。使用 Regular 字体文件时选择 Regular 字重。

元书示例的顺序为：

```text
PingFangSC-Regular
AppleColorEmoji
ZapfDingbatsITC
NotoSansSymbols2-Regular.ttf
NotoSansSymbols[wght].ttf
Catrinity.otf
unifont.otf          # 仅限 BMP CJK 范围
unifont_upper.otf    # 仅限 CJK 扩展范围
```

元书用 `name` 引用系统字体，用 `url` 引用 `fonts/` 中的文件；`ranges` 的 `location` 为起始码位，`length` 为码位数量。范围设置不会增加字体本身缺少的字形。

应用中的字体设置可作用于全部键盘；皮肤设置了 `fontFace` 后，以皮肤配置为准。详见[元书字体文档](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/structure/#fontface)。
