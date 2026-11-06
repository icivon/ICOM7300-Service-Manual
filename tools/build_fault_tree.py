"""Build the symptom -> region -> component-level troubleshooting tree.

This tree is DERIVED knowledge: the IC-7300 service manual contains no
troubleshooting section. Every step therefore cites manual evidence (page +
verbatim quote + designators from the SECTION 5 whitelist) and declares which
requested data the manual does not provide. No normal voltage, tolerance or
waveform is invented; steps say what to inspect and where the drawing is,
never "should read X V".

Usage: python tools/build_fault_tree.py
"""

from __future__ import annotations

from common import DATA, page_lines, read_jsonl, write_json, write_jsonl

WHITELIST = {c["ref"] for c in read_jsonl(DATA / "components.jsonl")}

# (id, symptom, aliases, suspects, steps, reasoning_basis, gap ids)
# step = (action, [(page, literal, [refs...])])
TREE = [
    (
        "no_display", "开机无显示 / 不通电",
        ["开机无显示", "黑屏", "不通电", "无法开机", "no display", "dead", "won't power on"],
        ["整机供电输入", "电源稳压链", "DISPLAY UNIT", "MAIN UNIT 复位与 FPGA 配置"],
        [
            ("先核对外部直流供电与保险丝：规格书要求 13.8 V DC ±15%，测试连接要求 13.8 V/30 A。手册未给出机内测试点正常电压，不要用推断阈值判断。",
             [(4, "13.8 V DC", []), (16, "13.8 V/30 A", []), (16, "Fuses", [])]),
            ("若外部供电正常，按 §2 内部视图逐级核对稳压器标注：14V/8V/5V/3R3V 等电源网络在 §8 接线图中分布于各板。",
             [(6, "3.3 V REGULATOR", []), (8, "9 V REGULATOR", []), (57, "14V", [])]),
            ("核对 DISPLAY UNIT 与 MAIN UNIT 之间的连接与显示器件：§5 给出 DS1（LCD）与 J51 等接插件位号，§7 给出板图位置。",
             [(36, "[FRONT UNIT]", ["DS1", "EP1"]), (57, "J51", ["J51"])]),
            ("若供电与连接正常，检查 MAIN UNIT 的 CPU/FPGA 上电配置链（FPGA 程序由外部 EEPROM 在开机时加载），对应 §3-3 与 §10 MAIN UNIT 图纸。",
             [(14, "external EEPROM", ["IC1351", "IC301"]), (63, "14V", [])]),
        ],
        "依据 §1 供电规格、§2 稳压器标注、§8 电源网络分布与 §3-3 FPGA 上电加载描述，按『外部供电→稳压→显示接口→数字核心』顺序排列；属派生推理。",
        ["no_dc_voltage_table", "no_net_tolerance", "no_troubleshooting_section"],
    ),
    (
        "low_tx_power", "发射功率低",
        ["发射功率低", "功率上不去", "输出功率小", "low power", "low tx output"],
        ["PA UNIT 功放", "PA UNIT 驱动级", "RF UNIT 增益控制/YGR AMP", "ALC 与功率检测", "TUNER UNIT 与天馈"],
        [
            ("先排除天馈与假负载：§4 要求 50 Ω 假负载/功率计，HF 100% 档调整目标为 105 W（§4-4 原文）。",
             [(16, "50 or 100", []), (19, "105 W", [])]),
            ("沿 TX 信号链向后核对 PA UNIT：驱动级 Q121、推挽功放 Q131/Q132，§3-1 说明功放输出可达 100 W（HF/50 MHz）。",
             [(10, "drive amplifier (Q121)", ["Q121"]), (10, "push-pull power amplifier", ["Q131", "Q132"])]),
            ("核对前向/反射波检测与 ALC 环路：D961/D962 检波、IC981 缓冲后送 MAIN UNIT CPU 监控；误动作会压低驱动。",
             [(10, "SWR detection cir", ["D961", "D962", "IC981"]), (12, "ALC circuit", [])]),
            ("核对 RF UNIT 侧增益控制（D1051/D1052）与 YGR AMP（IC1031），以及 §4-3/§4-4 的 TX IDLING / TX POWER 调整项，最后查 §10 PA UNIT 图纸。",
             [(12, "gain controller (D1051 and D1052)", ["D1051", "D1052"]), (12, "YGR AMP (IC1031)", ["IC1031"]), (19, "ADJUSTMENT ITEM", [])]),
        ],
        "依据 §3-1/§3-2 发射信号链（RF 增益→驱动→功放→LPF→检波→天调）与 §4 功率调整目标值，按由外到内、由后级到前级排列；属派生推理。",
        ["no_dc_voltage_table", "no_waveform_data", "no_troubleshooting_section"],
    ),
    (
        "no_tx_output", "发射完全无输出",
        ["发射无输出", "不能发射", "无功率", "no transmit", "no tx"],
        ["MIC/调制输入", "FPGA/D-A 上变频", "RF UNIT 发射链", "PA UNIT 功放与继电器", "PTT/静音控制"],
        [
            ("先核对调制输入：§3-3 说明麦克风信号经 MIC AMP（IC1002）与 A/D（IC1001）进入 DSP，ACC 输入经 IC1003 静音开关。",
             [(15, "MIC] connector", ["IC1001", "IC1002", "IC1003"])]),
            ("核对数字调制与上变频链：DSP（IC901）产生 36 kHz TX IF，FPGA（IC1351）上变频，D/A（IC1331）转模拟，经 LPF（L1281/L1282 等）送 RF UNIT。",
             [(15, "digitally modulated in the DSP", ["IC901"]), (15, "D/A converter (IC1331)", ["IC1331", "IC1351"]), (15, "L1281, L1282", ["L1281"])]),
            ("核对 RF UNIT 发射通道的滤波器选择、增益控制与 YGR AMP，以及 TX/RX 切换相关二极管。",
             [(12, "The transmit signal from the MAIN UNIT", ["D1051", "D1052", "IC1031"]), (13, "TX/RX switching diode", ["D1231"])]),
            ("核对 PA UNIT 驱动/功放与 LPF 继电器选通，再按 §4-3/§4-4 检查 TX IDLING 与 TX POWER 调整菜单是否失准。",
             [(10, "100 watts", ["Q121", "Q131", "Q132"]), (10, "selected by the relays", []), (19, "50 W", [])]),
        ],
        "依据 §3-3 发射信号处理与 §3-1/§3-2 发射 RF 链，沿信号流向从 MIC 到天线逐段定位；属派生推理。",
        ["no_dc_voltage_table", "no_waveform_data", "no_troubleshooting_section"],
    ),
    (
        "rx_noise", "接收有噪声 / 灵敏度低",
        ["接收有噪声", "噪声大", "灵敏度低", "收不到弱信号", "noisy receiver", "low sensitivity"],
        ["RF UNIT 前置放大与波段滤波", "MAIN UNIT 外部 AGC 与 A/D 输入", "电源纹波/接地", "天馈与天调"],
        [
            ("先隔离外部干扰与天馈：确认假负载/信号源条件符合 §4 测试连接（SSG 输出范围、50 Ω 终端）。",
             [(16, "Standard signal", []), (16, "1–120 W", [])]),
            ("核对 RX 前端的衰减器与前放：§3-2 说明衰减器 D1081~D1083 在 0–20 dB 间切换，前放 Q1211 之后进入 15 个波段滤波器。",
             [(11, "RX mute switch", ["D1001"]), (11, "0 dB (bypass) and 20 dB", ["D1081"]), (11, "preamp", ["Q1211"])]),
            ("核对 MAIN UNIT 外部 AGC 与 A/D 输入：D1231 切换、D1251 PIN 衰减、IC971 提供 AGC 电压，电平须落在 A/D 动态范围内。",
             [(13, "TX/RX switching diode", ["D1231"]), (13, "external", ["D1251", "IC971"]), (13, "A/D con", [])]),
            ("核对各板电源网络（3R3V/8V/5V 等）与稳压器标注，最后查 §10 RF/MAIN UNIT 图纸与 §7 板图定位。",
             [(57, "3R3V", []), (6, "8 V REGULATOR", []), (69, "3R3V", [])]),
        ],
        "依据 §3-2 接收信号链（衰减→滤波→前放→外部 AGC→A/D）与 Direct Sampling 系统对 A/D 输入动态范围的要求；先外部后前端、先模拟后数字；属派生推理。",
        ["no_dc_voltage_table", "no_net_tolerance", "no_troubleshooting_section"],
    ),
    (
        "no_rx", "完全无接收",
        ["无接收", "收不到信号", "静噪", "no receive", "no rx"],
        ["RX 静音开关", "RF UNIT 滤波器选通", "A/D 与 FPGA", "DSP 解调", "AF 输出级"],
        [
            ("沿 RX 链从天线端确认：§3-2 指出接收信号经 RX mute switch（D1001）与波段滤波器才到前放。",
             [(11, "RX mute switch", ["D1001"]), (11, "The received signal from the PA UNIT", [])]),
            ("核对 MAIN UNIT 的 A/D→FPGA（IC1351）→36 kHz IF 路径；§3-3 说明 FPGA 程序由外部 EEPROM 上电加载。",
             [(13, "A/D con", ["IC1351"]), (14, "external EEPROM", ["IC1351"])]),
            ("核对 DSP（IC901）解调与 D/A（IC991）之后的 AF 放大链（IC992、IC721）。",
             [(14, "DSP (IC901)", ["IC901"]), (14, "AF AMP (IC992)", ["IC991", "IC992", "IC721"])]),
            ("核对扬声器 LPF 与 speaker SW（Q746）；外接 [EXT-SP] 插入时会断开机内扬声器。",
             [(14, "L731, L732", ["L731", "L732", "C731"]), (14, "speaker SW (Q746)", ["Q746"])]),
        ],
        "依据 §3-2/§3-3 接收信号链按信号流向逐段二分；无接收与灵敏度低的区别在于优先检查静音/选通/数字核心而非前端增益；属派生推理。",
        ["no_dc_voltage_table", "no_waveform_data", "no_troubleshooting_section"],
    ),
    (
        "no_audio", "音频无声 / 扬声器不响",
        ["无声音", "音频无声", "扬声器不响", "no audio", "no sound"],
        ["D 类 AF 功放", "扬声器 LPF 与切换", "EXT-SP 插孔", "D/A 输出"],
        [
            ("先排除外接扬声器插孔与静音设置：§3-3 明确 [EXT-SP] 接入时机内扬声器被断开。",
             [(14, "EXT -SP", [])]),
            ("核对 D/A（IC991）→ AF AMP（IC992）→ D 类功放（IC721）链，§3-3 标注输出可达 2.5 W（8 Ω、1 kHz、10% 失真）。",
             [(14, "D/A converter (IC991)", ["IC991", "IC992", "IC721"]), (14, "2.5", [])]),
            ("核对扬声器 LPF（L731/L732/C731~C735）与 speaker SW（Q746）位号在 §5/§7/§10 中的位置。",
             [(14, "L731, L732", ["L731", "L732", "C731"])]),
        ],
        "依据 §3-3 AF 电路描述，按『输出接口→功放→前级→D/A』逆序定位；属派生推理。",
        ["no_dc_voltage_table", "no_waveform_data", "no_troubleshooting_section"],
    ),
    (
        "tuner_no_match", "天调不动作 / SWR 异常",
        ["天调不动作", "驻波高", "SWR 高", "调谐失败", "tuner", "high swr"],
        ["TUNER UNIT", "SWR/PWR 检测", "PA UNIT LPF 继电器", "天馈与接地"],
        [
            ("先排除天馈与负载：§4 调整程序要求 50 Ω/100 Ω 假负载与功率计，SWR 读数异常首先可能是外部负载。",
             [(16, "50 or 100", [])]),
            ("核对 SWR 检测电路：§3-1 说明 CM 耦合器与检波二极管 D961/D962 产生前向/反射波检测电压，经 IC981 缓冲送 MAIN UNIT CPU。",
             [(10, "SWR detection cir", ["D961", "D962", "IC981"])]),
            ("核对 TUNER UNIT（IC1701）与 PA UNIT 的 LPF/继电器选通；§3-1 说明 LPF 由两侧继电器按发射频率选通。",
             [(10, "selected by the relays", []), (10, "through the TUNER UNIT", ["IC1701"])]),
            ("核对 §4-6 TUNER REFERENCE VOLTAGE ADJUSTMENT 项目；注意该调整项在手册中未给出电压目标值。",
             [(21, "TUNER REFERENCE", [])]),
        ],
        "依据 §3-1 发射末级与 SWR/天调控制关系，先外部负载再检测电路再执行机构；属派生推理。",
        ["no_tuner_ref_voltage_value", "no_dc_voltage_table", "no_troubleshooting_section"],
    ),
    (
        "frequency_unstable", "频率不准 / 失谐",
        ["频率不准", "频偏", "失谐", "frequency offset", "drift"],
        ["基准时钟/TCXO", "FPGA 数字本振", "§4-6 参考频率调整"],
        [
            ("核对规格：§1 标称频率稳定度优于 ±0.5 ppm（–10°C~+60°C），测试设备要求频率精度 ±1 ppm 或更好。",
             [(4, "0.5 ppm", []), (16, "1 ppm", [])]),
            ("核对 §4-6 FREQUENCY ADJUSTMENTS 中的 REF ADJ 与 TUNER REFERENCE VOLTAGE ADJUSTMENT 调整项。",
             [(21, "REF ADJ", []), (21, "FREQUENCY ADJUSTMENTS", [])]),
            ("核对 MAIN UNIT 时钟/FPGA 相关位号在 §5 与 §10 图纸中的位置；手册未给出时钟测试点波形或电平。",
             [(14, "LO (DDS)", ["IC1351"]), (63, "14V", [])]),
        ],
        "依据 §1 频率稳定度规格、§4-6 频率调整项与 §3-3 FPGA 数字本振（DDS）描述；属派生推理。",
        ["no_waveform_data", "no_dc_voltage_table", "no_troubleshooting_section"],
    ),
    (
        "usb_not_recognized", "USB 不识别 / CI-V 异常",
        ["USB 不识别", "连不上电脑", "USB 故障", "usb", "ci-v"],
        ["USB 接口与电源网络", "MAIN UNIT USB 编解码", "连接线缆"],
        [
            ("先排除线缆与主机侧；§5 给出相关接插件位号，§8 给出整机接线与 USB 电源网络标签。",
             [(57, "J51", ["J51"]), (60, "USB3R3V", [])]),
            ("核对 USB3R3V 等电源网络在 §9 框图与 §10 MAIN UNIT 图纸中的分布。",
             [(60, "USB3R3V", []), (65, "USB3R3V", [])]),
            ("核对 MAIN UNIT 侧 USB/音频编解码相关位号在 §5 料表中的位置。",
             [(22, "[MAIN UNIT]", ["IC301"])]),
        ],
        "依据 §8/§9 接线与框图中的 USB 电源网络标注，按『线缆→供电→接口芯片』定位；属派生推理。",
        ["no_dc_voltage_table", "no_net_tolerance", "no_troubleshooting_section"],
    ),
]


