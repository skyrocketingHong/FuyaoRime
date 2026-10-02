#!/usr/bin/env bash
# fuyaorime-update-macos.sh - 增量更新 FuyaoRime 并重新部署鼠须管
#
# 首次运行（无版本标记）下载全量包，此后只下载增量包；跨多天时按发布
# 链逐个应用，任一环缺失即回退全量包，避免跳版漏文件。删除清单从增量
# 包内 INCREMENTAL-README.txt 解析（格式由 make_diff_package.py 固定）。
#
# 用法：fuyaorime-update-macos.sh [Rime 目录]
# 目录缺省 ~/Library/Rime，适合放入 crontab 每日运行。

set -euo pipefail

REPO="skyrocketingHong/FuyaoRime"
RIME_DIR="${1:-$HOME/Library/Rime}"
MARKER="$RIME_DIR/fuyaorime-version.txt"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

fetch() {
    curl -fsSL --retry 2 --connect-timeout 15 -o "$2" "$1"
}

# 匿名限频 60 次/小时；导出 GITHUB_TOKEN 可解除限制
release_tags() {
    local auth=()
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
    fi
    curl -fsSL --retry 2 ${auth[@]+"${auth[@]}"} \
        "https://api.github.com/repos/$REPO/releases?per_page=100" \
        | grep -oE '"tag_name": "v[0-9]{8}"' | grep -oE '[0-9]{8}' | sort -u
}

apply_diff() {
    unzip -oq "$1" -d "$RIME_DIR"
    local readme="$RIME_DIR/INCREMENTAL-README.txt"
    [ -f "$readme" ] || return 0
    awk '/已从配置包移除/ {del=1; next} del && /^  - / {sub(/^  - /, ""); print; next} del {exit}' "$readme" \
        | while IFS= read -r f; do rm -f -- "$RIME_DIR/$f"; done
    rm -f "$readme"
}

install_full() {
    fetch "https://github.com/$REPO/releases/download/v$latest/fuyaorime-$latest.zip" \
        "$WORK_DIR/full.zip" || { log "全量包下载失败"; exit 1; }
    unzip -oq "$WORK_DIR/full.zip" -d "$RIME_DIR"
    log "已应用全量包 $latest"
}

redeploy() {
    local squirrel="/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel"
    if [ -x "$squirrel" ]; then
        "$squirrel" --reload
        log "已通知鼠须管重新加载"
    else
        log "未找到鼠须管，请在输入法菜单手动选择"重新部署""
    fi
}

main() {
    local tags latest current t
    tags=$(release_tags) || { log "获取 release 列表失败"; exit 1; }
    [ -n "$tags" ] || { log "未解析到任何 release"; exit 1; }
    latest=$(printf '%s\n' "$tags" | tail -1)

    mkdir -p "$RIME_DIR"
    current=$(cat "$MARKER" 2>/dev/null || true)
    if [ "$current" = "$latest" ]; then
        log "已是最新版本 $latest"
        return 0
    fi

    if [ -z "$current" ] || ! [[ "$current" =~ ^[0-9]{8}$ ]]; then
        log "未检测到本地版本标记，执行全量安装 $latest"
        install_full
    else
        log "本地版本 ${current}，开始增量更新到 ${latest}"
        for t in $(printf '%s\n' "$tags" | awk -v c="$current" '$0 > c'); do
            if fetch "https://github.com/$REPO/releases/download/v$t/fuyaorime-$t-diff-from-$current.zip" \
                    "$WORK_DIR/diff.zip"; then
                apply_diff "$WORK_DIR/diff.zip"
                current=$t
            else
                current=""
                break
            fi
        done
        if [ "$current" != "$latest" ]; then
            log "增量链中断，回退全量包"
            install_full
        fi
    fi

    printf '%s\n' "$latest" > "$MARKER"
    redeploy
}

main
