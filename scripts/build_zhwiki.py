#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_zhwiki.py - 从维基媒体 dump 自建 zhwiki 系词库

数据源为 dumps.wikimedia.org 的条目标题列表（all-titles-in-ns0，仅标题、
不含正文），转换流程移植自 felixonmars/fcitx5-pinyin-zhwiki 的 Makefile
与 convert.py：OpenCC 繁转简、标题过滤、pypinyin 标注拼音。

维基 dump 每月 1 日（维基媒体时区）发布一批，但标题文件就绪时间不固
定：实测 zhwiki 在 1 日 11:00～14:00 UTC 之间居多，2026 年 8 月批次拖
到 4 日，zhwikisource 曾拖到 2 日。因此按月去重、以当月批次为目标：
每月 1 日（北京时间）起开始检查，批次未就绪则由每日运行重试，当月批
次全部建成后才停止检查。自建产物版本号取 dump 日期（YYYYMMDD），与
上游 release 的日期版本可比：update_dicts.py 侧已有本地版本新于远端
则跳过的保护，本脚本侧的版本门槛保证不会用旧 dump 覆盖新内容。

web-slang 单独处理：数据源是维基百科页面《中国大陆网络用语列表》的
实时 wikitext（转换逻辑移植自上游 zhwiki-web-slang.py），上游 release
自 20260416 后未再更新，改为每日尝试快照自建；页面内容无变化时不落
盘、版本号不变，有变化时版本号取快照日期。

依赖：opencc、pypinyin、regex、more-itertools（pip 安装）

用法：
    python3 scripts/build_zhwiki.py                # 构建全部词库（每月一次）
    python3 scripts/build_zhwiki.py --only zhwiki  # 只构建 zhwiki（不记月状态）
    python3 scripts/build_zhwiki.py --force        # 忽略版本门槛强制重建

