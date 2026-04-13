# Skills

A monorepo of self-contained skills. Each subdirectory is an independent skill with its own contract, scripts, and assets.

## Skills

| Skill | Description |
|-------|-------------|
| [pokepaste-team-translator](./pokepaste-team-translator/) | Parse Pokepaste pages into structured English/Chinese JSON, validate translations, and render mobile-friendly HTML share cards |

## Structure

```
<skill-name>/
  SKILL.md       # Skill contract and usage
  scripts/       # CLI entrypoints
  scripts/lib/   # Internal implementation
  dict/          # Translation dictionaries
  assets/        # Templates and configuration
  tests/         # Test suite
```

Each skill is designed to be **deterministic and dependency-light** — no LLM calls, no runtime network beyond fetching source data.
