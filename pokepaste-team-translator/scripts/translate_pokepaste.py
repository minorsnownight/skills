#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.translation_assets import load_assets_config, load_dictionary_bundle
from scripts.lib.translation_pipeline import (
    fetch_pokepaste_html,
    parse_pokepaste_html,
    translate_team,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate a Pokepaste page into raw/zh JSON.")
    parser.add_argument("url", help="pokepast.es URL")
    parser.add_argument("--config", default="assets/assets.json")
    parser.add_argument("--dict-dir", default="dict")
    parser.add_argument("--image-root", default="temp/pokemon-dataset-zh/data/images")
    args = parser.parse_args()

    assets_config = load_assets_config(Path(args.config))
    bundle = load_dictionary_bundle(
        dict_dir=Path(args.dict_dir),
        image_root=Path(args.image_root),
        image_base_url=assets_config["image_source_base_url"],
    )
    html_text = fetch_pokepaste_html(args.url)
    raw_team = parse_pokepaste_html(html_text, args.url)
    team_zh = translate_team(raw_team, bundle, assets_config)
    print(json.dumps({"team_raw": raw_team, "team_zh": team_zh}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
