#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.translation_assets import load_assets_config
from scripts.lib.translation_validation import validate_translated_team


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate translated team JSON.")
    parser.add_argument("team_raw_json")
    parser.add_argument("team_zh_json")
    parser.add_argument("--config", default="assets/assets.json")
    args = parser.parse_args()

    raw_team = json.loads(Path(args.team_raw_json).read_text(encoding="utf-8"))
    team_zh = json.loads(Path(args.team_zh_json).read_text(encoding="utf-8"))
    assets_config = load_assets_config(Path(args.config))
    report = validate_translated_team(raw_team, team_zh, assets_config)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
