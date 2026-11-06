"""Build measurements, power-net labels, signal chains and the explicit gaps list.

Every numeric value is located by literal search in the extracted page text;
if the literal is absent the record is dropped and reported, never invented.
Fault logic and stage ordering are marked `derived`; net-label nominal voltages
are marked `inferred` because the manual prints net names, not measured values.

Usage: python tools/build_knowledge.py
"""

from __future__ import annotations

import json
import re
from collections import Counter

from common import DATA, page_lines, read_jsonl, source, write_json, write_jsonl

WHITELIST = {c["ref"] for c in read_jsonl(DATA / "components.jsonl")}


def find_raw(page: int, literal: str) -> str | None:
    for line in page_lines(page):
        if literal in line:
            return line.strip()
    return None


def quote(page: int, literal: str, **extra) -> dict | None:
    raw = find_raw(page, literal)
    if raw is None:
        return None
    return source(page, raw, **extra)


# Net labels reviewed from net_label_candidates.json. "LRB551V" (a diode part
# number) and "R3V" (a fragment) are deliberately excluded.
NET_NOMINALS: dict[str, float | None] = {
    "14V": 14.0, "8V": 8.0, "5V": 5.0, "3R3V": 3.3, "H3R3V": 3.3,
    "F3R3V": 3.3, "USB3R3V": 3.3, "RFA3R3V": 3.3, "RFD3R3V": 3.3,
    "VDD(3R3V)": 3.3, "1R2V": 1.2, "F1R2V": 1.2, "1.2V": 1.2,
    "2R5V": 2.5, "F2R5V": 2.5, "2.5V": 2.5, "H1R18V": 1.18,
    "H4V": 4.0, "T5V": 5.0, "P9V": 9.0, "T9V": 9.0, "F8V": 8.0,
    "AD5V": 5.0, "ACC8V": 8.0, "+3V": 3.0, "+5V": 5.0, "+8V": 8.0,
    "HFID1V": None, "HFID2V": None,
}

# (name, literal, page, value, unit, circuit)
ADJUSTMENT_TARGETS = [
    ("TX power 100% (HF)", "105 W", 19, 105, "W", "PA UNIT / TX power"),
    ("TX power 50% (HF)", "52.5 W", 19, 52.5, "W", "PA UNIT / TX power"),
    ("TX total gain (HF)", "50 W", 19, 50, "W", "PA UNIT / TX power"),
    ("TX power 10% (HF)", "12.5 W", 19, 12.5, "W", "PA UNIT / TX power"),
    ("AM carrier power (HF)", "25 W", 19, 25, "W", "PA UNIT / TX power"),
    ("TX power 1% (HF)", "2 W", 19, 2, "W", "PA UNIT / TX power"),
    ("AF generator level", "30 mVrms", 19, 30, "mVrms", "MAIN UNIT / modulator"),
    ("AF generator frequency", "1.5 kHz", 19, 1.5, "kHz", "MAIN UNIT / modulator"),
    ("Dummy load rating", "50 or 100", 16, 50, "ohm", "test setup"),
    ("RF power meter range", "1–120 W", 16, 120, "W", "test setup"),
    ("DC supply requirement", "13.8 V/30 A", 16, 13.8, "V", "power supply"),
    ("AC millivoltmeter range", "10 mV to 10", 16, 10, "V", "test setup"),
]

