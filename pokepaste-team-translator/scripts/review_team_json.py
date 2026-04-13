#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.team_review import review_translation
from scripts.lib.translation_assets import load_assets_config, load_dictionary_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic review suggestions.")
    parser.add_argument("team_raw_json")
    parser.add_argument("team_zh_json")
    parser.add_argument("validation_report_json")
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
    raw_team = json.loads(Path(args.team_raw_json).read_text(encoding="utf-8"))
    team_zh = json.loads(Path(args.team_zh_json).read_text(encoding="utf-8"))
    validation_report = json.loads(Path(args.validation_report_json).read_text(encoding="utf-8"))
    review = review_translation(raw_team, team_zh, validation_report, bundle)
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
