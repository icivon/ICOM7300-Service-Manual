# 手册结构与使用约定

机型：Icom IC-7300（HF/50 MHz TRANSCEIVER），手册号 S-15218XZ-C1，2016 年 3 月版，75 页。
原手册为 InDesign 导出的矢量 PDF，带完整文字层；本 Skill 只含派生的结构化数据，**不含原 PDF 页面**。

## 章节页码（PDF 物理页号，非印刷页码如 10-4）

| 章节 | 标题 | PDF 物理页 |
|---|---|---|
| front | FRONT COVER / INTRODUCTION / TOC | 1–3 |
| 1 | SPECIFICATIONS | 4–5 |
| 2 | INSIDE VIEWS | 6–9 |
| 3 | CIRCUIT DESCRIPTION | 10–15 |
| 4 | ADJUSTMENT PROCEDURE | 16–21 |
| 5 | PARTS LIST | 22–40 |
| 6 | MECHANICAL PARTS | 41–46 |
| 7 | BOARD LAYOUTS | 47–56 |
| 8 | GENERAL WIRING | 57–58 |
| 9 | BLOCK DIAGRAM | 59–61 |
| 10 | SCHEMATIC DIAGRAM | 62–73 |
| back | ADDRESS / BACK COVER | 74–75 |

## 数据覆盖标记（必须遵守）

| 标记 | 含义 |
|---|---|
| `manual` | 直接来自手册文字层的原文位号/数值，附页码与原文片段 |
| `derived` | 基于手册证据整理的故障树、信号链阶段顺序；不是手册原文 |
| `not_in_manual` | 手册确实没有的数据，值为空，禁止用经验值填补 |

## 硬性规则

1. 位号精确：`Q1001` ≠ `Q1002`；`R1`、`J1` 等 362 个位号跨板复用，必须结合板名。
2. 数值只引用带页码的原文；电源网络标签（`14V`/`8V`/`3R3V`）是网络名，标称值由名称推断，**不是实测电压**。
3. 遇到 `not_in_manual` 项，明确回答「手册未覆盖」，不要给出电压阈值、波形或允差。
4. 原理图为矢量图纸，文字层顺序混乱；位号与页码映射以 `components` 数据与 `ref_page_index.json` 为准，歧义项不做猜测性回填。
