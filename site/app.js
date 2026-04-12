/**
 * 宝可梦队伍中文翻译器
 *
 * 输入 PokePast URL，输出中文队伍页面
 */

const POKEPAST_BASE = "https://pokepast.es";
const CORS_PROXY = "https://api.allorigins.win/raw?url=";

// 字典文件列表
const DICT_FILES = [
    "pokemon", "pokemon-forms", "moves", "abilities", "items", "types", "natures",
];

// 字段标签翻译
const LABEL_MAP = {
    "Ability:": "特性:",
    "Level:": "等级:",
    "Tera Type:": "太晶属性:",
    "EVs:": "努力值:",
    "IVs:": "个体值:",
};

// 能力值缩写翻译
const STAT_MAP = {
    HP: "HP", Atk: "攻击", Def: "防御", SpA: "特攻", SpD: "特防", Spe: "速度",
};

// ============ 翻译器 ============

class Translator {
    constructor() {
        this.exact = {};  // 精确匹配索引
        this.lower = {};  // 小写匹配索引
    }

    async load(dictDir = "dict") {
        const loads = DICT_FILES.map(async (name) => {
            const url = `${dictDir}/${name}.json`;
            try {
                const resp = await fetch(url);
                if (!resp.ok) return;
                const data = await resp.json();
                for (const [en, translations] of Object.entries(data)) {
                    this.exact[en] = translations;
                    const low = en.toLowerCase();
                    if (!(low in this.lower)) {
                        this.lower[low] = translations;
                    }
                }
            } catch (e) {
                console.warn(`字典加载失败: ${url}`, e);
            }
        });
        await Promise.all(loads);
        const total = Object.keys(this.exact).length;
        console.log(`字典加载完成: ${total} 条`);
    }

    /** 翻译术语，返回简中；找不到返回原文；简中缺失回退繁中 */
    translate(term) {
        const translations = this.exact[term] || this.lower[term.toLowerCase()];
        if (!translations) return term;
        return translations["zh-hans"] || translations["zh-hant"] || term;
    }
}

// ============ 页面解析 ============

/** 通过 CORS 代理获取 PokePast 页面 */
async function fetchPokepast(url) {
    const proxyUrl = CORS_PROXY + encodeURIComponent(url);
    const resp = await fetch(proxyUrl);
    if (!resp.ok) throw new Error(`请求失败: ${resp.status}`);
    return await resp.text();
}

/** 从 HTML 解析队伍数据 */
function parseTeam(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");

    // 队伍标题
    const title = doc.querySelector("title")?.textContent || "";
    const format = doc.querySelector("aside p")?.textContent || "";

    // 每只宝可梦
    const articles = doc.querySelectorAll("article");
    const team = [];

    for (const article of articles) {
        const imgDiv = article.querySelector("div.img");
        const pokemonImg = imgDiv?.querySelector("img.img-pokemon")?.getAttribute("src") || "";
        const itemImg = imgDiv?.querySelector("img.img-item")?.getAttribute("src") || "";

        const pre = article.querySelector("pre");
        if (!pre) continue;

        // 提取带标签的 HTML 内容和纯文本
        const mon = {
            pokemonImg: resolveUrl(pokemonImg),
            itemImg: resolveUrl(itemImg),
            nameType: "",       // 属性 class
            name: "",           // 宝可梦名
            item: "",           // 道具名
            lines: [],          // 其余行（保留 HTML span 结构）
        };

        // 逐行解析 pre 的 innerHTML
        const htmlContent = pre.innerHTML;
        const rawLines = htmlContent.split("\n");

        let firstLine = true;
        for (let rawLine of rawLines) {
            const text = rawLine.replace(/<[^>]+>/g, "").trim();
            if (!text) continue;

            if (firstLine) {
                // 第一行: "Charizard @ Charizardite Y"
                firstLine = false;
                // 提取属性 class
                const typeMatch = rawLine.match(/class="type-(\w+)"/);
                mon.nameType = typeMatch ? typeMatch[1] : "normal";

                if (text.includes("@")) {
                    const atIdx = text.indexOf("@");
                    mon.name = text.substring(0, atIdx).trim();
                    mon.item = text.substring(atIdx + 1).trim();
                } else {
                    mon.name = text;
                }
            } else {
                mon.lines.push({ html: rawLine, text });
            }
        }

        team.push(mon);
    }

    return { title, format, team };
}

/** 将相对 URL 转为绝对 URL */
function resolveUrl(src) {
    if (!src || src.startsWith("http")) return src;
    return POKEPAST_BASE + src;
}

// ============ 渲染翻译后的队伍 ============

