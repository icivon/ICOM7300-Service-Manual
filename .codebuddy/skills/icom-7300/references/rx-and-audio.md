# 接收噪声 / 无接收 / 音频无声

> **coverage: derived** — 本文件的故障树是基于手册 §3/§9 信号链与 §1/§4 参数整理的派生知识。
> 原手册 **没有故障排查章节**。每个步骤下方给出手册原文锚点（PDF 物理页号），可回查。
> 手册 **未给出测试点正常电压/波形/允差**，本文件不包含任何电压阈值判断。见 `manual-gaps.md`。

## 接收有噪声 / 灵敏度低

- 识别词：接收有噪声, 噪声大, 灵敏度低, 收不到弱信号, noisy receiver, low sensitivity
- 可疑区域：RF UNIT 前置放大与波段滤波 / MAIN UNIT 外部 AGC 与 A/D 输入 / 电源纹波/接地 / 天馈与天调
- 推理依据：依据 §3-2 接收信号链（衰减→滤波→前放→外部 AGC→A/D）与 Direct Sampling 系统对 A/D 输入动态范围的要求；先外部后前端、先模拟后数字；属派生推理。
- 手册未覆盖：no_dc_voltage_table, no_net_tolerance, no_troubleshooting_section

### 排查步骤

1. 先隔离外部干扰与天馈：确认假负载/信号源条件符合 §4 测试连接（SSG 输出范围、50 Ω 终端）。
   - 证据 `p16`：Standard signal ｜ 位号：—
   - 证据 `p16`：Measuring range: 1–120 WFrequency range: 0.1–60 MHz ｜ 位号：—

2. 核对 RX 前端的衰减器与前放：§3-2 说明衰减器 D1081~D1083 在 0–20 dB 间切换，前放 Q1211 之后进入 15 个波段滤波器。
   - 证据 `p11`：the RX mute switch (D1001), passes through or bypasses ｜ 位号：D1001
   - 证据 `p11`：tenuation level to between 0 dB (bypass) and 20 dB. ｜ 位号：D1081
   - 证据 `p11`：UNIT through the attenuator, ﬁ lter, and preamp. ｜ 位号：Q1211

3. 核对 MAIN UNIT 外部 AGC 与 A/D 输入：D1231 切换、D1251 PIN 衰减、IC971 提供 AGC 电压，电平须落在 A/D 动态范围内。
   - 证据 `p13`：TX/RX switching diode (D1231) and applied to the external ｜ 位号：D1231
   - 证据 `p13`：TX/RX switching diode (D1231) and applied to the external ｜ 位号：D1251, IC971
   - 证据 `p13`：A/D converter. The digital signal is then converted into the 36 ｜ 位号：—

4. 核对各板电源网络（3R3V/8V/5V 等）与稳压器标注，最后查 §10 RF/MAIN UNIT 图纸与 §7 板图定位。
   - 证据 `p57`：3R3V ｜ 位号：—
   - 证据 `p6`：8 V REGULATOR ｜ 位号：—
   - 证据 `p69`：3R3V ｜ 位号：—


## 完全无接收

- 识别词：无接收, 收不到信号, 静噪, no receive, no rx
- 可疑区域：RX 静音开关 / RF UNIT 滤波器选通 / A/D 与 FPGA / DSP 解调 / AF 输出级
- 推理依据：依据 §3-2/§3-3 接收信号链按信号流向逐段二分；无接收与灵敏度低的区别在于优先检查静音/选通/数字核心而非前端增益；属派生推理。
- 手册未覆盖：no_dc_voltage_table, no_waveform_data, no_troubleshooting_section

### 排查步骤

1. 沿 RX 链从天线端确认：§3-2 指出接收信号经 RX mute switch（D1001）与波段滤波器才到前放。
   - 证据 `p11`：the RX mute switch (D1001), passes through or bypasses ｜ 位号：D1001
   - 证据 `p11`：The received signal from the PA UNIT is passed to the MAIN ｜ 位号：—

2. 核对 MAIN UNIT 的 A/D→FPGA（IC1351）→36 kHz IF 路径；§3-3 说明 FPGA 程序由外部 EEPROM 上电加载。
   - 证据 `p13`：A/D converter. The digital signal is then converted into the 36 ｜ 位号：IC1351
   - 证据 `p14`：external EEPROM, and loaded when the transceiver power is ｜ 位号：IC1351

3. 核对 DSP（IC901）解调与 D/A（IC991）之后的 AF 放大链（IC992、IC721）。
   - 证据 `p14`：The processed signal is applied to the DSP (IC901). ｜ 位号：IC901
   - 证据 `p14`：The AF signal is ampliﬁ ed by the AF AMP (IC992), and then ｜ 位号：IC991, IC992, IC721

4. 核对扬声器 LPF 与 speaker SW（Q746）；外接 [EXT-SP] 插入时会断开机内扬声器。
   - 证据 `p14`：(L731, L732 and C731 ~ C735), which attenuates unwanted ｜ 位号：L731, L732, C731
   - 证据 `p14`：frequency components, and to the speaker SW (Q746). ｜ 位号：Q746


## 音频无声 / 扬声器不响

- 识别词：无声音, 音频无声, 扬声器不响, no audio, no sound
- 可疑区域：D 类 AF 功放 / 扬声器 LPF 与切换 / EXT-SP 插孔 / D/A 输出
- 推理依据：依据 §3-3 AF 电路描述，按『输出接口→功放→前级→D/A』逆序定位；属派生推理。
- 手册未覆盖：no_dc_voltage_table, no_waveform_data, no_troubleshooting_section

### 排查步骤

1. 先排除外接扬声器插孔与静音设置：§3-3 明确 [EXT-SP] 接入时机内扬声器被断开。
   - 证据 `p14`：When an external speaker is connected to the [EXT -SP] jack, ｜ 位号：—

2. 核对 D/A（IC991）→ AF AMP（IC992）→ D 类功放（IC721）链，§3-3 标注输出可达 2.5 W（8 Ω、1 kHz、10% 失真）。
   - 证据 `p14`：is applied to the D/A converter (IC991) to be converted into ｜ 位号：IC991, IC992, IC721
   - 证据 `p14`：by the D-class AF power AMP (IC721) to obtain up to 2.5 ｜ 位号：—

3. 核对扬声器 LPF（L731/L732/C731~C735）与 speaker SW（Q746）位号在 §5/§7/§10 中的位置。
   - 证据 `p14`：(L731, L732 and C731 ~ C735), which attenuates unwanted ｜ 位号：L731, L732, C731

