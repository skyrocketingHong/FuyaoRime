#!/usr/bin/env bash
# fuyaorime-update-linux.sh - 增量更新 FuyaoRime 并重新部署 ibus-rime / fcitx5-rime
#
# 仅在本地版本与最新增量包基线一致时使用 diff，否则下载最新全量包。
# 写入前校验 INCREMENTAL-README.txt 中的适用版本，不跨版串联增量包。
#
# 用法：fuyaorime-update-linux.sh [Rime 目录] [--github-proxy URL]
# 目录缺省 ${XDG_CONFIG_HOME:-~/.config}/rime，适合放入 crontab 每日运行。

set -euo pipefail

REPO="skyrocketingHong/FuyaoRime"
RIME_DIR=""
GITHUB_PROXY=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --github-proxy)
            [ "$#" -ge 2 ] || { echo "--github-proxy 缺少代理前缀" >&2; exit 2; }
            GITHUB_PROXY="$2"
            shift 2
            ;;
        -h|--help)
            echo "用法：${BASH_SOURCE[0]##*/} [Rime 目录] [--github-proxy URL]"
            exit 0
            ;;
        -*) echo "未知选项，请使用 --help 查看用法" >&2; exit 2 ;;
        *)
            [ -z "$RIME_DIR" ] || { echo "只能指定一个 Rime 目录" >&2; exit 2; }
            RIME_DIR="$1"
            shift
            ;;
    esac
done
RIME_DIR="${RIME_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/rime}"
# ASVS 1.2.2、2.2.1：代理前缀仅接受不含查询串、片段及空白的 HTTP(S) 地址。
proxy_pattern='^https?://[^/?#[:space:]]+(/[^?#[:space:]]*)?$'
if [ -n "$GITHUB_PROXY" ] && ! [[ "$GITHUB_PROXY" =~ $proxy_pattern ]]; then
    echo "GitHub 代理前缀必须是有效的 HTTP(S) 地址，且不含查询串、片段或空白" >&2
    exit 2
fi
while [[ "$GITHUB_PROXY" == */ ]]; do GITHUB_PROXY="${GITHUB_PROXY%/}"; done
MARKER="$RIME_DIR/fuyaorime-version.txt"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

fetch() {
    local url="$1" name="${1##*/}" route="直连" status
    if [ -n "$GITHUB_PROXY" ]; then
        url="$GITHUB_PROXY/$url"
        route="代理转发"
    fi
    log "开始下载 ${name}（${route}），下方显示下载量、速度和预计剩余时间"
    if curl --no-silent -fL --retry 2 --connect-timeout 15 \
            --speed-limit 1 --speed-time 60 -o "$2" "$url"; then
        log "下载完成 ${name}"
    else
        status=$?
        log "下载失败 ${name}（curl 退出码 ${status}）"
        return "$status"
    fi
}

valid_version() { [[ "$1" =~ ^[0-9]{8}(-v[1-9][0-9]{0,3})?$ ]]; }

version_key() {
    local day="${1%%-v*}" revision=1
    if [ "$day" != "$1" ]; then revision="${1##*-v}"; fi
    printf '%s.%04d' "$day" "$revision"
}

