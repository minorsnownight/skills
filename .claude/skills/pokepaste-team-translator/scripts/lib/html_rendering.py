from __future__ import annotations

import base64
import html
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _template_path(assets_config: dict, template_name: str) -> Path:
    template_entry = assets_config["templates"][template_name]
    return _repo_root() / template_entry["html_template"]


def _resolve_template_name(assets_config: dict, template_name: str | None) -> str:
    template_registry = assets_config.get("templates", {})
    default_template = assets_config.get("default_template")
    if template_name and template_name in template_registry:
        return template_name
    if default_template in template_registry:
        return default_template
    if template_registry:
        return sorted(template_registry)[0]
    raise ValueError("no registered HTML templates configured")


# 赛制代码 → 可读名称映射
_FORMAT_MAP = {
    "vgc": "VGC",
    "doubles": "Doubles",
    "singles": "Singles",
    "champions": "Champions",
    "regulation": "Reg",
    "regma": "Reg Ma",
    "rege": "Reg E",
    "regf": "Reg F",
    "regg": "Reg G",
    "regh": "Reg H",
    "regi": "Reg I",
    "regj": "Reg J",
    "regk": "Reg K",
    "regl": "Reg L",
    "series1": "Series 1",
    "series2": "Series 2",
    "series3": "Series 3",
    "series4": "Series 4",
    "series5": "Series 5",
    "series6": "Series 6",
    "series7": "Series 7",
    "series8": "Series 8",
    "series9": "Series 9",
    "series10": "Series 10",
    "series11": "Series 11",
    "series12": "Series 12",
    "series13": "Series 13",
    "ou": "OU",
    "uu": "UU",
    "ru": "RU",
    "nu": "NU",
    "pu": "PU",
    "ubers": "Ubers",
    "ag": "AG",
    "bh": "BH",
    "lc": "LC",
    "monotype": "Monotype",
    "bdsp": "BDSP",
    "la": "LA",
    "natdex": "NatDex",
}


def _format_to_readable(format_code: str) -> str:
    """将 gen9championsvgc2026regma 等转为 Champions VGC 2026 Reg Ma。"""
    if not format_code:
        return ""
    # 去掉 gen 前缀
    s = re.sub(r"^gen\d+", "", format_code)
    # 去掉年份
    year_match = re.search(r"(20\d{2})", s)
    year = year_match.group(1) if year_match else ""
    s = s.replace(year, "")
    # 按已知关键词拆分并翻译
    parts = []
    i = 0
    while s:
        matched = False
        for key in sorted(_FORMAT_MAP, key=len, reverse=True):
            if s[i:].lower().startswith(key.lower()):
                parts.append(_FORMAT_MAP[key])
                s = s[i + len(key):]
                i = 0
                matched = True
                break
        if not matched:
            i += 1
            if i >= len(s):
                remainder = s.strip()
                if remainder:
                    parts.append(remainder.upper())
                break
    if year:
        parts.append(year)
    return " ".join(parts) or format_code


def _fetch_image_as_data_url(url: str, timeout: int = 10, retries: int = 2) -> str:
    """下载图片并编码为 base64 data URL，失败时返回原始 URL。"""
    # URL 编码路径中的非 ASCII 字符
    parsed = urllib.parse.urlsplit(url)
    encoded_path = urllib.parse.quote(parsed.path, safe="/:")
    encoded_url = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, encoded_path, parsed.query, parsed.fragment)
    )
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(encoded_url, headers={"User-Agent": "pokepaste-team-translator"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "image/png")
                return f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}"
        except Exception:
            continue
    return url


def _render_member(member: dict) -> str:
    details = [
        ("道具", member.get("item_zh") or member.get("item")),
        ("特性", member.get("ability_zh") or member.get("ability")),
    ]
    if member.get("nature_zh") or member.get("nature"):
        details.append(("性格", member.get("nature_zh") or member.get("nature")))
    if member.get("tera_type_zh"):
        details.append(("太晶", member["tera_type_zh"]))
    if member.get("evs_zh"):
        details.append(("努力值", member["evs_zh"]))
    detail_html = "".join(
        f'<div class="meta-line"><span class="label">{html.escape(label)}</span>'
        f'<span class="value">{html.escape(value)}</span></div>'
        for label, value in details
        if value
    )
    moves_html = " / ".join(
        html.escape(move) for move in member.get("moves_zh", [])
    )
    pokemon_image = _fetch_image_as_data_url(member["images"]["pokemon"]["url"]) if member["images"]["pokemon"]["url"] else ""
    item_image = _fetch_image_as_data_url(member["images"]["item"]["url"]) if member["images"]["item"]["url"] else ""
    return (
        '<section class="pokemon-row">'
        '<div class="art">'
        f'<img class="pokemon-image" src="{html.escape(pokemon_image)}" alt="{html.escape(member.get("species_zh") or member["species"])}">'
        f'<img class="item-image" src="{html.escape(item_image)}" alt="{html.escape(member.get("item_zh") or member.get("item") or "")}">'
        "</div>"
        '<div class="body">'
        f'<div class="name-line"><span class="name-zh">{html.escape(member.get("species_zh") or member["species"])}</span>'
        f'<span class="name-en">{html.escape(member["species"])}</span></div>'
        f"{detail_html}"
        f'<div class="meta-line"><span class="label">招式</span>'
        f'<span class="value">{moves_html}</span></div>'
        "</div>"
        "</section>"
    )


def render_share_card_html(team_zh: dict, assets_config: dict, template_name: str | None = None) -> str:
    template_name = _resolve_template_name(assets_config, template_name)
    template = _template_path(assets_config, template_name).read_text(encoding="utf-8")
    team_rows = "\n".join(_render_member(member) for member in team_zh["members"])
    replacements = {
        "{{template_name}}": html.escape(template_name),
        "{{team_title}}": html.escape(
            f"{team_zh['meta']['author']}'s {team_zh['meta']['team_name']}"
            if team_zh["meta"].get("author")
            else team_zh["meta"]["team_name"]
        ),
        "{{team_code}}": html.escape(team_zh["meta"].get("team_code") or ""),
        "{{source_url}}": html.escape(team_zh["meta"].get("source_url") or ""),
        "{{format_readable}}": html.escape(_format_to_readable(team_zh["meta"].get("format") or "")),
        "{{generated_date}}": datetime.now().strftime("%Y%m%d"),
        "{{copyright_name}}": html.escape(assets_config.get("copyright_name") or ""),
        "{{team_rows}}": team_rows,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template
