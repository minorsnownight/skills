# Get Pokemon Champions Teams from PokePast

## Overview

A Claude Code Skill that takes one or more PokePaste URLs, translates team data into official Chinese Showdown format, queries current season info, provides detailed competitive strategy analysis, and generates Markdown documents.

## Directory Structure

```
get-pokemon-champions-teams-from-pokepast/
  SKILL.md              # Skill 主文件
  dict/                 # 字典 JSON（由 get-dict.py 生成）
    pokemon.json
    pokemon-forms.json
    moves.json
    abilities.json
    items.json
    types.json
    natures.json
  scripts/
    get-dict.py         # 克隆 api-data → 生成字典到 dict/
    get-pokepast.py     # 抓取 PokePaste → 解析 + 翻译 → 输出中文 Showdown 文本
  temp/
    pokeapi-data/       # api-data 仓库（git clone --depth 1）
    docs/               # 生成的 Markdown 文档
```

## Script 1: `get-dict.py`

**职责**：克隆 PokeAPI/api-data 仓库，提取英/日/简中/繁中映射，生成字典 JSON。

**流程**：
1. 检查 `temp/pokeapi-data/` 是否存在，不存在则 `git clone --depth 1 https://github.com/PokeAPI/api-data.git temp/pokeapi-data`
2. 遍历 7 个分类：

   | 输出文件名 | 仓库目录名 |
   |-----------|-----------|
   | pokemon.json | pokemon-species |
   | pokemon-forms.json | pokemon-form |
   | moves.json | move |
   | abilities.json | ability |
   | items.json | item |
   | types.json | type |
   | natures.json | nature |

3. 从 `temp/pokeapi-data/data/api/v2/<dir>/<id>/index.json` 提取 `names` 字段
4. 生成映射 `{英文名: {ja: ..., zh-hans: ..., zh-hant: ...}}`
5. 同时生成 Showdown 别名（slug.title()，如 `charizard-mega-y` → `Charizard-Mega-Y`），别名不覆盖已有主条目
6. 写入 `dict/<name>.json`

**翻译回退**：zh-hans 优先，缺失回退 zh-hant，都无则无中文条目

## Script 2: `get-pokepast.py`

**职责**：抓取 PokePaste 页面，解析 HTML，加载字典翻译，输出中文 Showdown 文本。

**输入**：一个或多个 PokePaste URL（命令行参数）

**流程**：
1. 加载 `dict/` 下所有字典（精确匹配索引 + 小写匹配索引）
2. 逐个抓取 URL，解析 HTML：
   - 标题（保留英文）
   - 队伍码（标题末尾 10 位字母数字，有则提取，无则省略）
   - 作者（标题中 `'s ` 前的部分）
   - 每只宝可梦：名称、道具、特性、等级、EVs、IVs、性格、招式
3. 翻译所有术语为官方中文，输出格式：

```
=== Title TEAMCODE ===
队伍码: TEAMCODE

宝可梦中文名 @ 道具中文名
特性: 特性中文名
等级: 50
努力值: 31 HP / 1 攻击 / 10 防御 / 23 特防 / 1 速度
性格: 性格中文名
- 招式中文名
- 招式中文名
- 招式中文名
- 招式中文名
```

**格式规则**：
- 标题保留英文原文
- 队伍码：仅当标题末尾存在 10 位字母数字时显示 `队伍码: XXXXXXXXXX`，否则省略
- 标签统一 `标签: 值` 格式：`特性:`、`等级:`、`努力值:`、`个体值:`、`性格:`
- 能力缩写翻译：Atk→攻击、Def→防御、SpA→特攻、SpD→特防、Spe→速度，HP 保持
- 招式前缀 `- `（短横+空格）
- 多个队伍间以空行分隔

**翻译规则**：
- 精确匹配优先，其次小写匹配
- zh-hans 优先，缺失回退 zh-hant，都无则保留英文原文

**错误处理**：
- URL 抓取失败：输出错误信息，继续处理下一个
- 页面无队伍数据：输出警告，继续处理下一个

## Skill: `SKILL.md`

**触发方式**：用户输入 `/get-pokemon-champions-teams-from-pokepast` + 一个或多个 PokePaste URL

**执行流程**：

1. **检查字典**：检查 `dict/` 目录是否存在且非空，否则执行 `python scripts/get-dict.py`
2. **翻译队伍**：执行 `python scripts/get-pokepast.py <urls>`，获取中文 Showdown 文本
3. **查询赛季信息**：用 WebSearch 查询当前 pokemon-champions 赛季规则和公告（如 `pokemonchampions.jp/sc/news/`）
4. **策略分析**：基于翻译后的队伍 + 赛季规则 + 联网查找资料，Claude 撰写详细策略分析
5. **生成文档**：将翻译 + 赛季信息 + 策略分析整合为 Markdown，每个队伍一个文件，保存到 `temp/docs/`
6. **审查文档**：以宝可梦竞技游戏专家身份审查所有生成的文档，检查格式错误、文字错误、翻译错误、策略错误，发现问题则修正后重新保存

**文件命名**：`YYYYMMDD-队伍名称-作者.md`

  - 日期：当天日期
  - 队伍名称：从标题提取（去掉作者和队伍码部分）
  - 作者：从标题中 `'s ` 前提取
  - 示例：`20260412-Gengar-Kommo-o-Team-UB_SLOW.md`

**Markdown 文档结构**：

```markdown
# 队伍标题

队伍码: XXXXXXXXXX
赛制: gen9championsvgc2026regma
来源: https://pokepast.es/xxxxx

## 队伍配置

（中文 Showdown 格式，每只宝可梦一个代码块）

## 赛季信息

（当前赛季规则要点）

## 策略分析

### 核心战术
### 联防关系
### 选出建议
### 宝可梦角色
```

## Dependencies

- Python 3（标准库：json, os, sys, urllib.request, re, subprocess）
- git（用于克隆 api-data 仓库）
- Internet access（抓取 PokePaste 页面、查询赛季信息）

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `get-pokemon-champions-teams-from-pokepast/SKILL.md` | Create | Skill 主文件 |
| `get-pokemon-champions-teams-from-pokepast/scripts/get-dict.py` | Create | 字典生成脚本 |
| `get-pokemon-champions-teams-from-pokepast/scripts/get-pokepast.py` | Create | 抓取+翻译脚本 |
| `pokemon-chinese-dict.py` | Delete | 旧字典生成脚本，功能由 get-dict.py 替代 |
| `pokepast-translate.py` | Delete | 旧翻译脚本，功能由 get-pokepast.py 替代 |
| `site/` | Delete | 旧前端页面，不再需要 |
| `.claude/skills/pokepast-team-zh/` | Delete | 旧 Skill，由新 Skill 替代 |
