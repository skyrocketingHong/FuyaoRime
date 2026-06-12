#!/bin/bash
# merge.sh - 合并雾凇拼音和自定义配置

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

UPSTREAM_DIR="$PROJECT_DIR/upstream/rime-ice"
OVERLAY_DIR="$PROJECT_DIR/overlay"
OUTPUT_DIR="$PROJECT_DIR/output"

echo "=== 开始合并 Rime 配置 ==="

# 清理输出目录
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# 1. 复制雾凇拼音核心文件
echo "[1/5] 复制雾凇拼音核心文件..."
# 只复制需要的 schema 文件（全拼、英文、部首拼音）
for schema in rime_ice.schema.yaml melt_eng.schema.yaml radical_pinyin.schema.yaml; do
    cp "$UPSTREAM_DIR/$schema" "$OUTPUT_DIR/" 2>/dev/null || true
done
# 复制其他配置文件
cp "$UPSTREAM_DIR/default.yaml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR/rime_ice.dict.yaml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR/melt_eng.dict.yaml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR/radical_pinyin.dict.yaml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR/symbols_v.yaml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR/symbols_caps_v.yaml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR/user.yaml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR/recipe.yaml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR"/*.txt "$OUTPUT_DIR/" 2>/dev/null || true
cp "$UPSTREAM_DIR/LICENSE" "$OUTPUT_DIR/"

# 复制子目录
cp -r "$UPSTREAM_DIR/cn_dicts" "$OUTPUT_DIR/"
# 只复制全拼需要的英文词典，跳过双拼专用的 cn_en_*.txt
mkdir -p "$OUTPUT_DIR/en_dicts"
cp "$UPSTREAM_DIR/en_dicts/cn_en.txt" "$OUTPUT_DIR/en_dicts/"
cp "$UPSTREAM_DIR/en_dicts/en.dict.yaml" "$OUTPUT_DIR/en_dicts/"
cp "$UPSTREAM_DIR/en_dicts/en_ext.dict.yaml" "$OUTPUT_DIR/en_dicts/"
cp -r "$UPSTREAM_DIR/opencc" "$OUTPUT_DIR/"
cp -r "$UPSTREAM_DIR/lua" "$OUTPUT_DIR/"

# 只复制 others 中的必要文件，跳过文档和资源
mkdir -p "$OUTPUT_DIR/others"
cp "$UPSTREAM_DIR/others/cn_en.txt" "$OUTPUT_DIR/others/" 2>/dev/null || true
cp "$UPSTREAM_DIR/others/emoji-map.txt" "$OUTPUT_DIR/others/" 2>/dev/null || true

# 2. 复制万象拼音语言模型和脚本
echo "[2/5] 复制万象拼音语言模型和脚本..."
if [ -f "$PROJECT_DIR/upstream/wanxiang/wanxiang-lts-zh-hans.gram" ]; then
    cp "$PROJECT_DIR/upstream/wanxiang/wanxiang-lts-zh-hans.gram" "$OUTPUT_DIR/"
    if [ -f "$PROJECT_DIR/upstream/wanxiang/version.txt" ]; then
        cp "$PROJECT_DIR/upstream/wanxiang/version.txt" "$OUTPUT_DIR/wanxiang-lts-zh-hans.gram.version"
    fi
fi

# 3. 复制自定义词库
echo "[3/5] 复制自定义词库..."
if [ -d "$PROJECT_DIR/custom_dicts" ]; then
    mkdir -p "$OUTPUT_DIR/custom_dicts"
    cp "$PROJECT_DIR/custom_dicts"/*.yaml "$OUTPUT_DIR/custom_dicts/" 2>/dev/null || true
fi

# 4. 覆盖自定义配置
echo "[4/5] 覆盖自定义配置..."
# 复制 overlay 目录下的所有文件
if [ -d "$OVERLAY_DIR" ]; then
    # 复制根目录下的自定义文件
    for f in "$OVERLAY_DIR"/*.yaml "$OVERLAY_DIR"/*.txt; do
        if [ -f "$f" ]; then
            cp "$f" "$OUTPUT_DIR/"
        fi
    done
    
    # 复制 lua 目录下的自定义脚本
    if [ -d "$OVERLAY_DIR/lua" ]; then
        mkdir -p "$OUTPUT_DIR/lua"
        cp "$OVERLAY_DIR/lua"/*.lua "$OUTPUT_DIR/lua/" 2>/dev/null || true
    fi
fi

# 5. 清理不需要的文件
echo "[5/5] 清理临时文件..."
rm -f "$OUTPUT_DIR"/*.custom.yaml.example
rm -f "$OUTPUT_DIR/go.work"
rm -rf "$OUTPUT_DIR/.github"
rm -rf "$OUTPUT_DIR/build"
rm -rf "$OUTPUT_DIR/others/script"

echo ""
echo "=== 合并完成 ==="
echo "输出目录: $OUTPUT_DIR"
echo ""
echo "文件列表:"
ls -la "$OUTPUT_DIR"
