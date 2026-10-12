#!/usr/bin/env bash
# fuyaorime-update-android.sh - 在 Termux 中通过 Shizuku 更新小企鹅输入法的 FuyaoRime 配置
#
# Termux 负责查询版本、下载校验并解压到共享存储的暂存目录；
# 再通过 rish 以 shell 身份把暂存文件写入 Android/data 下的 Rime 用户目录，
# 最后强制停止输入法，输入法重启时检测到顶层 YAML 变化会自动重新部署。
# 增量与全量的选择逻辑与桌面脚本一致，不串联历史增量包。
#
# 用法：fuyaorime-update-android.sh [Rime 目录] [--github-proxy URL]
#                               [--rish 路径] [--ime-package 包名] [--staging-root 目录]
# Rime 目录缺省 /storage/emulated/0/Android/data/<包名>/files/data/rime，
# 暂存目录缺省位于 /storage/emulated/0/Download，运行结束后自动清理。
# 需要 Termux 的 curl、unzip 与存储权限（termux-setup-storage），
# 以及运行中的 Shizuku 导出的 rish 与 rish_shizuku.dex（须放在 Termux 私有目录）。

set -euo pipefail

REPO="skyrocketingHong/FuyaoRime"
RIME_DIR=""
GITHUB_PROXY=""
RISH=""
IME_PACKAGE="org.fcitx.fcitx5.android"
STAGING_ROOT="/storage/emulated/0/Download"
usage() {
    echo "用法：${BASH_SOURCE[0]##*/} [Rime 目录] [--github-proxy URL]" \
         "[--rish 路径] [--ime-package 包名] [--staging-root 目录]"
}
while [ "$#" -gt 0 ]; do
    case "$1" in
        --github-proxy)
            [ "$#" -ge 2 ] || { echo "--github-proxy 缺少代理前缀" >&2; exit 2; }
            GITHUB_PROXY="$2"
            shift 2
            ;;
        --rish)
            [ "$#" -ge 2 ] || { echo "--rish 缺少路径" >&2; exit 2; }
            RISH="$2"
            shift 2
            ;;
        --ime-package)
            [ "$#" -ge 2 ] || { echo "--ime-package 缺少包名" >&2; exit 2; }
            IME_PACKAGE="$2"
            shift 2
            ;;
        --staging-root)
            [ "$#" -ge 2 ] || { echo "--staging-root 缺少目录" >&2; exit 2; }
            STAGING_ROOT="$2"
            shift 2
            ;;
        -h|--help)
            usage
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
RIME_DIR="${RIME_DIR:-/storage/emulated/0/Android/data/$IME_PACKAGE/files/data/rime}"
while [[ "$RIME_DIR" == */ ]]; do RIME_DIR="${RIME_DIR%/}"; done
while [[ "$STAGING_ROOT" == */ ]]; do STAGING_ROOT="${STAGING_ROOT%/}"; done
STAGE_DIR="$STAGING_ROOT/fuyaorime-update-staging"
# ASVS 1.2.2、2.2.1：代理前缀仅接受不含查询串、片段及空白的 HTTP(S) 地址。
proxy_pattern='^https?://[^/?#[:space:]]+(/[^?#[:space:]]*)?$'
if [ -n "$GITHUB_PROXY" ] && ! [[ "$GITHUB_PROXY" =~ $proxy_pattern ]]; then
    echo "GitHub 代理前缀必须是有效的 HTTP(S) 地址，且不含查询串、片段或空白" >&2
    exit 2
fi
while [[ "$GITHUB_PROXY" == */ ]]; do GITHUB_PROXY="${GITHUB_PROXY%/}"; done
if ! [[ "$IME_PACKAGE" =~ ^[A-Za-z0-9._]+$ ]]; then
    echo "包名仅允许字母、数字、点号和下划线" >&2
    exit 2
fi
# rish 以单引号内嵌路径执行远端命令，所有用户提供的路径与包内路径都必须先排除单引号。
for path_value in "$RIME_DIR" "$STAGING_ROOT" "$RISH"; do
    [[ "$path_value" != *"'"* ]] || { echo "路径包含单引号，无法安全传递给 rish" >&2; exit 2; }
