#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_zhwiki.py - 从维基媒体 dump 自建 zhwiki 系词库

数据源为 dumps.wikimedia.org 的条目标题列表（all-titles-in-ns0，仅标题、
不含正文），转换流程移植自 felixonmars/fcitx5-pinyin-zhwiki 的 Makefile
与 convert.py：OpenCC 繁转简、标题过滤、pypinyin 标注拼音。

维基 dump 约每月发布一批，因此按需构建：仅当最新 dump 日期新于
custom_dicts/ 下对应词库的版本号时才下载并重建，同一批 dump 不会重复
构建。自建产物版本号取 dump 日期（YYYYMMDD），与上游 release 的日期版
本可比：update_dicts.py 侧已有本地版本新于远端则跳过的保护，本脚本侧
的版本门槛保证不会用旧 dump 覆盖新内容。

依赖：opencc、pypinyin、regex、more-itertools（pip 安装）

用法：
    python3 scripts/build_zhwiki.py                # 构建全部三库
    python3 scripts/build_zhwiki.py --only zhwiki  # 只构建 zhwiki
    python3 scripts/build_zhwiki.py --force        # 忽略版本门槛强制重建

单个词库构建失败只打印告警、保留现有词库（回退到上游下载版本），不中
止整体流程；release notes 以本地词库版本号为准。
"""

import argparse
import gzip
import logging
import os
import re
import sys
import tempfile
import unicodedata
import urllib.request

import opencc
import regex
from more_itertools import collapse
from pypinyin import lazy_pinyin

DUMP_PROJECTS = ['zhwiki', 'zhwiktionary', 'zhwikisource']
DUMPS_INDEX_URL = 'https://dumps.wikimedia.org/{}/'
TITLES_GZ_URL = 'https://dumps.wikimedia.org/{project}/{date}/{project}-{date}-all-titles-in-ns0.gz'

# 生成规则版本：变更过滤规则时递增，与 scripts/.zhwiki_build_rules 中
# 记录的版本不一致即强制重建（词库版本号仍是 dump 日期，无法体现规则
# 变化）
# 1: 上游 convert.py 原样移植
# 2: 过滤判决书等司法文书标题与「-」开头的词目
BUILD_RULES_VERSION = 2
RULES_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.zhwiki_build_rules')

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


# ===== 构建流程 =====

HTTP_TIMEOUT = 60  # 秒，连接与每次读取的超时


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
            # 纯连字符类标题（如「--」）会得到空拼音；「-D」「-i」等词缀
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


def rules_version_matches():
    try:
        with open(RULES_STATE_FILE, encoding='utf-8') as f:
            return f.read().strip() == str(BUILD_RULES_VERSION)
    except OSError:
        return False


def write_rules_version():
    with open(RULES_STATE_FILE, 'w', encoding='utf-8') as f:
        f.write(f'{BUILD_RULES_VERSION}\n')


def main():
    parser = argparse.ArgumentParser(description='从维基媒体标题 dump 自建 zhwiki 系词库')
    parser.add_argument('--only', choices=DUMP_PROJECTS, action='append',
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

    projects = args.only or DUMP_PROJECTS
    failed = []
    for project in projects:
        try:
            if not build_project(project, os.path.join(target_dir, f'{project}.dict.yaml'),
                                 force=force):
                failed.append(project)
        except Exception as e:
            # 单库失败保留现有词库（上游下载版本兜底），不中止整体
            print(f"[{project}] 构建失败，保留现有词库: {e}")
            failed.append(project)

    if not failed:
        write_rules_version()
        print('全部词库构建完成')
    else:
        print(f"以下词库未更新: {', '.join(failed)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