GAPS = [
    ("no_troubleshooting_section", "故障现象排查表 / 故障树", 3, "SECTION", "全册检索 trouble/symptom/fault/failure 命中 0；§1-§10 无 troubleshooting 章节。故障树由本工具基于 §3/§9 信号链派生。"),
    ("no_dc_voltage_table", "元件级 DC 测试点电压表", 65, "SHORT", "§10 检查点 CP* 仅标位号或 SHORT，手册未给出任何正常电压值。"),
    ("no_waveform_data", "测试点波形 / 示波器截图", 62, "MAIN UNIT", "§10 原理图为静态图纸，无波形图、无时序图。"),
    ("no_net_tolerance", "电源网络允差与实测条件", 57, "14V", "§8-§10 仅有电源网络标签（14V/8V/5V/3R3V 等），无允差、无测量条件。"),
    ("no_tuner_ref_voltage_value", "天调参考电压调整目标值", 21, "TUNER REFERENCE", "§4-6 列出 TUNER REFERENCE VOLTAGE ADJUSTMENT 项目，但 VALUE 栏无具体电压数值。"),
    ("no_component_function_per_ref", "逐位号的功能说明", 25, "REF PARTS", "§5 提供料号/规格/坐标，未逐件标注所属功能电路；电路归属由 §3/§10 交叉定位。"),
    ("no_location_for_all", "全部元件的板坐标", 38, "M.=Mounted side", "§5 中 131 行无 LOCATION 坐标（VR/RIT/SD 等小板与机械件）。"),
    ("ambiguous_designator_reuse", "位号跨板复用消歧", 22, "[MAIN UNIT]", "362 个位号在多块板上复用（如 R1、J1），查询必须结合板名；工具对跨板页命中不做猜测性回填。"),
]

RX_STAGES = [
    ("ANT / TUNER / PA 滤波与 SWR 检测", "PA UNIT", ["D961", "D962", "IC1701", "IC981"], [(10, "SWR detection cir"), (10, "through the TUNER UNIT")]),
    ("RF UNIT 输入保护、衰减与波段滤波", "RF UNIT", ["D1001", "D1081", "Q1211", "Q1212", "Q1213"], [(11, "RX mute switch"), (11, "15"), (11, "BPFs")]),
    ("RF UNIT 前置放大后送 MAIN UNIT", "RF UNIT", ["Q1211", "Q1212", "Q1213"], [(11, "preamp"), (11, "passed to the MAIN")]),
    ("MAIN UNIT TX/RX 切换与外部 AGC 衰减", "MAIN UNIT", ["D1231", "D1251", "IC971"], [(13, "TX/RX switching diode"), (13, "external")]),
    ("A/D 转换与 FPGA 下变频为 36 kHz IF", "MAIN UNIT", ["IC1351"], [(13, "A/D con"), (13, "36 kHz IF signal"), (14, "FPGA (IC1351)")]),
    ("DSP 解调 / 降噪 / 静噪", "MAIN UNIT", ["IC901"], [(14, "DSP (IC901)"), (14, "36 kHz IF signal is digitally demodulated")]),
    ("D/A 转换与 AF 放大", "MAIN UNIT", ["IC991", "IC992", "IC721"], [(14, "D/A converter (IC991)"), (14, "AF AMP (IC992)")]),
    ("扬声器 LPF / 切换输出", "MAIN UNIT", ["L731", "L732", "C731", "Q746"], [(14, "L731, L732"), (14, "speaker SW (Q746)")]),
]

TX_STAGES = [
    ("MIC / ACC 输入、MIC AMP 与 A/D 转换", "MAIN UNIT", ["IC1001", "IC1002", "IC1003"], [(15, "MIC] connector"), (15, "A/D converter (IC1001)")]),
    ("DSP 调制为 36 kHz TX IF", "MAIN UNIT", ["IC901"], [(15, "digitally modulated in the DSP"), (15, "36 kHz transmit IF")]),
    ("FPGA 上变频与 D/A 转换", "MAIN UNIT", ["IC1351", "IC1331"], [(15, "FPGA (IC1351)"), (15, "D/A converter (IC1331)")]),
    ("TX LPF 后送 RF UNIT", "MAIN UNIT", ["L1281", "L1282", "C1281"], [(15, "L1281, L1282")]),
    ("RF UNIT 波段滤波、增益控制与 YGR AMP", "RF UNIT", ["D1051", "D1052", "IC1031"], [(12, "gain controller (D1051 and D1052)"), (12, "YGR AMP (IC1031)")]),
    ("PA UNIT 驱动放大与推挽功放", "PA UNIT", ["Q121", "Q131", "Q132", "Q1411"], [(10, "drive amplifier (Q121)"), (10, "push-pull power amplifier")]),
    ("PA UNIT LPF 与前向/反射波检测", "PA UNIT", ["D961", "D962", "IC981"], [(10, "LPF"), (10, "SWR detection cir")]),
    ("TUNER UNIT 至天线", "TUNER UNIT", ["IC1701"], [(10, "through the TUNER UNIT")]),
]