/** 翻译一行内容（保留 span 标签，替换文本） */
function translateLine(line, translator) {
    const { html, text } = line;

    // 招式行: "- Heat Wave"
    if (text.startsWith("- ")) {
        const moveName = text.substring(2);
        const translated = translator.translate(moveName);
        return `<span class="type-${extractTypeClass(html)}">-</span> ${translated}`;
    }

    // Nature 行: "Timid Nature"
    if (text.endsWith("Nature")) {
        const natureName = text.replace("Nature", "").trim();
        const translated = translator.translate(natureName);
        return `${translated} 性格`;
    }

    // 带标签的行: "Ability: ...", "Tera Type: ...", "EVs: ...", "IVs: ..."
    for (const [enLabel, zhLabel] of Object.entries(LABEL_MAP)) {
        if (text.startsWith(enLabel)) {
            const valuePart = text.substring(enLabel.length).trim();

            // Tera Type: 值在 span.type-* 里
            if (enLabel === "Tera Type:") {
                const teraType = valuePart;
                const typeClass = extractTypeClass(html);
                const translated = translator.translate(teraType);
                return `<span class="attr">${zhLabel}</span><span class="type-${typeClass}">${translated}</span>  `;
            }

            // EVs / IVs: 翻译能力值缩写
            if (enLabel === "EVs:" || enLabel === "IVs:") {
                const translated = translateStats(html, translator);
                return `<span class="attr">${zhLabel}</span>${translated}`;
            }

            // Ability / Level
            const translated = translator.translate(valuePart);
            return `<span class="attr">${zhLabel}</span>${translated}  `;
        }
    }

    // 其他行原样返回
    return html;
}

/** 提取 type-xxx 的 class 名 */
function extractTypeClass(html) {
    const m = html.match(/type-(\w+)/);
    return m ? m[1] : "normal";
}

/** 翻译能力值行中的数值和缩写 */
function translateStats(html, translator) {
    // 替换 stat-xxx span 中的文本
    return html.replace(/<span class="stat-(\w+)">(.+?)<\/span>/g, (match, statClass, content) => {
        // content 如 "252 SpA" 或 "4 HP"
        const translated = content.replace(/\b(HP|Atk|Def|SpA|SpD|Spe)\b/g, (stat) => {
            return STAT_MAP[stat] || stat;
        });
        return `<span class="stat-${statClass}">${translated}</span>`;
    });
}

/** 渲染完整的队伍 HTML */
function renderTeam(teamData, translator) {
    const { title, format, team } = teamData;
    let html = "";

    // 标题（不翻译）
    if (title) {
        html += `<div class="team-title">${escapeHtml(title)}</div>`;
    }
    if (format) {
        html += `<div class="team-format">${escapeHtml(format)}</div>`;
    }

    html += '<div class="team-grid">';

    for (const mon of team) {
        const nameZh = translator.translate(mon.name);
        const itemZh = mon.item ? translator.translate(mon.item) : "";

        html += "<article>";

        // 图片
        if (mon.pokemonImg) {
            html += '<div class="img">';
            html += `<img class="img-pokemon" src="${mon.pokemonImg}" alt="${escapeHtml(nameZh)}" onerror="this.style.display='none'">`;
            if (mon.itemImg) {
                html += `<img class="img-item" src="${mon.itemImg}" alt="${escapeHtml(itemZh)}" onerror="this.style.display='none'">`;
            }
            html += "</div>";
        }

        // 文本
        html += "<pre>";
        // 第一行: 名字 + 道具
        html += `<span class="type-${mon.nameType}">${escapeHtml(nameZh)}</span>`;
        if (itemZh) {
            html += ` @ ${escapeHtml(itemZh)}  `;
        }
        html += "\n";

        // 其余行
        for (const line of mon.lines) {
            html += translateLine(line, translator) + "\n";
        }

        html += "</pre></article>";
    }

    html += "</div>";
    return html;
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ============ 主逻辑 ============

let translator = null;

async function handleTranslate() {
    const urlInput = document.getElementById("urlInput");
    const btn = document.getElementById("translateBtn");
    const status = document.getElementById("status");
    const display = document.getElementById("teamDisplay");

    const url = urlInput.value.trim();
    if (!url) {
        status.textContent = "请输入链接";
        status.className = "status error";
        return;
    }

    if (!url.includes("pokepast.es")) {
        status.textContent = "请输入有效的 PokePast 链接";
        status.className = "status error";
        return;
    }

    btn.disabled = true;
    status.textContent = "加载字典...";
    status.className = "status";

    try {
        // 首次加载字典
        if (!translator) {
            translator = new Translator();
            await translator.load();
        }

        status.textContent = "获取页面...";
        const html = await fetchPokepast(url);

        status.textContent = "解析中...";
        const teamData = parseTeam(html);

        if (teamData.team.length === 0) {
            throw new Error("未识别到队伍数据");
        }

        status.textContent = `已翻译 ${teamData.team.length} 只宝可梦`;
        display.innerHTML = renderTeam(teamData, translator);

    } catch (e) {
        status.textContent = `错误: ${e.message}`;
        status.className = "status error";
        console.error(e);
    } finally {
        btn.disabled = false;
    }
}

// 回车键触发翻译
document.getElementById("urlInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleTranslate();
});
