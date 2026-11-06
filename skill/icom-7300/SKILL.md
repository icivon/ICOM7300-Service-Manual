---
name: icom-7300
description: "Icom IC-7300 短波电台维修辅助。支持中文、日文、英文提问并自动用同一语言回答。当用户描述故障现象（开机无显示 / 送信出力が低い / low TX power、接收噪声、无接收、音频无声、天调不动作、频率不准、USB 异常等），或需要定位到电路模块、元件位号、原理图页码、测试参数时使用。提供故障现象 → 故障区域 → 元件级指引，明确标注手册未覆盖的数据。仅提供技术参考，实际故障自行判断。"
description_zh: "IC-7300 故障现象 → 电路定位 → 元件级指引（中/日/英三语，仅技术参考）"
description_en: "IC-7300 symptom to circuit and component-level service reference (ZH/JA/EN, reference only)"
metadata:
  slug: "icom-7300"
  displayName: "IC-7300 维修辅助"
  version: "1.1.0"
  summary: "故障现象 → 电路定位 → 元件级指引（中/日/英三语）"
disable: false
---

# Icom IC-7300 维修辅助（Skill 模式）

基于官方 Service Manual（S-15218XZ-C1，75 页）的结构化派生数据。

## 语言规则（必须遵守）

- 自动识别提问语言：中文 / 日文（假名或日文汉字）/ 英文，并**用同一种语言**组织回答。
- 三语症状与排查步骤对照见 `references/i18n.md`；日文、英文提问时按需加载该文件。
- **不翻译技术标识**：元件位号（`Q1001`）、料号、板名、页码、手册原文引用一律保持原样。
- 无法判断语言时默认中文。

## 使用流程

1. 从用户描述中识别故障现象，按下方路由表**只加载匹配的 1–2 个参考文件**（渐进披露，勿一次读完全部）。
2. 需要信号链/参数/位号细节时，再加载对应的 `signal-chain.md`、`measurements.md` 或 `component-lookup.md`。
3. 回答给出：可疑区域 → 电路模块 → 关键位号与 PDF 物理页码 → 排查步骤，并标明数据来源。
4. 若用户问到 `manual-gaps.md` 中的项目，明确回答「手册未覆盖」。

## 路由表

| 用户描述 | 加载文件 |
|---|---|
| 供电 / 开机无显示 | `references/power-and-display.md` |
| 发射功率低 / 发射无输出 | `references/tx-power.md` |
| 接收噪声 / 无接收 / 音频无声 | `references/rx-and-audio.md` |
| 天调 / SWR / 频率不准 | `references/tuner-and-frequency.md` |
| USB / 控制接口 | `references/usb-and-control.md` |
| 接收/发射信号链、节点顺序 | `references/signal-chain.md` |
| 测试点、电压、调整目标值 | `references/measurements.md` |
| 位号查询、跨板消歧、三层定位 | `references/component-lookup.md` |
| 手册章节与页码、数据覆盖规则 | `references/overview.md` |
| 「手册有没有 XX 数据」 | `references/manual-gaps.md` |
| 日文 / 英文提问、三语症状与步骤对照 | `references/i18n.md` |

## 不可违反的约束

- **不要编造测试参数**：数值只在带页码的原文中出现过才可使用；电源网络标签（`14V`、`3R3V` 等）是网络名，其标称值由名称推断，不是实测值，也不是允差。
- **位号必须精确**：`Q1001` ≠ `Q1002`；跨板重名位号要指明板名。
- **故障树是派生知识**：手册没有 troubleshooting 章节，回答时标明 `coverage: derived`，不要声称「手册建议」。
- **缺失就说明缺失**：手册未提供元件级 DC 电压表、波形图、允差、测试点正常值，见 `references/manual-gaps.md`。

## 免责承诺 / 免責 / Disclaimer

- **ZH**：本 Skill 仅提供技术参考，不构成维修结论。因技术判断错误或误用造成的设备损坏、人身伤害或经济损失，提供者不承担责任；实际故障请自行判断。
- **JA**：本 Skill は技術参考のみを提供し、修理上の結論を示すものではありません。判断の誤りによる損害について提供者は責任を負いません。実際の故障は利用者が自ら判断してください。
- **EN**: This Skill provides technical reference only, not a repair diagnosis. The provider accepts no liability for damage or loss from incorrect judgement; the user must assess the actual fault independently.

完整三语声明见 `references/i18n.md` 与 `NOTICE`。

## 与 MCP 模式的区别

本 Skill 是轻量离线查询，适合快速定位。需要精确位号检索（2797 条元件）、跨实体关联、带 `citations` 的可验证结果时，使用同包的 MCP Server（`mcp/server.py`）。两者由同一份 `data/*.jsonl` 生成，内容一致。

> 原手册 PDF 不在分发包内（权限位禁止 modify/assemble，且版权归 Icom Inc.）。页码指向使用者自备的正版 PDF。
