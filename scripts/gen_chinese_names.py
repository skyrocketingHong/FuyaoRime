#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_chinese_names.py - 生成中文人名词库
从 wainshine/Chinese-Names-Corpus 下载姓氏与名字语料，
用 pypinyin 标注拼音后生成 custom_dicts/chinese_names.dict.yaml。

依赖：pypinyin（pip install pypinyin）
词库为静态生成：上游语料更新后重新运行即可，update_dicts.py 每次同步时调用。
"""

import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from xml.etree import ElementTree as ET

CORPUS_BASE = "https://raw.githubusercontent.com/wainshine/Chinese-Names-Corpus/master/Chinese_Names_Corpus/"
FAMILY_URL = CORPUS_BASE + urllib.parse.quote("Chinese_Family_Name（1k）.xlsx")
NAMES_URL = CORPUS_BASE + urllib.parse.quote("Chinese_Names_Corpus（120W）.txt")

# 姓氏多音字校正：仅收录与 pypinyin 默认读音字母不同的（声调不影响 Rime 词库）
SURNAME_PINYIN_OVERRIDES = {
    "单": "shan", "朴": "piao", "解": "xie", "仇": "qiu", "查": "zha",
    "翟": "zhai", "区": "ou", "乐": "yue", "缪": "miao", "郇": "huan",
    "隗": "kui", "覃": "qin", "折": "she", "种": "chong", "谌": "chen",
    "员": "yun", "蔚": "yu", "祭": "zhai", "冮": "gang", "繁": "po",
    "句": "gou", "啜": "chuai", "乜": "nie",
    "万俟": "mo qi", "尉迟": "yu chi", "长孙": "zhang sun",
    "澹台": "tan tai", "单于": "xian yu",
}

NAME_WEIGHT = 100
CJK_RE = re.compile(r"^[\u4e00-\u9fff]+$")


def download(url, dest):
    print(f"正在下载: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"下载 {url} 失败: {e}")
        return False


def read_family_xlsx(path):
    """返回 [(姓氏, 词频)] 列表"""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", ns):
            shared.append("".join(t.text or "" for t in si.iter(
                "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
    sheet = sorted(n for n in z.namelist()
                   if re.match(r"xl/worksheets/sheet\d+\.xml", n))[0]
    root = ET.fromstring(z.read(sheet))
    result = []
    for row in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
        cells = []
        for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
            t, v = c.get("t"), c.find("m:v", ns)
            val = v.text if v is not None else ""
            if t == "s" and val:
                val = shared[int(val)]
            cells.append(val)
        if len(cells) >= 2 and CJK_RE.match(cells[0]) and cells[1].isdigit():
            result.append((cells[0], int(cells[1])))
    return result


def corpus_version(names_path):
    """从语料头部日期行（如 2025.11.09）提取版本号"""
    with open(names_path, encoding="utf-8-sig") as f:
        for _ in range(5):
            line = f.readline()
            m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", line)
            if m:
                return "".join(m.groups())
    return None


def generate():
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        print("缺少 pypinyin，无法生成人名词库。安装：pip install pypinyin")
        return False

    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(os.path.dirname(script_dir), "custom_dicts")
    os.makedirs(target_dir, exist_ok=True)
    dest = os.path.join(target_dir, "chinese_names.dict.yaml")

    with tempfile.TemporaryDirectory() as tmp:
        family_path = os.path.join(tmp, "family.xlsx")
        names_path = os.path.join(tmp, "names.txt")
        if not download(FAMILY_URL, family_path):
            return False
        if not download(NAMES_URL, names_path):
            return False

        version = corpus_version(names_path) or "0"
        # 语料版本未变时跳过重新生成，保持输出稳定
        if os.path.exists(dest):
            with open(dest, encoding="utf-8") as f:
                m = re.search(r'version:\s*"([^"]+)"', f.read(512))
            if m and m.group(1) == version:
                print(f"人名词库已是最新版本 ({version})，跳过更新。")
                return True
        lines = []
        # 姓氏：使用语料自带词频
        for surname, tf in read_family_xlsx(family_path):
            py = SURNAME_PINYIN_OVERRIDES.get(surname) or " ".join(lazy_pinyin(surname))
            lines.append(f"{surname}\t{py}\t{tf}")
        surname_count = len(lines)

        # 名字：统一低权重，避免干扰常用词排序
        seen, skipped = set(), 0
        with open(names_path, encoding="utf-8-sig") as f:
            for line in f:
                name = line.strip()
                if not CJK_RE.match(name) or not 2 <= len(name) <= 4 or name in seen:
                    continue
                py_list = lazy_pinyin(name)
                if any(not p.isascii() for p in py_list):
                    skipped += 1
                    continue
                seen.add(name)
                lines.append(f"{name}\t{' '.join(py_list)}\t{NAME_WEIGHT}")

        header = (
            "# Rime dictionary\n"
            "# encoding: utf-8\n"
            "# 来源：wainshine/Chinese-Names-Corpus（Chinese_Family_Name、Chinese_Names_Corpus）\n"
            "# 生成：scripts/gen_chinese_names.py，拼音由 pypinyin 标注，姓氏多音字人工校正\n"
            "---\n"
            f"name: chinese_names\n"
            f'version: "{version}"\n'
            "sort: by_weight\n"
            "...\n"
        )
        with open(dest, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(lines))
            f.write("\n")

        print(f"成功生成人名词库: chinese_names "
              f"(姓氏 {surname_count}，名字 {len(lines) - surname_count}，跳过 {skipped}，版本 {version})")
        return True


if __name__ == "__main__":
    sys.exit(0 if generate() else 1)
