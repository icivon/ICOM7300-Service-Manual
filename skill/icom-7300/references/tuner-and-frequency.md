# 天调 / SWR / 频率不准

> **coverage: derived** — 本文件的故障树是基于手册 §3/§9 信号链与 §1/§4 参数整理的派生知识。
> 原手册 **没有故障排查章节**。每个步骤下方给出手册原文锚点（PDF 物理页号），可回查。
> 手册 **未给出测试点正常电压/波形/允差**，本文件不包含任何电压阈值判断。见 `manual-gaps.md`。

## 天调不动作 / SWR 异常

- 识别词：天调不动作, 驻波高, SWR 高, 调谐失败, tuner, high swr
- 可疑区域：TUNER UNIT / SWR/PWR 检测 / PA UNIT LPF 继电器 / 天馈与接地
- 推理依据：依据 §3-1 发射末级与 SWR/天调控制关系，先外部负载再检测电路再执行机构；属派生推理。
- 手册未覆盖：no_tuner_ref_voltage_value, no_dc_voltage_table, no_troubleshooting_section

### 排查步骤

1. 先排除天馈与负载：§4 调整程序要求 50 Ω/100 Ω 假负载与功率计，SWR 读数异常首先可能是外部负载。
   - 证据 `p16`：(50 or 100 Ω/120 W) ｜ 位号：—

2. 核对 SWR 检测电路：§3-1 说明 CM 耦合器与检波二极管 D961/D962 产生前向/反射波检测电压，经 IC981 缓冲送 MAIN UNIT CPU。
   - 证据 `p10`：The transmit signal is passed through the SWR detection cir- ｜ 位号：D961, D962, IC981

3. 核对 TUNER UNIT（IC1701）与 PA UNIT 的 LPF/继电器选通；§3-1 说明 LPF 由两侧继电器按发射频率选通。
   - 证据 `p10`：are selected by the relays on both sides of each LPF , accord- ｜ 位号：—
   - 证据 `p10`：through the TUNER UNIT. ｜ 位号：IC1701

4. 核对 §4-6 TUNER REFERENCE VOLTAGE ADJUSTMENT 项目；注意该调整项在手册中未给出电压目标值。
   - 证据 `p21`：TUNER REFERENCE ｜ 位号：—


## 频率不准 / 失谐

- 识别词：频率不准, 频偏, 失谐, frequency offset, drift
- 可疑区域：基准时钟/TCXO / FPGA 数字本振 / §4-6 参考频率调整
- 推理依据：依据 §1 频率稳定度规格、§4-6 频率调整项与 §3-3 FPGA 数字本振（DDS）描述；属派生推理。
- 手册未覆盖：no_waveform_data, no_dc_voltage_table, no_troubleshooting_section

### 排查步骤

1. 核对规格：§1 标称频率稳定度优于 ±0.5 ppm（–10°C~+60°C），测试设备要求频率精度 ±1 ppm 或更好。
   - 证据 `p4`：Less than ±0.5 ppm (–10°C to +60°C, +14°F to +140°F) ｜ 位号：—
   - 证据 `p16`：±1 ppm or better ｜ 位号：—

2. 核对 §4-6 FREQUENCY ADJUSTMENTS 中的 REF ADJ 与 TUNER REFERENCE VOLTAGE ADJUSTMENT 调整项。
   - 证据 `p21`：(Enters to the [TUNER/REF ADJ.] menu.) ｜ 位号：—
   - 证据 `p21`：4-6 FREQUENCY ADJUSTMENTS ｜ 位号：—

3. 核对 MAIN UNIT 时钟/FPGA 相关位号在 §5 与 §10 图纸中的位置；手册未给出时钟测试点波形或电平。
   - 证据 `p14`：LO (DDS) ｜ 位号：IC1351
   - 证据 `p63`：14V ｜ 位号：—

