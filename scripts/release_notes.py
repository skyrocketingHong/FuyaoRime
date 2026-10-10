#!/usr/bin/env python3
"""Select the preceding release and describe the actual configuration package."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote

REPOSITORY = 'https://github.com/skyrocketingHong/FuyaoRime'
ICE = 'https://github.com/iDvel/rime-ice/blob/main/'
RADICAL = 'https://github.com/mirtlecn/rime-radical-pinyin'
EXTRA_SOURCES = {
    'zhwiki': ('维基百科', 'https://dumps.wikimedia.org/zhwiki/'),
    'zhwikisource': ('维基文库', 'https://dumps.wikimedia.org/zhwikisource/'),
    'zhwiktionary': ('维基词典', 'https://dumps.wikimedia.org/zhwiktionary/'),
    'web-slang': ('网络用语', 'https://zh.wikipedia.org/wiki/' + quote('中国大陆网络用语列表')),
    'moegirl': ('萌娘百科', 'https://github.com/outloudvi/mw2fcitx'),
    'cn_places': ('车站地名', 'https://pinyin.sogou.com/dict/detail/index/170672'),
    'popular_new_words': ('网络流行新词', 'https://pinyin.sogou.com/dict/detail/index/4'),
    'chinese_names': ('中文人名', 'https://github.com/wainshine/Chinese-Names-Corpus'),
    'chengyu_suyu': ('成语俗语', 'https://pinyin.sogou.com/dict/detail/index/15097'),
    'gushi_mingju': ('古诗词名句', 'https://pinyin.sogou.com/dict/detail/index/2'),
    'tangshi_300': ('唐诗三百首', 'https://pinyin.sogou.com/dict/detail/index/1'),
}


def version_key(version):
    match = re.fullmatch(r'([0-9]{8})(?:-v([1-9][0-9]{0,3}))?', version)
    if not match:
        raise ValueError(f'无效版本：{version}')
    return int(match[1]), int(match[2] or 1)


def previous_release(releases, current):
    eligible = []
    for release in releases:
        tag = release.get('tag_name', '')
        if release.get('draft') or release.get('prerelease') or not tag.startswith('v'):
            continue
        try:
            key = version_key(tag[1:])
        except ValueError:
            continue
        if key < version_key(current):
            eligible.append((key, tag))
    return max(eligible)[1] if eligible else ''


def dictionary_version(path):
    with path.open(encoding='utf-8-sig') as handle:
        for _ in range(80):
            line = handle.readline()
            if not line or line.strip() == '...':
                break
            match = re.match(r'^version:\s*(.+?)\s*$', line)
            if match:
                value = match[1].split('#', 1)[0].strip().strip('\"\'')
                return value.replace('|', '\\|').replace('<', '&lt;').replace('>', '&gt;')
    return '未标注'


def source_rows(output):
    rows = []
    for folder in ('cn_dicts', 'en_dicts'):
        for path in sorted((output / folder).glob('*.dict.yaml')):
            relative = path.relative_to(output).as_posix()
            rows.append((relative, ICE + relative, dictionary_version(path)))
    for path in sorted((output / 'en_dicts').glob('cn_en*.txt')):
        relative = path.relative_to(output).as_posix()
        rows.append((relative, ICE + relative, '随雾凇同步'))
    for path in sorted((output / 'custom_dicts').glob('*.dict.yaml')):
        key = path.name.removesuffix('.dict.yaml')
        if key not in EXTRA_SOURCES:
            raise ValueError(f'词库缺少来源链接：{key}')
        label, url = EXTRA_SOURCES[key]
        rows.append((f'{label}（{key}）', url, dictionary_version(path)))
    path = output / 'radical_pinyin.dict.yaml'
    if path.exists():
        rows.append(('部件拆字', RADICAL, dictionary_version(path)))
    path = output / 'build/zdict.reverse.bin'
    if path.exists():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        rows.append(('汉典带调注音', RADICAL + '#反查带声调注音', f'SHA-256 `{digest}`'))
    path = output / 'wanxiang-lts-zh-hans.gram.version'
    if path.exists():
        rows.append(('万象语言模型', 'https://github.com/amzxyz/RIME-LMDG/releases/tag/LTS', path.read_text().strip() or '未标注'))
    return rows


def render(output, version, summary=None, highlight=''):
    version_key(version)
    base = f'{REPOSITORY}/releases/download/v{version}/'
    lines = [highlight.strip() or '同步词库和语言模型。', '', '## 下载', '',
             f'- [全量包]({base}fuyaorime-{version}.zip)：首次安装或跨版本更新。']
    if summary:
        if summary['to'] != version or version_key(summary['from']) >= version_key(version):
            raise ValueError('增量清单与发布版本不匹配')
        previous = summary['from']
        lines.append(f'- [增量包]({base}fuyaorime-{version}-diff-from-{previous}.zip)：仅用于 `{previous}`，其他版本使用全量包。')
    lines += ['', '解压覆盖到当前 Rime 配置目录后重新部署。']
    if '-v' in version:
        lines += ['', f'使用自动更新时，请先更新[桌面脚本]({REPOSITORY}#自动更新)或 [iOS 快捷指令]({REPOSITORY}/blob/main/updater/IOS.md)，旧版不识别修订号。']
    rows = source_rows(output)
    lines += ['', '<details>', '<summary>词库、模型与来源</summary>', '',
              '| 词库或模型 | 包内版本 |', '| :--- | :--- |']
    lines += [f'| [{name}]({url}) | {version} |' for name, url, version in rows]
    lines += ['', '</details>']
    if summary:
        lines += ['', '## 增量变更', '',
                  f"相对 `v{summary['from']}`：新增 {len(summary['added'])} 个、修改 {len(summary['modified'])} 个、删除 {len(summary['deleted'])} 个文件。",
                  '', '<details>', '<summary>查看文件清单</summary>', '']
        for key, label in [('added', '新增'), ('modified', '修改'), ('deleted', '删除')]:
            lines += [f'### {label}', '']
            lines += [f'- `{path}`' for path in summary[key]] or ['无。']
            lines += ['']
        lines += ['</details>']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    previous = sub.add_parser('previous')
    previous.add_argument('version')
    notes = sub.add_parser('render')
    notes.add_argument('version')
    notes.add_argument('--output-dir', type=Path, default=Path('output'))
    notes.add_argument('--summary', type=Path, default=Path('diff-summary.json'))
    notes.add_argument('--notes-file', type=Path, default=Path('release_notes.md'))
    args = parser.parse_args()
    if args.command == 'previous':
        print(previous_release(json.load(sys.stdin), args.version))
    else:
        summary = json.loads(args.summary.read_text()) if args.summary.exists() else None
        args.notes_file.write_text(render(args.output_dir, args.version, summary,
                                         os.environ.get('RELEASE_HIGHLIGHT', '')), encoding='utf-8')


if __name__ == '__main__':
    main()
