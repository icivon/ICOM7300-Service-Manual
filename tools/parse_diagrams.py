"""Coordinate-aware token reconstruction for the diagram pages (SECTION 7-10).

The diagram pages are vector drawings whose text layer is emitted in drawing
order: values and designators are split, reversed or concatenated (e.g.
"22PC724", "47KR725", "C1022C1023"). Naive string concatenation fabricates
designators such as "CP12127". This module therefore:

  1. rebuilds words from positioned characters via pdfplumber.extract_words
  2. accepts a designator ONLY when it is in the SECTION 5 whitelist, either
     as an exact word or via a unique segmentation of a concatenated word
  3. sends every other candidate to unresolved (never guessed, never stored)
  4. collects power-net label candidates and CP* check points for review

Usage: python tools/parse_diagrams.py
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

import pdfplumber

from common import (
    DATA,
    MANUAL_PDF,
    SCHEMATIC_SUBSECTIONS,
    SECTIONS,
    read_jsonl,
    write_json,
    write_jsonl,
)

VALUE_SEG = re.compile(r"^[0-9][0-9A-Z.]{0,7}$")
NET_CANDIDATE = re.compile(r"^\+?[A-Z]{0,6}[0-9]{1,3}(?:[R.][0-9]{1,3})?V$|^VDD\(3R3V\)$")
CP_TOKEN = re.compile(r"^CP[0-9]{1,4}$")


def section_range(section_id: str) -> range:
    s = next(s for s in SECTIONS if s["id"] == section_id)
    return range(s["page_start"], s["page_end"] + 1)


def schematic_board(page: int) -> str | None:
    for s in SCHEMATIC_SUBSECTIONS:
        if s["page_start"] <= page <= s["page_end"]:
            return s["board"]
    return None


def segmentations(token: str, whitelist: set[str]) -> list[tuple[str, ...]]:
    """Return every way to split a token into whitelist refs / value segments."""
    n = len(token)
    if n > 24 or not any(ch.isdigit() for ch in token):
        return []
    results: list[tuple[str, ...]] = []

    def walk(pos: int, parts: list[str]) -> None:
        if len(parts) > 3:
            return
        if pos == n:
            if any(p in whitelist for p in parts):
                results.append(tuple(parts))
            return
        for end in range(pos + 1, min(n, pos + 9) + 1):
            seg = token[pos:end]
            if seg in whitelist or VALUE_SEG.match(seg):
                walk(end, parts + [seg])

    walk(0, [])
    return results


def resolve_token(token: str, whitelist: set[str]) -> tuple[list[str], str | None]:
    """-> (accepted refs, status). status: exact|split|ambiguous|none"""
    if token in whitelist:
        return [token], "exact"
    segs = segmentations(token, whitelist)
    if not segs:
        return [], "none"
    ref_sets = {tuple(p for p in seg if p in whitelist) for seg in segs}
    if len(ref_sets) != 1:
        return [], "ambiguous"
    refs = list(next(iter(ref_sets)))
    return refs, "split"


def main() -> int:
    components = read_jsonl(DATA / "components.jsonl")
    whitelist = {c["ref"] for c in components}
    ref_keys: dict[str, list[str]] = defaultdict(list)
    for c in components:
        ref_keys[c["ref"]].append(c["ref_key"])

    diagram_sections = {
        "7": "BOARD LAYOUTS",
        "8": "GENERAL WIRING",
        "9": "BLOCK DIAGRAM",
        "10": "SCHEMATIC DIAGRAM",
    }
    all_pages = [p for sid in diagram_sections for p in section_range(sid)]

    ref_pages: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"schematic": [], "board_layout": []})
    methods: Counter = Counter()
    unresolved: list[dict] = []
    net_candidates: dict[str, dict] = {}
    cp_tokens: dict[str, dict] = {}
    page_stats: list[dict] = []

    with pdfplumber.open(str(MANUAL_PDF)) as pdf:
        for page_no in all_pages:
            words = pdf.pages[page_no - 1].extract_words(x_tolerance=1.0)
            exact = split = ambiguous = 0
            for w in words:
                token = w["text"].strip()
                if not token:
                    continue
                refs, status = resolve_token(token, whitelist)
                if status == "exact":
                    exact += 1
                elif status == "split":
                    split += 1
                elif status == "ambiguous":
                    ambiguous += 1
                    unresolved.append(
                        {"page": page_no, "token": token, "reason": "multiple possible segmentations"}
                    )
                for ref in refs:
                    if page_no in section_range("7"):
                        bucket = "board_layout"
                    elif page_no in section_range("10"):
                        bucket = "schematic"
                    else:
                        bucket = None
                    if bucket and page_no not in ref_pages[ref][bucket]:
                        ref_pages[ref][bucket].append(page_no)
                # BOARD LAYOUT sheets (p47-56) contain ruler/coordinate
                # fragments such as "01V", "51V", "59V". They are not power
                # nets, so net labels and check points are collected only from
                # GENERAL WIRING / BLOCK / SCHEMATIC sheets (p57-73).
                if page_no >= 57 and CP_TOKEN.match(token):
                    cp_tokens.setdefault(token, {"pages": [], "raw_text": token})
                    if page_no not in cp_tokens[token]["pages"]:
                        cp_tokens[token]["pages"].append(page_no)
                if page_no >= 57 and NET_CANDIDATE.match(token) and not re.match(r"^[0-9]{3,}V$", token):
                    ent = net_candidates.setdefault(
                        token, {"pages": set(), "count": 0, "raw_text": token}
                    )
                    ent["count"] += 1
                    ent["pages"].add(page_no)
            methods["exact"] += exact
            methods["split"] += split
            methods["ambiguous"] += ambiguous
            page_stats.append(
                {"page": page_no, "words": len(words), "exact": exact, "split": split, "ambiguous": ambiguous}
            )

    # Only unambiguous page hits are written back into the component master.
    ambiguous_hits: list[dict] = []
    updated = []
    for c in components:
        ref = c["ref"]
        entry = ref_pages.get(ref)
        if not entry:
            updated.append(c)
            continue
        c = dict(c)
        for kind in ("schematic", "board_layout"):
            pages = sorted(entry[kind])
            if not pages:
                continue
            if len(ref_keys[ref]) == 1:
                c[f"{kind}_pages"] = pages
                continue
            matched = []
            for p in pages:
                board = schematic_board(p)
                if kind == "schematic" and board and f"{board}::{ref}" in ref_keys[ref]:
                    matched.append(p)
                else:
                    ambiguous_hits.append({"ref": ref, "page": p, "kind": kind, "reason": "designator reused across boards"})
            c[f"{kind}_pages"] = sorted(set(matched))
        updated.append(c)
    write_jsonl(DATA / "components.jsonl", updated)

    write_json(
        DATA / "manifest" / "ref_page_index.json",
        {
            "note": "Page-level designator occurrences. schematic pages are scoped to the board subsection where possible.",
            "refs": {k: {"schematic_pages": v["schematic"], "board_layout_pages": v["board_layout"]} for k, v in sorted(ref_pages.items())},
        },
    )
    write_json(
        DATA / "manifest" / "net_label_candidates.json",
        {
            "note": "Candidates extracted from SECTION 7-10 word tokens. These are POWER NET LABELS, not measured voltages. Requires review before becoming net_labels.jsonl.",
            "candidates": {
                k: {"count": v["count"], "pages": sorted(v["pages"]), "raw_text": v["raw_text"]}
                for k, v in sorted(net_candidates.items(), key=lambda kv: -kv[1]["count"])
            },
        },
    )
    write_json(
        DATA / "manifest" / "check_points.json",
        {
            "note": "CP* check points found in diagram pages. The manual gives no normal voltage for these.",
            "check_points": {
                k: {"pages": sorted(set(v["pages"])), "raw_text": v["raw_text"]}
                for k, v in sorted(cp_tokens.items())
            },
        },
    )
    write_json(
        DATA / "manifest" / "diagram_report.json",
        {
            "pages_processed": [all_pages[0], all_pages[-1]],
            "word_resolution": dict(methods),
            "unresolved_count": len(unresolved),
            "unresolved_sample": unresolved[:30],
            "ambiguous_page_hits": len(ambiguous_hits),
            "ambiguous_page_hits_sample": ambiguous_hits[:20],
            "refs_with_schematic_pages": sum(1 for c in updated if c["schematic_pages"]),
            "refs_with_board_layout_pages": sum(1 for c in updated if c["board_layout_pages"]),
            "net_label_candidates": len(net_candidates),
            "check_points": len(cp_tokens),
            "page_stats": page_stats,
        },
    )
    print(f"words resolved: {dict(methods)}")
    print(f"refs with schematic pages: {sum(1 for c in updated if c['schematic_pages'])}, board layout pages: {sum(1 for c in updated if c['board_layout_pages'])}")
    print(f"unresolved tokens: {len(unresolved)}, ambiguous page hits (not written): {len(ambiguous_hits)}")
    print(f"power-net candidates: {len(net_candidates)} -> {sorted(net_candidates)[:18]}")
    print(f"CP check points: {len(cp_tokens)} -> {sorted(cp_tokens)[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