单个词库构建失败只打印告警、保留现有词库（回退到上游下载版本），不中
止整体流程；release notes 以本地词库版本号为准。
"""

import argparse
import datetime
import gzip
import json
import logging
import os
import re
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request

import opencc
import regex
from more_itertools import collapse
from pypinyin import lazy_pinyin

DUMP_PROJECTS = ['zhwiki', 'zhwiktionary', 'zhwikisource']
DUMPS_INDEX_URL = 'https://dumps.wikimedia.org/{}/'
TITLES_GZ_URL = 'https://dumps.wikimedia.org/{project}/{date}/{project}-{date}-all-titles-in-ns0.gz'

WEB_SLANG_PAGE = '中国大陆网络用语列表'
WEB_SLANG_API_URL = ('https://zh.wikipedia.org/w/rest.php/v1/page/'
                     + urllib.parse.quote(WEB_SLANG_PAGE))

# 生成规则版本：变更过滤规则时递增，与 scripts/.zhwiki_build_rules 中
# 记录的版本不一致即强制重建（词库版本号仍是 dump 日期，无法体现规则
# 变化）
# 1: 上游 convert.py 原样移植
# 2: 过滤判决书等司法文书标题与连字符开头的词目
BUILD_RULES_VERSION = 2
RULES_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.zhwiki_build_rules')

# 版本日期与月度目标均以北京时间为准，运行器系统时钟是 UTC
BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))

# ===== 以下转换逻辑移植自上游 convert.py，保持规则一致 =====

_MINIMUM_LEN = 2
_LIST_PAGE_ENDINGS = ['列表', '对照表']

# 维基文库 2026 年批量导入裁判文书（占 ns0 标题约八成），此类标题对
# 输入法无价值；zhwiki/zhwiktionary 偶有同名条目一并过滤
_JUDICIAL_DOC_RE = regex.compile(r'判决书|裁定书|决定书|起诉书|裁决书|调解书|上诉状')

_PINYIN_SEPARATOR = "'"
# https://ayaka.shn.hk/hanregex/
_CONVERTABLE_RE = regex.compile(
    r"([\p{Unified_Ideograph}\u3006\u3007\u00b7\u002d\u2010\u2013\u2014]"
    r"[\ufe00-\ufe0f\U000e0100-\U000e01ef]?|[a-zA-Z\p{Greek}])+")
_HANZI_RE = regex.compile(
    r"([\p{Unified_Ideograph}\u3006\u3007\u00b7\u002d\u2010\u2013\u2014]"
    r"[\ufe00-\ufe0f\U000e0100-\U000e01ef]?)+")
_BOUND_RE = regex.compile(
    r"(?<=[\p{Unified_Ideograph}\u3006\u3007\u00b7\u002d\u2010\u2013\u2014]"
    r"[\ufe00-\ufe0f\U000e0100-\U000e01ef]?)(?=[a-zA-Z\p{Greek}])"
    r"|(?<=[a-zA-Z\p{Greek}])(?=[\p{Unified_Ideograph}\u3006\u3007\u00b7\u002d"
    r"\u2010\u2013\u2014][\ufe00-\ufe0f\U000e0100-\U000e01ef]?)")
_INTERPUNCT_TRANSTAB = str.maketrans("", "", "·-‐–—")
_TO_SIMPLIFIED_CHINESE = opencc.OpenCC('t2s.json')

_PINYIN_FIXES = {
    'n': 'en',  # https://github.com/felixonmars/fcitx5-pinyin-zhwiki/issues/13
}

_GREEK2LATIN = {
    u'\u0391': ['A', 'L', 'P', 'ha'],          # Alpha
    u'\u0392': ['B', 'E', 'ta'],               # Beta
    u'\u0393': ['ga', 'M', 'ma'],              # Gamma
    u'\u0394': ['de', 'L', 'ta'],              # Delta
    u'\u0395': ['E', 'P', 'si', 'L', 'O', 'N'],  # Epsilon
    u'\u0396': ['ze', 'ta'],                   # Zeta
    u'\u0397': ['E', 'ta'],                    # Eta
    u'\u0398': ['T', 'he', 'ta'],              # Theta
    u'\u0399': ['I', 'O', 'ta'],               # Iota
    u'\u039A': ['ka', 'P', 'pa'],              # Kappa
    u'\u039B': ['la', 'M', 'B', 'da'],         # Lambda
    u'\u039C': ['mu'],                         # Mu
    u'\u039D': ['nu'],                         # Nu
    u'\u039E': ['xi'],                         # Xi
    u'\u039F': ['O', 'mi', 'C', 'R', 'O', 'N'],  # Omicron
    u'\u03A0': ['pi'],                         # Pi
    u'\u03A1': ['R', 'H', 'O'],                # Rho
    u'\u03A3': ['si', 'G', 'ma'],              # Sigma
    u'\u03A4': ['ta', 'U'],                    # Tau
    u'\u03A5': ['U', 'P', 'si', 'L', 'O', 'N'],  # Upsilon
    u'\u03A6': ['P', 'hi'],                    # Phi
    u'\u03A7': ['C', 'hi'],                    # Chi
    u'\u03A8': ['P', 'si'],                    # Psi
    u'\u03A9': ['O', 'me', 'ga'],              # Omega
    u'\u03B1': ['A', 'L', 'P', 'ha'],          # alpha
    u'\u03B2': ['B', 'E', 'ta'],               # beta
    u'\u03B3': ['ga', 'M', 'ma'],              # gamma
    u'\u03B4': ['de', 'L', 'ta'],              # delta
    u'\u03B5': ['E', 'P', 'si', 'L', 'O', 'N'],  # epsilon
    u'\u03B6': ['ze', 'ta'],                   # zeta
    u'\u03B7': ['E', 'ta'],                    # eta
    u'\u03B8': ['T', 'he', 'ta'],              # theta
    u'\u03B9': ['I', 'O', 'ta'],               # iota
    u'\u03BA': ['ka', 'P', 'pa'],              # kappa
    u'\u03BB': ['la', 'M', 'B', 'da'],         # lambda
    u'\u03BC': ['mu'],                         # mu
    u'\u03BD': ['nu'],                         # nu
    u'\u03BE': ['xi'],                         # xi
    u'\u03BF': ['O', 'mi', 'C', 'R', 'O', 'N'],  # omicron
    u'\u03C0': ['pi'],                         # pi
    u'\u03C1': ['R', 'H', 'O'],                # rho
    u'\u03C3': ['si', 'G', 'ma'],              # sigma
    u'\u03C4': ['ta', 'U'],                    # tau
    u'\u03C5': ['U', 'P', 'si', 'L', 'O', 'N'],  # upsilon
    u'\u03C6': ['P', 'hi'],                    # phi
    u'\u03C7': ['C', 'hi'],                    # chi
    u'\u03C8': ['P', 'si'],                    # psi
    u'\u03C9': ['O', 'me', 'ga'],              # omega
    # NFD of final sigma is itself
    u'\u03C2': ['si', 'G', 'ma'],              # final sigma
}


def is_good_title(title, previous_title=None):
    if not _CONVERTABLE_RE.fullmatch(title):
        return False
    if not _HANZI_RE.search(title):
        return False
    if len(title) < _MINIMUM_LEN:
        return False
    if title.endswith(tuple(_LIST_PAGE_ENDINGS)):
        return False
    if _JUDICIAL_DOC_RE.search(title):
        return False
    if previous_title and \
      len(previous_title) >= 4 and \
      title.startswith(previous_title):
        return False
    return True


def map_to_libime_compatible_fmt(s):
    if _HANZI_RE.fullmatch(s):
        yield from [_PINYIN_FIXES.get(item, item) for item in lazy_pinyin(s)]
    else:
        # NFD of Greek letter is basic alphabet + modifier, so the first char
        # is basic alphabet. e.g. ἁ -> α + ̔
        yield from [_GREEK2LATIN.get(unicodedata.normalize('NFD', item)[0], item.upper())
                    for item in s]


def convert_titles(titles_path):
    """逐行转换标题文件，产出 (word, pinyin) 生成器"""
    previous_title = None
    with open(titles_path, encoding='utf-8') as f:
        for line in f:
            title = _TO_SIMPLIFIED_CHINESE.convert(line.strip())
            if is_good_title(title, previous_title):
                stripped_title = title.translate(_INTERPUNCT_TRANSTAB)
                pinyins = [map_to_libime_compatible_fmt(s)
                           for s in regex.split(_BOUND_RE, stripped_title) if s]
                pinyin = _PINYIN_SEPARATOR.join(collapse(pinyins)).replace("'", " ")
                if _HANZI_RE.search(pinyin):
                    logging.info(f'Failed to convert to Pinyin. Ignoring: {pinyin}')
                    continue
                yield title, pinyin
                previous_title = title


# ===== web-slang：解析逻辑移植自上游 zhwiki-web-slang.py =====

def fetch_web_slang_wikitext():
    # 维基媒体 API 要求可识别的 User-Agent
    req = urllib.request.Request(
        WEB_SLANG_API_URL,
        headers={'User-Agent': 'FuyaoRime/1.0 (https://github.com/skyrocketingHong/FuyaoRime)'})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode('utf-8'))['source']


def trim_templates(wikitext):
    template_level = 0
    new_wikitext = ""
    while True:
        assert template_level >= 0, ValueError("Unbalanced template in wikitext:\n" + wikitext)
        pre_open, open_tag, post_open = wikitext.partition("{{")
        pre_close, close_tag, post_close = wikitext.partition("}}")
        if open_tag and (not close_tag or len(pre_open) < len(pre_close)):
            wikitext = post_open
            if template_level == 0:
                new_wikitext += pre_open
            template_level += 1
        elif close_tag:
            wikitext = post_close
            template_level -= 1
        else:
            assert template_level == 0, ValueError("Unbalanced template in wikitext:\n" + wikitext)
            assert open_tag == close_tag == "", RuntimeError("Cosmic radiation detected")
            new_wikitext += wikitext
            break
    return new_wikitext


def process_web_slang(wikitext):
    """从页面 wikitext 提取词条，保持页面顺序去重"""
    wikitext = trim_templates(wikitext)
    words = {}

    def add_word(word):
        for garbage in ("[", "]", "…", ":", "：", ")", "）", '"', "“", "”", "-{", "}-", "简称", "簡稱"):
            word = word.replace(garbage, "")
        words[word.strip()] = None

    def add_words(word):
        for word_separator in ("、", "/", "|", "，", "。", "?", "？", "(", "（"):
            if word_separator in word:
                for w in word.split(word_separator):
                    add_words(w.strip())
                break
        else:
            add_word(word)

    def iter_bolds(line):
        line_bak = line
        while "'''" in line:
            _, sep1, line = line.partition("'''")
            bold, sep2, line = line.partition("'''")
            assert sep1 and sep2, ValueError("Unclosed ''' in line: " + line_bak)
            yield bold

    for line in wikitext.split("\n"):
        if not line.startswith("*"):
            continue
        line = line.strip("*").strip()
        pre_colon, sep, post_colon = line.partition("'''：")
        if not sep:
            pre_colon, sep, post_colon = line.partition("''':")
        for bold in iter_bolds(pre_colon + sep):
            add_words(bold)
        for bold in iter_bolds(post_colon):
            # 冒号后的粗体跳过缩写来源（长度通常不大于 2）
            if len(bold) > 2:
                add_words(bold)

    return words


# ===== 构建流程 =====

HTTP_TIMEOUT = 60  # 秒，连接与每次读取的超时

# 标题 dump 的本地缓存目录（可用环境变量 FUYAO_TITLES_CACHE 覆盖）：
# dumps.wikimedia.org 连接不稳定时，可用 curl 等工具断点续传下载到此处，
# 脚本检测到同名文件即跳过下载
CACHE_DIR = os.environ.get(
    'FUYAO_TITLES_CACHE', os.path.expanduser('~/Library/Caches/fuyaorime'))


def find_cached_titles(project, dump_date):
    cache_path = os.path.join(CACHE_DIR, f'{project}-{dump_date}-all-titles-in-ns0.gz')
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        return cache_path
    return None


def http_get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)


def list_dump_dates(project):
    """列出 dumps.wikimedia.org 上该项目全部 dump 日期，升序返回"""
    html = http_get(DUMPS_INDEX_URL.format(project)).read().decode('utf-8')
    dates = re.findall(r'href="(\d{8})/"', html)
    return sorted(set(dates))


def find_latest_available_dump(project):
    """从新到旧找到标题文件确实存在（可完整下载）的 dump 日期"""
    for date in reversed(list_dump_dates(project)):
        url = TITLES_GZ_URL.format(project=project, date=date)
        try:
            with http_get(url) as resp:
                if resp.status == 200:
                    return date, url
        except Exception:
            continue
    return None, None


def get_local_dict_version(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        for line in f:
            match = re.match(r'version:\s*"?([^"\s]+)"?', line)
            if match:
                return match.group(1).strip()
    return None


def build_project(project, dest_file, force=False):
    dump_date, gz_url = find_latest_available_dump(project)
    if not dump_date:
        print(f"[{project}] 未找到可用的标题 dump，跳过")
        return False

    local_version = get_local_dict_version(dest_file)
    if not force and local_version and re.fullmatch(r'\d{8}', local_version) \
            and local_version >= dump_date:
        print(f"[{project}] 本地版本 ({local_version}) 已覆盖 dump {dump_date}，跳过")
        return True

    print(f"[{project}] 使用 dump {dump_date} 重建词库...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        gz_path = os.path.join(tmp_dir, 'titles.gz')
        titles_path = os.path.join(tmp_dir, 'titles')
        cached = find_cached_titles(project, dump_date)
        if cached:
            print(f"[{project}] 使用本地缓存: {cached}")
            gz_path = cached
        else:
            print(f"[{project}] 正在下载: {gz_url}")
            last_err = None
            for attempt in range(3):
                try:
                    with http_get(gz_url) as resp, open(gz_path, 'wb') as f:
                        f.write(resp.read())
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    print(f"[{project}] 下载失败（第 {attempt + 1} 次）: {e}")
            if last_err is not None:
                raise RuntimeError(f'下载标题 dump 失败: {last_err}')
        with gzip.open(gz_path, 'rb') as gz_in, open(titles_path, 'wb') as f_out:
            f_out.write(gz_in.read())

        print(f"[{project}] 正在转换标题（繁转简、拼音标注）...")
        entries = set()
        count = 0
        for word, pinyin in convert_titles(titles_path):
            # 纯连字符类标题（如 "--"）会得到空拼音；"-D"、"-i" 等词缀
            # 条目以连字符开头，均无输入价值。上游成品同样存在这些行、
            # 由下载路径的 cleanup_dict_file 清理，这里直接过滤保持一致
            if not pinyin or word.startswith('-'):
                continue
            entries.add(f'{word}\t{pinyin}\n')
            count += 1
            if count % 200000 == 0:
                print(f"[{project}] 已处理 {count} 条")

        # 临时文件写在目标目录内再原子替换：os.replace 不能跨文件系统
        # （如 macOS 系统盘临时目录到外置盘仓库）
        tmp_dict = dest_file + '.tmp'
        with open(tmp_dict, 'w', encoding='utf-8') as f:
            f.write(f'---\nname: {project}\nversion: "{dump_date}"\nsort: by_weight\n...\n')
            f.writelines(sorted(entries))

        os.replace(tmp_dict, dest_file)
        size_mb = os.path.getsize(dest_file) / 1024 / 1024
        print(f"[{project}] 成功生成 {dest_file}（{len(entries)} 条，{size_mb:.1f} MB，版本 {dump_date}）")
        return True


def build_web_slang(dest_file, force=False):
    print(f"[web-slang] 抓取《{WEB_SLANG_PAGE}》并重建词库...")
    words = process_web_slang(fetch_web_slang_wikitext())
    with tempfile.TemporaryDirectory() as tmp_dir:
        words_path = os.path.join(tmp_dir, 'web-slang.source')
        with open(words_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(words) + '\n')
        entries = set()
        for word, pinyin in convert_titles(words_path):
            if not pinyin or word.startswith('-'):
                continue
            entries.add(f'{word}\t{pinyin}\n')
    body = ''.join(sorted(entries))

    # 内容未变化不落盘，版本号不随快照逐日空转
    if not force and os.path.exists(dest_file):
        with open(dest_file, encoding='utf-8') as f:
            old_body = f.read().split('\n...\n', 1)[-1]
        if old_body == body:
            print(f"[web-slang] 页面内容无变化，跳过（{len(entries)} 条）")
            return True

    version = datetime.datetime.now(BEIJING_TZ).date().strftime('%Y%m%d')
    tmp_dict = dest_file + '.tmp'
    with open(tmp_dict, 'w', encoding='utf-8') as f:
        f.write(f'---\nname: web-slang\nversion: "{version}"\nsort: by_weight\n...\n')
        f.write(body)
    os.replace(tmp_dict, dest_file)
    print(f"[web-slang] 成功生成 {dest_file}（{len(entries)} 条，版本 {version}）")
    return True


def rules_version_matches():
    try:
        with open(RULES_STATE_FILE, encoding='utf-8') as f:
            return f.read().strip() == str(BUILD_RULES_VERSION)
    except OSError:
        return False


def write_rules_version():
    with open(RULES_STATE_FILE, 'w', encoding='utf-8') as f:
        f.write(f'{BUILD_RULES_VERSION}\n')


def month_target(today=None):
    """当月批次日期（YYYYMM01），dump 目录固定为每月 1 日"""
    if today is None:
        today = datetime.datetime.now(BEIJING_TZ).date()
    return today.strftime('%Y%m') + '01'


def monthly_build_done(dict_dir, target):
    for name in DUMP_PROJECTS:
        version = get_local_dict_version(os.path.join(dict_dir, f'{name}.dict.yaml'))
        if not version or version < target:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description='从维基媒体标题 dump 自建 zhwiki 系词库')
    parser.add_argument('--only', choices=DUMP_PROJECTS + ['web-slang'], action='append',
                        help='只构建指定词库，可重复传入')
    parser.add_argument('--force', action='store_true',
                        help='忽略版本门槛，强制重建')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    target_dir = os.path.join(project_dir, 'custom_dicts')
    os.makedirs(target_dir, exist_ok=True)

    # 过滤规则变更（BUILD_RULES_VERSION 递增）时强制重建一次
    force = args.force or not rules_version_matches()

    # dump 三库月度门槛：版本均不早于当月批次（YYYYMM01）即本月已完成，
    # 不再访问 dump 站点；未达标（含批次未就绪）由每日运行重试。
    # --force 与 --only 为人工指定，不受门槛约束
    target = month_target()
    dump_projects = [p for p in (args.only or DUMP_PROJECTS) if p != 'web-slang']
    failed = []

    if not force and not args.only and monthly_build_done(target_dir, target):
        print(f'当月 dump 批次（{target}）均已构建，跳过三库自建')
    else:
        for project in dump_projects:
            try:
                if not build_project(project, os.path.join(target_dir, f'{project}.dict.yaml'),
                                     force=force):
                    failed.append(project)
            except Exception as e:
                # 单库失败保留现有词库（上游下载版本兜底），不中止整体
                print(f"[{project}] 构建失败，保留现有词库: {e}")
                failed.append(project)

    # web-slang 每日尝试快照，内容无变化不落盘
    if not args.only or 'web-slang' in args.only:
        try:
            if not build_web_slang(os.path.join(target_dir, 'web-slang.dict.yaml'),
                                   force=force):
                failed.append('web-slang')
        except Exception as e:
            print(f"[web-slang] 构建失败，保留现有词库: {e}")
            failed.append('web-slang')

    if not failed:
        write_rules_version()
        print('全部词库构建完成')
    else:
        print(f"以下词库未更新: {', '.join(failed)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
