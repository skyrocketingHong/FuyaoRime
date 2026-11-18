#!/bin/bash
# merge.sh - 构建 Fuyao Rime 配置包

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

OVERLAY_DIR="$PROJECT_DIR/overlay"
PACKAGE_DIR="$PROJECT_DIR/output"
READINGS_FILE="$PROJECT_DIR/upstream/radical-readings/zdict.reverse.bin"

# 注音是全拼拆字功能的必要资源，缺失时不能发布不完整的配置包。
if [ ! -s "$READINGS_FILE" ]; then
    echo "缺少带调注音资源，请先运行 python3 scripts/fetch_radical_readings.py" >&2
    exit 1
fi

# 在项目卷上准备完整配置包，成功后再替换上一次输出。
OUTPUT_DIR="$(mktemp -d "$PROJECT_DIR/.fuyaorime-build.XXXXXXXX")"
trap 'rm -rf "$OUTPUT_DIR"' EXIT

echo "=== 开始合并 Rime 配置 ==="

echo "[1/5] 生成基础方案和词库..."
python3 "$SCRIPT_DIR/stage_base.py" "$PROJECT_DIR" "$OUTPUT_DIR"

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

    # 复制 fcitx5 主题，由 Linux 更新脚本从配置包安装到 fcitx5 主题目录
    if [ -d "$OVERLAY_DIR/fcitx5-themes" ]; then
        cp -r "$OVERLAY_DIR/fcitx5-themes" "$OUTPUT_DIR/"
    fi
fi

# 5. 清理不需要的文件
echo "[5/5] 清理临时文件..."
rm -f "$OUTPUT_DIR"/*.custom.yaml.example
rm -f "$OUTPUT_DIR/go.work"
rm -rf "$OUTPUT_DIR/.github"
rm -rf "$OUTPUT_DIR/build"
rm -rf "$OUTPUT_DIR/others/script"

# build 目录清理后仅放入专门下载的注音词典，不混入本机编译缓存。
mkdir -p "$OUTPUT_DIR/build"
cp "$READINGS_FILE" "$OUTPUT_DIR/build/zdict.reverse.bin"

rm -rf "$PACKAGE_DIR"
mv "$OUTPUT_DIR" "$PACKAGE_DIR"

echo ""
echo "=== 合并完成 ==="
echo "输出目录: $PACKAGE_DIR"
echo ""
echo "文件列表:"
ls -la "$PACKAGE_DIR"
