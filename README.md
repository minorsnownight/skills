# pokepast-zh

将 [PokePast](https://pokepast.es) 队伍页面翻译为中文的 Claude Code Skill。

## 功能

- 输入 PokePaste URL，输出官方中文 Showdown 格式队伍配置
- 查询 Pokemon Champions 当前赛季信息
- 生成详细策略分析文档（核心战术、联防关系、选出建议、宝可梦角色）
- 自动审查文档中的翻译和策略错误

## 使用方式

在 Claude Code 中调用 skill：

```
/get-pokemon-champions-teams-from-pokepast https://pokepast.es/xxxxx
```

支持多个 URL：

```
/get-pokemon-champions-teams-from-pokepast https://pokepast.es/aaa https://pokepast.es/bbb
```

生成的 Markdown 文档保存在 `temp/docs/` 目录。

## 更新字典

```bash
cd get-pokemon-champions-teams-from-pokepast
python scripts/get-dict.py
```

该脚本会自动克隆 [PokeAPI/api-data](https://github.com/PokeAPI/api-data) 仓库并生成字典到 `dict/` 目录。

## 项目结构

```
get-pokemon-champions-teams-from-pokepast/
  SKILL.md              # Skill 主文件
  dict/                 # 字典文件（由 get-dict.py 生成）
  scripts/
    get-dict.py         # 字典生成脚本
    get-pokepast.py     # 抓取 + 翻译脚本
  temp/
    pokeapi-data/       # api-data 仓库
    docs/               # 生成的文档
```