# 公开 Release 跳转不依赖 REST API 的匿名请求额度。
latest_version() {
    local url version
    url=$(curl -fsSLI --retry 2 --connect-timeout 15 --max-time 45 \
        -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest") || return 1
    version="${url##*/v}"
    if valid_version "$version" && [ "$url" = "https://github.com/$REPO/releases/tag/v$version" ]; then
        printf '%s\n' "$version"
    else
        log "Release 页面未返回有效的 FuyaoRime 日期版本" >&2
        return 1
    fi
}

validate_diff() {
    local version
    log "正在校验增量包和适用版本"
    unzip -tq "$1" >/dev/null 2>&1 || return 1
    version=$(unzip -p "$1" INCREMENTAL-README.txt 2>/dev/null \
        | tr -d '\r' | sed -n '/^适用版本:/p') || return 1
    [ "$version" = "适用版本: $2 -> $3" ]
}

is_protected_path() {
    local path
    path=$(printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]')
    case "/$path/" in
        */installation.yaml/*|*/userdb/*|*/*.userdb/*) return 0 ;;
    esac
    return 1
}

assert_safe_target() {
    local rest="$1" part target="$RIME_DIR"
    case "$rest" in
        ""|/*|*\\*|*:*) log "拒绝不安全的更新路径"; return 1 ;;
    esac
    case "/$rest/" in */../*) log "拒绝越出配置目录的路径"; return 1 ;; esac
    while [ -n "$rest" ]; do
        part="${rest%%/*}"
        if [ "$rest" = "$part" ]; then rest=""; else rest="${rest#*/}"; fi
        [ -n "$part" ] && [ "$part" != "." ] || continue
        target="$target/$part"
        [ ! -L "$target" ] || { log "更新路径包含符号链接，已停止"; return 1; }
    done
}

extract_package() {
    local path
    log "正在检查配置包路径"
    unzip -Z1 "$1" > "$WORK_DIR/package-files.txt"
    while IFS= read -r path; do
        is_protected_path "$path" && continue
        assert_safe_target "$path" || return 1
    done < "$WORK_DIR/package-files.txt"
    unzip -Z -l "$1" | awk '$1 ~ /^l/ {link=1} END {exit link ? 1 : 0}' \
        || { log "配置包包含符号链接，已停止"; return 1; }
    # 在解压阶段排除用户数据，不能覆盖后再用可能过期的数据库备份恢复。
    log "正在解压并更新配置，保留安装信息和用户数据库"
    rm -f "$MARKER"
    unzip -oq -C "$1" -d "$RIME_DIR" -x \
        'installation.yaml' '*/installation.yaml' 'installation.yaml/*' '*/installation.yaml/*' \
        '*.userdb' '*.userdb/*' 'userdb' 'userdb/*' '*/userdb' '*/userdb/*'
}

apply_diff() {
    extract_package "$1"
    local readme="$RIME_DIR/INCREMENTAL-README.txt"
    [ -f "$readme" ] || return 0
    awk '/已从配置包移除/ {del=1; next} del && /^  - / {sub(/^  - /, ""); print; next} del {exit}' "$readme" \
        | while IFS= read -r f; do
            f="${f%$'\r'}"
            if is_protected_path "$f"; then
                log "已忽略用户数据的删除请求"
                continue
            fi
            assert_safe_target "$f" || exit 1
            [ ! -d "$RIME_DIR/$f" ] || continue
            rm -f -- "$RIME_DIR/$f"
        done
    rm -f "$readme"
}

install_full() {
    fetch "https://github.com/$REPO/releases/download/v$latest/fuyaorime-$latest.zip" \
        "$WORK_DIR/full.zip" || { log "全量包下载失败"; exit 1; }
    log "正在校验全量包"
    unzip -tq "$WORK_DIR/full.zip" >/dev/null 2>&1 || { log "全量包校验失败"; exit 1; }
    extract_package "$WORK_DIR/full.zip"
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
    local latest current
    log "正在查询最新 Release 版本"
    latest=$(latest_version) || { log "获取最新 Release 版本失败，请检查 GitHub 连接"; exit 1; }

    mkdir -p "$RIME_DIR"
    current=$(cat "$MARKER" 2>/dev/null || true)
    if [ "$current" = "$latest" ]; then
        log "已是最新版本 $latest"
        return 0
    fi
    if valid_version "$current" && [[ "$(version_key "$current")" > "$(version_key "$latest")" ]]; then
        log "本地版本 ${current} 新于远端 ${latest}，跳过更新"
        return 0
    fi

    if ! valid_version "$current"; then
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