done
case "$STAGE_DIR" in
    "$RIME_DIR"|"$RIME_DIR"/*) echo "暂存目录不能位于 Rime 目录内" >&2; exit 2 ;;
esac
MARKER="$RIME_DIR/fuyaorime-version.txt"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR" "$STAGE_DIR"' EXIT

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

shq() { printf "'%s'" "$1"; }

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

# Termux 无法进入 Android/data，无法像桌面脚本那样沿目标路径排查符号链接，
# 改为拒绝包含引号或空白的条目，符号链接由写入端先删后拷来中和。
assert_safe_target() {
    case "$1" in
        ""|/*|*\\*|*:*|*\'*|*' '*|*\"*) log "拒绝不安全的更新路径"; return 1 ;;
    esac
    case "/$1/" in */../*) log "拒绝越出配置目录的路径"; return 1 ;; esac
}

resolve_rish() {
    local candidate
    if [ -z "$RISH" ]; then
        if command -v rish >/dev/null 2>&1; then
            RISH="$(command -v rish)"
        else
            for candidate in "$HOME/rish" "$HOME/bin/rish" "${PREFIX:-/data/data/com.termux/files/usr}/bin/rish"; do
                if [ -x "$candidate" ]; then
                    RISH="$candidate"
                    break
                fi
            done
        fi
    fi
    if [ -z "$RISH" ] || [ ! -x "$RISH" ]; then
        log "找不到可执行的 rish。请在 Shizuku 中导出 rish 与 rish_shizuku.dex，复制到 Termux 私有目录后重试"
        exit 1
    fi
    log "使用 rish：$RISH"
}

prepare_staging() {
    local path
    rm -rf "$STAGE_DIR"
    mkdir -p "$STAGE_DIR" \
        || { log "无法创建暂存目录，请先执行 termux-setup-storage 授予存储权限"; exit 1; }
    unzip -Z1 "$1" > "$WORK_DIR/package-files.txt"
    while IFS= read -r path; do
        is_protected_path "$path" && continue
        assert_safe_target "$path" || exit 1
    done < "$WORK_DIR/package-files.txt"
    unzip -Z -l "$1" | awk '$1 ~ /^l/ {link=1} END {exit link ? 1 : 0}' \
        || { log "配置包包含符号链接，已停止"; exit 1; }
    log "正在解压到共享存储暂存目录，供 rish 读取"
    unzip -oq -C "$1" -d "$STAGE_DIR" -x \
        'installation.yaml' '*/installation.yaml' 'installation.yaml/*' '*/installation.yaml/*' \
        '*.userdb' '*.userdb/*' 'userdb' 'userdb/*' '*/userdb' '*/userdb/*'
}

# 在解压阶段排除用户数据，不能覆盖后再用可能过期的数据库备份恢复。
install_to_device() {
    local mode="$1" latest="$2" path entry del_args="" remote_cmd
    if [ "$mode" = diff ] && [ -f "$STAGE_DIR/INCREMENTAL-README.txt" ]; then
        while IFS= read -r path; do
            path="${path%$'\r'}"
            if is_protected_path "$path"; then
                log "已忽略用户数据的删除请求"
                continue
            fi
            assert_safe_target "$path" || exit 1
            del_args="$del_args $(shq "$RIME_DIR/$path")"
        done < <(awk '/已从配置包移除/ {del=1; next} del && /^  - / {sub(/^  - /, ""); print; next} del {exit}' \
            "$STAGE_DIR/INCREMENTAL-README.txt")
    fi
    rm -f "$STAGE_DIR/INCREMENTAL-README.txt"
    local entries
    entries=()
    while IFS= read -r entry; do
        [ -n "$entry" ] && entries+=("$entry")
    done < <(ls -A "$STAGE_DIR")
    [ "${#entries[@]}" -gt 0 ] || { log "暂存目录为空，已停止"; exit 1; }
    remote_cmd="mkdir -p $(shq "$RIME_DIR") && rm -f $(shq "$MARKER")"
    if [ "$mode" = full ]; then
        # 全量包各顶层条目完整：整项替换可顺带清掉包内已删除的旧文件与同名符号链接。
        for entry in "${entries[@]}"; do
            remote_cmd+=" && rm -rf -- $(shq "$RIME_DIR/$entry")"
        done
    else
        # 增量包目录不完整，只按包内文件清单预删除同名路径，防止 cp 跟随既有符号链接写入别处。
        while IFS= read -r path; do
            case "$path" in ''|*/|INCREMENTAL-README.txt) continue ;; esac
            is_protected_path "$path" && continue
            remote_cmd+=" && rm -f -- $(shq "$RIME_DIR/$path")"
        done < "$WORK_DIR/package-files.txt"
    fi
    for entry in "${entries[@]}"; do
        remote_cmd+=" && cp -a $(shq "$STAGE_DIR/$entry") $(shq "$RIME_DIR")/"
    done
    # 删除清单是建议性清理，远端无法区分目录条目，失败不应中断安装（与桌面脚本跳过目录一致）。
    [ -z "$del_args" ] || remote_cmd+=" && { rm -f --$del_args 2>/dev/null || true; }"
    # librime 的 detect_modifications 只比较用户目录顶层 YAML 的修改时间，
    # 触碰配置包自有的顶层词库引用文件，确保输入法重启后一定重新部署。
    remote_cmd+=" && touch -c $(shq "$RIME_DIR/rime_ice.custom.dict.yaml")"
    remote_cmd+=" && echo $(shq "$latest") > $(shq "$MARKER")"
    log "正在通过 rish 写入配置目录"
    "$RISH" -c "$remote_cmd" \
        || { log "写入配置目录失败；若为权限问题，请确认 Shizuku 正在运行"; exit 1; }
}

