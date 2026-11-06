# 供电 / 开机无显示

> **coverage: derived** — 本文件的故障树是基于手册 §3/§9 信号链与 §1/§4 参数整理的派生知识。
> 原手册 **没有故障排查章节**。每个步骤下方给出手册原文锚点（PDF 物理页号），可回查。
> 手册 **未给出测试点正常电压/波形/允差**，本文件不包含任何电压阈值判断。见 `manual-gaps.md`。

## 开机无显示 / 不通电

- 识别词：开机无显示, 黑屏, 不通电, 无法开机, no display, dead, won't power on
- 可疑区域：整机供电输入 / 电源稳压链 / DISPLAY UNIT / MAIN UNIT 复位与 FPGA 配置
- 推理依据：依据 §1 供电规格、§2 稳压器标注、§8 电源网络分布与 §3-3 FPGA 上电加载描述，按『外部供电→稳压→显示接口→数字核心』顺序排列；属派生推理。
- 手册未覆盖：no_dc_voltage_table, no_net_tolerance, no_troubleshooting_section

### 排查步骤

1. 先核对外部直流供电与保险丝：规格书要求 13.8 V DC ±15%，测试连接要求 13.8 V/30 A。手册未给出机内测试点正常电压，不要用推断阈值判断。
   - 证据 `p4`：13.8 V DC (±15%) ｜ 位号：—
   - 证据 `p16`：(13.8 V/30 A) ｜ 位号：—
   - 证据 `p16`：Fuses ｜ 位号：—

2. 若外部供电正常，按 §2 内部视图逐级核对稳压器标注：14V/8V/5V/3R3V 等电源网络在 §8 接线图中分布于各板。
   - 证据 `p6`：3.3 V REGULATOR ｜ 位号：—
   - 证据 `p8`：9 V REGULATOR ｜ 位号：—
   - 证据 `p57`：14V ｜ 位号：—

3. 核对 DISPLAY UNIT 与 MAIN UNIT 之间的连接与显示器件：§5 给出 DS1（LCD）与 J51 等接插件位号，§7 给出板图位置。
   - 证据 `p36`：[FRONT UNIT] ｜ 位号：DS1, EP1
   - 证据 `p57`：J51 ｜ 位号：J51

4. 若供电与连接正常，检查 MAIN UNIT 的 CPU/FPGA 上电配置链（FPGA 程序由外部 EEPROM 在开机时加载），对应 §3-3 与 §10 MAIN UNIT 图纸。
   - 证据 `p14`：external EEPROM, and loaded when the transceiver power is ｜ 位号：IC1351, IC301
   - 证据 `p63`：14V ｜ 位号：—

