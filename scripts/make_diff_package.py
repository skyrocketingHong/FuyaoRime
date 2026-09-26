#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_diff_package.py - 生成相对上一版发布包的增量更新包

对比当前 output 目录与上一版全量 zip，把新增与修改过的文件（保持目录
结构）打进增量包，并附 INCREMENTAL-README.txt 说明用法与已删除文件清
单。已安装上一版的用户下载增量包解压覆盖到 Rime 配置目录后重新部署
即可；上一版存在而当前版本不存在的文件列入删除清单，需手动删除。

即使两版内容完全一致也会生成仅含说明文件的增量包（说明无需更新），
便于发布流程统一处理。

用法:
    make_diff_package.py <当前配置目录> <上一版全量zip> <输出zip> <上一版日期> <当前日期>
"""

import hashlib
import os
import sys
import zipfile

IGNORED_NAMES = {'.DS_Store', 'Thumbs.db'}


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def collect_current(curr_dir):
    """当前目录下全部文件，返回 {相对路径: 绝对路径}"""
    files = {}
    for root, _, names in os.walk(curr_dir):
        for name in names:
            if name in IGNORED_NAMES:
                continue
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, curr_dir)
            files[rel_path] = abs_path
    return files


def read_prev_zip(prev_zip):
    """上一版 zip 内全部条目，返回 {相对路径: sha256}"""
    entries = {}
    with zipfile.ZipFile(prev_zip, 'r') as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            rel_path = info.filename
            if os.path.basename(rel_path) in IGNORED_NAMES:
                continue
            h = hashlib.sha256()
            with zf.open(info) as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
            entries[rel_path] = h.hexdigest()
    return entries


def main():
    if len(sys.argv) != 6:
        print(__doc__)
        return 1
    curr_dir, prev_zip, out_zip, prev_date, curr_date = sys.argv[1:6]

    current = collect_current(curr_dir)
    previous = read_prev_zip(prev_zip)

    changed = []   # 新增或修改
    for rel_path in sorted(current):
        if rel_path not in previous or previous[rel_path] != file_sha256(current[rel_path]):
            changed.append(rel_path)
    deleted = sorted(set(previous) - set(current))

    readme = [
        'FuyaoRime 增量更新包',
        '',
        f'适用版本: {prev_date} -> {curr_date}',
        '',
        '用法: 解压全部内容覆盖到 Rime 配置目录，然后重新部署 Rime。',
        '  - macOS: ~/Library/Rime/',
        '  - Windows: %APPDATA%\\Rime\\',
        '  - Linux: ~/.config/rime/',
        '',
    ]
    if changed:
        readme.append(f'本包包含 {len(changed)} 个新增或修改的文件:')
        readme.extend(f'  - {p}' for p in changed)
    else:
        readme.append('本版与上一版无文件差异，无需下载安装。')
    if deleted:
        readme.append('')
        readme.append(f'以下 {len(deleted)} 个文件已从配置包移除，可手动删除（不删除一般不影响使用）:')
        readme.extend(f'  - {p}' for p in deleted)
    readme.append('')

    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('INCREMENTAL-README.txt', '\n'.join(readme))
        for rel_path in changed:
            zf.write(current[rel_path], rel_path)

    size_mb = os.path.getsize(out_zip) / 1024 / 1024
    print(f'增量包已生成: {out_zip}（{len(changed)} 个文件变更，'
          f'{len(deleted)} 个删除，{size_mb:.1f} MB）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
