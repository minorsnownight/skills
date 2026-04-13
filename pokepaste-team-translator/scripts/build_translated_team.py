#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.translation_assets import load_assets_config, load_dictionary_bundle
from scripts.lib.translation_pipeline import (
    build_output_slug,
    build_translated_team_artifacts,
    fetch_pokepaste_html,
    parse_pokepaste_html,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build translated Pokepaste artifacts.")
    parser.add_argument("urls", nargs="+", help="One or more pokepast.es URLs")
    parser.add_argument("--output-root", default="temp/output", help="Artifact root directory")
    parser.add_argument("--template", default=None, help="Configured template name")
    parser.add_argument("--config", default="assets/assets.json", help="Assets config path")
    parser.add_argument("--dict-dir", default="dict", help="Dictionary directory")
    parser.add_argument(
        "--image-root",
        default="temp/pokemon-dataset-zh/data/images",
        help="Image root directory",
    )
    args = parser.parse_args()

    assets_config = load_assets_config(Path(args.config))
    bundle = load_dictionary_bundle(
        dict_dir=Path(args.dict_dir),
        image_root=Path(args.image_root),
        image_base_url=assets_config["image_source_base_url"],
    )
    output_root = Path(args.output_root)
    for url in args.urls:
        html_text = fetch_pokepaste_html(url)
        raw_team = parse_pokepaste_html(html_text, url)
        output_dir = output_root / build_output_slug(raw_team)
        build_translated_team_artifacts(
            raw_team=raw_team,
            bundle=bundle,
            assets_config=assets_config,
            output_dir=output_dir,
            template_name=args.template,
        )
        print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