restart_ime() {
    log "正在请求重启输入法以触发重新部署"
    if "$RISH" -c "am force-stop $(shq "$IME_PACKAGE")"; then
        log "已请求重启 ${IME_PACKAGE}，输入法下次启动时会检测配置变化并自动重新部署"
    else
        log "重启请求失败，配置已更新；输入法下次自行重启时仍会自动重新部署"
    fi
}

main() {
    local latest current mode package_zip
    resolve_rish
    "$RISH" -c true >/dev/null 2>&1 \
        || { log "无法通过 rish 执行命令，请确认 Shizuku 已启动"; exit 1; }
    log "正在查询最新 Release 版本"
    latest=$(latest_version) || { log "获取最新 Release 版本失败，请检查 GitHub 连接"; exit 1; }
    current=$("$RISH" -c "cat $(shq "$MARKER") 2>/dev/null" 2>/dev/null | tr -d '\r\n') || current=""

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
        mode=full
        package_zip="$WORK_DIR/full.zip"
        fetch "https://github.com/$REPO/releases/download/v$latest/fuyaorime-$latest.zip" \
            "$package_zip" || { log "全量包下载失败"; exit 1; }
        log "正在校验全量包"
        unzip -tq "$package_zip" >/dev/null 2>&1 || { log "全量包校验失败"; exit 1; }
    else
        package_zip="$WORK_DIR/diff.zip"
        if fetch "https://github.com/$REPO/releases/download/v$latest/fuyaorime-$latest-diff-from-$current.zip" \
                "$package_zip" && validate_diff "$package_zip" "$current" "$latest"; then
            mode=diff
            log "已下载并校验增量包 ${current} -> $latest"
        else
            log "无匹配本地版本 ${current} 的有效增量包，使用全量包 $latest"
            mode=full
            package_zip="$WORK_DIR/full.zip"
            fetch "https://github.com/$REPO/releases/download/v$latest/fuyaorime-$latest.zip" \
                "$package_zip" || { log "全量包下载失败"; exit 1; }
            log "正在校验全量包"
            unzip -tq "$package_zip" >/dev/null 2>&1 || { log "全量包校验失败"; exit 1; }
        fi
    fi

    prepare_staging "$package_zip"
    install_to_device "$mode" "$latest"
    log "已应用${mode}包 $latest"
    restart_ime
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main
fi
