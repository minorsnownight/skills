from __future__ import annotations

import html
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from scripts.lib.html_rendering import render_share_card_html
from scripts.lib.team_review import review_translation
from scripts.lib.translation_assets import DictionaryBundle, STAT_LABELS_ZH
from scripts.lib.translation_validation import validate_translated_team


STAT_KEYS = ("HP", "Atk", "Def", "SpA", "SpD", "Spe")
STAT_TOKEN_MAP = {
    "HP": "HP",
    "Atk": "Atk",
    "Def": "Def",
    "SpA": "SpA",
    "SpD": "SpD",
    "Spe": "Spe",
}


def fetch_pokepaste_html(url: str, retries: int = 3, timeout: int = 20) -> str:
    last_error: Optional[Exception] = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.read().decode("utf-8", "replace")
        except Exception as exc:  # pragma: no cover - exercised in live verification
            last_error = exc
    raise RuntimeError(f"failed to fetch {url}: {last_error}") from last_error


def _clean_html_fragment(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def _parse_title_metadata(title_text: str) -> dict:
    title_text = html.unescape(title_text)
    match = re.match(
        r"^(?P<author>.+?)'s (?P<team_name>.+) (?P<team_code>[A-Z0-9]{10})$",
        title_text,
    )
    if not match:
        return {
            "title": title_text,
            "author": None,
            "team_name": title_text,
            "team_code": None,
        }
    return {
        "title": title_text,
        "author": match.group("author"),
        "team_name": match.group("team_name"),
        "team_code": match.group("team_code"),
    }


def _default_stats(default: int) -> dict:
    return {key: default for key in STAT_KEYS}


def _parse_stats_line(line: str, default: int) -> dict:
    stats = _default_stats(default)
    payload = line.split(":", 1)[1].strip()
    for part in payload.split("/"):
        part = part.strip()
        if not part:
            continue
        value_token, stat_token = part.split(" ", 1)
        stats[STAT_TOKEN_MAP[stat_token.strip()]] = int(value_token)
    return stats


def _split_header_term(header: str) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
    item = None
    if " @ " in header:
        left, item = header.split(" @ ", 1)
    else:
        left = header
    left = left.strip()
    gender = None
    gender_match = re.match(r"^(?P<term>.+?) \((?P<gender>M|F)\)$", left)
    if gender_match:
        left = gender_match.group("term")
        gender = gender_match.group("gender")
    nickname = None
    species = left
    nickname_match = re.match(r"^(?P<nickname>.+) \((?P<species>.+)\)$", left)
    if nickname_match:
        nickname = nickname_match.group("nickname")
        species = nickname_match.group("species")
    return species.strip(), item.strip() if item else None, gender, nickname


def _parse_member(article_html: str, slot: int) -> dict:
    image_match = re.search(
        r'<img class="img-pokemon" src="(?P<pokemon>[^"]+)">.*?<img class="img-item" src="(?P<item>[^"]+)">',
        article_html,
        re.S,
    )
    pre_match = re.search(r"<pre>(.*?)</pre>", article_html, re.S)
    if not pre_match:
        raise ValueError(f"article {slot} missing pre block")
    plain_lines = [
        line.rstrip()
        for line in _clean_html_fragment(pre_match.group(1)).strip().splitlines()
        if line.strip()
    ]
    species, item, gender, nickname = _split_header_term(plain_lines[0])
    member = {
        "slot": slot,
        "species": species,
        "nickname": nickname,
        "gender": gender,
        "item": item,
        "ability": None,
        "level": None,
        "tera_type": None,
        "nature": None,
        "evs": _default_stats(0),
        "ivs": _default_stats(31),
        "moves": [],
        "pokepaste_images": {
            "pokemon_sprite": image_match.group("pokemon") if image_match else None,
            "item_icon": image_match.group("item") if image_match else None,
        },
    }
    for line in plain_lines[1:]:
        if line.startswith("Ability: "):
            member["ability"] = line.split(": ", 1)[1]
        elif line.startswith("Level: "):
            member["level"] = int(line.split(": ", 1)[1])
        elif line.startswith("Tera Type: "):
            member["tera_type"] = line.split(": ", 1)[1]
        elif line.startswith("EVs: "):
            member["evs"] = _parse_stats_line(line, 0)
        elif line.startswith("IVs: "):
            member["ivs"] = _parse_stats_line(line, 31)
        elif line.endswith(" Nature"):
            member["nature"] = line[: -len(" Nature")]
        elif line.startswith("- "):
            member["moves"].append(line[2:])
    return member


def parse_pokepaste_html(html_text: str, source_url: str) -> dict:
    title_match = re.search(r"<title>(.*?)</title>", html_text, re.S)
    if not title_match:
        raise ValueError("missing page title")
    format_match = re.search(r"<p>Format: ([^<]+)</p>", html_text)
    articles = re.findall(r"<article>(.*?)</article>", html_text, re.S)
    metadata = _parse_title_metadata(title_match.group(1))
    return {
        "meta": {
            "source_url": source_url,
            "title": metadata["title"],
            "author": metadata["author"],
            "team_name": metadata["team_name"],
            "team_code": metadata["team_code"],
            "format": format_match.group(1) if format_match else None,
        },
        "members": [_parse_member(article, index + 1) for index, article in enumerate(articles)],
    }


def _format_stats_zh(stats: dict) -> str:
    parts = []
    for key in STAT_KEYS:
        value = stats.get(key, 0)
        if value:
            parts.append(f"{value} {STAT_LABELS_ZH[key]}")
    return " / ".join(parts)


def _track_unresolved(unresolved_terms: list, field: str, term: Optional[str], member_slot: int) -> None:
    if term:
        unresolved_terms.append({"field": field, "term": term, "member_slot": member_slot})


def translate_team(raw_team: dict, bundle: DictionaryBundle, assets_config: dict) -> dict:
    unresolved_terms = []
    members = []
    for member in raw_team["members"]:
        species_zh = bundle.translate_species(member["species"])
        item_zh = bundle.translate_item(member["item"]) if member["item"] else None
        ability_zh = bundle.translate_ability(member["ability"]) if member["ability"] else None
        nature_zh = bundle.translate_nature(member["nature"]) if member["nature"] else None
        tera_type_zh = bundle.translate_type(member["tera_type"]) if member["tera_type"] else None
        moves_zh = []
        for move in member["moves"]:
            move_zh = bundle.translate_move(move)
            if move_zh is None:
                _track_unresolved(unresolved_terms, "move", move, member["slot"])
                move_zh = move
            moves_zh.append(move_zh)
        if species_zh is None:
            _track_unresolved(unresolved_terms, "species", member["species"], member["slot"])
        if item_zh is None and member["item"]:
            _track_unresolved(unresolved_terms, "item", member["item"], member["slot"])
        if ability_zh is None and member["ability"]:
            _track_unresolved(unresolved_terms, "ability", member["ability"], member["slot"])
        if nature_zh is None and member["nature"]:
            _track_unresolved(unresolved_terms, "nature", member["nature"], member["slot"])
        if tera_type_zh is None and member["tera_type"]:
            _track_unresolved(unresolved_terms, "tera_type", member["tera_type"], member["slot"])
        members.append(
            {
                **member,
                "species_zh": species_zh,
                "item_zh": item_zh,
                "ability_zh": ability_zh,
                "nature_zh": nature_zh,
                "tera_type_zh": tera_type_zh,
                "moves_zh": moves_zh,
                "evs_zh": _format_stats_zh(member["evs"]),
                "ivs_zh": _format_stats_zh(member["ivs"]),
                "images": {
                    "pokemon": bundle.resolve_pokemon_image(species_zh),
                    "item": bundle.resolve_item_image(item_zh),
                },
            }
        )
    return {
        "meta": {
            **raw_team["meta"],
            "format_zh": raw_team["meta"].get("format"),
            "image_source_base_url": assets_config["image_source_base_url"],
        },
        "members": members,
        "unresolved_terms": unresolved_terms,
    }


def build_output_slug(raw_team: dict) -> str:
    safe_team = re.sub(r"[^A-Za-z0-9-]+", "-", raw_team["meta"]["team_name"]).strip("-")
    safe_author = re.sub(r"[^A-Za-z0-9_-]+", "-", raw_team["meta"]["author"] or "unknown").strip("-")
    return f"{datetime.now().strftime('%Y%m%d')}-{safe_team}-{safe_author}-{raw_team['meta']['team_code']}"


def build_translated_team_artifacts(
    raw_team: dict,
    bundle: DictionaryBundle,
    assets_config: dict,
    output_dir: Path,
    template_name: Optional[str] = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    team_zh = translate_team(raw_team, bundle, assets_config)
    validation_report = validate_translated_team(
        raw_team,
        team_zh,
        assets_config,
        template_name=template_name,
    )
    review_suggestions = review_translation(raw_team, team_zh, validation_report, bundle)
    share_card_html = render_share_card_html(team_zh, assets_config, template_name=template_name)

    (output_dir / "team-raw.json").write_text(
        json.dumps(raw_team, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "team-zh.json").write_text(
        json.dumps(team_zh, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "validation-report.json").write_text(
        json.dumps(validation_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "review-suggestions.json").write_text(
        json.dumps(review_suggestions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "share-card.html").write_text(share_card_html, encoding="utf-8")

    return {
        "team_raw": raw_team,
        "team_zh": team_zh,
        "validation_report": validation_report,
        "review_suggestions": review_suggestions,
        "share_card_html": share_card_html,
    }