def build_net_labels() -> tuple[list[dict], list[str]]:
    path = DATA / "manifest" / "net_label_candidates.json"
    candidates = json.loads(path.read_text(encoding="utf-8"))["candidates"]
    rows, missing = [], []
    for name, meta in sorted(candidates.items()):
        if name not in NET_NOMINALS:
            continue  # reviewed out: part number / fragment
        page = meta["pages"][0]
        raw = find_raw(page, name) or meta["raw_text"]
        rows.append(
            {
                "name": name,
                "nominal_volt": NET_NOMINALS[name],
                "nominal_is_inferred": True,
                "pages": meta["pages"],
                "coverage": "manual",
                "source": source(
                    page,
                    raw,
                    note="电源/信号网络标签（net label）。标称电压由网络名推断；手册未给出实测值、允差或测量条件。",
                ),
            }
        )
    dropped = sorted(set(candidates) - set(NET_NOMINALS))
    write_json(
        DATA / "manifest" / "net_label_review.json",
        {
            "reviewed_out": dropped,
            "reason": "LRB551V 为二极管型号，R3V 为文字层碎片；其余候选均带 nominal_is_inferred 标记。",
            "candidate_count": len(candidates),
            "accepted_count": len(rows),
        },
    )
    return rows, missing


def build_measurements() -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    missing: list[str] = []

    def add(kind, name, value, unit, page, literal, circuit=None, note=""):
        s = quote(page, literal)
        if s is None:
            missing.append(f"{kind}:{name}:p{page}:{literal}")
            return
        rows.append(
            {
                "id": f"{kind}:{name}",
                "kind": kind,
                "name": name,
                "value": value,
                "unit": unit,
                "normal_voltage": None,
                "circuit": circuit,
                "coverage": "manual",
                "source": s,
                "note": note,
            }
        )

    add("power_supply_spec", "电源要求", 13.8, "V DC", 4, "13.8 V DC", "整机", "规格书标注 ±15%。")
    add("power_supply_spec", "直流电源容量", 13.8, "V/30 A", 16, "13.8 V/30 A", "测试连接")
    add("power_supply_spec", "频率稳定度", 0.5, "ppm", 4, "0.5 ppm", "基准时钟")
    add("power_supply_spec", "AF 功放输出", 2.5, "W", 14, "2.5", "MAIN UNIT / AF")

    # Regulator rails printed on the INSIDE VIEWS sheets (p6-9).
    rail_re = re.compile(r"(\d+(?:\.\d+)?)\s*V\s+REGULATOR", re.I)
    rail_seen: Counter = Counter()
    for page in range(6, 10):
        for line in page_lines(page):
            m = rail_re.search(line)
            if not m:
                continue
            val = float(m.group(1))
            rail_seen[(page, val)] += 1
            rows.append(
                {
                    "id": f"regulator_rail:p{page}:{val}V:{rail_seen[(page, val)]}",
                    "kind": "regulator_rail",
                    "name": f"{val} V REGULATOR",
                    "value": val,
                    "unit": "V",
                    "normal_voltage": None,
                    "circuit": "电源稳压（§2 INSIDE VIEWS 标注）",
                    "coverage": "manual",
                    "source": source(page, line.strip(), note="整机内部视图上的稳压器标注，非测试点实测值。"),
                }
            )

    for name, literal, page, value, unit, circuit in ADJUSTMENT_TARGETS:
        add(
            "adjustment_target", name, value, unit, page, literal, circuit,
            "§4 ADJUSTMENT PROCEDURE 的调整/测试条件目标值；需结合该页完整表格阅读。",
        )

    # Check points: the manual lists the designator but gives no normal voltage.
    cp = json.loads((DATA / "manifest" / "check_points.json").read_text(encoding="utf-8"))["check_points"]
    for name, meta in sorted(cp.items()):
        page = meta["pages"][0]
        rows.append(
            {
                "id": f"test_point:{name}",
                "kind": "test_point",
                "name": name,
                "value": None,
                "unit": None,
                "normal_voltage": None,
                "circuit": None,
                "coverage": "not_in_manual",
                "source": source(
                    page,
                    meta["raw_text"],
                    note="检查点位号由 pdfplumber 词级重组取得；手册未给出正常电压或波形。",
                ),
                "note": "手册未覆盖：无正常电压/波形/允差。不得填入推断值。",
            }
        )
    return rows, missing


