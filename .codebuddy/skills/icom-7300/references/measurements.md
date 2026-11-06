# 测试参数 / 电源网络 / 检查点

> 所有数值均来自手册文字层并附页码；`not_in_manual` 项保持空白。

## 规格与调整目标值（coverage: manual）

| 类别 | 名称 | 值 | 单位 | 所属电路 | 页码 |
|---|---|---|---|---|---|
| power_supply_spec | 电源要求 | 13.8 | V DC | 整机 | p4 |
| power_supply_spec | 直流电源容量 | 13.8 | V/30 A | 测试连接 | p16 |
| power_supply_spec | 频率稳定度 | 0.5 | ppm | 基准时钟 | p4 |
| power_supply_spec | AF 功放输出 | 2.5 | W | MAIN UNIT / AF | p14 |
| regulator_rail | 3.3 V REGULATOR | 3.3 | V | 电源稳压（§2 INSIDE VIEWS 标注） | p6 |
| regulator_rail | 8.0 V REGULATOR | 8.0 | V | 电源稳压（§2 INSIDE VIEWS 标注） | p6 |
| regulator_rail | 8.0 V REGULATOR | 8.0 | V | 电源稳压（§2 INSIDE VIEWS 标注） | p6 |
| regulator_rail | 3.0 V REGULATOR | 3.0 | V | 电源稳压（§2 INSIDE VIEWS 标注） | p6 |
| regulator_rail | 5.0 V REGULATOR | 5.0 | V | 电源稳压（§2 INSIDE VIEWS 标注） | p7 |
| regulator_rail | 9.0 V REGULATOR | 9.0 | V | 电源稳压（§2 INSIDE VIEWS 标注） | p8 |
| adjustment_target | TX power 100% (HF) | 105 | W | PA UNIT / TX power | p19 |
| adjustment_target | TX power 50% (HF) | 52.5 | W | PA UNIT / TX power | p19 |
| adjustment_target | TX total gain (HF) | 50 | W | PA UNIT / TX power | p19 |
| adjustment_target | TX power 10% (HF) | 12.5 | W | PA UNIT / TX power | p19 |
| adjustment_target | AM carrier power (HF) | 25 | W | PA UNIT / TX power | p19 |
| adjustment_target | TX power 1% (HF) | 2 | W | PA UNIT / TX power | p19 |
| adjustment_target | AF generator level | 30 | mVrms | MAIN UNIT / modulator | p19 |
| adjustment_target | AF generator frequency | 1.5 | kHz | MAIN UNIT / modulator | p19 |
| adjustment_target | Dummy load rating | 50 | ohm | test setup | p16 |
| adjustment_target | RF power meter range | 120 | W | test setup | p16 |
| adjustment_target | DC supply requirement | 13.8 | V | power supply | p16 |
| adjustment_target | AC millivoltmeter range | 10 | V | test setup | p16 |

## 电源网络标签（标称值由名称推断，不是实测值）

| 网络名 | 推断标称 V | 出现页 | 说明 |
|---|---|---|---|
| +3V | 3.0 | p60 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| +5V | 5.0 | p60 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| +8V | 8.0 | p60, p62 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| 1.2V | 1.2 | p63 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| 14V | 14.0 | p59, p60, p63, p65, p66, p69… | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| 1R2V | 1.2 | p63, p66, p68 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| 2.5V | 2.5 | p63 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| 2R5V | 2.5 | p60, p63, p68 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| 3R3V | 3.3 | p58, p60, p61, p62, p63, p64… | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| 5V | 5.0 | p58, p60, p61, p62, p63, p65… | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| 8V | 8.0 | p58, p59, p60, p61, p62, p63… | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| ACC8V | 8.0 | p60 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| AD5V | 5.0 | p60, p66 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| F1R2V | 1.2 | p68 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| F2R5V | 2.5 | p68 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| F3R3V | 3.3 | p68 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| F8V | 8.0 | p60, p63 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| H1R18V | 1.18 | p60, p63, p64 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| H3R3V | 3.3 | p60, p63, p64, p65 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| H4V | 4.0 | p60, p63, p65 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| HFID1V | — | p60, p63, p72 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| HFID2V | — | p60, p63, p72 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| P9V | 9.0 | p59, p72, p73 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| RFA3R3V | 3.3 | p60 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| RFD3R3V | 3.3 | p60 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| T5V | 5.0 | p59, p69 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| T9V | 9.0 | p59, p72, p73 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| USB3R3V | 3.3 | p60, p65 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |
| VDD(3R3V) | 3.3 | p58, p63 | 电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。 |

## 检查点 CP*（coverage: not_in_manual）

手册 §10 仅给出检查点位号，**没有正常电压、波形或允差**。下表 `value` 必须保持空白。

| 检查点 | 出现页 | 正常电压 |
|---|---|---|
| CP1 | p62 | 手册未覆盖 |
| CP1001 | p66 | 手册未覆盖 |
| CP121 | p63 | 手册未覆盖 |
| CP122 | p63 | 手册未覆盖 |
| CP1304 | p67 | 手册未覆盖 |
| CP1305 | p67 | 手册未覆盖 |
| CP1306 | p67 | 手册未覆盖 |
| CP1333 | p67 | 手册未覆盖 |
| CP1334 | p67 | 手册未覆盖 |
| CP1335 | p67 | 手册未覆盖 |
| CP1356 | p68 | 手册未覆盖 |
| CP1357 | p68 | 手册未覆盖 |
| CP1358 | p68 | 手册未覆盖 |
| CP1359 | p68 | 手册未覆盖 |
| CP151 | p63 | 手册未覆盖 |
| CP691 | p65 | 手册未覆盖 |
| CP692 | p65 | 手册未覆盖 |
| CP693 | p65 | 手册未覆盖 |
| CP711 | p65 | 手册未覆盖 |
| CP712 | p65 | 手册未覆盖 |
| CP741 | p65 | 手册未覆盖 |
| CP772 | p65 | 手册未覆盖 |
| CP901 | p66 | 手册未覆盖 |
| CP902 | p66 | 手册未覆盖 |
| CP971 | p66 | 手册未覆盖 |
| CP981 | p73 | 手册未覆盖 |
| CP982 | p73 | 手册未覆盖 |
