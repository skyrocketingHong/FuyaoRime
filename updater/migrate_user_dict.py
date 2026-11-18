#!/usr/bin/env python3
"""Convert a Rime user dictionary snapshot from rime_ice to fuyao_rime."""

import argparse
from pathlib import Path
import re
import tempfile


METADATA = re.compile(rb"(?m)^(?:\A\xef\xbb\xbf)?#@/(db_name|db_type)\t([^\r\n]*)")


def migrate_snapshot(source: Path) -> Path:
    if not source.is_file():
        raise ValueError("请选择 Rime 用户资料同步生成的 .userdb.txt 快照")

    data = source.read_bytes()
    data.decode("utf-8")
    metadata = list(METADATA.finditer(data))
    names = [item for item in metadata if item[1] == b"db_name"]
    types = [item[2] for item in metadata if item[1] == b"db_type"]
    if len(names) != 1 or types != [b"userdb"]:
        raise ValueError("快照须有唯一的 Rime 用户词库名称和类型")
    (name,) = names
    if not re.fullmatch(rb"rime_ice(?:\.userdb(?:\.kct|\.txt)?)?", name[2]):
        raise ValueError("此脚本只迁移 rime_ice 个人词库快照")

    start, end = name.span(2)
    converted = data[:start] + b"fuyao_rime" + data[end:]
    directory = Path(tempfile.mkdtemp(prefix="fuyaorime-migration-", dir=source.parent))
    staged = directory / ".snapshot.tmp"
    try:
        staged.write_bytes(converted)
        return staged.replace(directory / "fuyao_rime.userdb.txt")
    except BaseException:
        staged.unlink(missing_ok=True)
        directory.rmdir()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="将 rime_ice 用户词库快照转换为 fuyao_rime")
    parser.add_argument("snapshot", type=Path, help="由 Rime 同步生成的 rime_ice.userdb.txt")
    args = parser.parse_args()
    try:
        output = migrate_snapshot(args.snapshot)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(output)


if __name__ == "__main__":
    main()
