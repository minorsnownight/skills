#!/usr/bin/env python3
"""
从 PokeAPI 本地数据提取宝可梦多语言映射关系，生成本地 JSON 文件

用法: python pokemon-chinese-dict.py

执行流程:
  1. 克隆 PokeAPI/api-data 仓库到本地（已存在则跳过）
  2. 解析本地 JSON 文件，提取英/日/简中/繁中名称
  3. 输出映射文件到 site/dict/ 目录

输出文件保存在 site/dict/ 目录下:
  pokemon.json       - 宝可梦名称
  pokemon-forms.json - 宝可梦形态名称
  moves.json         - 招式名称
  abilities.json     - 特性名称
  items.json         - 道具名称
  types.json         - 属性名称
  natures.json       - 性格名称

每条记录格式:
  {
    "Charizard": {
      "ja": "リザードン",
      "zh-hans": "喷火龙",
      "zh-hant": "噴火龍"
    }
  }

依赖: git
"""

import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.join(SCRIPT_DIR, "api-data")
DICT_DIR = os.path.join(SCRIPT_DIR, "site", "dict")
REPO_URL = "https://github.com/PokeAPI/api-data.git"

# 要提取的语言代码
LANGUAGES = ["en", "ja", "zh-hans", "zh-hant"]

# 要提取的分类: {输出文件名: 仓库中目录名}
CATEGORIES = {
    "pokemon": "pokemon-species",
    "pokemon-forms": "pokemon-form",
    "moves": "move",
    "abilities": "ability",
    "items": "item",
    "types": "type",
    "natures": "nature",
}


def clone_repo():
    """克隆 api-data 仓库，已存在则跳过"""
    data_dir = os.path.join(REPO_DIR, "data", "api", "v2")
    if os.path.isdir(data_dir):
        print(f"[跳过] 数据已存在: {REPO_DIR}")
        return

    if os.path.isdir(REPO_DIR):
        print(f"[错误] 目录已存在但数据不完整: {REPO_DIR}")
        print("  请删除该目录后重试，或手动克隆仓库到该路径")
        sys.exit(1)

    print(f"[克隆] {REPO_URL} -> {REPO_DIR}")
    print("  这可能需要几分钟，仓库较大...")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, REPO_DIR],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[错误] 克隆失败:\n{result.stderr}")
        sys.exit(1)
    print("  克隆完成")


def extract_name_entry(json_path):
    """从单个 index.json 提取多语言名称

    合并 names 和 form_names 两个字段（pokemon-form 特有），
    names 优先，form_names 补充缺失的语言。

    返回 (英文名, 翻译字典, Showdown别名列表) 或 None
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [跳过] {json_path}: {e}")
        return None

    # 合并 names 和 form_names，names 优先
    lang_names = {}
    for field in ["form_names", "names"]:  # 先 form_names，后 names 覆盖
        for n in data.get(field, []):
            lang = n["language"]["name"]
            if lang in LANGUAGES:
                lang_names[lang] = n["name"]

    # 必须有英文名才有效
    en_name = lang_names.get("en")
    if not en_name:
        return None

    # 构建非英文字典
    translations = {}
    for lang in LANGUAGES[1:]:  # ja, zh-hans, zh-hant
        if lang in lang_names:
            translations[lang] = lang_names[lang]

    if not translations:
        return None

    # 从 name 字段(slug)生成 Showdown 格式别名
    # 如 rotom-wash -> Rotom-Wash, charizard-mega-y -> Charizard-Mega-Y
    aliases = []
    slug = data.get("name", "")
    if slug:
        showdown_name = slug.title()
        if showdown_name != en_name:
            aliases.append(showdown_name)

    return (en_name, translations, aliases)


def process_category(name, resource_dir):
    """处理一个分类：遍历本地 JSON 文件提取多语言映射"""
    data_path = os.path.join(REPO_DIR, "data", "api", "v2", resource_dir)
    if not os.path.isdir(data_path):
        print(f"  [跳过] 目录不存在: {data_path}")
        return {}

    # 收集所有 index.json 路径
    entries = []
    for entry in sorted(os.listdir(data_path)):
        index_path = os.path.join(data_path, entry, "index.json")
        if os.path.isfile(index_path):
            entries.append(index_path)

    total = len(entries)
    print(f"\n>>> {name} ({resource_dir}): {total} 个文件")

    mapping = {}
    alias_count = 0
    for i, path in enumerate(entries, 1):
        result = extract_name_entry(path)
        if result:
            en_name, translations, aliases = result
            mapping[en_name] = translations
            for alias in aliases:
                if alias not in mapping:
                    mapping[alias] = translations
                    alias_count += 1
        if i % 500 == 0 or i == total:
            print(f"    {i}/{total}")

    print(f"    完成，有效映射 {len(mapping)} 条（含 {alias_count} 条 Showdown 别名）")
    return mapping


def main():
    # Windows 下确保控制台输出 UTF-8
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    start_time = time.time()

    print("=== 宝可梦多语言映射提取工具 ===")
    print(f"语言: {', '.join(LANGUAGES)}")
    print(f"输出: {DICT_DIR}")

    # 步骤 1: 克隆仓库
    clone_repo()

    # 步骤 2: 解析本地数据
    os.makedirs(DICT_DIR, exist_ok=True)

    for name, resource_dir in CATEGORIES.items():
        mapping = process_category(name, resource_dir)
        filepath = os.path.join(DICT_DIR, f"{name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"    -> {filepath}")

    elapsed = time.time() - start_time

    # 输出汇总
    print(f"\n=== 完成 ===")
    print(f"总耗时: {elapsed:.1f} 秒")
    print(f"文件列表:")
    for name in CATEGORIES:
        filepath = os.path.join(DICT_DIR, f"{name}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                count = len(json.load(f))
            print(f"  {name}.json: {count} 条")


if __name__ == "__main__":
    main()
