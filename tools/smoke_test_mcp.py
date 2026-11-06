"""End-to-end smoke test for the MCP server over real stdio JSON-RPC.

Covers the handshake, exact designator lookup, citations, data-integrity
rules, and ZH / JA / EN automatic language matching.

Usage: python tools/smoke_test_mcp.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "mcp" / "server.py"


class Client:
    def __init__(self, server_path: Path | None = None) -> None:
        self.p = subprocess.Popen(
            [sys.executable, str(server_path or SERVER)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.n = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.n += 1
        msg = {"jsonrpc": "2.0", "id": self.n, "method": method}
        if params:
            msg["params"] = params
        assert self.p.stdin and self.p.stdout
        self.p.stdin.write(json.dumps(msg, ensure_ascii=False).encode("utf-8") + b"\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError(f"server closed early; stderr={self.p.stderr.read().decode(errors='replace')}")
        return json.loads(line.decode("utf-8"))

    def tool(self, name: str, args: dict | None = None) -> dict:
        resp = self.call("tools/call", {"name": name, "arguments": args or {}})
        assert "result" in resp, resp
        assert not resp["result"]["isError"], resp["result"]
        return json.loads(resp["result"]["content"][0]["text"])

    def close(self) -> None:
        if self.p.stdin:
            self.p.stdin.close()
        self.p.wait(timeout=10)


FAILURES: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(("  PASS " if ok else "  FAIL ") + label + (f" :: {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(label)


def test_core(c: Client) -> None:
    init = c.call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "1"}})
    check(init["result"]["protocolVersion"] == "2025-06-18", "initialize handshake")
    check("tools" in init["result"]["capabilities"], "capabilities.tools")
    check("中文" in init["result"]["instructions"] and "责任" in init["result"]["instructions"], "default zh instructions carry disclaimer")

    tools = c.call("tools/list")["result"]["tools"]
    check(len(tools) == 11, "tools/list count", str(len(tools)))
    check(all("inputSchema" in t and "lang" in t["inputSchema"]["properties"] for t in tools), "tools expose lang parameter")

    r = c.tool("lookup_component", {"ref": "Q1001"})
    check(bool(r["results"]), "lookup Q1001 found")
    check(all(x["ref"] == "Q1001" for x in r["results"]), "exact designator (no Q1002 leakage)")
    check(bool(r["citations"]) and all(cit["raw_text"] and isinstance(cit["page"], int) for cit in r["citations"]), "citations carry page + verbatim quote")
    boards = [x["board"] for x in r["results"]]
    check(len(c.tool("lookup_component", {"ref": "Q1001", "board": boards[0]})["results"]) == 1, "board disambiguation")
    nf = c.tool("lookup_component", {"ref": "Q9999"})
    check(nf["results"] == [], "unknown ref returns no result")
    check(any("猜测" in n or "推測" in n or "guess" in n.lower() for n in nf["notices"]), "unknown ref explicitly refuses guessing")

    d = c.tool("diagnose", {"symptom": "发射功率低"})
    check(d["results"] and d["results"][0]["id"] == "low_tx_power", "diagnose zh")
    check(d["coverage"] == "derived", "diagnose marked derived")
    check(all(st["evidence"] for st in d["results"][0]["steps"]), "every diagnostic step has evidence")
    check(len(d["citations"]) >= 5, "diagnose citations")

    tp = c.tool("get_measurements", {"kind": "test_point"})
    check(bool(tp["results"]) and all(x["value"] is None and x["normal_voltage"] is None for x in tp["results"]), "no fabricated test-point voltage")
    check(all(x["coverage"] == "not_in_manual" for x in tp["results"]), "test points marked not_in_manual")
    check(all(x["nominal_is_inferred"] for x in c.tool("get_net_labels")["results"]), "net nominals flagged inferred")
    check(len(c.tool("trace_signal", {"direction": "RX"})["results"]) == 8, "RX chain 8 stages")
    check(any(x["value"] == 105 for x in c.tool("get_adjustment", {"item": "105"})["results"]), "adjustment target 105 W traceable")
    check(len(c.tool("list_manual_gaps")["results"]) >= 8, "manual gaps listed")
    check(bool(c.call("resources/list")["result"]["resources"]), "resources/list")
    check("source_sha256" in c.call("resources/read", {"uri": "manual://dataset/manifest"})["result"]["contents"][0]["text"], "resources/read manifest")
    i18n = c.call("resources/read", {"uri": "manual://i18n"})["result"]["contents"][0]["text"]
    check("disclaimer" in i18n and "ja" in i18n, "i18n resource readable")
    bad = c.call("tools/call", {"name": "trace_signal", "arguments": {"direction": "XX"}})
    check("direction" in bad["result"]["content"][0]["text"], "invalid direction handled")


def test_multilingual(c: Client) -> None:
    print("  -- multilingual --")
    zh = c.tool("diagnose", {"symptom": "发射功率低"})
    ja = c.tool("diagnose", {"symptom": "送信出力が低い"})
    en = c.tool("diagnose", {"symptom": "low tx power"})
    check(zh["language"] == "zh", "zh question -> zh answer", zh["language"])
    check(ja["language"] == "ja", "ja question -> ja answer", ja["language"])
    check(en["language"] == "en", "en question -> en answer", en["language"])
    check(all(x["results"] and x["results"][0]["id"] == "low_tx_power" for x in (zh, ja, en)), "all three languages resolve the same fault")
    check("送信" in ja["results"][0]["symptom"], "ja symptom localised", ja["results"][0]["symptom"])
    check("Low transmit" in en["results"][0]["symptom"], "en symptom localised", en["results"][0]["symptom"])
    check("最初に" in ja["results"][0]["steps"][0]["action"], "ja step localised")
    check("Rule out" in en["results"][0]["steps"][0]["action"], "en step localised")
    check("責任" in ja["disclaimer"], "ja disclaimer present")
    check("liability" in en["disclaimer"], "en disclaimer present")
    check("责任" in zh["disclaimer"], "zh disclaimer present")
    check(len({zh["disclaimer"], ja["disclaimer"], en["disclaimer"]}) == 3, "disclaimers are three distinct translations")
    # Verbatim manual evidence must never be translated.
    zh_ev = [e["raw_text"] for st in zh["results"][0]["steps"] for e in st["evidence"]]
    en_ev = [e["raw_text"] for st in en["results"][0]["steps"] for e in st["evidence"]]
    check(zh_ev == en_ev and bool(zh_ev), "verbatim manual quotes unchanged across languages")

    ja_comp = c.tool("lookup_component", {"ref": "Q1001", "lang": "ja"})
    zh_comp = c.tool("lookup_component", {"ref": "Q1001", "lang": "zh"})
    check(ja_comp["language"] == "ja", "explicit lang override")
    check([x["part_no"] for x in ja_comp["results"]] == [x["part_no"] for x in zh_comp["results"]], "part numbers never translated")
    check(any("基板" in n for n in ja_comp["notices"]), "ja lookup notices")

    ja_gaps = c.tool("list_manual_gaps", {"lang": "ja"})
    check(all(any("\u3040" <= ch <= "\u30ff" for ch in x["item"]) for x in ja_gaps["results"]), "ja manual gaps localised")
    en_chain = c.tool("trace_signal", {"direction": "RX", "lang": "en"})
    check("ANT" in en_chain["results"][0]["stage"] and "フィルタ" not in en_chain["results"][0]["stage"], "en signal stages localised")
    en_tp = c.tool("get_measurements", {"kind": "test_point", "lang": "en"})
    check(all(x["value"] is None for x in en_tp["results"]), "localisation does not fabricate voltages")
    check(any("not_in_manual" in n or "uncovered" in n.lower() for n in en_tp["notices"]), "en gap notice")

    # Kana-free Japanese phrasing must still be detected as Japanese.
    ja2 = c.tool("diagnose", {"symptom": "送信出力低下"})
    check(ja2["language"] == "ja", "kana-free Japanese detected", ja2["language"])
    # Pure technical tokens must not flip the answer language.
    keep = c.tool("lookup_component", {"ref": "Q1001"})
    check(keep["language"] == "ja", "technical token keeps current language", keep["language"])


def main() -> int:
    c = Client()
    try:
        test_core(c)
        test_multilingual(c)
    finally:
        c.close()

    c2 = Client()
    try:
        init = c2.call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "locale": "ja", "clientInfo": {"name": "smoke-ja"}})
        check("責任" in init["result"]["instructions"], "initialize locale=ja instructions")
        check(c2.tool("list_manual_gaps")["language"] == "ja", "initialize locale becomes default answer language")
    finally:
        c2.close()

    print(f"\n{len(FAILURES)} failures")
    for f in FAILURES:
        print("  -", f)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
