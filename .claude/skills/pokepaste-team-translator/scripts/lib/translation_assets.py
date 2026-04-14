from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


STAT_LABELS_ZH = {
    "HP": "HP",
    "Atk": "攻击",
    "Def": "防御",
    "SpA": "特攻",
    "SpD": "特防",
    "Spe": "速度",
}


def _load_json(path: Path) -> Dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_assets_config(config_path: Path) -> dict:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    required_keys = {"image_source_base_url", "templates", "default_template"}
    missing = sorted(required_keys - set(config))
    if missing:
        raise ValueError(f"assets config missing keys: {', '.join(missing)}")
    if config["default_template"] not in config["templates"]:
        raise ValueError("default_template is not registered in templates")
    return config


@dataclass
class DictionaryBundle:
    pokemon: Dict[str, str]
    pokemon_forms: Dict[str, str]
    items: Dict[str, str]
    abilities: Dict[str, str]
    moves: Dict[str, str]
    natures: Dict[str, str]
    types: Dict[str, str]
    aliases: Dict[str, str]
    pokemon_images: Dict[str, str]
    item_images: Dict[str, str]
    image_base_url: str

    def translate_species(self, term: str) -> Optional[str]:
        return (
            self.pokemon.get(term)
            or self.pokemon_forms.get(term)
            or self.aliases.get(term)
        )

    def translate_item(self, term: str) -> Optional[str]:
        return self.items.get(term) or self.aliases.get(term)

    def translate_ability(self, term: str) -> Optional[str]:
        return self.abilities.get(term) or self.aliases.get(term)

    def translate_move(self, term: str) -> Optional[str]:
        return self.moves.get(term) or self.aliases.get(term)

    def translate_nature(self, term: str) -> Optional[str]:
        return self.natures.get(term) or self.aliases.get(term)

    def translate_type(self, term: str) -> Optional[str]:
        return self.types.get(term) or self.aliases.get(term)

    def resolve_pokemon_image(self, chinese_name: Optional[str]) -> dict:
        if not chinese_name:
            return {"relative_path": None, "url": None, "status": "missing"}
        relative_path = (
            self.pokemon_images.get(chinese_name)
            or self.pokemon_images.get(chinese_name.split("-", 1)[0])
        )
        if not relative_path:
            return {"relative_path": None, "url": None, "status": "missing"}
        return {
            "relative_path": relative_path,
            "url": f"{self.image_base_url.rstrip('/')}/{relative_path}",
            "status": "ok",
        }

    def resolve_item_image(self, chinese_name: Optional[str]) -> dict:
        if not chinese_name:
            return {"relative_path": None, "url": None, "status": "missing"}
        relative_path = self.item_images.get(chinese_name)
        if not relative_path:
            return {"relative_path": None, "url": None, "status": "missing"}
        return {
            "relative_path": relative_path,
            "url": f"{self.image_base_url.rstrip('/')}/{relative_path}",
            "status": "ok",
        }

    def suggest_alias(self, term: str, field: str) -> Optional[dict]:
        normalized = term.strip()
        gender_match = re.match(r"^(?P<base>.+?) \((M|F)\)$", normalized)
        if gender_match:
            candidate = gender_match.group("base")
            translation = self._translate_by_field(candidate, field)
            if translation:
                return {
                    "source_term": term,
                    "canonical_term": candidate,
                    "translation": translation,
                    "field": field,
                    "reason": "trimmed trailing gender marker",
                }
        return None

    def _translate_by_field(self, term: str, field: str) -> Optional[str]:
        if field == "species":
            return self.translate_species(term)
        if field == "item":
            return self.translate_item(term)
        if field == "ability":
            return self.translate_ability(term)
        if field == "move":
            return self.translate_move(term)
        if field == "nature":
            return self.translate_nature(term)
        if field == "tera_type":
            return self.translate_type(term)
        return None


def _image_candidate_score(name: str) -> tuple[int, int]:
    penalty = 0
    if "-超级" in name:
        penalty += 3
    if "-超极巨化" in name:
        penalty += 3
    if "-雄性" in name or "-雌性" in name:
        penalty += 1
    if "-阿罗拉" in name or "-洗翠" in name or "-伽勒尔" in name:
        penalty += 2
    return (penalty, len(name))


def _register_image(index: Dict[str, str], key: str, rel_path: str) -> None:
    current = index.get(key)
    if current is None:
        index[key] = rel_path
        return
    if _image_candidate_score(Path(rel_path).stem) < _image_candidate_score(Path(current).stem):
        index[key] = rel_path


def _build_pokemon_image_index(image_root: Path) -> Dict[str, str]:
    root = image_root / "home"
    index: Dict[str, str] = {}
    if not root.exists():
        return index
    for path in sorted(root.glob("*.png")):
        if "shiny" in path.name:
            continue
        stem = path.stem
        if "-" not in stem:
            continue
        _, _, chinese_name = stem.partition("-")
        rel_path = path.relative_to(image_root).as_posix()
        _register_image(index, chinese_name, rel_path)
        if "-" in chinese_name:
            base_name = chinese_name.split("-", 1)[0]
            _register_image(index, base_name, rel_path)
    return index


def _build_item_image_index(image_root: Path) -> Dict[str, str]:
    root = image_root / "items"
    index: Dict[str, str] = {}
    if not root.exists():
        return index
    for path in sorted(root.glob("*.png")):
        rel_path = path.relative_to(image_root).as_posix()
        _register_image(index, path.stem, rel_path)
    return index


def load_dictionary_bundle(
    dict_dir: Path,
    image_base_url: str,
) -> DictionaryBundle:
    return DictionaryBundle(
        pokemon=_load_json(dict_dir / "pokemon.json"),
        pokemon_forms=_load_json(dict_dir / "pokemon-forms.json"),
        items=_load_json(dict_dir / "items.json"),
        abilities=_load_json(dict_dir / "abilities.json"),
        moves=_load_json(dict_dir / "moves.json"),
        natures=_load_json(dict_dir / "natures.json"),
        types=_load_json(dict_dir / "types.json"),
        aliases=_load_json(dict_dir / "alias.json"),
        pokemon_images=_load_json(dict_dir / "pokemon-images.json"),
        item_images=_load_json(dict_dir / "item-images.json"),
        image_base_url=image_base_url,
    )
