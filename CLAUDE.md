# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **skills monorepo** for mew-skills — each subdirectory is a self-contained "skill" with its own SKILL.md contract, scripts, and assets. Skills are translation-only tools with no LLM or runtime network dependency beyond fetching source data.

Current skill: **pokepaste-team-translator** — parses Pokepaste pages into structured English/Chinese JSON artifacts, validates them, produces deterministic review suggestions, and renders mobile-friendly HTML share cards. Located at `.claude/skills/pokepaste-team-translator/`.

## Commands

All commands run from the skill subdirectory (`.claude/skills/pokepaste-team-translator/`).

```bash
# Rebuild translation dictionaries from temp/pokemon-dataset-zh/data/
python3 scripts/build_dictionaries.py

# Build full artifact set for one or more Pokepaste URLs
python3 scripts/build_translated_team.py <url1> [url2] ...

# Single-URL translate (prints raw+zh JSON to stdout)
python3 scripts/translate_pokepaste.py <url>

# Validate a translated team pair
python3 scripts/validate_team_json.py <team-raw.json> <team-zh.json>

# Generate deterministic review suggestions
python3 scripts/review_team_json.py <team-raw.json> <team-zh.json> <validation-report.json>

# Render HTML share card
python3 scripts/render_team_html.py <team-zh.json>

# Run tests (from skill subdirectory)
python3 -m pytest tests/
# Or with unittest:
python3 -m unittest discover -s tests
# Run a single test class/method:
python3 -m unittest tests.test_translation_pipeline.TranslationPipelineTest.test_parse_pokepaste_html_extracts_expected_metadata
```

## Architecture

### Pipeline stages (sequential)

1. **Fetch** — `fetch_pokepaste_html()` downloads raw HTML from pokepast.es
2. **Parse** — `parse_pokepaste_html()` extracts structured English team data (`team-raw.json`)
3. **Translate** — `translate_team()` applies dictionary lookups to produce Chinese fields (`team-zh.json`)
4. **Validate** — `validate_translated_team()` checks structural completeness (`validation-report.json`)
5. **Review** — `review_translation()` generates deterministic alias suggestions (`review-suggestions.json`)
6. **Render** — `render_share_card_html()` produces the HTML share card (`share-card.html`)

### Key design constraints

- **No LLM dependency** — all translation is dictionary-based lookup
- **Deterministic review** — same inputs always produce same review suggestions
- **Validation ≠ Review** — validation is structural (missing fields, missing images); review is semantic (alias proposals, ambiguous findings). Keep them separate.
- **Graceful degradation** — missing images or translations do not halt generation; they are reported in output artifacts

### Module layout

```
scripts/              # CLI entrypoints (one per pipeline stage)
scripts/lib/          # Internal implementation (not a public interface)
  dictionary_builder  # Rebuilds dict/ JSON from pokemon-dataset-zh source
  translation_assets  # DictionaryBundle dataclass + image index builders
  translation_pipeline # Core pipeline: fetch → parse → translate → artifacts
  translation_validation # Structural validation logic
  team_review         # Deterministic alias suggestion engine
  html_rendering      # Template-based HTML share card rendering
dict/                 # Pre-built en→zh translation mappings (JSON)
assets/               # Template config + HTML templates
temp/                 # Runtime data (gitignored): pokemon-dataset-zh clone, output
tests/                # unittest-based tests with fixture HTML files
```

### Dictionary system

- `dict/` contains flat `en→zh` string mappings for pokemon, moves, abilities, items, natures, types, and aliases
- `DictionaryBundle` dataclass in `translation_assets.py` is the runtime interface: `translate_species()`, `translate_move()`, etc., with alias fallback
- `dict/alias.json` is hand-curated; never modified as a runtime side effect
- `dict/pokemon-images.json` and `dict/item-images.json` are built by scanning `temp/pokemon-dataset-zh/data/images/` during `build_dictionaries.py`
- Image URL resolution: `image_base_url + relative_path` from `assets.json`

### Output artifacts

For each team URL, `build_translated_team.py` writes to `temp/output/<slug>/`:
- `team-raw.json` — parsed English team
- `team-zh.json` — translated Chinese team with image URLs and unresolved terms
- `validation-report.json` — structural issues only
- `review-suggestions.json` — alias proposals and ambiguous findings
- `share-card.html` — rendered HTML card

The slug format: `YYYYMMDD-<team-name>-<author>-<team-code>`

## Data source

`temp/pokemon-dataset-zh/` is a git clone of [42arch/pokemon-dataset-zh](https://github.com/42arch/pokemon-dataset-zh). It must exist before `build_dictionaries.py` can run. Clone it if missing. The translation pipeline (`build_translated_team.py` etc.) uses pre-built dictionaries in `dict/` and does not require the dataset clone.

## Commit style

Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`.
