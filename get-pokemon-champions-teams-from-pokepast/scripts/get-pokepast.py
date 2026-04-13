#!/usr/bin/env python3
"""
PokePast 队伍中文翻译脚本

输入一个或多个 PokePaste URL，输出官方中文 Showdown 格式文本。

用法:
  python get-pokepast.py <url1> [url2] ...

输出格式:
  === 标题 ===
  队伍码: XXXXXXXXXX  (如果有)
  作者: Author  (如果有)
  赛制: Format  (如果有)
  来源: https://pokepast.es/xxxxx

  宝可梦中文名 @ 道具中文名
  特性: 特性中文名
  等级: 50
  努力值: 31 HP / 1 攻击 / 10 防御 / 23 特防 / 1 速度
  性格: 性格中文名
  - 招式中文名
  ...
"""

import json
import os
import re
import sys
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DICT_DIR = os.path.join(SKILL_DIR, "dict")

# 要加载的字典文件
DICT_FILES = ["pokemon", "pokemon-forms", "moves", "abilities", "items", "types", "natures", "alias"]

# 标签翻译
LABEL_MAP = {
    "Ability:": "特性:",
    "Level:": "等级:",
    "Tera Type:": "太晶属性:",
    "EVs:": "努力值:",
    "IVs:": "个体值:",
}

# 能力值缩写翻译
STAT_MAP = {
    "HP": "HP",
    "Atk": "攻击",
    "Def": "防御",
    "SpA": "特攻",
    "SpD": "特防",
    "Spe": "速度",
}

# 队伍码匹配：10位字母数字
TEAM_CODE_RE = re.compile(r'\b([A-Z0-9]{10})\b')

# 未解析术语追踪
unresolved_terms = set()


def load_dicts():
    """加载所有字典文件，返回精确匹配和小写匹配两个索引"""
    exact = {}
    lower = {}

    for name in DICT_FILES:
        filepath = os.path.join(DICT_DIR, f"{name}.json")
        if not os.path.isfile(filepath):
            if name == "alias":
                continue  # alias.json 是可选的
            print(f"[警告] 字典文件不存在: {filepath}", file=sys.stderr)
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for en, translations in data.items():
            exact[en] = translations
            low = en.lower()
            if low not in lower:
                lower[low] = translations

    total = len(exact)
    print(f"[字典] 加载完成: {total} 条", file=sys.stderr)
    return exact, lower


def translate(term, exact, lower):
    """翻译术语，返回简中；找不到返回原文，并记录未解析术语"""
    translations = exact.get(term) or lower.get(term.lower())
    if not translations:
        _record_unresolved(term)
        return term
    zh = translations.get("zh-hans")
    if zh:
        return zh
    # 有翻译条目但无简中，视为未解析
    _record_unresolved(term)
    return term


def _record_unresolved(term):
    """记录未解析术语，过滤纯数字和单字符"""
    if term.isdigit() or len(term) <= 1:
        return
    unresolved_terms.add(term)


def fetch_page(url):
    """获取 PokePaste 页面 HTML"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def extract_team_code(title):
    """从标题末尾提取10位队伍码，没有则返回 None"""
    matches = TEAM_CODE_RE.findall(title)
    return matches[-1] if matches else None


def extract_author(title):
    """从标题中提取作者名（'s 前的部分），没有则返回空字符串"""
    match = re.match(r"^(.+?)'s\s", title)
    return match.group(1).strip() if match else ""


def extract_team_name(title):
    """从标题提取队伍名称（去掉作者和队伍码）"""
    # 去掉作者 "Author's "
    name = re.sub(r"^.+?'s\s+", "", title)
    # 去掉末尾队伍码
    name = re.sub(r"\s+[A-Z0-9]{10}$", "", name)
    return name.strip()


