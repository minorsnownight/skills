#!/usr/bin/env python3
"""
从 pokemon-dataset-zh 提取宝可梦多语言映射关系，生成本地 JSON 文件

用法: python get-dict.py

执行流程:
  1. 克隆 pokemon-dataset-zh 仓库到 temp/pokemon-dataset-zh（已存在则跳过）
  2. 第 1 层：从数据集直接提取英/日/简中映射
  3. 第 2 层：根据中文形态名模式规则生成缺失的形态映射
  4. 第 3 层：从 alias.json 合并手动映射
  5. 输出映射文件到 dict/ 目录

输出文件保存在 dict/ 目录下:
  pokemon.json       - 宝可梦名称
  pokemon-forms.json - 宝可梦形态名称
  moves.json         - 招式名称
  abilities.json     - 特性名称
  items.json         - 道具名称
  types.json         - 属性名称（保留不动）
  natures.json       - 性格名称（保留不动）
  alias.json         - 手动映射（保留不动，由用户维护）

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
import re
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
REPO_DIR = os.path.join(SKILL_DIR, "temp", "pokemon-dataset-zh")
DICT_DIR = os.path.join(SKILL_DIR, "dict")
REPO_URL = "https://github.com/42arch/pokemon-dataset-zh.git"

# 跳过重新生成的文件（由用户手动维护）
SKIP_FILES = {"types.json", "natures.json", "alias.json"}


def clone_repo():
    """克隆 pokemon-dataset-zh 仓库，已存在则跳过"""
    data_dir = os.path.join(REPO_DIR, "data")
    if os.path.isdir(data_dir):
        print(f"[跳过] 数据已存在: {REPO_DIR}")
        return

    if os.path.isdir(REPO_DIR):
        print(f"[错误] 目录已存在但数据不完整: {REPO_DIR}")
        print("  请删除该目录后重试")
        sys.exit(1)

    print(f"[克隆] {REPO_URL} -> {REPO_DIR}")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, REPO_DIR],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[错误] 克隆失败:\n{result.stderr}")
        sys.exit(1)
    print("  克隆完成")


def add_alias(mapping, key, translations):
    """添加条目，已有主条目时不覆盖；同时生成空格→连字符别名"""
    if key not in mapping:
        mapping[key] = translations
    # 生成空格→连字符别名（如 "Mr. Mime" → "Mr.-Mime"）
    if " " in key:
        alias_key = key.replace(" ", "-")
        if alias_key not in mapping:
            mapping[alias_key] = translations


# ============================================================
# 第 1 层：从 pokemon-dataset-zh 直接提取
# ============================================================

def build_pokemon():
    """从 simple_pokedex.json 构建基础种映射"""
    filepath = os.path.join(REPO_DIR, "data", "simple_pokedex.json")
    with open(filepath, "r", encoding="utf-8") as f:
        pokedex = json.load(f)

    mapping = {}
    for p in pokedex:
        name_en = p.get("name_en", "")
        name_jp = p.get("name_jp", "")
        name_zh = p.get("name_zh", "")
        if not name_en:
            continue
        translations = {}
        if name_jp:
            translations["ja"] = name_jp
        if name_zh:
            translations["zh-hans"] = name_zh
        if translations:
            add_alias(mapping, name_en, translations)

    print(f"  基础种: {len(pokedex)} 条，映射 {len(mapping)} 条（含别名）")
    return mapping


def build_moves():
    """从 move_list.json 构建招式映射"""
    filepath = os.path.join(REPO_DIR, "data", "move_list.json")
    with open(filepath, "r", encoding="utf-8") as f:
        moves = json.load(f)

    mapping = {}
    for m in moves:
        name_en = m.get("name_en", "")
        name_jp = m.get("name_jp", "")
        name_zh = m.get("name_zh", "")
        if not name_en:
            continue
        translations = {}
        if name_jp:
            translations["ja"] = name_jp
        if name_zh:
            translations["zh-hans"] = name_zh
        if translations:
            add_alias(mapping, name_en, translations)

    print(f"  招式: {len(moves)} 条，映射 {len(mapping)} 条（含别名）")
    return mapping


def build_abilities():
    """从 ability_list.json 构建特性映射"""
    filepath = os.path.join(REPO_DIR, "data", "ability_list.json")
    with open(filepath, "r", encoding="utf-8") as f:
        abilities = json.load(f)

    mapping = {}
    for a in abilities:
        name_en = a.get("name_en", "")
        name_ja = a.get("name_ja", "")
        name_zh = a.get("name_zh", "")
        if not name_en:
            continue
        translations = {}
        if name_ja:
            translations["ja"] = name_ja
        if name_zh:
            translations["zh-hans"] = name_zh
        if translations:
            add_alias(mapping, name_en, translations)

    print(f"  特性: {len(abilities)} 条，映射 {len(mapping)} 条（含别名）")
    return mapping


def build_items():
    """从 item_list.json 展平构建道具映射"""
    filepath = os.path.join(REPO_DIR, "data", "item_list.json")
    with open(filepath, "r", encoding="utf-8") as f:
        categories = json.load(f)

    items = []

    def flatten(nodes):
        for node in nodes:
            if node.get("type") == "item":
                items.append(node)
            elif "children" in node:
                flatten(node["children"])

    flatten(categories)

    mapping = {}
    for item in items:
        name_en = item.get("name_en", "")
        name_ja = item.get("name_ja", "")
        name_zh = item.get("name_zh", "")
        if not name_en:
            continue
        translations = {}
        if name_ja:
            translations["ja"] = name_ja
        if name_zh:
            translations["zh-hans"] = name_zh
        if translations:
            add_alias(mapping, name_en, translations)

    print(f"  道具: {len(items)} 条，映射 {len(mapping)} 条（含别名）")
    return mapping


def build_pokemon_forms():
    """从详情 JSON 提取形态映射（第 1 层 + 第 2 层）"""
    simple_path = os.path.join(REPO_DIR, "data", "simple_pokedex.json")
    with open(simple_path, "r", encoding="utf-8") as f:
        pokedex = json.load(f)

    # 建立中文→英文索引
    zh_to_en = {}
    for p in pokedex:
        zh_to_en[p["name_zh"]] = p["name_en"]

    mapping = {}

    # --- 第 1 层：从 evolution_chains / mega_evolution / gigantamax_evolution 图片提取 ---

    pokemon_dir = os.path.join(REPO_DIR, "data", "pokemon")
    total = len(pokedex)

    for i, p in enumerate(pokedex, 1):
        idx = p["index"]
        name_zh = p["name_zh"]
        name_en = p["name_en"]
        filepath = os.path.join(pokemon_dir, f"{idx}-{name_zh}.json")
        if not os.path.isfile(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            detail = json.load(f)

        # 从 evolution_chains 提取
        for chain in detail.get("evolution_chains", []):
            for entry in chain:
                form_name = entry.get("form_name")
                image = entry.get("image", "")
                if not form_name or not image:
                    continue
                en_form = _extract_showdown_name(image, name_en)
                if en_form and en_form != name_en:
                    # 从 Showdown 英文名反查正确的物种中文名
                    actual_zh = _resolve_species_zh(en_form, zh_to_en)
                    zh_name = _format_zh_form_name(actual_zh, form_name)
                    add_alias(mapping, en_form, {"zh-hans": zh_name})

        # 从 mega_evolution 提取
        for mega in detail.get("mega_evolution", []):
            form_name = mega.get("form_name", "")
            image = mega.get("image", "")
            if not form_name or not image:
                continue
            en_form = _extract_showdown_name(image, name_en)
            if en_form and en_form != name_en:
                actual_zh = _resolve_species_zh(en_form, zh_to_en)
                zh_name = _format_zh_form_name(actual_zh, form_name)
                add_alias(mapping, en_form, {"zh-hans": zh_name})

        # 从 gigantamax_evolution 提取
        for gmax in detail.get("gigantamax_evolution", []):
            form_name = gmax.get("form_name", "")
            image = gmax.get("image", "")
            if not form_name or not image:
                continue
            en_form = _extract_showdown_name(image, name_en)
            if en_form and en_form != name_en:
                actual_zh = _resolve_species_zh(en_form, zh_to_en)
                zh_name = _format_zh_form_name(actual_zh, form_name)
                add_alias(mapping, en_form, {"zh-hans": zh_name})

        if i % 200 == 0 or i == total:
            print(f"    {i}/{total}")

    layer1_count = len(mapping)
    print(f"  第 1 层（直接提取）: {layer1_count} 条")

    # --- 第 2 层：规则生成 ---

    rule_count = 0
    for p in pokedex:
        idx = p["index"]
        name_zh = p["name_zh"]
        name_en = p["name_en"]
        filepath = os.path.join(pokemon_dir, f"{idx}-{name_zh}.json")
        if not os.path.isfile(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            detail = json.load(f)

        for form in detail.get("forms", []):
            form_zh = form.get("name", "")
            if not form_zh:
                continue

            # 尝试规则匹配
            en_suffix = _match_form_rule(form_zh)
            if en_suffix is None:
                continue

            en_form = f"{name_en}{en_suffix}"
            if en_form in mapping:
                continue

            zh_name = _format_zh_form_name(name_zh, form_zh)
            add_alias(mapping, en_form, {"zh-hans": zh_name})
            rule_count += 1

    print(f"  第 2 层（规则生成）: +{rule_count} 条，总计 {len(mapping)} 条")
    return mapping


def _extract_showdown_name(image_filename, fallback_en):
    """从图片文件名提取 Showdown 风格英文名

    示例:
      "925Maushold-Four_Dream.png" → "Maushold-Four"
      "006Charizard_Mega_X_Dream.png" → "Charizard-Mega-X"
      "006Charizard-Gigantamax_Dream.png" → "Charizard-Gmax"
      "0359Absol-Mega.png" → "Absol-Mega"
    """
    m = re.match(r"\d+(.+?)(?:_Dream)?\.png$", image_filename)
    if not m:
        return fallback_en
    name = m.group(1)
    # 下划线替换为连字符（Mega 形态）
    name = name.replace("_", "-")
    # Gigantamax → Gmax
    name = name.replace("-Gigantamax", "-Gmax")
    return name


def _format_zh_form_name(species_zh, form_zh):
    """格式化中文形态名

    如果形态名已包含种名，直接使用；否则拼接 "种名-形态名"。
    - "超级喷火龙Ｘ" 包含 "喷火龙" → "超级喷火龙Ｘ"
    - "四只家庭" 不包含 "一家鼠" → "一家鼠-四只家庭"
    - "盾牌形态" 不包含 "坚盾剑怪" → "坚盾剑怪-盾牌形态"
    """
    if species_zh in form_zh:
        return form_zh
    return f"{species_zh}-{form_zh}"


def _resolve_species_zh(showdown_name, zh_to_en):
    """从 Showdown 英文名反查正确的物种中文名

    Showdown 名如 "Maushold-Four" → 基础种是 "Maushold" → 查中文名 "一家鼠"
    如果找不到精确匹配，尝试取连字符前的部分。
    """
    # 尝试完整名
    for zh, en in zh_to_en.items():
        if en == showdown_name:
            return zh

    # 取连字符前的部分作为基础种名
    base_en = showdown_name.split("-")[0]
    for zh, en in zh_to_en.items():
        if en == base_en:
            return zh

    return ""  # 找不到则返回空，_format_zh_form_name 会只用形态名


# 形态中文→Showdown 后缀规则
_FORM_RULES = [
    # (匹配函数, Showdown后缀)
    (lambda n: n.startswith("超级") and n.endswith("Ｘ"), "-Mega-X"),
    (lambda n: n.startswith("超级") and n.endswith("Ｙ"), "-Mega-Y"),
    (lambda n: n.startswith("超级"), "-Mega"),
    (lambda n: n.startswith("超极巨化"), "-Gmax"),
    (lambda n: n.endswith("阿罗拉的样子"), "-Alola"),
    (lambda n: n.endswith("伽勒尔的样子"), "-Galar"),
    (lambda n: n.endswith("洗翠的样子"), "-Hisui"),
    (lambda n: n.endswith("帕底亚的样子"), "-Paldea"),
    (lambda n: n.endswith("雄性的样子"), "-Male"),
    (lambda n: n.endswith("雌性的样子"), "-Female"),
    (lambda n: n.endswith("起源形态"), "-Origin"),
    (lambda n: n.endswith("灵兽形态"), "-Therian"),
    (lambda n: n.endswith("化身形态"), "-Incarnate"),
]


def _match_form_rule(form_zh):
    """根据中文形态名匹配规则，返回 Showdown 后缀或 None"""
    # 基础种名（与种名相同）跳过
    for matcher, suffix in _FORM_RULES:
        if matcher(form_zh):
            return suffix
    return None


# ============================================================
# 第 3 层：合并 alias.json
# ============================================================

def merge_alias(mapping):
    """从 alias.json 合并手动映射到 pokemon-forms.json"""
    alias_path = os.path.join(DICT_DIR, "alias.json")
    if not os.path.isfile(alias_path):
        print("  第 3 层: alias.json 不存在，跳过")
        return 0

    with open(alias_path, "r", encoding="utf-8") as f:
        alias = json.load(f)

    added = 0
    for key, translations in alias.items():
        if key not in mapping:
            mapping[key] = translations
            added += 1
        # 已有条目不覆盖，但补充缺失的语言字段
        else:
            for lang, val in translations.items():
                if lang not in mapping[key]:
                    mapping[key][lang] = val

    print(f"  第 3 层（alias.json）: 新增 {added} 条，补充语言字段若干")
    return added


# ============================================================
# 主流程
# ============================================================

def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    start_time = time.time()

    print("=== 宝可梦多语言映射提取工具（pokemon-dataset-zh）===")
    print(f"输出: {DICT_DIR}")

    # 步骤 0: 克隆仓库
    clone_repo()

    # 步骤 1-2: 构建映射
    os.makedirs(DICT_DIR, exist_ok=True)

    print("\n--- 基础种 ---")
    pokemon = build_pokemon()

    print("\n--- 形态（三层策略）---")
    pokemon_forms = build_pokemon_forms()
    merge_alias(pokemon_forms)

    print("\n--- 招式 ---")
    moves = build_moves()

    print("\n--- 特性 ---")
    abilities = build_abilities()

    print("\n--- 道具 ---")
    items = build_items()

    # 写入文件
    print("\n--- 写入文件 ---")
    file_data = {
        "pokemon": pokemon,
        "pokemon-forms": pokemon_forms,
        "moves": moves,
        "abilities": abilities,
        "items": items,
    }

    for name, data in file_data.items():
        filepath = os.path.join(DICT_DIR, f"{name}.json")
        if f"{name}.json" in SKIP_FILES:
            print(f"  [跳过] {name}.json（保留不动）")
            continue
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  {name}.json: {len(data)} 条")

    # 确认保留文件存在
    for skip_name in SKIP_FILES:
        skip_path = os.path.join(DICT_DIR, skip_name)
        if os.path.isfile(skip_path):
            with open(skip_path, "r", encoding="utf-8") as f:
                count = len(json.load(f))
            print(f"  {skip_name}: {count} 条（保留不动）")
        else:
            print(f"  {skip_name}: 文件不存在")

    elapsed = time.time() - start_time
    print(f"\n=== 完成 ===")
    print(f"总耗时: {elapsed:.1f} 秒")


if __name__ == "__main__":
    main()
