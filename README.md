# FuyaoRime

自动同步 [雾凇拼音](https://github.com/iDvel/rime-ice) 和 [万象拼音](https://github.com/amzxyz/rime_wanxiang) 的 Rime 输入法配置仓库。

## 功能特点

- 每周自动拉取上游最新词库和配置
- 自动下载万象拼音语言模型
- 自动更新额外词库（维基百科、萌娘百科等）
- 保留自定义皮肤和配置
- 生成可直接使用的配置包

## 包含内容

### 来自雾凇拼音
- 全拼/双拼方案
- 中文词库（8105字表、基础词库、扩展词库、腾讯词向量）
- 英文词库
- OpenCC 映射
- Lua 扩展脚本

### 来自万象拼音
- 语言模型 (wanxiang-lts-zh-hans.gram)
- 用户预测功能 (user_predict.lua)

### 自定义内容
- macOS 皮肤（薄荷绿/柑橘黄）
- Windows 皮肤（薄荷绿/柑橘黄）
- 额外词库：
  - 中文维基百科 (zhwiki)
  - 维基文库 (zhwikisource)
  - 维基词典 (zhwiktionary)
  - 萌娘百科 (moegirl)
  - 网络俚语 (web-slang)
  - 中国地名 (cn_places)
  - 流行新词 (popular_new_words)

## 使用方法

### 方法一：下载 Release 包（推荐）

1. 前往 [Releases](../../releases) 页面
2. 下载最新的 `fuyaorime-*.zip`
3. 解压到 Rime 配置目录：
   - macOS: `~/Library/Rime/`
   - Windows: `%APPDATA%\Rime\`
   - Linux: `~/.config/rime/`
4. 重新部署 Rime

### 方法二：手动同步

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/FuyaoRime.git
cd FuyaoRime

# 运行合并脚本
chmod +x scripts/merge.sh
bash scripts/merge.sh

# 复制到 Rime 配置目录
cp -r output/* ~/Library/Rime/
```

## 目录结构

```
FuyaoRime/
├── .github/workflows/
│   └── sync.yml              # GitHub Actions 工作流
├── overlay/                  # 自定义配置（覆盖上游）
│   ├── squirrel.custom.yaml  # macOS 皮肤
│   ├── weasel.custom.yaml    # Windows 皮肤
│   ├── default.custom.yaml   # 默认方案
│   ├── rime_ice.custom.yaml  # 雾凇自定义
│   ├── rime_ice.custom.dict.yaml  # 自定义词典配置
│   ├── custom_phrase.txt     # 自定义短语
│   └── lua/
│       └── user_predict.lua  # 用户预测
├── custom_dicts/             # 额外词库
├── scripts/
│   ├── merge.sh              # 合并脚本
│   └── update_dicts.py       # 词库更新脚本
└── README.md
```

## 自动同步

仓库配置了 GitHub Actions，每周日凌晨自动：
1. 拉取雾凇拼音最新版本
2. 下载万象拼音语言模型
3. 更新额外词库
4. 合并所有文件
5. 发布到 Releases

也可以在 Actions 页面手动触发同步。

## 自定义

### 修改皮肤
编辑 `overlay/squirrel.custom.yaml`（macOS）或 `overlay/weasel.custom.yaml`（Windows）。

### 添加词库
1. 将词库文件放入 `custom_dicts/` 目录
2. 编辑 `overlay/rime_ice.custom.dict.yaml` 添加引用

### 修改方案配置
编辑 `overlay/rime_ice.custom.yaml`。

## 致谢

- [iDvel/rime-ice](https://github.com/iDvel/rime-ice) - 雾凇拼音
- [amzxyz/rime_wanxiang](https://github.com/amzxyz/rime_wanxiang) - 万象拼音
- [felixonmars/fcitx5-pinyin-zhwiki](https://github.com/felixonmars/fcitx5-pinyin-zhwiki) - 维基百科词库
- [outloudvi/mw2fcitx](https://github.com/outloudvi/mw2fcitx) - 萌娘百科词库
