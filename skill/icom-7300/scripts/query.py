#!/usr/bin/env python3
"""Offline evidence query for the IC-7300 Skill.

Zero third-party dependencies: Python 3.9+ standard library only.
The database is located by walking up from this file, so the script works from
skill/, .codebuddy/skills/ and an unpacked distribution zip, regardless of the
current working directory. Override with --db PATH.

Every result carries `coverage` and `citations`. This tool NEVER fabricates a
value: records with coverage=not_in_manual keep value=null.

Examples (Windows: use `py -3`; elsewhere: `python3`):
  query.py stats
  query.py ref DS1 --board "DISPLAY UNIT"
  query.py ref Q1001
  query.py search "TUNER REFERENCE"
  query.py board "FRONT UNIT" --limit 20
  query.py page 62 --limit 40
  query.py measure --name TUNER
  query.py net 14V
  query.py chain TX
  query.py fault
  query.py gaps
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

NOTICE = (
    "coverage=manual: traceable to the manual text layer (page + short quote in "
    "citations). coverage=derived: derived reasoning, not verbatim manual text. "
    "coverage=not_in_manual: the manual does not provide this value; it stays null "
    "and MUST NOT be filled with experience, inference or generic radio data."
)


def find_db(start: Path) -> Path | None:
    for p in (start, *start.parents):
        candidate = p / "data" / "manual.sqlite"
        if candidate.is_file():
            return candidate
    return None


def connect(db: Path) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def pages(raw: str | None) -> list[int]:
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def citation(row: sqlite3.Row, text_col: str = "raw_text") -> dict:
    return {
        "page": row["source_page"] if "source_page" in row.keys() else None,
        "raw_text": (row[text_col] or "")[:150] if text_col in row.keys() else "",
    }


def emit(args: argparse.Namespace, results: list, citations: list | None = None, **extra) -> None:
    payload = {
        "command": args.command,
        "database": str(args.db),
        "count": len(results),
        "results": results[: args.limit] if not args.no_trim else results,
        "citations": citations or [],
        "coverage_notice": NOTICE,
        **extra,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def cmd_stats(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    tables = ["components", "net_labels", "measurements", "signal_chain", "faults", "manual_gaps", "fts"]
    results = [{"table": t, "rows": c.execute(f"select count(*) from {t}").fetchone()[0]} for t in tables]
    sections = [dict(r) for r in c.execute("select id,title,page_start,page_end from sections")]
    emit(args, results, sections=sections)


def cmd_ref(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    # Exact equality only: Q1001 must never leak into Q1002.
    rows = c.execute("select * from components where ref = ?", (args.ref,)).fetchall()
    if args.board:
        rows = [r for r in rows if r["board"] == args.board]
    results = [
        {
            "ref": r["ref"],
            "board": r["board"],
            "part_no": r["part_no"],
            "description": r["description"],
            "mounted_side": r["mounted_side"],
            "location": {"x": r["x"], "y": r["y"]},
            "parts_list_page": r["source_page"],
            "schematic_pages": pages(r["schematic_pages"]),
            "board_layout_pages": pages(r["board_layout_pages"]),
            "coverage": r["coverage"],
        }
        for r in rows
    ]
    note = None
    if len({r["board"] for r in rows}) > 1:
        note = "Designator is reused across boards; use --board to disambiguate."
    emit(args, results, [citation(r) for r in rows], note=note)


def cmd_board(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    rows = c.execute("select * from components where board = ? order by ref", (args.board,)).fetchall()
    results = [
        {
            "ref": r["ref"],
            "part_no": r["part_no"],
            "description": r["description"],
            "schematic_pages": pages(r["schematic_pages"]),
            "board_layout_pages": pages(r["board_layout_pages"]),
            "coverage": r["coverage"],
        }
        for r in rows
    ]
    emit(args, results, [citation(r) for r in rows[: args.limit]])


def cmd_page(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    rows = c.execute("select ref,board,schematic_pages,board_layout_pages,source_page,raw_text from components").fetchall()
    results = []
    for r in rows:
        sch, bl = pages(r["schematic_pages"]), pages(r["board_layout_pages"])
        if args.page in sch or args.page in bl:
            results.append(
                {
                    "ref": r["ref"],
                    "board": r["board"],
                    "in_schematic": args.page in sch,
                    "in_board_layout": args.page in bl,
                }
            )
    sec = c.execute(
        "select id,title from sections where page_start <= ? and page_end >= ?", (args.page, args.page)
    ).fetchall()
    emit(args, results, sections=[dict(x) for x in sec], note="PDF physical page, not printed page number.")


def cmd_search(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    q = args.text.strip()
    tokens = [t for t in q.replace('"', "").split() if t]
    expr = " OR ".join(f'"{t}"' for t in tokens) if tokens else '""'
    try:
        rows = c.execute(
            "select entity,key,body from fts where fts match ? limit ?", (expr, args.limit)
        ).fetchall()
        mode = "fts"
    except sqlite3.OperationalError:
        rows, mode = [], "fts_error"
    # FTS5 unicode61 does not segment Chinese; fall back to a literal scan so a
    # Chinese symptom can still reach the technical identifiers.
    if not rows:
        rows = c.execute(
            "select entity,key,body from fts where body like ? limit ?", (f"%{q}%", args.limit)
        ).fetchall()
        mode = "like"
    results = [{"entity": r["entity"], "key": r["key"], "body": r["body"][:300]} for r in rows]
    emit(args, results, mode=mode, note="No hit means the derived dataset has no such term; check gaps.")


def cmd_measure(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    sql, params = "select * from measurements where 1=1", []
    if args.name:
        sql += " and name like ?"
        params.append(f"%{args.name}%")
    if args.kind:
        sql += " and kind = ?"
        params.append(args.kind)
    rows = c.execute(sql + " order by kind,name", params).fetchall()
    results = [
        {
            "id": r["id"],
            "kind": r["kind"],
            "name": r["name"],
            "value": r["value"],
            "unit": r["unit"],
            "normal_voltage": r["normal_voltage"],
            "circuit": r["circuit"],
            "coverage": r["coverage"],
            "note": r["note"],
        }
        for r in rows
    ]
    note = None
    if not rows:
        note = "No such measurement in the manual-derived data. Run 'gaps' to check whether the manual covers it at all."
    emit(args, results, [citation(r) for r in rows[: args.limit]], note=note)


def cmd_net(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    rows = c.execute("select * from net_labels where name like ? order by name", (f"%{args.name}%",)).fetchall()
    results = [
        {
            "name": r["name"],
            "nominal_volt": r["nominal_volt"],
            "nominal_is_inferred": bool(r["nominal_is_inferred"]),
            "pages": pages(r["pages"]),
            "coverage": r["coverage"],
            "note": r["note"],
        }
        for r in rows
    ]
    emit(args, results, [citation(r) for r in rows[: args.limit]])


def cmd_chain(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    rows = c.execute(
        "select * from signal_chain where direction = ? order by ord", (args.direction,)
    ).fetchall()
    results = [dict(r) | {"refs": pages(r["refs"]), "evidence": pages(r["evidence"])} for r in rows]
    emit(args, results)


def cmd_fault(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    rows = c.execute("select * from faults").fetchall()
    results = []
    for r in rows:
        item = dict(r)
        for col in ("aliases", "suspects", "steps", "manual_gaps"):
            item[col] = pages(item[col]) if isinstance(item[col], str) else item[col]
        if args.keyword and args.keyword.lower() not in json.dumps(item, ensure_ascii=False).lower():
            continue
        results.append(item)
    emit(args, results, note="Fault trees are coverage=derived; the manual has no troubleshooting section.")


def cmd_gaps(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    rows = c.execute("select * from manual_gaps").fetchall()
    results = [dict(r) for r in rows]
    emit(args, results, [citation(r) for r in rows], note="Answer '手册未覆盖' for these; never guess a value.")


USER_FIELDS = ("ref", "board", "value", "unit", "source", "measured_at")


def cmd_userdata(args: argparse.Namespace, c: sqlite3.Connection) -> None:
    """Optional user-measured values. This file is local and never shipped.

    A record without complete provenance is rejected instead of being trusted.
    Nothing here is ever presented as manual data.
    """
    path = args.db.parent / "user_data" / "measurements.jsonl"
    if not path.is_file():
        emit(
            args, [],
            note=(
                "No user-supplied data file. To make 'not_in_manual' items actionable, create "
                f"{path} with one JSON object per line and required fields: "
                f"{', '.join(USER_FIELDS)} (optional: note). Such values are "
                "coverage=user_supplied, must always be quoted with their source, and are "
                "never described as coming from the service manual."
            ),
        )
        return
    results, rejected = [], []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            rejected.append({"line": lineno, "reason": "invalid JSON"})
            continue
        missing = [f for f in USER_FIELDS if not row.get(f)]
        if missing:
            rejected.append({"line": lineno, "reason": f"missing {', '.join(missing)}"})
            continue
        if args.ref and row["ref"] != args.ref:
            continue
        results.append({**row, "coverage": "user_supplied"})
    emit(
        args, results,
        rejected=rejected,
        note=(
            "coverage=user_supplied: measured by the user, NOT from the service manual. "
            "State the source and date; never present these as manual values."
        ),
    )


COMMANDS = {
    "userdata": cmd_userdata,
    "stats": cmd_stats,
    "ref": cmd_ref,
    "board": cmd_board,
    "page": cmd_page,
    "search": cmd_search,
    "measure": cmd_measure,
    "net": cmd_net,
    "chain": cmd_chain,
    "fault": cmd_fault,
    "gaps": cmd_gaps,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=None, help="path to data/manual.sqlite (auto-detected by default)")
    parser.add_argument("--limit", type=int, default=50, help="max results (default 50)")
    parser.add_argument("--no-trim", action="store_true", help="do not trim results to --limit")
    # Accept global flags before OR after the subcommand. SUPPRESS keeps the
    # global default when the flag is absent on the child parser.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--limit", type=int, default=argparse.SUPPRESS)
    common.add_argument("--no-trim", action="store_true", default=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", parents=[common], help="table sizes and chapter page ranges")
    p = sub.add_parser("ref", parents=[common], help="exact designator lookup (equality match)")
    p.add_argument("ref")
    p.add_argument("--board", help="disambiguate a designator reused across boards")
    p = sub.add_parser("board", parents=[common], help="list all components on one board")
    p.add_argument("board")
    p = sub.add_parser("page", parents=[common], help="which components appear on a PDF physical page")
    p.add_argument("page", type=int)
    p = sub.add_parser("search", parents=[common], help="full-text search over the derived dataset")
    p.add_argument("text")
    p = sub.add_parser("measure", parents=[common], help="specs, adjustment targets, check points")
    p.add_argument("--name")
    p.add_argument("--kind")
    p = sub.add_parser("net", parents=[common], help="power net labels")
    p.add_argument("name", nargs="?", default="")
    p = sub.add_parser("chain", parents=[common], help="RX/TX signal chain stages")
    p.add_argument("direction", choices=["RX", "TX"])
    p = sub.add_parser("fault", parents=[common], help="derived fault trees")
    p.add_argument("--keyword")
    p = sub.add_parser("gaps", parents=[common], help="what the manual does NOT cover")
    p = sub.add_parser("userdata", parents=[common], help="optional user-measured values (local, not shipped)")
    p.add_argument("--ref", help="filter by exact designator")

    args = parser.parse_args()
    db = args.db or find_db(Path(__file__).resolve().parent)
    if db is None or not db.is_file():
        print(
            "ERROR: data/manual.sqlite not found. Pass --db PATH (e.g. the unpacked distribution's data/manual.sqlite).",
            file=sys.stderr,
        )
        return 2
    args.db = db.resolve()
    with connect(args.db) as c:
        COMMANDS[args.command](args, c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
