"""Build the portable SQLite index used by the MCP server.

Only stdlib is used. The original PDF is hashed for traceability but never
copied into the distributable package.

Usage: python tools/build_db.py
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from common import (
    DATA,
    DEVICE_MODEL,
    MANUAL_ID,
    MANUAL_PDF,
    SCHEMA_VERSION,
    SECTIONS,
    read_jsonl,
    write_json,
)

DB = DATA / "manual.sqlite"


def j(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> int:
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(str(DB))
    con.executescript(
        """
        CREATE TABLE sections(id TEXT PRIMARY KEY, title TEXT, page_start INT, page_end INT);
        CREATE TABLE components(
            ref_key TEXT PRIMARY KEY, ref TEXT NOT NULL, board TEXT, part_no TEXT,
            description TEXT, mounted_side TEXT, x REAL, y REAL,
            schematic_pages TEXT, board_layout_pages TEXT,
            source_page INT, raw_text TEXT, coverage TEXT);
        CREATE INDEX idx_components_ref ON components(ref);
        CREATE INDEX idx_components_board ON components(board);
        CREATE TABLE net_labels(
            name TEXT PRIMARY KEY, nominal_volt REAL, nominal_is_inferred INT,
            pages TEXT, source_page INT, raw_text TEXT, note TEXT, coverage TEXT);
        CREATE TABLE measurements(
            id TEXT PRIMARY KEY, kind TEXT, name TEXT, value TEXT, unit TEXT,
            normal_voltage TEXT, circuit TEXT, coverage TEXT,
            source_page INT, raw_text TEXT, note TEXT);
        CREATE INDEX idx_measurements_kind ON measurements(kind);
        CREATE TABLE signal_chain(
            direction TEXT, ord INT, stage TEXT, board TEXT, refs TEXT,
            coverage TEXT, evidence TEXT, reasoning_basis TEXT,
            PRIMARY KEY(direction, ord));
        CREATE TABLE faults(
            id TEXT PRIMARY KEY, symptom TEXT, aliases TEXT, suspects TEXT,
            steps TEXT, coverage TEXT, reasoning_basis TEXT, manual_gaps TEXT);
        CREATE TABLE manual_gaps(
            id TEXT PRIMARY KEY, item TEXT, detail TEXT,
            source_page INT, raw_text TEXT, coverage TEXT);
        CREATE VIRTUAL TABLE fts USING fts5(entity, key, body, tokenize='unicode61');
        """
    )

    con.executemany(
        "INSERT INTO sections VALUES(?,?,?,?)",
        [(s["id"], s["title"], s["page_start"], s["page_end"]) for s in SECTIONS],
    )

    components = read_jsonl(DATA / "components.jsonl")
    con.executemany(
        "INSERT INTO components VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                c["ref_key"], c["ref"], c["board"], c["part_no"], c["description"],
                c["mounted_side"], (c["location"] or {}).get("x"), (c["location"] or {}).get("y"),
                j(c["schematic_pages"]), j(c["board_layout_pages"]),
                c["source"]["page"], c["source"]["raw_text"], c["coverage"],
            )
            for c in components
        ],
    )
    con.executemany(
        "INSERT INTO fts(entity,key,body) VALUES('component',?,?)",
        [
            (c["ref_key"], " ".join([c["ref"], c["board"], c["part_no"], c["description"]]))
            for c in components
        ],
    )

    nets = read_jsonl(DATA / "net_labels.jsonl")
    con.executemany(
        "INSERT INTO net_labels VALUES(?,?,?,?,?,?,?,?)",
        [
            (n["name"], n["nominal_volt"], int(n["nominal_is_inferred"]), j(n["pages"]),
             n["source"]["page"], n["source"]["raw_text"], n["source"].get("note", ""), n["coverage"])
            for n in nets
        ],
    )
    con.executemany(
        "INSERT INTO fts(entity,key,body) VALUES('net_label',?,?)",
        [(n["name"], " ".join([n["name"], "power net", n["source"].get("note", "")])) for n in nets],
    )

    meas = read_jsonl(DATA / "measurements.jsonl")
    con.executemany(
        "INSERT INTO measurements VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        [
            (m["id"], m["kind"], m["name"], j(m["value"]), m["unit"], j(m["normal_voltage"]),
             m["circuit"], m["coverage"], m["source"]["page"], m["source"]["raw_text"], m.get("note", ""))
            for m in meas
        ],
    )
    con.executemany(
        "INSERT INTO fts(entity,key,body) VALUES('measurement',?,?)",
        [(m["id"], " ".join(str(x) for x in [m["kind"], m["name"], m["value"], m["unit"], m["circuit"]] if x is not None)) for m in meas],
    )

    chains = read_jsonl(DATA / "signal_chain.jsonl")
    con.executemany(
        "INSERT INTO signal_chain VALUES(?,?,?,?,?,?,?,?)",
        [(s["direction"], s["order"], s["stage"], s["board"], j(s["refs"]), s["coverage"], j(s["evidence"]), s["reasoning_basis"]) for s in chains],
    )
    con.executemany(
        "INSERT INTO fts(entity,key,body) VALUES('signal_chain',?,?)",
        [(f'{s["direction"]}#{s["order"]}', " ".join([s["direction"], s["stage"], s["board"], " ".join(s["refs"])])) for s in chains],
    )

    faults = read_jsonl(DATA / "fault_tree.jsonl")
    con.executemany(
        "INSERT INTO faults VALUES(?,?,?,?,?,?,?,?)",
        [(f["id"], f["symptom"], j(f["aliases"]), j(f["suspects"]), j(f["steps"]),
          f["coverage"], f["reasoning_basis"], j(f["manual_gaps"])) for f in faults],
    )
    con.executemany(
        "INSERT INTO fts(entity,key,body) VALUES('fault',?,?)",
        [(f["id"], " ".join([f["symptom"], " ".join(f["aliases"]), " ".join(f["suspects"])])) for f in faults],
    )

    gaps = read_jsonl(DATA / "manual_gaps.jsonl")
    con.executemany(
        "INSERT INTO manual_gaps VALUES(?,?,?,?,?,?)",
        [(g["id"], g["item"], g["detail"], g["source"]["page"], g["source"]["raw_text"], g["coverage"]) for g in gaps],
    )
    con.executemany(
        "INSERT INTO fts(entity,key,body) VALUES('manual_gap',?,?)",
        [(g["id"], " ".join([g["item"], g["detail"]])) for g in gaps],
    )

    con.commit()
    counts = {
        t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("sections", "components", "net_labels", "measurements", "signal_chain", "faults", "manual_gaps", "fts")
    }
    con.close()

    sha = hashlib.sha256(MANUAL_PDF.read_bytes()).hexdigest()
    write_json(
        DATA / "manifest" / "dataset.json",
        {
            "device_model": DEVICE_MODEL,
            "manual_id": MANUAL_ID,
            "manual_title": "IC-7300 SERVICE MANUAL",
            "schema_version": SCHEMA_VERSION,
            "source_sha256": sha,
            "source_pages": 75,
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tables": counts,
            "coverage_note": "manual=verbatim text layer; derived=engineering inference; not_in_manual=explicitly absent. See manual_gaps table.",
            "distribution_note": "The original PDF is NOT included. Permission bits deny modify/assemble. End users must supply their own licensed copy for page lookup.",
        },
    )
    print("sqlite:", DB)
    print("tables:", json.dumps(counts))
    print("source_sha256:", sha[:16], "...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
