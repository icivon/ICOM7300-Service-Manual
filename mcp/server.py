#!/usr/bin/env python3
"""Icom IC-7300 service assistant - MCP server (stdio, JSON-RPC 2.0).

Zero third-party dependencies: only the Python standard library, the portable
SQLite index in ../data/manual.sqlite and ../data/locale/icom7300.i18n.json.
Implements the MCP handshake, tools and resources directly, so the
distributable works on any Python 3.9+ without installing an SDK.

Multilingual behaviour:
  * Questions are accepted in Chinese, Japanese and English.
  * The answer language is detected per tool call from the question text, or
    set explicitly with the `lang` argument / initialize `locale`.
  * Designators, part numbers, page numbers and verbatim manual quotes are
    NEVER translated; only explanatory text is localised.
  * Every answer carries the liability disclaimer in the answer language.

Every tool result carries `citations` (page + verbatim fragment + section) and
an explicit coverage notice. Designator lookup is an equality match, never a
LIKE/fuzzy match: Q1001 is never confused with Q1002.

Usage: python mcp/server.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = DATA / "manual.sqlite"
REFS = ROOT / "skill" / "icom-7300" / "references"
if not REFS.exists():
    # A package that only carries the CodeBuddy layout still exposes resources.
    REFS = ROOT / ".codebuddy" / "skills" / "icom-7300" / "references"
MANIFEST = DATA / "manifest" / "dataset.json"
I18N_PATH = DATA / "locale" / "icom7300.i18n.json"

PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
DEFAULT_PROTOCOL = "2024-11-05"

with I18N_PATH.open(encoding="utf-8") as _fh:
    I18N = json.load(_fh)
LANGS = tuple(I18N["languages"])
FALLBACK = I18N["default_language"]
CURRENT_LANG = FALLBACK

KANA = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\uff66-\uff9f]")
HAN = re.compile(r"[\u3400-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")
ZH_ONLY = set("发无电显动连调输线噪识问题开关测试据应该机级声说话请帮查办软连")
JA_ONLY = set("発電無雑続異扱接続異常調整基準受信送信出力基板鳴動確認済点検")
DESIGNATOR_ONLY = re.compile(r"^[A-Z]{1,3}[0-9]{1,5}[A-Z]?$")


def log(msg: str) -> None:
    sys.stderr.write(f"[icom7300-mcp] {msg}\n")
    sys.stderr.flush()


def normalize_lang(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip().lower().replace("_", "-")
    aliases = {"zh": "zh", "zh-cn": "zh", "chinese": "zh", "cn": "zh", "中文": "zh",
               "ja": "ja", "ja-jp": "ja", "japanese": "ja", "jp": "ja", "日本語": "ja",
               "en": "en", "en-us": "en", "english": "en"}
    return aliases.get(v) if v in aliases else (v if v in LANGS else None)


def detect_language(text: str) -> str | None:
    """Detect zh / ja / en from the user's own words. Technical tokens preserve
    the current language instead of flipping it to English."""
    s = (text or "").strip()
    if not s or DESIGNATOR_ONLY.match(s):
        return None
    if KANA.search(s):
        return "ja"
    if HAN.search(s):
        if any(ch in ZH_ONLY for ch in s):
            return "zh"
        if any(ch in JA_ONLY for ch in s):
            return "ja"
        return FALLBACK
    if LATIN.search(s):
        # "Q1001 MAIN UNIT" / "USB" are technical tokens in capitals, not an
        # English question; keep the current language for those.
        if not any(ch.islower() for ch in s):
            return None
        return "en"
    return None


def set_lang(lang: str) -> None:
    global CURRENT_LANG
    CURRENT_LANG = lang if lang in LANGS else FALLBACK


def tr(group: str, key: str, lang: str | None = None, default: str | None = None) -> str:
    entry = I18N.get(group, {}).get(key)
    if isinstance(entry, dict):
        return entry.get(lang or CURRENT_LANG) or entry.get(FALLBACK) or (default or key)
    if isinstance(entry, str):
        return entry
    return default if default is not None else key


def t(key: str, **kwargs: Any) -> str:
    text = tr("notices", key)
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return text


def citation(page: int, raw_text: str, **extra: Any) -> dict:
    return {"page": page, "raw_text": raw_text, **extra}


def jload(value: str | None, default):
    if value is None:
        return default
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return default


class Store:
    def __init__(self) -> None:
        if not DB.exists():
            raise FileNotFoundError(f"missing {DB}; run tools/build_db.py first")
        self.con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        self.con.row_factory = sqlite3.Row

    def rows(self, sql: str, args: tuple = ()) -> list[dict]:
        return [dict(r) for r in self.con.execute(sql, args).fetchall()]

    def one(self, sql: str, args: tuple = ()) -> dict | None:
        r = self.con.execute(sql, args).fetchone()
        return dict(r) if r else None

    def device(self) -> dict:
        m = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
        return {"device_model": m.get("device_model", "Icom IC-7300"), "manual_id": m.get("manual_id"), "schema_version": m.get("schema_version")}


def result(tool: str, query: dict, results: Any, citations: list[dict] | None = None,
           notices: list[str] | None = None, coverage: str | None = None, store: Store | None = None) -> dict:
    return {
        "tool": tool,
        **(store.device() if store else {}),
        "language": CURRENT_LANG,
        "disclaimer": I18N["disclaimer"][CURRENT_LANG],
        "query": query,
        "coverage": coverage,
        "results": results,
        "citations": citations or [],
        "notices": notices or [],
    }


def localized_fault(fid: str, lang: str) -> dict:
    return I18N["faults"].get(fid, {})


def tool_diagnose(s: Store, a: dict) -> dict:
    q = str(a.get("symptom", "")).strip()
    limit = min(max(int(a.get("max_results", 3)), 1), 9)
    if not q:
        return result("diagnose", a, [], notices=[t("empty_symptom")], store=s)
    faults = s.rows("SELECT * FROM faults")
    scored = []
    for f in faults:
        aliases = list(jload(f["aliases"], []))
        loc = localized_fault(f["id"], CURRENT_LANG)
        for lang in LANGS:
            aliases += loc.get("aliases", {}).get(lang, [])
        score = 0
        for alias in aliases:
            al, ql = str(alias).lower(), q.lower()
            if al == ql:
                score = max(score, 100)
            elif al in ql or ql in al:
                score = max(score, 80)
            else:
                shared = len(set(al) & set(ql))
                score = max(score, int(30 * shared / max(len(set(ql)), 1)))
        if score > 0:
            scored.append((score, f))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return result(
            "diagnose", a, [],
            notices=[t("diagnose_no_match", q=q), t("diagnose_derived")],
            coverage="derived", store=s,
        )
    out, cites = [], []
    for score, f in scored[:limit]:
        steps = jload(f["steps"], [])
        out.append(
            {
                "id": f["id"], "symptom": f["symptom"], "match_score": score,
                "coverage": f["coverage"], "suspects": jload(f["suspects"], []),
                "reasoning_basis": f["reasoning_basis"],
                "manual_gaps": jload(f["manual_gaps"], []),
                "steps": [
                    {
                        "order": st["order"], "action": st["action"],
                        "evidence": [
                            {"page": e["page"], "raw_text": e["raw_text"], "refs": e.get("refs", [])}
                            for e in st.get("evidence", [])
                        ],
                    }
                    for st in steps
                ],
            }
        )
        for st in steps:
            for e in st.get("evidence", []):
                cites.append(citation(e["page"], e["raw_text"], fault_id=f["id"]))
    return result(
        "diagnose", a, out, cites,
        [t("diagnose_derived"), t("diagnose_no_voltage")], "derived", s,
    )


def tool_lookup_component(s: Store, a: dict) -> dict:
    ref = str(a.get("ref", "")).strip().upper()
    board = a.get("board")
    if not ref:
        return result("lookup_component", a, [], notices=[t("empty_ref")], store=s)
    # Equality match only. No LIKE, no prefix fallback into results.
    sql = "SELECT * FROM components WHERE ref = ?"
    args: tuple = (ref,)
    if board:
        sql += " AND board = ? COLLATE NOCASE"
        args += (str(board),)
    rows = s.rows(sql + " ORDER BY board", args)
    if not rows:
        nearby = s.rows("SELECT DISTINCT ref FROM components WHERE ref LIKE ? ORDER BY ref LIMIT 5", (ref[:2] + "%",))
        notices = [t("lookup_not_found", ref=ref), t("lookup_nearby_hint")]
        if nearby:
            notices.append(t("nearby_prefix", refs=str([r["ref"] for r in nearby])))
        return result("lookup_component", a, [], notices=notices, store=s)
    out = [
        {
            "ref": r["ref"], "board": r["board"], "ref_key": r["ref_key"],
            "part_no": r["part_no"], "description": r["description"],
            "mounted_side": r["mounted_side"],
            "location": {"x": r["x"], "y": r["y"]} if r["x"] is not None else None,
            "schematic_pages": jload(r["schematic_pages"], []),
            "board_layout_pages": jload(r["board_layout_pages"], []),
            "parts_list_page": r["source_page"], "coverage": r["coverage"],
        }
        for r in rows
    ]
    cites = [citation(r["source_page"], r["raw_text"], section="5 PARTS LIST") for r in rows]
    notices = []
    if len(rows) > 1 and not board:
        notices.append(t("lookup_ambiguous", ref=ref, n=len(rows)))
    for r in rows:
        if not jload(r["schematic_pages"], []):
            notices.append(t("lookup_no_schematic", key=r["ref_key"]))
    return result("lookup_component", a, out, cites, notices, "manual", s)


def tool_find_circuit(s: Store, a: dict) -> dict:
    q = str(a.get("keyword", "")).strip()
    if not q:
        return result("find_circuit", a, [], notices=[t("empty_keyword")], store=s)
    rows = s.rows("SELECT * FROM signal_chain ORDER BY direction, ord")
    ql = q.lower()
    hits = [r for r in rows if ql in " ".join([r["stage"], r["board"], r["refs"] or ""]).lower()
            or ql in " ".join(tr("signal_stages", f'{r["direction"]}:{r["ord"]}', lang=l, default="") for l in LANGS).lower()]
    out, cites = [], []
    for r in hits:
        ev = jload(r["evidence"], [])
        out.append(
            {
                "direction": r["direction"], "order": r["ord"], "stage": r["stage"],
                "board": r["board"], "refs": jload(r["refs"], []), "coverage": r["coverage"],
                "evidence": [{"page": e["page"], "raw_text": e["raw_text"]} for e in ev],
            }
        )
        cites += [citation(e["page"], e["raw_text"], direction=r["direction"], order=r["ord"]) for e in ev]
    notices = [t("circuit_derived")] if hits else [t("circuit_no_match", q=q)]
    return result("find_circuit", a, out, cites, notices, "derived" if hits else None, s)


def tool_trace_signal(s: Store, a: dict) -> dict:
    d = str(a.get("direction", "")).upper()
    if d not in ("RX", "TX"):
        return result("trace_signal", a, [], notices=[t("invalid_direction")], store=s)
    rows = s.rows("SELECT * FROM signal_chain WHERE direction = ? ORDER BY ord", (d,))
    out, cites = [], []
    for r in rows:
        ev = jload(r["evidence"], [])
        out.append({"order": r["ord"], "stage": r["stage"], "board": r["board"], "refs": jload(r["refs"], []), "coverage": r["coverage"]})
        cites += [citation(e["page"], e["raw_text"], direction=d, order=r["ord"]) for e in ev]
    return result("trace_signal", a, out, cites, [t("trace_derived")], "derived", s)


def tool_get_measurements(s: Store, a: dict) -> dict:
    kind, name = a.get("kind"), a.get("name")
    sql, args, conds = "SELECT * FROM measurements", [], []
    if kind:
        conds.append("kind = ?")
        args.append(kind)
    if name:
        conds.append("(name LIKE ? OR raw_text LIKE ?)")
        args += [f"%{name}%", f"%{name}%"]
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    rows = s.rows(sql + " ORDER BY kind, id", tuple(args))[: min(max(int(a.get("limit", 60)), 1), 200)]
    out = [
        {
            "id": r["id"], "kind": r["kind"], "name": r["name"],
            "value": jload(r["value"], None), "unit": r["unit"],
            "normal_voltage": jload(r["normal_voltage"], None),
            "circuit": r["circuit"], "coverage": r["coverage"],
            "source_page": r["source_page"], "note": r["note"],
        }
        for r in rows
    ]
    cites = [citation(r["source_page"], r["raw_text"], measurement_id=r["id"]) for r in rows]
    notices = [t("measurements_traceable")]
    if any(r["coverage"] == "not_in_manual" for r in rows):
        notices.append(t("measurements_gap"))
    return result("get_measurements", a, out, cites, notices, None, s)


def tool_get_net_labels(s: Store, a: dict) -> dict:
    name = a.get("name")
    rows = (s.rows("SELECT * FROM net_labels WHERE name = ? OR name LIKE ? ORDER BY name", (name, f"%{name}%"))
            if name else s.rows("SELECT * FROM net_labels ORDER BY name"))
    out = [
        {
            "name": r["name"], "nominal_volt": r["nominal_volt"],
            "nominal_is_inferred": bool(r["nominal_is_inferred"]),
            "pages": jload(r["pages"], []), "coverage": r["coverage"], "note": r["note"],
        }
        for r in rows
    ]
    cites = [citation(r["source_page"], r["raw_text"], net=r["name"]) for r in rows]
    return result("get_net_labels", a, out, cites, [t("nets_inferred")], "manual", s)


def tool_get_adjustment(s: Store, a: dict) -> dict:
    item = a.get("item")
    rows = (s.rows("SELECT * FROM measurements WHERE kind = 'adjustment_target' AND (name LIKE ? OR raw_text LIKE ?)", (f"%{item}%", f"%{item}%"))
            if item else s.rows("SELECT * FROM measurements WHERE kind = 'adjustment_target'"))
    out = [
        {"name": r["name"], "value": jload(r["value"], None), "unit": r["unit"], "circuit": r["circuit"], "source_page": r["source_page"], "raw_text": r["raw_text"]}
        for r in rows
    ]
    return result(
        "get_adjustment", a, out,
        [citation(r["source_page"], r["raw_text"], section="4 ADJUSTMENT PROCEDURE") for r in rows],
        [t("adjustment_table")], "manual", s,
    )


def tool_get_page_ref(s: Store, a: dict) -> dict:
    sid = a.get("section_id")
    rows = s.rows("SELECT * FROM sections WHERE id = ?", (sid,)) if sid else s.rows("SELECT * FROM sections")
    out = [
        {"id": r["id"], "title": r["title"], "page_start": r["page_start"], "page_end": r["page_end"],
         "how_to_read": t("page_how_to", a=r["page_start"], b=r["page_end"])}
        for r in rows
    ]
    return result("get_page_ref", a, out, [], [t("page_ref_note")], "manual", s)


def tool_list_manual_gaps(s: Store, a: dict) -> dict:
    rows = s.rows("SELECT * FROM manual_gaps ORDER BY id")
    out = [{"id": r["id"], "item": r["item"], "detail": r["detail"], "source_page": r["source_page"], "coverage": r["coverage"]} for r in rows]
    return result(
        "list_manual_gaps", a, out,
        [citation(r["source_page"], r["raw_text"], gap_id=r["id"]) for r in rows],
        [t("gaps_instruction")], "not_in_manual", s,
    )


def tool_list_fault_symptoms(s: Store, a: dict) -> dict:
    rows = s.rows("SELECT id, symptom, aliases, coverage FROM faults ORDER BY id")
    return result(
        "list_fault_symptoms", a,
        [{"id": r["id"], "symptom": r["symptom"], "aliases": jload(r["aliases"], []), "coverage": r["coverage"]} for r in rows],
        [], [t("faults_derived")], "derived", s,
    )


def tool_search_all(s: Store, a: dict) -> dict:
    q = str(a.get("query", "")).strip()
    limit = min(max(int(a.get("limit", 20)), 1), 100)
    if not q:
        return result("search_all", a, [], notices=[t("empty_query")], store=s)
    try:
        rows = s.rows("SELECT entity, key, body FROM fts WHERE fts MATCH ? LIMIT ?", ('"' + q.replace('"', '""') + '"', limit))
    except sqlite3.OperationalError:
        rows = s.rows("SELECT entity, key, body FROM fts WHERE body LIKE ? LIMIT ?", (f"%{q}%", limit))
    out = [{"entity": r["entity"], "key": r["key"], "excerpt": r["body"][:240]} for r in rows]
    notices = [t("search_hint")] if rows else [t("search_no_match", q=q)]
    return result("search_all", a, out, [], notices, None, s)


TOOLS: dict[str, Any] = {
    "diagnose": (tool_diagnose, {"symptom": {"type": "string", "description": "故障描述 / 症状 / symptom (zh/ja/en)"}, "max_results": {"type": "integer", "default": 3}}),
    "lookup_component": (tool_lookup_component, {"ref": {"type": "string"}, "board": {"type": "string"}}),
    "find_circuit": (tool_find_circuit, {"keyword": {"type": "string"}}),
    "trace_signal": (tool_trace_signal, {"direction": {"type": "string", "enum": ["RX", "TX"]}}),
    "get_measurements": (tool_get_measurements, {"kind": {"type": "string"}, "name": {"type": "string"}, "limit": {"type": "integer"}}),
    "get_net_labels": (tool_get_net_labels, {"name": {"type": "string"}}),
    "get_adjustment": (tool_get_adjustment, {"item": {"type": "string"}}),
    "get_page_ref": (tool_get_page_ref, {"section_id": {"type": "string"}}),
    "list_manual_gaps": (tool_list_manual_gaps, {}),
    "list_fault_symptoms": (tool_list_fault_symptoms, {}),
    "search_all": (tool_search_all, {"query": {"type": "string"}, "limit": {"type": "integer"}}),
}
REQUIRED_ARGS = {"diagnose": ["symptom"], "lookup_component": ["ref"], "find_circuit": ["keyword"],
                 "trace_signal": ["direction"], "search_all": ["query"]}


def tool_definitions(lang: str) -> list[dict]:
    defs = []
    for name, (_, props) in TOOLS.items():
        schema = {
            "type": "object",
            "properties": {
                **props,
                "lang": {
                    "type": "string", "enum": list(LANGS),
                    "description": "Force the answer language (zh / ja / en). If omitted, it is detected from the question text.",
                },
            },
            "required": REQUIRED_ARGS.get(name, []),
        }
        defs.append({"name": name, "description": tr("tool_descriptions", name, lang=lang, default=name), "inputSchema": schema})
    return defs


def localize_payload(tool_name: str, payload: dict, lang: str) -> dict:
    """Translate explanatory text only. Technical identifiers and verbatim
    manual quotes are intentionally left untouched."""
    results = payload.get("results")
    if not isinstance(results, list):
        return payload
    for item in results:
        if not isinstance(item, dict):
            continue
        if tool_name == "diagnose":
            loc = localized_fault(item.get("id", ""), lang)
            if not loc:
                continue
            for field in ("symptom", "reasoning_basis"):
                if field in loc and lang in loc[field]:
                    item[field] = loc[field][lang]
            if "suspects" in loc and lang in loc["suspects"]:
                item["suspects"] = loc["suspects"][lang]
            if isinstance(item.get("manual_gaps"), list):
                item["manual_gaps_localized"] = [
                    I18N["gaps"].get(gid, {}).get("item", {}).get(lang, gid)
                    for gid in item["manual_gaps"]
                ]
            steps = loc.get("steps", {}).get(lang, [])
            for st in item.get("steps", []):
                idx = st.get("order", 0) - 1
                if 0 <= idx < len(steps):
                    st["action"] = steps[idx]
        elif tool_name == "list_fault_symptoms":
            loc = localized_fault(item.get("id", ""), lang)
            if loc:
                item["symptom"] = loc.get("symptom", {}).get(lang, item.get("symptom"))
                item["aliases"] = loc.get("aliases", {}).get(lang, item.get("aliases"))
        elif tool_name == "list_manual_gaps":
            g = I18N["gaps"].get(item.get("id", ""), {})
            item["item"] = g.get("item", {}).get(lang, item.get("item"))
            item["detail"] = g.get("detail", {}).get(lang, item.get("detail"))
        elif tool_name in ("find_circuit", "trace_signal"):
            key = f'{item.get("direction")}:{item.get("order")}'
            item["stage"] = tr("signal_stages", key, lang=lang, default=item.get("stage"))
        elif tool_name == "get_measurements":
            item["note"] = t("measurements_gap") if item.get("coverage") == "not_in_manual" else t("measurements_traceable")
        elif tool_name == "get_net_labels":
            item["note"] = t("nets_inferred")
    return payload


def list_resources() -> list[dict]:
    out = [
        {"uri": "manual://dataset/manifest", "name": "Dataset manifest", "mimeType": "application/json", "description": "Model, schema version, source SHA256, table counts"},
        {"uri": "manual://i18n", "name": "ZH / JA / EN strings", "mimeType": "application/json", "description": "All localised strings, symptoms, steps and disclaimers"},
        {"uri": "manual://gaps", "name": "Manual coverage gaps", "mimeType": "text/markdown"},
    ]
    if REFS.exists():
        for p in sorted(REFS.rglob("*.md")):
            rel = p.relative_to(REFS).as_posix()
            out.append({"uri": f"manual://references/{rel}", "name": rel, "mimeType": "text/markdown"})
    return out


def read_resource(uri: str) -> tuple[str, str] | None:
    if uri == "manual://dataset/manifest" and MANIFEST.exists():
        return "application/json", MANIFEST.read_text(encoding="utf-8")
    if uri == "manual://i18n":
        return "application/json", I18N_PATH.read_text(encoding="utf-8")
    if uri == "manual://gaps":
        gap_file = REFS / "manual-gaps.md"
        if gap_file.exists():
            return "text/markdown", gap_file.read_text(encoding="utf-8")
    if uri.startswith("manual://references/"):
        target = (REFS / uri[len("manual://references/"):]).resolve()
        if REFS.resolve() in target.parents and target.exists() and target.suffix == ".md":
            return "text/markdown", target.read_text(encoding="utf-8")
    return None


class Server:
    def __init__(self) -> None:
        self.store = Store()
        self.protocol = DEFAULT_PROTOCOL
        self.default_lang = FALLBACK
        set_lang(FALLBACK)

    def handle(self, msg: dict) -> dict | None:
        global CURRENT_LANG
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}
        if method is None:
            return None
        if method == "initialize":
            req = params.get("protocolVersion", DEFAULT_PROTOCOL)
            self.protocol = req if req in PROTOCOLS else DEFAULT_PROTOCOL
            meta = params.get("_meta") or {}
            client = params.get("clientInfo") or {}
            locale = params.get("locale") or meta.get("locale") or client.get("locale")
            self.default_lang = normalize_lang(locale) or self.default_lang
            set_lang(self.default_lang)
            return {
                "protocolVersion": self.protocol,
                "capabilities": {"tools": {"listChanged": False}, "resources": {"listChanged": False}},
                "serverInfo": {"name": "icom-7300-service-assistant", "version": "1.0.0"},
                "instructions": I18N["instructions"][self.default_lang] + " " + I18N["disclaimer"][self.default_lang],
            }
        if method in ("notifications/initialized", "notifications/cancelled") or mid is None:
            return None
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": tool_definitions(CURRENT_LANG)}
        if method == "tools/call":
            name = params.get("name")
            args = dict(params.get("arguments") or {})
            explicit = normalize_lang(args.get("lang"))
            if explicit:
                set_lang(explicit)
            else:
                probe = " ".join(str(args.get(k) or "") for k in ("symptom", "query", "keyword", "name", "item", "ref"))
                detected = detect_language(probe)
                # No language signal (e.g. a bare designator) keeps the current
                # conversational language instead of resetting it.
                if detected:
                    set_lang(detected)
            if name not in TOOLS:
                return {"content": [{"type": "text", "text": json.dumps({"error": t("unknown_tool", name=name)}, ensure_ascii=False)}], "isError": True}
            try:
                payload = TOOLS[name][0](self.store, args)
                payload = localize_payload(name, payload, CURRENT_LANG)
            except Exception as exc:
                log(f"tool {name} failed: {exc}")
                return {"content": [{"type": "text", "text": json.dumps({"error": str(exc)}, ensure_ascii=False)}], "isError": True}
            return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}], "isError": False}
        if method == "resources/list":
            return {"resources": list_resources()}
        if method == "resources/read":
            uri = params.get("uri", "")
            got = read_resource(uri)
            if got is None:
                return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": f"resource not found: {uri}"}]}
            mime, text = got
            return {"contents": [{"uri": uri, "mimeType": mime, "text": text}]}
        if method == "resources/templates/list":
            return {"resourceTemplates": []}
        raise KeyError(method)

    def reply(self, mid, payload: dict | None) -> dict | None:
        return None if payload is None else {"jsonrpc": "2.0", "id": mid, "result": payload}

    @staticmethod
    def error(mid, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    def run(self) -> int:
        log(f"ready, db={DB}, languages={LANGS}")
        for raw in sys.stdin.buffer:
            if not raw.strip():
                continue
            try:
                msg = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                self.send(self.error(None, -32700, f"parse error: {exc}"))
                continue
            mid = msg.get("id") if isinstance(msg, dict) else None
            try:
                out = self.reply(mid, self.handle(msg))
            except KeyError as exc:
                out = self.error(mid, -32601, f"method not found: {exc.args[0]}")
            except Exception as exc:
                log(f"unhandled: {exc}")
                out = self.error(mid, -32603, str(exc))
            if out is not None:
                self.send(out)
        return 0

    @staticmethod
    def send(obj: dict) -> None:
        sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n")
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    try:
        raise SystemExit(Server().run())
    except FileNotFoundError as exc:
        log(str(exc))
        raise SystemExit(1)
