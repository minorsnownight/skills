# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Claude Code Skill that translates PokePaste team URLs into official Chinese Showdown format, queries current Pokemon Champions season rules, and generates strategy analysis Markdown documents.

## Commands

```bash
# Generate dictionary files (first-time setup, requires git + internet)
python get-pokemon-champions-teams-from-pokepast/scripts/get-dict.py

# Translate one or more PokePaste URLs to Chinese Showdown format
python get-pokemon-champions-teams-from-pokepast/scripts/get-pokepast.py <url1> [url2] ...

# Verify dictionary integrity
python -c "import json; [print(f'{n}.json: {len(json.load(open(f\"get-pokemon-champions-teams-from-pokepast/dict/{n}.json\")))} 条') for n in ['pokemon','pokemon-forms','moves','abilities','items','types','natures','alias']]"
```

No build step, no test framework, no linting. Scripts use Python 3 stdlib only.

## Architecture

Two-layer design: **Python scripts** handle data processing, **SKILL.md** orchestrates the full workflow including Claude-driven analysis.

```
get-pokemon-champions-teams-from-pokepast/
  SKILL.md        # Skill definition: 7-step workflow (check dict → translate → handle unresolved → season info → strategy → doc → review)
  dict/           # 8 JSON dictionaries (pokemon, pokemon-forms, moves, abilities, items, types, natures, alias)
  scripts/
    get-dict.py   # Clones pokemon-dataset-zh → 3-layer build (extract + rules + alias merge) → writes dict/*.json
    get-pokepast.py  # Fetches PokePaste HTML → parses team data → translates via dict → outputs Chinese Showdown text
  temp/           # gitignored: pokemon-dataset-zh/ (cloned repo) + docs/ (generated Markdown)
```

### Data flow

1. `get-dict.py` clones `42arch/pokemon-dataset-zh` (shallow) into `temp/pokemon-dataset-zh/`, applies a 3-layer strategy:
   - **Layer 1**: Direct extraction from `simple_pokedex.json`, `move_list.json`, `ability_list.json`, `item_list.json`, and form data from detail JSONs (image filenames → Showdown-style English names)
   - **Layer 2**: Rule-based generation for common Chinese form name patterns (超级→-Mega, 阿罗拉的样子→-Alola, 起源形态→-Origin, etc.)
   - **Layer 3**: Merge from `dict/alias.json` for irregular forms that can't be auto-generated

   Output: `{EnglishName: {ja, zh-hans, zh-hant}}` mappings. `types.json` and `natures.json` are preserved (manually maintained). `alias.json` is preserved (user-maintained).

2. `get-pokepast.py` loads all 8 dict files into an exact-match index and a lowercase-fallback index. For each URL: fetches HTML, extracts team from `<article>/<pre>` elements, translates terms (zh-hans only, no fallback; keeps English if no zh-hans). Outputs translated text to stdout, metadata JSON to stderr (`[META]`), and unresolved terms to stderr (`[UNRESOLVED]`).

### Translation rules

- Exact match first, then case-insensitive fallback
- Only zh-hans used; no language fallback. If zh-hans missing, keep English
- Labels: `Ability:` → `特性:`, `Level:` → `等级:`, `EVs:` → `努力值:`, `IVs:` → `个体值:`, `Tera Type:` → `太晶属性:`, `xxx Nature` → `性格: xxx`
- Stat abbreviations: Atk→攻击, Def→防御, SpA→特攻, SpD→特防, Spe→速度, HP stays HP

### Unresolved term handling

When `[UNRESOLVED]` appears in stderr, the SKILL.md workflow triggers an agent to:
1. Search local `temp/pokemon-dataset-zh/` data for the missing translation
2. Add found mappings to `dict/alias.json`
3. Re-run `get-pokepast.py`
4. Repeat until no unresolved terms remain

### SKILL.md workflow

1. Check `dict/` exists and is non-empty; if not, run `get-dict.py`
2. Run `get-pokepast.py` with user-provided URLs
3. Handle unresolved terms (agent-driven, step 2.5)
4. WebSearch for current Pokemon Champions season rules
5. Claude writes strategy analysis (核心战术, 联防关系, 选出建议, 宝可梦角色)
6. Generate Markdown doc per team to `temp/docs/`, named `YYYYMMDD-队伍名称-作者.md`
7. Expert review pass for format/translation/strategy errors

## Key conventions

- Team code: 10-character alphanumeric at end of title (e.g. `FNWB95NJDH`)
- Author: text before `'s ` in title
- `temp/` is gitignored (contains cloned repo and generated docs)
- `dict/alias.json` is user-maintained; `get-dict.py` preserves it (never overwrites)
- `dict/types.json` and `dict/natures.json` are manually maintained; `get-dict.py` preserves them
- All user-facing output in Simplified Chinese; technical terms/protocol names may stay English
- Core principle: scripts handle what they can; agent only intervenes for decisions requiring judgment (e.g. resolving unknown terms)
