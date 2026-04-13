#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.html_rendering import render_share_card_html
from scripts.lib.translation_assets import load_assets_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Render translated team HTML.")
    parser.add_argument("team_zh_json")
    parser.add_argument("--config", default="assets/assets.json")
    parser.add_argument("--template", default=None)
    args = parser.parse_args()

    team_zh = json.loads(Path(args.team_zh_json).read_text(encoding="utf-8"))
    assets_config = load_assets_config(Path(args.config))
    print(render_share_card_html(team_zh, assets_config, template_name=args.template))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
