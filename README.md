# pokepast-zh

将 [PokePast](https://pokepast.es) 队伍页面翻译为中文的静态 Web 工具。

字段数据来源于 [PokeAPI](https://pokeapi.co/)，覆盖宝可梦名称、招式、特性、道具、属性、性格的英/日/简中/繁中四语映射。

## 使用方式

1. 打开 `site/index.html`
2. 输入 PokePast 链接（如 `https://pokepast.es/xxxxx`）
3. 点击翻译，即可看到中文队伍页面

## 更新字典

```bash
# 先将 PokeAPI/api-data 克隆到项目根目录
git clone --depth 1 https://github.com/PokeAPI/api-data.git

# 运行脚本，生成字典到 site/dict/
python pokemon-chinese-dict.py
```

## 项目结构

```
pokemon-chinese-dict.py   # 字典生成脚本
site/
  index.html              # 前端页面
  app.js                  # 翻译逻辑
  dict/                   # 字典文件（由脚本生成）
```
