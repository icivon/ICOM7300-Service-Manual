# 发射功率低 / 发射无输出

> **coverage: derived** — 本文件的故障树是基于手册 §3/§9 信号链与 §1/§4 参数整理的派生知识。
> 原手册 **没有故障排查章节**。每个步骤下方给出手册原文锚点（PDF 物理页号），可回查。
> 手册 **未给出测试点正常电压/波形/允差**，本文件不包含任何电压阈值判断。见 `manual-gaps.md`。

## 发射功率低

- 识别词：发射功率低, 功率上不去, 输出功率小, low power, low tx output
- 可疑区域：PA UNIT 功放 / PA UNIT 驱动级 / RF UNIT 增益控制/YGR AMP / ALC 与功率检测 / TUNER UNIT 与天馈
- 推理依据：依据 §3-1/§3-2 发射信号链（RF 增益→驱动→功放→LPF→检波→天调）与 §4 功率调整目标值，按由外到内、由后级到前级排列；属派生推理。
- 手册未覆盖：no_dc_voltage_table, no_waveform_data, no_troubleshooting_section

### 排查步骤

1. 先排除天馈与假负载：§4 要求 50 Ω 假负载/功率计，HF 100% 档调整目标为 105 W（§4-4 原文）。
   - 证据 `p16`：(50 or 100 Ω/120 W) ｜ 位号：—
   - 证据 `p19`：105 W ｜ 位号：—

2. 沿 TX 信号链向后核对 PA UNIT：驱动级 Q121、推挽功放 Q131/Q132，§3-1 说明功放输出可达 100 W（HF/50 MHz）。
   - 证据 `p10`：and drive amplifier (Q121). These RF amplifiers are the high ｜ 位号：Q121
   - 证据 `p10`：to the push-pull power amplifier (Q131 and Q132) to be ampli- ｜ 位号：Q131, Q132

3. 核对前向/反射波检测与 ALC 环路：D961/D962 检波、IC981 缓冲后送 MAIN UNIT CPU 监控；误动作会压低驱动。
   - 证据 `p10`：The transmit signal is passed through the SWR detection cir- ｜ 位号：D961, D962, IC981
   - 证据 `p12`：The signal level is also adjusted by the ALC circuit (D1201 ｜ 位号：—

4. 核对 RF UNIT 侧增益控制（D1051/D1052）与 YGR AMP（IC1031），以及 §4-3/§4-4 的 TX IDLING / TX POWER 调整项，最后查 §10 PA UNIT 图纸。
   - 证据 `p12`：is adjusted by the gain controller (D1051 and D1052), which ｜ 位号：D1051, D1052
   - 证据 `p12`：signal is then amplified by the YGR AMP (IC1031) to obtain ｜ 位号：IC1031
   - 证据 `p19`：ADJUSTMENT ITEM TRANSCEIVER'S CONDITION OPERATION ADJUSTPOINT VALUE ｜ 位号：—


## 发射完全无输出

- 识别词：发射无输出, 不能发射, 无功率, no transmit, no tx
- 可疑区域：MIC/调制输入 / FPGA/D-A 上变频 / RF UNIT 发射链 / PA UNIT 功放与继电器 / PTT/静音控制
- 推理依据：依据 §3-3 发射信号处理与 §3-1/§3-2 发射 RF 链，沿信号流向从 MIC 到天线逐段定位；属派生推理。
- 手册未覆盖：no_dc_voltage_table, no_waveform_data, no_troubleshooting_section

### 排查步骤

1. 先核对调制输入：§3-3 说明麦克风信号经 MIC AMP（IC1002）与 A/D（IC1001）进入 DSP，ACC 输入经 IC1003 静音开关。
   - 证据 `p15`：The audio signal from the [MIC] connector on the front panel ｜ 位号：IC1001, IC1002, IC1003

2. 核对数字调制与上变频链：DSP（IC901）产生 36 kHz TX IF，FPGA（IC1351）上变频，D/A（IC1331）转模拟，经 LPF（L1281/L1282 等）送 RF UNIT。
   - 证据 `p15`：The signal is digitally modulated in the DSP (IC901), result- ｜ 位号：IC901
   - 证据 `p15`：the FPGA (IC1351), is applied to the D/A converter (IC1331) ｜ 位号：IC1331, IC1351
   - 证据 `p15`：signal is passed through the LPF (L1281, L1282, C1281, ｜ 位号：L1281

3. 核对 RF UNIT 发射通道的滤波器选择、增益控制与 YGR AMP，以及 TX/RX 切换相关二极管。
   - 证据 `p12`：The transmit signal from the MAIN UNIT is passed through ｜ 位号：D1051, D1052, IC1031
   - 证据 `p13`：TX/RX switching diode (D1231) and applied to the external ｜ 位号：D1231

4. 核对 PA UNIT 驱动/功放与 LPF 继电器选通，再按 §4-3/§4-4 检查 TX IDLING 与 TX POWER 调整菜单是否失准。
   - 证据 `p10`：fied up to 100 watts (for the HF/50 MHz band) or 50 watts (for ｜ 位号：Q121, Q131, Q132
   - 证据 `p10`：are selected by the relays on both sides of each LPF , accord- ｜ 位号：—
   - 证据 `p19`：[MAIN DIAL] 50 W ｜ 位号：—

