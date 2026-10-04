#!/usr/bin/env bash
# fuyaorime-update-linux.sh - 增量更新 FuyaoRime 并重新部署 ibus-rime / fcitx5-rime
#
# 仅在本地版本与最新增量包基线一致时使用 diff，否则下载最新全量包。
# 写入前校验 INCREMENTAL-README.txt 中的适用版本，不跨版串联增量包。
#
# 用法：fuyaorime-update-linux.sh [Rime 目录]
# 目录缺省 ${XDG_CONFIG_HOME:-~/.config}/rime，适合放入 crontab 每日运行。

set -euo pipefail

REPO="skyrocketingHong/FuyaoRime"
RIME_DIR="${1:-${XDG_CONFIG_HOME:-$HOME/.config}/rime}"
MARKER="$RIME_DIR/fuyaorime-version.txt"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

fetch() {
    curl -fsSL --retry 2 --connect-timeout 15 -o "$2" "$1"
}

# GITHUB_TOKEN 可提高 GitHub API 请求限额。
release_tags() {
    local auth=()
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
    fi
    curl -fsSL --retry 2 ${auth[@]+"${auth[@]}"} \
        "https://api.github.com/repos/$REPO/releases?per_page=100" \
        | grep -oE '"tag_name"[[:space:]]*:[[:space:]]*"v[0-9]{8}"' | grep -oE '[0-9]{8}' | sort -u
}

validate_diff() {
    local version
    unzip -tq "$1" >/dev/null 2>&1 || return 1
    version=$(unzip -p "$1" INCREMENTAL-README.txt 2>/dev/null \
        | tr -d '\r' | sed -n '/^适用版本:/p') || return 1
    [ "$version" = "适用版本: $2 -> $3" ]
}

apply_diff() {
    # 写入中断后无法再信任旧基线，下次运行须使用全量包。
    rm -f "$MARKER"
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
    unzip -tq "$WORK_DIR/full.zip" >/dev/null 2>&1 || { log "全量包校验失败"; exit 1; }
    rm -f "$MARKER"
    unzip -oq "$WORK_DIR/full.zip" -d "$RIME_DIR"
    log "已应用全量包 $latest"
}

redeploy() {
    if command -v fcitx5 >/dev/null 2>&1 && pgrep -x fcitx5 >/dev/null 2>&1; then
        # fcitx5 重启时自动重新部署 rime；cron 环境缺会话变量时可能失败
        fcitx5 --replace -d >/dev/null 2>&1 || true
        log "已请求重启 fcitx5"
    elif command -v ibus >/dev/null 2>&1; then
        ibus restart
        log "已重启 ibus"
    else
        log "未检测到 fcitx5 或 ibus，请手动重新部署"
    fi
}

main() {
    local tags latest current
    tags=$(release_tags) || { log "获取 release 列表失败"; exit 1; }
    [ -n "$tags" ] || { log "未解析到任何 release"; exit 1; }
    latest=$(printf '%s\n' "$tags" | tail -1)

    mkdir -p "$RIME_DIR"
    current=$(cat "$MARKER" 2>/dev/null || true)
    if [ "$current" = "$latest" ]; then
        log "已是最新版本 $latest"
        return 0
    fi
    if [[ "$current" =~ ^[0-9]{8}$ ]] && [[ "$current" > "$latest" ]]; then
        log "本地版本 ${current} 新于远端 ${latest}，跳过更新"
        return 0
    fi

    if [ -z "$current" ] || ! [[ "$current" =~ ^[0-9]{8}$ ]]; then
        log "未检测到本地版本标记，执行全量安装 $latest"
        install_full
    else
        if fetch "https://github.com/$REPO/releases/download/v$latest/fuyaorime-$latest-diff-from-$current.zip" \
                "$WORK_DIR/diff.zip" && validate_diff "$WORK_DIR/diff.zip" "$current" "$latest"; then
            apply_diff "$WORK_DIR/diff.zip"
            log "已应用增量包 ${current} -> ${latest}"
        else
            log "无匹配本地版本 ${current} 的有效增量包，使用全量包 ${latest}"
            install_full
        fi
    fi

    printf '%s\n' "$latest" > "$MARKER"
    redeploy
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main
fi