def parse_team(html, url, exact, lower):
    """解析 PokePaste 页面，返回翻译后的中文 Showdown 文本和元数据"""
    # 提取标题
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    title = title_match.group(1) if title_match else ""
    # HTML 实体解码
    title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')

    # 提取元数据
    team_code = extract_team_code(title)
    author = extract_author(title)
    team_name = extract_team_name(title)

    # 提取赛制（从 <p>Format: xxx</p> 中提取）
    format_match = re.search(r"Format:\s*([^<]+)", html)
    fmt = format_match.group(1).strip() if format_match else ""

    # 提取每只宝可梦
    articles = re.findall(r"<article>(.*?)</article>", html, re.DOTALL)

    lines = []
    # 标题行
    lines.append(f"=== {title} ===")
    if team_code:
        lines.append(f"队伍码: {team_code}")
    if author:
        lines.append(f"作者: {author}")
    if fmt:
        lines.append(f"赛制: {fmt}")
    lines.append(f"来源: {url}")
    lines.append("")

    for article_html in articles:
        # 提取 pre 内容
        pre_match = re.search(r"<pre>(.*?)</pre>", article_html, re.DOTALL)
        if not pre_match:
            continue

        pre_html = pre_match.group(1)
        raw_lines = pre_html.split("\n")

        first_line = True
        for raw_line in raw_lines:
            # 去除 HTML 标签得到纯文本
            text = re.sub(r"<[^>]+>", "", raw_line).strip()
            if not text:
                continue

            if first_line:
                # 第一行: 宝可梦名 @ 道具
                first_line = False
                # 去掉性别标记 (M)/(F)
                name_text = re.sub(r"\s*\([MF]\)", "", text)
                if " @ " in name_text:
                    at_idx = name_text.index(" @ ")
                    name = name_text[:at_idx].strip()
                    item = name_text[at_idx + 3:].strip()
                    name_zh = translate(name, exact, lower)
                    item_zh = translate(item, exact, lower)
                    lines.append(f"{name_zh} @ {item_zh}")
                else:
                    name_zh = translate(name_text, exact, lower)
                    lines.append(name_zh)
            else:
                # 带标签的行
                translated = translate_labeled_line(raw_line, text, exact, lower)
                lines.append(translated)

        lines.append("")

    result = "\n".join(lines)
    return {
        "text": result,
        "title": title,
        "team_code": team_code,
        "author": author,
        "team_name": team_name,
        "format": fmt,
        "url": url,
    }


def translate_labeled_line(raw_html, text, exact, lower):
    """翻译非首行内容"""
    # 招式行: "- Move Name"
    if text.startswith("- "):
        move_name = text[2:]
        return f"- {translate(move_name, exact, lower)}"

    # 性格行: "Timid Nature"
    if text.endswith(" Nature"):
        nature_name = text.replace(" Nature", "").strip()
        nature_zh = translate(nature_name, exact, lower)
        return f"性格: {nature_zh}"

    # 带标签的行
    for en_label, zh_label in LABEL_MAP.items():
        if text.startswith(en_label):
            value_part = text[len(en_label):].strip()

            # 太晶属性
            if en_label == "Tera Type:":
                return f"{zh_label} {translate(value_part, exact, lower)}"

            # 努力值 / 个体值
            if en_label in ("EVs:", "IVs:"):
                return f"{zh_label} {translate_stats(value_part)}"

            # 特性 / 等级
            return f"{zh_label} {translate(value_part, exact, lower)}"

    # 其他行原样返回
    return text


def translate_stats(stat_text):
    """翻译努力值/个体值行，如 '252 SpA / 4 SpD / 252 Spe'"""
    parts = stat_text.split(" / ")
    translated_parts = []
    for part in parts:
        part = part.strip()
        # 匹配 "数字 缩写" 模式
        match = re.match(r"(\d+)\s+(\w+)", part)
        if match:
            num, stat = match.groups()
            stat_zh = STAT_MAP.get(stat, stat)
            translated_parts.append(f"{num} {stat_zh}")
        else:
            translated_parts.append(part)
    return " / ".join(translated_parts)


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        print("用法: python get-pokepast.py <url1> [url2] ...", file=sys.stderr)
        sys.exit(1)

    urls = sys.argv[1:]

    # 加载字典
    exact, lower = load_dicts()

    results = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        print(f"[获取] {url}", file=sys.stderr)
        try:
            html = fetch_page(url)
            result = parse_team(html, url, exact, lower)
            results.append(result)
        except Exception as e:
            print(f"[错误] {url}: {e}", file=sys.stderr)
            results.append({
                "text": f"=== 获取失败 ===\n{url}\n错误: {e}\n",
                "title": "获取失败",
                "team_code": None,
                "author": "",
                "team_name": "",
                "format": "",
                "url": url,
            })

    # 输出翻译文本
    for r in results:
        print(r["text"])

    # 输出元数据为 JSON（到 stderr，方便 Skill 解析）
    meta = []
    for r in results:
        meta.append({
            "title": r["title"],
            "team_code": r["team_code"],
            "author": r["author"],
            "team_name": r["team_name"],
            "format": r["format"],
            "url": r["url"],
        })
    print(f"\n[META]\n{json.dumps(meta, ensure_ascii=False)}", file=sys.stderr)

    # 输出未解析术语
    if unresolved_terms:
        terms = sorted(unresolved_terms)
        print(f"\n[UNRESOLVED] {', '.join(terms)}", file=sys.stderr)


if __name__ == "__main__":
    main()
