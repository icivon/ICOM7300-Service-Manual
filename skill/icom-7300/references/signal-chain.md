# 接收 / 发射信号链

> coverage: **derived**（阶段划分与顺序），节点与位号引自 §3 CIRCUIT DESCRIPTION 原文。

## 接收（天线 → 音频）

| 序 | 阶段 | 板 | 关键位号 | 手册证据页 |
|---|---|---|---|---|
| 1 | ANT / TUNER / PA 滤波与 SWR 检测 | PA UNIT | D961, D962, IC1701, IC981 | p10, p10 |
| 2 | RF UNIT 输入保护、衰减与波段滤波 | RF UNIT | D1001, D1081, Q1211 | p11, p11, p11 |
| 3 | RF UNIT 前置放大后送 MAIN UNIT | RF UNIT | Q1211 | p11, p11 |
| 4 | MAIN UNIT TX/RX 切换与外部 AGC 衰减 | MAIN UNIT | D1231, D1251, IC971 | p13, p13 |
| 5 | A/D 转换与 FPGA 下变频为 36 kHz IF | MAIN UNIT | IC1351 | p13, p13, p14 |
| 6 | DSP 解调 / 降噪 / 静噪 | MAIN UNIT | IC901 | p14, p14 |
| 7 | D/A 转换与 AF 放大 | MAIN UNIT | IC991, IC992, IC721 | p14, p14 |
| 8 | 扬声器 LPF / 切换输出 | MAIN UNIT | L731, L732, C731, Q746 | p14, p14 |

依据：阶段划分与顺序由 §3 电路描述文字整理；节点与位号引自手册原文。

## 发射（麦克风 → 天线）

| 序 | 阶段 | 板 | 关键位号 | 手册证据页 |
|---|---|---|---|---|
| 1 | MIC / ACC 输入、MIC AMP 与 A/D 转换 | MAIN UNIT | IC1001, IC1002, IC1003 | p15, p15 |
| 2 | DSP 调制为 36 kHz TX IF | MAIN UNIT | IC901 | p15, p15 |
| 3 | FPGA 上变频与 D/A 转换 | MAIN UNIT | IC1351, IC1331 | p15, p15 |
| 4 | TX LPF 后送 RF UNIT | MAIN UNIT | L1281, L1282, C1281 | p15 |
| 5 | RF UNIT 波段滤波、增益控制与 YGR AMP | RF UNIT | D1051, D1052, IC1031 | p12, p12 |
| 6 | PA UNIT 驱动放大与推挽功放 | PA UNIT | Q121, Q131, Q132, Q1411 | p10, p10 |
| 7 | PA UNIT LPF 与前向/反射波检测 | PA UNIT | D961, D962, IC981 | p10, p10 |
| 8 | TUNER UNIT 至天线 | TUNER UNIT | IC1701 | p10 |

依据：阶段划分与顺序由 §3 电路描述文字整理；节点与位号引自手册原文。
