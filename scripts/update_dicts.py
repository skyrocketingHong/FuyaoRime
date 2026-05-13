#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_dicts.py - 更新额外词库
从 GitHub 和搜狗词库下载最新的词典文件
"""

import os
import sys
import json
import urllib.request
import re
import datetime

# 配置
GITHUB_DICTS = [
    {
        "repo": "felixonmars/fcitx5-pinyin-zhwiki",
        "files": {
            "zhwiki": "zhwiki-{}.dict.yaml",
            "web-slang": "web-slang-{}.dict.yaml",
            "zhwikisource": "zhwikisource-{}.dict.yaml",
            "zhwiktionary": "zhwiktionary-{}.dict.yaml",
        }
    },
    {
        "repo": "outloudvi/mw2fcitx",
        "files": {
            "moegirl": "moegirl.dict.yaml"
        }
    }
]

SOGOU_DICTS = {
    "cn_places": 170672,
    "popular_new_words": 4
}

_github_token = None


def _get_github_token():
    """从环境变量获取 GitHub Token"""
    global _github_token
    if _github_token is not None:
        return _github_token
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    _github_token = token or ''
    return _github_token


def _github_headers():
    """构造 GitHub API 请求头"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    token = _get_github_token()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def request_json(url):
    headers = _github_headers() if 'api.github.com' in url else {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"请求 {url} 失败: {e}")
        return None


def download_file(url, dest):
    print(f"正在下载: {url}")
    headers = _github_headers() if 'github.com' in url else {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(req)
        with open(dest, 'wb') as f:
            f.write(response.read())
        return True
    except Exception as e:
        print(f"下载 {url} 失败: {e}")
        return False


def get_local_version(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('version:'):
                    match = re.search(r'version:\s*"?([^"\s]+)"?', line)
                    if match:
                        return match.group(1).strip()
    except Exception:
        pass
    return None


def get_sogou_dict_update_date(dict_id):
    """从搜狗词库详情页获取更新日期"""
    url = f"https://pinyin.sogou.com/dict/detail/index/{dict_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        html = response.read().decode('utf-8')
        match = re.search(r'更(?:&nbsp;|\s)*新：(\d{4}-\d{2}-\d{2})', html)
        if match:
            return match.group(1).replace('-', '')
    except Exception as e:
        print(f"获取搜狗词库 {dict_id} 更新日期失败: {e}")
    return None


def cleanup_dict_file(filepath):
    """清理词库中无效的条目"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        with open(filepath, 'w', encoding='utf-8') as f:
            for line in lines:
                if line.startswith('——\t') and line.strip() == '——':
                    continue
                if line.startswith('--\t') and line.strip() == '--':
                    continue
                f.write(line)
    except Exception as e:
        print(f"清理 {filepath} 失败: {e}")


def patch_dict_metadata(filepath, target_name, target_version):
    """修改 yaml 头部信息中的 name 和 version 字段"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if not re.search(r'(?m)^name:\s*.*$', content):
            header = f"---\nname: {target_name}\n"
            if target_version:
                header += f'version: "{target_version}"\n'
            header += "sort: by_weight\n...\n"
            content = header + content
        else:
            content = re.sub(r'(?m)^name:\s*.*$', f'name: {target_name}', content)
            if target_version:
                if re.search(r'(?m)^version:\s*.*$', content):
                    content = re.sub(r'(?m)^version:\s*.*$', f'version: "{target_version}"', content)
                else:
                    content = re.sub(f'(name: {target_name})', f'\\1\nversion: "{target_version}"', content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"修改 {filepath} 的元数据失败: {e}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    target_dir = os.path.join(project_dir, "custom_dicts")
    os.makedirs(target_dir, exist_ok=True)

    # 1. 下载 GitHub 词库
    for repo_info in GITHUB_DICTS:
        repo = repo_info['repo']
        print(f"获取 {repo} 的最新发布...")
        release_info = request_json(f"https://api.github.com/repos/{repo}/releases/latest")
        if not release_info:
            continue

        assets = release_info.get('assets', [])
        tag_name = release_info.get('tag_name', '').replace('v', '')

        for dict_name, pattern in repo_info['files'].items():
            dest_file = os.path.join(target_dir, f"{dict_name}.dict.yaml")

            expected_filename = pattern.format(tag_name.replace('-', ''))
            if '{}' not in pattern:
                expected_filename = pattern

            download_url = None
            remote_version = tag_name.replace('-', '')

            for asset in assets:
                if asset['name'] == expected_filename or (dict_name in asset['name'] and asset['name'].endswith('.dict.yaml')):
                    download_url = asset['browser_download_url']
                    date_match = re.search(r'-(\d{8})', asset['name'])
                    if date_match:
                        remote_version = date_match.group(1)
                    break

            if not remote_version:
                remote_version = datetime.date.today().strftime('%Y%m%d')

            local_version = get_local_version(dest_file)
            if local_version == remote_version:
                print(f"词库 {dict_name} 已是最新版本 ({local_version})，跳过更新。")
                continue

            if download_url:
                if download_file(download_url, dest_file):
                    cleanup_dict_file(dest_file)
                    patch_dict_metadata(dest_file, dict_name, remote_version)
                    print(f"成功更新词库: {dict_name} (版本更新至 {remote_version})")
            else:
                print(f"在 release 中未找到匹配的词库文件: {dict_name}")

    # 2. 下载搜狗词库 (需要 imewlconverter，暂时跳过)
    print("\n注意: 搜狗词库需要 imewlconverter 工具，暂不支持在 Actions 中自动更新")
    print("如需更新 cn_places 和 popular_new_words，请在本地运行原始 update_dicts.py")

    print("\n更新完成！")


if __name__ == '__main__':
    main()
