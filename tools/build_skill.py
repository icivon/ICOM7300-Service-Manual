"""Generate the Agent Skill (SKILL.md + progressively-loaded references).

The Skill files are generated from the SAME jsonl datasets that back the MCP
server, so the two modes can never drift. SKILL.md stays a small routing table;
the detailed troubleshooting content lives in references/ and is only loaded
when a matching symptom is asked about.

Usage: python tools/build_skill.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from common import DATA, ROOT, SECTIONS, read_jsonl, write_json

I18N = json.loads((DATA / "locale" / "icom7300.i18n.json").read_text(encoding="utf-8"))
SKILL_DIR = ROOT / "skill" / "icom-7300"
REFS = SKILL_DIR / "references"

GROUPS = {
    "power-and-display": ("供电 / 开机无显示", ["no_display"]),
    "tx-power": ("发射功率低 / 发射无输出", ["low_tx_power", "no_tx_output"]),
    "rx-and-audio": ("接收噪声 / 无接收 / 音频无声", ["rx_noise", "no_rx", "no_audio"]),
    "tuner-and-frequency": ("天调 / SWR / 频率不准", ["tuner_no_match", "frequency_unstable"]),
    "usb-and-control": ("USB / 控制接口", ["usb_not_recognized"]),
}


def esc(text: str) -> str:
    return " ".join(str(text).split())


def fault_markdown(group_title: str, faults: list[dict]) -> str:
    lines = [
        f"# {group_title}",
        "",
        "> **coverage: derived** — 本文件的故障树是基于手册 §3/§9 信号链与 §1/§4 参数整理的派生知识。",
        "> 原手册 **没有故障排查章节**。每个步骤下方给出手册原文锚点（PDF 物理页号），可回查。",
        "> 手册 **未给出测试点正常电压/波形/允差**，本文件不包含任何电压阈值判断。见 `manual-gaps.md`。",
        "",
    ]
    for f in faults:
        lines += [
            f"## {f['symptom']}",
            "",
            f"- 识别词：{', '.join(f['aliases'])}",
            f"- 可疑区域：{' / '.join(f['suspects'])}",
            f"- 推理依据：{f['reasoning_basis']}",
            f"- 手册未覆盖：{', '.join(f['manual_gaps'])}",
            "",
            "### 排查步骤",
            "",
        ]
        for st in f["steps"]:
            lines.append(f"{st['order']}. {st['action']}")
            for e in st["evidence"]:
                refs = ", ".join(e.get("refs", [])) or "—"
                lines.append(f"   - 证据 `p{e['page']}`：{esc(e['raw_text'])[:150]} ｜ 位号：{refs}")
            lines.append("")
        lines.append("")
    return "\n".join(lines)


def build_overview() -> str:
    rows = ["| 章节 | 标题 | PDF 物理页 |", "|---|---|---|"]
    for s in SECTIONS:
        rows.append(f"| {s['id']} | {s['title']} | {s['page_start']}–{s['page_end']} |")
    return "\n".join(
        [
            "# 手册结构与使用约定",
            "",
            "机型：Icom IC-7300（HF/50 MHz TRANSCEIVER），手册号 S-15218XZ-C1，2016 年 3 月版，75 页。",
            "原手册为 InDesign 导出的矢量 PDF，带完整文字层；本 Skill 只含派生的结构化数据，**不含原 PDF 页面**。",
            "",
            "## 章节页码（PDF 物理页号，非印刷页码如 10-4）",
            "",
            *rows,
            "",
            "## 数据覆盖标记（必须遵守）",
            "",
            "| 标记 | 含义 |",
            "|---|---|",
            "| `manual` | 直接来自手册文字层的原文位号/数值，附页码与原文片段 |",
            "| `derived` | 基于手册证据整理的故障树、信号链阶段顺序；不是手册原文 |",
            "| `not_in_manual` | 手册确实没有的数据，值为空，禁止用经验值填补 |",
            "",
            "## 硬性规则",
            "",
            "1. 位号精确：`Q1001` ≠ `Q1002`；`R1`、`J1` 等 362 个位号跨板复用，必须结合板名。",
            "2. 数值只引用带页码的原文；电源网络标签（`14V`/`8V`/`3R3V`）是网络名，标称值由名称推断，**不是实测电压**。",
            "3. 遇到 `not_in_manual` 项，明确回答「手册未覆盖」，不要给出电压阈值、波形或允差。",
            "4. 原理图为矢量图纸，文字层顺序混乱；位号与页码映射以 `components` 数据与 `ref_page_index.json` 为准，歧义项不做猜测性回填。",
            "",
        ]
    )


def build_signal_chain(rows: list[dict]) -> str:
    out = ["# 接收 / 发射信号链", "", "> coverage: **derived**（阶段划分与顺序），节点与位号引自 §3 CIRCUIT DESCRIPTION 原文。", ""]
    for direction, title in (("RX", "接收（天线 → 音频）"), ("TX", "发射（麦克风 → 天线）")):
        out += [f"## {title}", "", "| 序 | 阶段 | 板 | 关键位号 | 手册证据页 |", "|---|---|---|---|---|"]
        for r in [x for x in rows if x["direction"] == direction]:
            pages = ", ".join(f"p{e['page']}" for e in r["evidence"])
            out.append(f"| {r['order']} | {r['stage']} | {r['board']} | {', '.join(r['refs']) or '—'} | {pages} |")
        out += ["", f"依据：{next(x for x in rows if x['direction'] == direction)['reasoning_basis']}", ""]
    return "\n".join(out)


def build_measurements(rows: list[dict], nets: list[dict]) -> str:
    out = [
        "# 测试参数 / 电源网络 / 检查点",
        "",
        "> 所有数值均来自手册文字层并附页码；`not_in_manual` 项保持空白。",
        "",
        "## 规格与调整目标值（coverage: manual）",
        "",
        "| 类别 | 名称 | 值 | 单位 | 所属电路 | 页码 |",
        "|---|---|---|---|---|---|",
    ]
    for m in rows:
        if m["kind"] == "test_point":
            continue
        val = "" if m["value"] is None else m["value"]
        out.append(f"| {m['kind']} | {esc(m['name'])} | {val} | {m['unit'] or '—'} | {m['circuit'] or '—'} | p{m['source']['page']} |")
    out += [
        "",
        "## 电源网络标签（标称值由名称推断，不是实测值）",
        "",
        "| 网络名 | 推断标称 V | 出现页 | 说明 |",
        "|---|---|---|---|",
    ]
    for n in nets:
        out.append(f"| {n['name']} | {n['nominal_volt'] if n['nominal_volt'] is not None else '—'} | {', '.join('p'+str(p) for p in n['pages'][:6])}{'…' if len(n['pages'])>6 else ''} | {n['source'].get('note','')[:60]} |")
    out += [
        "",
        "## 检查点 CP*（coverage: not_in_manual）",
        "",
        "手册 §10 仅给出检查点位号，**没有正常电压、波形或允差**。下表 `value` 必须保持空白。",
        "",
        "| 检查点 | 出现页 | 正常电压 |",
        "|---|---|---|",
    ]
    for m in rows:
        if m["kind"] == "test_point":
            out.append(f"| {m['name']} | p{m['source']['page']} | 手册未覆盖 |")
    out.append("")
    return "\n".join(out)


def build_gaps(rows: list[dict]) -> str:
    out = [
        "# 手册未覆盖项（not_in_manual）",
        "",
        "遇到以下请求时，明确回答「手册未覆盖」，**不得用经验值、推断值或通用机型数据填补**。",
        "",
    ]
    for g in rows:
        out += [f"## {g['item']} (`{g['id']}`)", "", g["detail"], "", f"手册锚点 `p{g['source']['page']}`：{esc(g['source']['raw_text'])[:150]}", ""]
    return "\n".join(out)


def build_component_lookup() -> str:
    return "\n".join(
        [
            "# 元件位号查询指引",
            "",
            "权威位号来自 §5 PARTS LIST（p22–40），共 2797 条 `(板名, 位号)` 记录，含料号、描述、安装面与板上坐标。",
            "",
            "## 精确性规则",
            "",
            "- 使用**等值匹配**：`Q1001` 与 `Q1002` 是不同元件，禁止前缀/模糊替换。",
            "- 362 个位号跨板复用（如 `Q1001` 同时存在于 `MAIN UNIT` 与 `RF UNIT`）。查询必须带板名，或返回全部候选并提示消歧。",
            "- 位号在 §7 板图（p47–56）与 §10 原理图（p62–73）中的出现页由坐标级文字重组 + §5 白名单交叉校验得到；跨板歧义命中**不回填**，见 `data/manifest/diagram_report.json`。",
            "- §3 块图中的组合标注 `Q1212/Q1213` 在 §5 料表中未列出，已从位号索引中排除，不做猜测。",
            "",
            "## 定位三层",
            "",
            "1. **故障现象 → 区域**：按 `SKILL.md` 路由表加载对应 `references/*.md`。",
            "2. **区域 → 电路模块**：查 `signal-chain.md` 的阶段与板名，或 `references/*.md` 中的可疑区域。",
            "3. **电路 → 元件/图纸**：查位号对应板、坐标、`schematic_pages`（§10 物理页）与 `board_layout_pages`（§7 物理页）。MCP 模式用 `lookup_component` 获取带原文引用的结果。",
            "",
            "> 本 Skill 为轻量模式，不携带完整 2797 条元件表。需要精确位号检索时，请使用 MCP 模式或查阅 `data/components.jsonl`。",
            "",
        ]
    )


def build_i18n_md(faults: list[dict], gaps: list[dict]) -> str:
    """Full ZH / JA / EN reference, loaded only when a multilingual answer is needed."""
    out = [
        "# 三语对照 / 三か国語対照 / Trilingual reference (ZH / JA / EN)",
        "",
        "## 语言规则 / 言語規則 / Language rules",
        "",
        "- **ZH**：自动识别提问语言（中文 / 日文 / 英文），并用**同一种语言**组织回答。位号、料号、页码、手册原文引用保持原样不翻译。",
        "- **JA**：質問の言語（中国語／日本語／英語）を自動判別し、**同じ言語**で回答します。位番・型番・ページ番号・マニュアル原文は翻訳しません。",
        "- **EN**: Detect the question language (Chinese / Japanese / English) and answer **in that same language**. Designators, part numbers, page numbers and verbatim manual quotes are never translated.",
        "- 若无法判断，默认中文 / 判別できない場合は中国語 / Default to Chinese when undetectable.",
        "",
        "## 症状路由 / 症状ルーティング / Symptom routing",
        "",
        "| 中文 | 日本語 | English | 参考文件 |",
        "|---|---|---|---|",
    ]
    for fname, (_, ids) in GROUPS.items():
        cells = []
        for lang in ("zh", "ja", "en"):
            names = [I18N["faults"][i]["symptom"][lang] for i in ids if i in I18N["faults"]]
            cells.append(" / ".join(names))
        out.append(f"| {cells[0]} | {cells[1]} | {cells[2]} | `references/{fname}.md` |")
    out += [
        "",
        "## 故障树三语对照 / 故障ツリー三か国語 / Trilingual fault tree",
        "",
        "> 技术内容与 `data/fault_tree.jsonl` 同源；证据原文与页码见各 `references/*-*.md` 文件。",
        "",
    ]
    for f in faults:
        loc = I18N["faults"].get(f["id"])
        if not loc:
            continue
        out += [f"### `{f['id']}`", ""]
        for lang, heading in (("zh", "中文"), ("ja", "日本語"), ("en", "English")):
            out += [
                f"**{heading} — {loc['symptom'][lang]}**",
                "",
                f"- 识别词 / 認識語 / aliases: {', '.join(loc['aliases'][lang])}",
                f"- 可疑区域 / 疑わしい領域 / suspects: {' / '.join(loc['suspects'][lang])}",
                f"- 依据 / 根拠 / basis: {loc['reasoning_basis'][lang]}",
                "",
            ]
            for i, action in enumerate(loc["steps"][lang], start=1):
                out.append(f"  {i}. {action}")
            out.append("")
    out += ["## 手册未覆盖 / マニュアル未記載 / Not in manual", ""]
    for g in gaps:
        loc = I18N["gaps"].get(g["id"], {})
        out += [
            f"### `{g['id']}` — p{g['source']['page']}",
            "",
            f"- ZH: **{loc.get('item', {}).get('zh', g['item'])}** — {loc.get('detail', {}).get('zh', g['detail'])}",
            f"- JA: **{loc.get('item', {}).get('ja', g['item'])}** — {loc.get('detail', {}).get('ja', g['detail'])}",
            f"- EN: **{loc.get('item', {}).get('en', g['item'])}** — {loc.get('detail', {}).get('en', g['detail'])}",
            "",
        ]
    out += [
        "## 免责承诺 / 免責 / Disclaimer",
        "",
        f"**ZH**：{I18N['disclaimer']['zh']}",
        "",
        f"**JA**：{I18N['disclaimer']['ja']}",
        "",
        f"**EN**：{I18N['disclaimer']['en']}",
        "",
    ]
    return "\n".join(out)


def build_skill_md() -> str:
    routes = ["| 用户描述 | 加载文件 |", "|---|---|"]
    for fname, (title, ids) in GROUPS.items():
        routes.append(f"| {title} | `references/{fname}.md` |")
    routes += [
        "| 接收/发射信号链、节点顺序 | `references/signal-chain.md` |",
        "| 测试点、电压、调整目标值 | `references/measurements.md` |",
        "| 位号查询、跨板消歧、三层定位 | `references/component-lookup.md` |",
        "| 手册章节与页码、数据覆盖规则 | `references/overview.md` |",
        "| 「手册有没有 XX 数据」 | `references/manual-gaps.md` |",
        "| 日文 / 英文提问、三语症状与步骤对照 | `references/i18n.md` |",
    ]
    return "\n".join(
        [
            "---",
            "name: icom-7300",
            "description: \"Icom IC-7300 短波电台维修辅助。支持中文、日文、英文提问并自动用同一语言回答。当用户描述故障现象（开机无显示 / 送信出力が低い / low TX power、接收噪声、无接收、音频无声、天调不动作、频率不准、USB 异常等），或需要定位到电路模块、元件位号、原理图页码、测试参数时使用。提供故障现象 → 故障区域 → 元件级指引，明确标注手册未覆盖的数据。仅提供技术参考，实际故障自行判断。\"",
            "description_zh: \"IC-7300 故障现象 → 电路定位 → 元件级指引（中/日/英三语，仅技术参考）\"",
            "description_en: \"IC-7300 symptom to circuit and component-level service reference (ZH/JA/EN, reference only)\"",
            "metadata:",
            "  slug: \"icom-7300\"",
            "  displayName: \"IC-7300 维修辅助\"",
            "  version: \"1.1.0\"",
            "  summary: \"故障现象 → 电路定位 → 元件级指引（中/日/英三语）\"",
            "disable: false",
            "---",
            "",
            "# Icom IC-7300 维修辅助（Skill 模式）",
            "",
            "基于官方 Service Manual（S-15218XZ-C1，75 页）的结构化派生数据。",
            "",
            "## 语言规则（必须遵守）",
            "",
            "- 自动识别提问语言：中文 / 日文（假名或日文汉字）/ 英文，并**用同一种语言**组织回答。",
            "- 三语症状与排查步骤对照见 `references/i18n.md`；日文、英文提问时按需加载该文件。",
            "- **不翻译技术标识**：元件位号（`Q1001`）、料号、板名、页码、手册原文引用一律保持原样。",
            "- 无法判断语言时默认中文。",
            "",
            "## 使用流程",
            "",
            "1. 从用户描述中识别故障现象，按下方路由表**只加载匹配的 1–2 个参考文件**（渐进披露，勿一次读完全部）。",
            "2. 需要信号链/参数/位号细节时，再加载对应的 `signal-chain.md`、`measurements.md` 或 `component-lookup.md`。",
            "3. 回答给出：可疑区域 → 电路模块 → 关键位号与 PDF 物理页码 → 排查步骤，并标明数据来源。",
            "4. 若用户问到 `manual-gaps.md` 中的项目，明确回答「手册未覆盖」。",
            "",
            "## 路由表",
            "",
            *routes,
            "",
            "## 不可违反的约束",
            "",
            "- **不要编造测试参数**：数值只在带页码的原文中出现过才可使用；电源网络标签（`14V`、`3R3V` 等）是网络名，其标称值由名称推断，不是实测值，也不是允差。",
            "- **位号必须精确**：`Q1001` ≠ `Q1002`；跨板重名位号要指明板名。",
            "- **故障树是派生知识**：手册没有 troubleshooting 章节，回答时标明 `coverage: derived`，不要声称「手册建议」。",
            "- **缺失就说明缺失**：手册未提供元件级 DC 电压表、波形图、允差、测试点正常值，见 `references/manual-gaps.md`。",
            "",
            "## 免责承诺 / 免責 / Disclaimer",
            "",
            "- **ZH**：本 Skill 仅提供技术参考，不构成维修结论。因技术判断错误或误用造成的设备损坏、人身伤害或经济损失，提供者不承担责任；实际故障请自行判断。",
            "- **JA**：本 Skill は技術参考のみを提供し、修理上の結論を示すものではありません。判断の誤りによる損害について提供者は責任を負いません。実際の故障は利用者が自ら判断してください。",
            "- **EN**: This Skill provides technical reference only, not a repair diagnosis. The provider accepts no liability for damage or loss from incorrect judgement; the user must assess the actual fault independently.",
            "",
            "完整三语声明见 `references/i18n.md` 与 `NOTICE`。",
            "",
            "## 与 MCP 模式的区别",
            "",
            "本 Skill 是轻量离线查询，适合快速定位。需要精确位号检索（2797 条元件）、跨实体关联、带 `citations` 的可验证结果时，使用同包的 MCP Server（`mcp/server.py`）。两者由同一份 `data/*.jsonl` 生成，内容一致。",
            "",
            "> 原手册 PDF 不在分发包内（权限位禁止 modify/assemble，且版权归 Icom Inc.）。页码指向使用者自备的正版 PDF。",
            "",
        ]
    )


def main() -> int:
    REFS.mkdir(parents=True, exist_ok=True)
    faults = read_jsonl(DATA / "fault_tree.jsonl")
    chains = read_jsonl(DATA / "signal_chain.jsonl")
    meas = read_jsonl(DATA / "measurements.jsonl")
    nets = read_jsonl(DATA / "net_labels.jsonl")
    gaps = read_jsonl(DATA / "manual_gaps.jsonl")

    (SKILL_DIR / "SKILL.md").write_text(build_skill_md(), encoding="utf-8")
    by_id = {f["id"]: f for f in faults}
    written = []
    for fname, (title, ids) in GROUPS.items():
        p = REFS / f"{fname}.md"
        p.write_text(fault_markdown(title, [by_id[i] for i in ids if i in by_id]), encoding="utf-8")
        written.append(p.name)
    files = {
        "overview.md": build_overview(),
        "signal-chain.md": build_signal_chain(chains),
        "measurements.md": build_measurements(meas, nets),
        "component-lookup.md": build_component_lookup(),
        "manual-gaps.md": build_gaps(gaps),
        "i18n.md": build_i18n_md(faults, gaps),
    }
    for name, content in files.items():
        (REFS / name).write_text(content, encoding="utf-8")
        written.append(name)

    # CodeBuddy (and Agent Skills clients) only discover skills under the
    # workspace-level `.codebuddy/skills/<skill-name>/` directory. Generate a
    # byte-identical copy there so no manual installation step is needed.
    cb_skill = ROOT / ".codebuddy" / "skills" / "icom-7300"
    cb_refs = cb_skill / "references"
    cb_refs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SKILL_DIR / "SKILL.md", cb_skill / "SKILL.md")
    for p in sorted(REFS.glob("*.md")):
        shutil.copy2(p, cb_refs / p.name)
    cb_files = sorted(p.relative_to(cb_skill).as_posix() for p in cb_skill.rglob("*.md"))

    write_json(
        DATA / "manifest" / "skill_report.json",
        {
            "skill_md_bytes": (SKILL_DIR / "SKILL.md").stat().st_size,
            "references": sorted(written),
            "generated_from": ["fault_tree.jsonl", "signal_chain.jsonl", "measurements.jsonl", "net_labels.jsonl", "manual_gaps.jsonl"],
            "codebuddy_project_path": ".codebuddy/skills/icom-7300/",
            "codebuddy_files": cb_files,
            "standard": "CodeBuddy Skills / Agent Skills (SKILL.md + references/)",
        },
    )
    print(f"SKILL.md: {(SKILL_DIR / 'SKILL.md').stat().st_size} bytes")
    print(f"references: {len(written)} -> {sorted(written)}")
    print(f"CodeBuddy project skill: .codebuddy/skills/icom-7300/ ({len(cb_files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
