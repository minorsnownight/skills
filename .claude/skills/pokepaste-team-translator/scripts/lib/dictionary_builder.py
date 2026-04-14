from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.lib.translation_assets import _build_item_image_index, _build_pokemon_image_index


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _add_alias(mapping: dict, key: str, value: str) -> None:
    if not key or not value:
        return
    mapping.setdefault(key, value)
    if " " in key:
        mapping.setdefault(key.replace(" ", "-"), value)


def _build_simple_mapping(items: list[dict]) -> dict:
    mapping = {}
    for item in items:
        _add_alias(mapping, item.get("name_en", ""), item.get("name_zh", ""))
    return mapping


def _find_pokemon_detail_path(pokemon_dir: Path, index: str, fallback_zh: str) -> Path | None:
    direct = pokemon_dir / f"{index}-{fallback_zh}.json"
    if direct.exists():
        return direct
    matches = sorted(pokemon_dir.glob(f"{index}-*.json"))
    return matches[0] if matches else None


def _build_pokemon_mapping(simple_pokedex: list[dict], pokemon_dir: Path) -> dict:
    mapping = {}
    for item in simple_pokedex:
        name_en = item.get("name_en", "")
        name_zh = item.get("name_zh", "")
        detail_path = _find_pokemon_detail_path(pokemon_dir, item["index"], name_zh)
        if detail_path and detail_path.exists():
            detail = _load_json(detail_path)
            name_zh = detail.get("name_zh", name_zh)
        _add_alias(mapping, name_en, name_zh)
    return mapping


def _flatten_items(nodes: list[dict], flattened: list[dict]) -> None:
    for node in nodes:
        if node.get("type") == "item":
            flattened.append(node)
        for child in node.get("children", []):
            _flatten_items([child], flattened)


def _extract_showdown_name(image_filename: str, fallback_en: str) -> str:
    match = re.match(r"\d+(.+?)(?:_Dream)?\.png$", image_filename)
    if not match:
        return fallback_en
    name = match.group(1).replace("_", "-")
    return name.replace("-Gigantamax", "-Gmax")


def _format_zh_form_name(species_zh: str, form_zh: str) -> str:
    if species_zh and species_zh in form_zh:
        return form_zh
    if species_zh:
        return f"{species_zh}-{form_zh}"
    return form_zh


def _resolve_species_zh(showdown_name: str, zh_to_en: dict[str, str]) -> str:
    for zh_name, en_name in zh_to_en.items():
        if en_name == showdown_name:
            return zh_name
    base = showdown_name.split("-")[0]
    for zh_name, en_name in zh_to_en.items():
        if en_name == base:
            return zh_name
    return ""


_FORM_RULES = [
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


def _match_form_rule(form_zh: str) -> str | None:
    for matcher, suffix in _FORM_RULES:
        if matcher(form_zh):
            return suffix
    return None


def _build_pokemon_forms(simple_pokedex: list[dict], pokemon_dir: Path, aliases: dict[str, str]) -> dict:
    zh_to_en = {entry["name_zh"]: entry["name_en"] for entry in simple_pokedex}
    mapping = {}
    for entry in simple_pokedex:
        detail_path = _find_pokemon_detail_path(pokemon_dir, entry["index"], entry["name_zh"])
        if not detail_path or not detail_path.exists():
            continue
        detail = _load_json(detail_path)
        for key in ("evolution_chains", "mega_evolution", "gigantamax_evolution"):
            groups = detail.get(key, [])
            if key == "evolution_chains":
                iterable = [candidate for group in groups for candidate in group]
            else:
                iterable = groups
            for candidate in iterable:
                form_name = candidate.get("form_name")
                image = candidate.get("image", "")
                if not form_name or not image:
                    continue
                showdown_name = _extract_showdown_name(image, entry["name_en"])
                if showdown_name == entry["name_en"]:
                    continue
                species_zh = _resolve_species_zh(showdown_name, zh_to_en)
                _add_alias(mapping, showdown_name, _format_zh_form_name(species_zh, form_name))
        for form in detail.get("forms", []):
            form_name = form.get("name", "")
            suffix = _match_form_rule(form_name)
            if not suffix:
                continue
            showdown_name = f'{entry["name_en"]}{suffix}'
            _add_alias(mapping, showdown_name, _format_zh_form_name(entry["name_zh"], form_name))
    for key, value in aliases.items():
        mapping.setdefault(key, value)
    return mapping


def build_dictionary_payloads(dataset_root: Path, image_root: Path, existing_dict_dir: Path) -> dict:
    simple_pokedex = _load_json(dataset_root / "simple_pokedex.json")
    abilities = _load_json(dataset_root / "ability_list.json")
    moves = _load_json(dataset_root / "move_list.json")
    item_tree = _load_json(dataset_root / "item_list.json")
    flattened_items = []
    _flatten_items(item_tree, flattened_items)
    aliases = _load_json(existing_dict_dir / "alias.json")
    natures = _load_json(existing_dict_dir / "natures.json")
    types = _load_json(existing_dict_dir / "types.json")
    return {
        "pokemon": _build_pokemon_mapping(simple_pokedex, dataset_root / "pokemon"),
        "pokemon-forms": _build_pokemon_forms(simple_pokedex, dataset_root / "pokemon", aliases),
        "moves": _build_simple_mapping(moves),
        "abilities": _build_simple_mapping(abilities),
        "items": _build_simple_mapping(flattened_items),
        "natures": natures,
        "types": types,
        "alias": aliases,
        "pokemon-images": _build_pokemon_image_index(image_root),
        "item-images": _build_item_image_index(image_root),
    }
