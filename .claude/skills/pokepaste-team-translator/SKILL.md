---
name: pokepaste-team-translator
description: Use when the user provides one or more `pokepast.es` URLs, asks for Pokemon team translation, wants a structured Chinese team export, or needs a mobile-friendly HTML team card from a Pokepaste link.
---

# Pokepaste Team Translator

This skill is translation-only. It parses Pokepaste pages into structured English and Chinese artifacts, validates them, produces deterministic review suggestions, and renders an HTML share card.

## Public entrypoints

Use these scripts as the supported interface:

- `python3 scripts/build_dictionaries.py`
- `python3 scripts/build_translated_team.py <url1> [url2] ...`
- `python3 scripts/translate_pokepaste.py <url>`
- `python3 scripts/validate_team_json.py <team-raw.json> <team-zh.json>`
- `python3 scripts/review_team_json.py <team-raw.json> <team-zh.json> <validation-report.json>`
- `python3 scripts/render_team_html.py <team-zh.json>`

Treat `scripts/lib/` as internal implementation detail.

## Deliverables

For each team URL, generate:

1. `team-raw.json`
2. `team-zh.json`
3. `validation-report.json`
4. `review-suggestions.json`
5. `share-card.html`

All user-facing artifacts must remain in **Simplified Chinese**.  
This skill file is intentionally written in **English**.

## Workflow

### 1. Rebuild dictionaries if needed

```bash
python3 scripts/build_dictionaries.py
```

This rebuilds translation mappings and image indexes from a clone of [42arch/pokemon-dataset-zh](https://github.com/42arch/pokemon-dataset-zh) at `temp/pokemon-dataset-zh/data/`. The translation pipeline itself uses pre-built dictionaries in `dict/` and does not require this clone.

### 2. Build the full artifact set

```bash
python3 scripts/build_translated_team.py <url1> [url2] ...
```

Artifacts are written under `temp/output/<slug>/`.

## Validation contract

`validation-report.json` is structural only.

Report:
- missing required fields
- missing translations
- missing image URLs
- invalid template configuration

Do not place alias suggestions or semantic judgments in this file.

## Review contract

`review-suggestions.json` is deterministic and unit-testable.

Rules:
- no live LLM dependency
- no network dependency beyond fetching Pokepaste
- suggestions must be reproducible for the same inputs
- alias proposals must be structured records
- ambiguous issues must be surfaced for human follow-up
- do not directly edit `dict/alias.json` as a runtime side effect

## Assets

Configured assets live under:

- `assets/assets.json`
- `assets/templates/`

Rules:
- image indexes are pre-built in `dict/pokemon-images.json` and `dict/item-images.json`; rebuild with `build_dictionaries.py` when the dataset changes
- publishable image URLs must be derived from `assets/assets.json`
- do not rely on PokePaste-hosted images in final artifacts
- if an image is missing, keep generation alive and report it