def main() -> int:
    rows = []
    problems: list[str] = []
    for fid, symptom, aliases, suspects, steps, basis, gaps in TREE:
        built_steps = []
        for order, (action, ev_specs) in enumerate(steps, start=1):
            evidence = []
            for page, literal, refs in ev_specs:
                raw = next((l.strip() for l in page_lines(page) if literal in l), None)
                if raw is None:
                    problems.append(f"{fid} step{order}: missing p{page} literal {literal!r}")
                    continue
                bad = [r for r in refs if r not in WHITELIST]
                if bad:
                    problems.append(f"{fid} step{order}: refs not in whitelist {bad}")
                evidence.append(
                    {
                        "page": page,
                        "raw_text": raw,
                        "refs": [r for r in refs if r in WHITELIST],
                        "note": "手册原文锚点；步骤逻辑为派生推理。",
                    }
                )
            built_steps.append({"order": order, "action": action, "evidence": evidence})
        rows.append(
            {
                "id": fid,
                "symptom": symptom,
                "aliases": aliases,
                "suspects": suspects,
                "steps": built_steps,
                "coverage": "derived",
                "reasoning_basis": basis,
                "manual_gaps": gaps,
            }
        )
    write_jsonl(DATA / "fault_tree.jsonl", rows)
    write_json(
        DATA / "manifest" / "fault_tree_report.json",
        {"faults": len(rows), "steps": sum(len(r["steps"]) for r in rows), "evidence": sum(len(s["evidence"]) for r in rows for s in r["steps"]), "problems": problems},
    )
    print(f"faults={len(rows)} steps={sum(len(r['steps']) for r in rows)} evidence={sum(len(s['evidence']) for r in rows for s in r['steps'])}")
    print(f"problems: {len(problems)}")
    for p in problems[:25]:
        print("  ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
