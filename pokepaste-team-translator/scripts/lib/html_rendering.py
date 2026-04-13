from __future__ import annotations

import html
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
    moves_html = "".join(
        f'<span class="move">{html.escape(move)}</span>'
        for move in member.get("moves_zh", [])
    )
    pokemon_image = member["images"]["pokemon"]["url"] or ""
    item_image = member["images"]["item"]["url"] or ""
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
        f'<div class="moves">{moves_html}</div>'
        "</div>"
        "</section>"
    )


def render_share_card_html(team_zh: dict, assets_config: dict, template_name: str | None = None) -> str:
    template_name = _resolve_template_name(assets_config, template_name)
    template = _template_path(assets_config, template_name).read_text(encoding="utf-8")
    team_rows = "\n".join(_render_member(member) for member in team_zh["members"])
    replacements = {
        "{{template_name}}": html.escape(template_name),
        "{{team_title}}": html.escape(team_zh["meta"]["title"]),
        "{{team_code}}": html.escape(team_zh["meta"].get("team_code") or ""),
        "{{team_rows}}": team_rows,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template
