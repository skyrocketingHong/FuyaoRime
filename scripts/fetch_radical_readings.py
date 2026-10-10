#!/usr/bin/env python3
"""Fetch the upstream tone-marked reverse dictionary used by full pinyin."""

from io import BytesIO
from pathlib import Path
import argparse
import hashlib
import os
import stat
import tempfile
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://github.com/mirtlecn/rime-radical-pinyin/releases/latest/download/extra.zip"
MEMBER = "build/zdict.reverse.bin"
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_DICTIONARY_BYTES = 8 * 1024 * 1024
MAGIC = b"Rime::Reverse/3."


def read_dictionary(archive_bytes):
    # ASVS 5.2.2/5.2.3: bound sizes, check the binary header, and read one member.
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError("注音资源压缩包超过大小限制")
    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        matches = [info for info in archive.infolist() if info.filename == MEMBER]
        if len(matches) != 1:
            raise ValueError("压缩包必须包含唯一的 build/zdict.reverse.bin")
        info = matches[0]
        if stat.S_ISLNK(info.external_attr >> 16) or not 32 < info.file_size <= MAX_DICTIONARY_BYTES:
            raise ValueError("注音词典类型或大小无效")
        data = archive.read(info)
    if not data.startswith(MAGIC):
        raise ValueError("注音词典缺少 Rime Reverse 文件头")
    return data


def install_dictionary(archive_bytes, destination):
    data = read_dictionary(archive_bytes)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Keep the previous valid resource intact until the replacement is complete.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="读取已下载的上游 extra.zip")
    args = parser.parse_args()
    destination = ROOT / "upstream/radical-readings/zdict.reverse.bin"
    if args.archive:
        with args.archive.open("rb") as handle:
            data = handle.read(MAX_ARCHIVE_BYTES + 1)
    else:
        print("下载拆字带调注音资源...", flush=True)
        # ASVS 12.2.1: use verified HTTPS; no insecure transport fallback.
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "FuyaoRime"})
        with urllib.request.urlopen(request, timeout=60) as response:
            if not response.url.startswith("https://"):
                raise ValueError("注音资源下载不能降级到 HTTP")
            data = response.read(MAX_ARCHIVE_BYTES + 1)
    digest = install_dictionary(data, destination)
    print(f"注音资源已就绪：{destination.name}，SHA-256 {digest}", flush=True)


if __name__ == "__main__":
    main()
