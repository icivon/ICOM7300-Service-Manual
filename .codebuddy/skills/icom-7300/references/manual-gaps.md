# 手册未覆盖项（not_in_manual）

遇到以下请求时，明确回答「手册未覆盖」，**不得用经验值、推断值或通用机型数据填补**。

## 故障现象排查表 / 故障树 (`no_troubleshooting_section`)

全册检索 trouble/symptom/fault/failure 命中 0；§1-§10 无 troubleshooting 章节。故障树由本工具基于 §3/§9 信号链派生。

手册锚点 `p3`：SECTION 1 SPECIFICATIONS

## 元件级 DC 测试点电压表 (`no_dc_voltage_table`)

§10 检查点 CP* 仅标位号或 SHORT，手册未给出任何正常电压值。

手册锚点 `p65`：SHORT

## 测试点波形 / 示波器截图 (`no_waveform_data`)

§10 原理图为静态图纸，无波形图、无时序图。

手册锚点 `p62`：To the MAIN UNIT

## 电源网络允差与实测条件 (`no_net_tolerance`)

§8-§10 仅有电源网络标签（14V/8V/5V/3R3V 等），无允差、无测量条件。

手册锚点 `p57`：14V

## 天调参考电压调整目标值 (`no_tuner_ref_voltage_value`)

§4-6 列出 TUNER REFERENCE VOLTAGE ADJUSTMENT 项目，但 VALUE 栏无具体电压数值。

手册锚点 `p21`：TUNER REFERENCE

## 逐位号的功能说明 (`no_component_function_per_ref`)

§5 提供料号/规格/坐标，未逐件标注所属功能电路；电路归属由 §3/§10 交叉定位。

手册锚点 `p25`：REF PARTS DESCRIPTION M. H/V NO. NO. LOCATION

## 全部元件的板坐标 (`no_location_for_all`)

§5 中 131 行无 LOCATION 坐标（VR/RIT/SD 等小板与机械件）。

手册锚点 `p38`：M.=Mounted side (T: Mounted on the Top side, B: Mounted on the Bottom side)

## 位号跨板复用消歧 (`ambiguous_designator_reuse`)

362 个位号在多块板上复用（如 R1、J1），查询必须结合板名；工具对跨板页命中不做猜测性回填。

手册锚点 `p22`：[MAIN UNIT]