def build_signal_chain() -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    dropped_refs: list[dict] = []
    for direction, stages in (("RX", RX_STAGES), ("TX", TX_STAGES)):
        for order, (stage, board, refs, ev_specs) in enumerate(stages, start=1):
            evidence, missing_ev = [], []
            for page, literal in ev_specs:
                q = quote(page, literal, note="§3 CIRCUIT DESCRIPTION 原文片段")
                if q is None:
                    missing_ev.append(f"p{page}:{literal}")
                else:
                    evidence.append(q)
            valid_refs = [r for r in refs if r in WHITELIST]
            for r in refs:
                if r not in WHITELIST:
                    dropped_refs.append({"direction": direction, "order": order, "ref": r, "reason": "not in SECTION 5 parts list"})
            rows.append(
                {
                    "direction": direction,
                    "order": order,
                    "stage": stage,
                    "board": board,
                    "refs": valid_refs,
                    "coverage": "derived",
                    "evidence": evidence,
                    "reasoning_basis": "阶段划分与顺序由 §3 电路描述文字整理；节点与位号引自手册原文。",
                    "missing_evidence": missing_ev,
                }
            )
    write_json(DATA / "manifest" / "signal_chain_report.json", {"dropped_refs": dropped_refs, "missing_evidence": [e for r in rows for e in r["missing_evidence"]]})
    return rows, []


def build_gaps() -> tuple[list[dict], list[str]]:
    rows, missing = [], []
    for gid, name, page, literal, detail in GAPS:
        raw = find_raw(page, literal)
        if raw is None:
            missing.append(f"gap:{gid}:p{page}:{literal}")
            continue
        rows.append(
            {
                "id": gid,
                "item": name,
                "detail": detail,
                "coverage": "not_in_manual",
                "source": source(page, raw, note="该行是手册中最接近的锚点原文；缺失结论来自全册文字层检索。"),
            }
        )
    return rows, missing


def main() -> int:
    net, m1 = build_net_labels()
    meas, m2 = build_measurements()
    chain, m3 = build_signal_chain()
    gaps, m4 = build_gaps()
    write_jsonl(DATA / "net_labels.jsonl", net)
    write_jsonl(DATA / "measurements.jsonl", meas)
    write_jsonl(DATA / "signal_chain.jsonl", chain)
    write_jsonl(DATA / "manual_gaps.jsonl", gaps)
    all_missing = m1 + m2 + m3 + m4
    write_json(DATA / "manifest" / "knowledge_report.json", {"missing_literals": all_missing, "counts": {"net_labels": len(net), "measurements": len(meas), "signal_nodes": len(chain), "manual_gaps": len(gaps)}})
    print(f"net_labels={len(net)} measurements={len(meas)} signal_nodes={len(chain)} manual_gaps={len(gaps)}")
    print(f"missing literals (records dropped, never invented): {len(all_missing)}")
    for m in all_missing[:20]:
        print("  MISSING", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
