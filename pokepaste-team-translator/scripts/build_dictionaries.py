#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.dictionary_builder import build_dictionary_payloads


def main() -> int:
    parser = argparse.ArgumentParser(description="Build translation dictionaries for the rewrite pipeline.")
    parser.add_argument("--dataset-root", default="temp/pokemon-dataset-zh/data")
    parser.add_argument("--image-root", default="temp/pokemon-dataset-zh/data/images")
    parser.add_argument("--dict-dir", default="dict")
    args = parser.parse_args()

    dict_dir = Path(args.dict_dir)
    dict_dir.mkdir(parents=True, exist_ok=True)
    payloads = build_dictionary_payloads(
        dataset_root=Path(args.dataset_root),
        image_root=Path(args.image_root),
        existing_dict_dir=dict_dir,
    )
    summary = {}
    for name, data in payloads.items():
        path = dict_dir / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        summary[name] = len(data)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
