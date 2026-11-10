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

set_classicui_key() {
    # set_classicui_key <file> <key> <value>：键存在则整行替换，否则追加。
    # 不用 sed -i，兼容测试环境和 BSD 工具链。
    local file="$1" key="$2" value="$3" tmp
    if grep -q "^${key}=" "$file" 2>/dev/null; then
        tmp="${file}.fuyaorime.tmp"
        awk -v key="$key" -v value="$value" '
            index($0, key "=") == 1 { print key "=" value; replaced = 1; next }
            { print }
            END { if (!replaced) print key "=" value }' "$file" > "$tmp" \
            && cat "$tmp" > "$file" && rm -f "$tmp"
    else
        printf '%s=%s\n' "$key" "$value" >> "$file"
    fi
}

# classicui.conf 为顶层键值文件；仅管理 Theme/DarkTheme/UseDarkTheme，
# 用户自选的非 fuyaorime 主题保持原样，仅在全新配置时开启跟随系统明暗。
configure_classicui_theme() {
    local conf="$1/classicui.conf" existed=0 theme="" dark="" target="fuyaorime-citrus"
    if [ -f "$conf" ]; then
        existed=1
        theme=$(sed -n 's/^Theme=//p' "$conf" | tail -n 1 | tr -d '\r')
        dark=$(sed -n 's/^DarkTheme=//p' "$conf" | tail -n 1 | tr -d '\r')
    fi
    if [ -n "$theme" ] && [ "${theme#fuyaorime-}" = "$theme" ]; then
        log "fcitx5 使用自定义主题 ${theme}，保持不变"
        return 0
    fi
    mkdir -p "$1"
    set_classicui_key "$conf" "Theme" "$target"
    if [ -z "$dark" ] || [ "${dark#fuyaorime-}" != "$dark" ]; then
        set_classicui_key "$conf" "DarkTheme" "${target}-dark"
    fi
    if [ "$existed" -eq 0 ]; then
        set_classicui_key "$conf" "UseDarkTheme" "True"
    fi
    log "fcitx5 已启用皮肤 ${target}（暗色 ${target}-dark）"
}

# 将配置包内的 fcitx5 主题安装到用户主题目录，供 fcitx5-rime 复刻桌面端配色；
# 仅检测到 fcitx5 时执行，ibus-rime 的候选窗跟随系统主题，无法由 Rime 配置定制。
install_fcitx5_theme() {
    [ -d "$RIME_DIR/fcitx5-themes" ] || return 0
    local data_home="${XDG_DATA_HOME:-$HOME/.local/share}" config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
    if [ ! -d "$data_home/fcitx5" ] && [ ! -d "$config_home/fcitx5" ]; then
        return 0
    fi
    local theme_dir="$data_home/fcitx5/themes" theme
    mkdir -p "$theme_dir"
    for theme in "$RIME_DIR/fcitx5-themes"/*; do
        [ -d "$theme" ] || continue
        rm -rf "${theme_dir:?}/${theme##*/}"
        cp -r "$theme" "$theme_dir/"
    done
    log "已安装 FuyaoRime fcitx5 皮肤（薄荷绿、柑橘黄及暗色变体）"
    configure_classicui_theme "$config_home/fcitx5/conf"
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
        install_fcitx5_theme || log "fcitx5 皮肤安装失败，输入法配置不受影响"
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
    install_fcitx5_theme || log "fcitx5 皮肤安装失败，输入法配置不受影响"
    redeploy
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main
fi
