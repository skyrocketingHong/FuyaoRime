#!/usr/bin/env python3
"""Stage the base input schemes and rewrite their package identifiers."""

from pathlib import Path
import re
import shutil
import sys


UPSTREAM_ID = "rime_ice"
SCHEMA_ID = "fuyao_rime"
UPSTREAM_URL = "https://github.com/iDvel/rime-ice"
SOURCE_URL = re.escape(UPSTREAM_URL)


def base_source_dir(project: Path) -> Path:
    upstream = project / "upstream"
    base = upstream / "base"
    legacy = upstream / "rime-ice"
    return legacy if not base.is_dir() and legacy.is_dir() else base


def replace_names(text: str) -> str:
    text = text.replace(UPSTREAM_ID, SCHEMA_ID)
    text = re.sub(r"[雾霧]凇拼音", "Fuyao Rime", text)
    text = re.sub(r"[雾霧]凇", "基础方案", text)
    # Keep attribution in SOURCES.txt and preserve issue numbers in comments.
    text = re.sub(rf"(?m)^[ \t]*(?:#[ \t]*)?{SOURCE_URL}/?[ \t]*(?:\r?\n|$)", "", text)
    text = re.sub(rf"\[([^\]\r\n]+)\]\({SOURCE_URL}/issues/([0-9]+)\)",
                  r"\1（上游讨论 #\2）", text)
    text = text.replace(f"{UPSTREAM_URL}/issues/", "上游讨论 #")
    return re.sub(rf"[ \t]+{SOURCE_URL}/?(?=[ \t\r\n]|$)", "", text)


def rewrite(path: Path) -> None:
    if path.suffix not in {".yaml", ".lua", ".json", ".txt"}:
        return
    original = path.read_bytes().decode("utf-8")
    if path.name.endswith(".dict.yaml"):
        header_end = re.search(r"(?m)^\.\.\.[ \t]*(?:\r?\n|$)", original)
        if header_end is None:
            raise ValueError(f"词典缺少 YAML 头结束标记：{path.name}")
        offset = header_end.end()
        rewritten = replace_names(original[:offset]) + original[offset:]
    elif path.suffix == ".txt":
        rewritten = "".join(replace_names(line) if line.lstrip().startswith("#") else line
                            for line in original.splitlines(keepends=True))
    else:
        rewritten = replace_names(original)
    if rewritten != original:
        path.write_bytes(rewritten.encode("utf-8"))


def stage_base(project: Path, output: Path) -> None:
    source = base_source_dir(project)
    # Check the required inputs before replacing any previously built package.
    entry_points = {
        f"{UPSTREAM_ID}.schema.yaml": rf"^  schema_id: {UPSTREAM_ID}\b",
        f"{UPSTREAM_ID}.dict.yaml": rf"^name: {UPSTREAM_ID}\b",
        "default.yaml": rf"^  - schema: {UPSTREAM_ID}\b",
        "t9.schema.yaml": rf"^__include: {UPSTREAM_ID}\.schema\.yaml:/",
    }
    for name, pattern in entry_points.items():
        text = (source / name).read_text(encoding="utf-8")
        if not re.search(pattern, text, re.MULTILINE):
            raise ValueError(f"基础配置入口不匹配：{name}")

    for name in ("cn_dicts", "en_dicts", "opencc", "lua"):
        shutil.copytree(source / name, output / name)

    files = [*source.glob("*.schema.yaml"), *source.glob("*.txt"), source / "LICENSE"]
    files.extend(source / name for name in (
        f"{UPSTREAM_ID}.dict.yaml", "melt_eng.dict.yaml", "radical_pinyin.dict.yaml",
        "default.yaml", "symbols_v.yaml", "symbols_caps_v.yaml", "user.yaml", "recipe.yaml",
        "others/cn_en.txt", "others/emoji-map.txt",
    ) if (source / name).is_file())
    for path in files:
        relative = path.relative_to(source).as_posix().replace(UPSTREAM_ID, SCHEMA_ID)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    for path in output.rglob("*"):
        if path.is_file():
            rewrite(path)


if __name__ == "__main__":
    try:
        stage_base(*map(Path, sys.argv[1:]))
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
