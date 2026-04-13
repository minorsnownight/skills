---
name: get-pokemon-champions-teams-from-pokepast
description: >
  将 PokePaste 队伍翻译为官方中文 Showdown 格式，查询 Pokemon Champions 赛季信息，
  撰写详细策略分析并生成 Markdown 文档。当用户提供一个或多个 https://pokepast.es/xxxxx
  链接时触发，或当用户提及"宝可梦冠军队伍"、"PokePast 翻译"、"队伍中文翻译"时使用。
---

# Pokemon Champions Teams from PokePast

将 PokePaste 队伍链接转为官方中文队伍配置 + 策略分析文档。

## 执行流程

### 1. 检查字典

检查 `dict/` 目录是否存在且非空。若为空或不存在：

```bash
python scripts/get-dict.py
```

该脚本会自动克隆 pokemon-dataset-zh 到 `temp/pokemon-dataset-zh/` 并通过三层策略生成字典 JSON 到 `dict/`：
- 第 1 层：从 pokemon-dataset-zh 直接提取
- 第 2 层：根据中文形态名模式规则生成
- 第 3 层：从 `dict/alias.json` 合并手动映射

### 2. 翻译队伍

```bash
python scripts/get-pokepast.py <url1> [url2] ...
```

输出中文 Showdown 格式文本到 stdout，元数据 JSON 到 stderr（以 `[META]` 开头）。

### 2.5 处理未解析术语

如果 get-pokepast.py 输出中包含 `[UNRESOLVED]` 标记的术语：

1. 分析未解析的英文术语，尝试拆分（如 `Maushold-Four` → `Maushold` + `Four`）
2. 搜索本地 `temp/pokemon-dataset-zh/` 数据，查找对应的中文翻译
3. 将找到的映射添加到 `dict/alias.json`，格式与其他 dict 文件一致：
   ```json
   {
     "EnglishName": {
       "ja": "日本語名",
       "zh-hans": "简体中文",
       "zh-hant": "繁體中文"
     }
   }
   ```
   语言缺失则不填该字段。
4. 重新运行 `python scripts/get-pokepast.py <urls>`
5. 重复直到无未解析术语

元数据格式：
```json
[{"title": "...", "team_code": "XXXXXXXXXX", "author": "...", "team_name": "...", "format": "...", "url": "..."}]
```

### 3. 查询赛季信息

用 WebSearch 查询当前 Pokemon Champions 赛季规则：
- 搜索 `pokemonchampions.jp/sc/news/` 获取官方公告
- 搜索 `news.pokemon-home.com/sc/` 获取赛季详情
- 提取赛制规则要点（可用宝可梦、道具限制、等级限制等）

### 4. 策略分析

基于翻译后的队伍配置 + 赛季规则 + 联网查找资料，撰写详细策略分析，使用简体中文。包含：

- **核心战术**：队伍的核心赢法，关键招式组合运作方式
- **联防关系**：属性互补、掩护配合（威吓轮转、愤怒粉、双墙等）
- **选出建议**：面对不同对手类型（高速进攻、空间队、天气队等）的推荐选出
- **宝可梦角色**：每只宝可梦的定位和关键招式用途

分析必须基于队伍实际配置（招式、道具、特性、努力值分配），不要泛泛而谈。

### 5. 生成文档

每个队伍生成一个 Markdown 文件，保存到 `temp/docs/`。

**文件命名**：`YYYYMMDD-队伍名称-作者.md`
- 日期：当天日期
- 队伍名称：从标题提取（去掉作者和队伍码），空格替换为连字符
- 作者：标题中 `'s` 前的部分
- 示例：`20260412-Gengar-Kommo-o-Team-UB_SLOW.md`

**文档结构**：

```markdown
# 队伍标题

队伍码: XXXXXXXXXX
赛制: gen9championsvgc2026regma
来源: https://pokepast.es/xxxxx

## 队伍配置

宝可梦中文名 @ 道具中文名
特性: 特性中文名
等级: 50
努力值: 31 HP / 1 攻击 / 10 防御 / 23 特防 / 1 速度
性格: 性格中文名
- 招式中文名
- 招式中文名
- 招式中文名
- 招式中文名

## 赛季信息

（当前赛季规则要点）

## 策略分析

### 核心战术
（内容）

### 联防关系
（内容）

### 选出建议
（内容）

### 宝可梦角色
- **宝可梦中文名**：角色定位和关键招式用途
```

多个队伍时每个队伍一个独立文件。

### 6. 审查文档

以宝可梦竞技游戏专家身份审查所有生成的文档，检查：
- 格式错误（Markdown 语法、标题层级、代码块）
- 文字错误（错别字、标点符号）
- 翻译错误（术语是否为官方中文译名）
- 策略错误（战术分析是否符合实际配置和 VGC 环境常识）

发现问题则修正后重新保存，直到无错误。

## 注意事项

- 队伍码（如 FNWB95NJDH）是宝可梦冠军游戏中的模板码，10 位字母数字组合
- 部分术语可能没有中文翻译（PokeAPI 数据缺失），保留英文原文
- 策略分析要结合宝可梦冠军 VGC 环境特点
- 来源 URL 必须标注在文档中
