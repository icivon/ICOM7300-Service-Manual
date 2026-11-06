"""Parse SECTION 5 (PARTS LIST, p22-40) into the authoritative component table.

This is the single source of truth for designators. Diagram pages (SECTION
7/8/9/10) have a fragmented text layer, so every designator found there is
validated against the whitelist produced here. A designator that is not in the
whitelist is reported as unresolved instead of being guessed.

Usage: python tools/parse_parts_list.py
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from common import DATA, section_for, source, write_json, write_jsonl

REF_LINE = re.compile(r"^([A-Z]{1,3}[0-9]{1,5}[A-Z]?)\s+(\d{9,11})\s+(.*)$")
LOCATION = re.compile(r"\s+([TB])\s+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")
GROUP = re.compile(r"^\s*\[([^\]]+)\]\s*$")
PAGES = range(22, 41)


def main() -> int:
    records: list[dict] = []
    group_counts: Counter = Counter()
    duplicates: list[dict] = []
    unresolved: list[dict] = []
    board = "UNSPECIFIED"
    seen: dict[str, dict] = {}

    for page in PAGES:
        from common import page_lines

        for line_no, line in enumerate(page_lines(page), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            m_group = GROUP.match(line)
            if m_group:
                candidate = m_group.group(1).strip()
                # "[#03]/[#05]/[#06]" are H/V (hardware-version) markers that
                # continue the previous component row; they are NOT board names.
                if re.match(r"^#\d+$", candidate):
                    continue
                board = candidate
                continue
            m = REF_LINE.match(stripped)
            if not m:
                continue
            ref, part_no, rest = m.group(1), m.group(2), m.group(3).strip()
            m_loc = LOCATION.search(rest)
            if m_loc:
                side = m_loc.group(1)
                location = {"x": float(m_loc.group(2)), "y": float(m_loc.group(3))}
                description = rest[: m_loc.start()].strip()
            else:
                side = None
                location = None
                description = rest
            # Footer/header noise that happens to look like a part row.
            if description.startswith(("Eqv.=", "M.=", "S.=", "REF PARTS")):
                continue
            if len(description) < 2:
                unresolved.append(
                    {"page": page, "line": line_no, "text": stripped, "reason": "empty description"}
                )
                continue

            ref_key = f"{board}::{ref}"
            record = {
                "ref": ref,
                "board": board,
                "ref_key": ref_key,
                "part_no": part_no,
                "description": description,
                "mounted_side": side,
                "location": location,
                "schematic_pages": [],
                "board_layout_pages": [],
                "coverage": "manual",
                "source": source(page, stripped, note="SECTION 5 PARTS LIST verbatim row"),
            }
            if ref_key in seen:
                duplicates.append(
                    {
                        "ref_key": ref_key,
                        "first_page": seen[ref_key]["source"]["page"],
                        "again_page": page,
                        "text": stripped,
                    }
                )
                continue
            seen[ref_key] = record
            records.append(record)
            group_counts[board] += 1

    by_ref: dict[str, list[str]] = defaultdict(list)
    for r in records:
        by_ref[r["ref"]].append(r["ref_key"])

    n = write_jsonl(DATA / "components.jsonl", records)
    write_json(
        DATA / "manifest" / "ref_whitelist.json",
        {
            "source": "SECTION 5 PARTS LIST (p22-40)",
            "total_ref_keys": len(records),
            "unique_refs": len(by_ref),
            "ambiguous_refs": {k: v for k, v in sorted(by_ref.items()) if len(v) > 1},
            "boards": dict(sorted(group_counts.items())),
        },
    )
    write_json(
        DATA / "manifest" / "parse_report.json",
        {
            "pages_parsed": [PAGES.start, PAGES.stop - 1],
            "records": n,
            "boards": dict(sorted(group_counts.items())),
            "rows_with_location": sum(1 for r in records if r["location"]),
            "rows_without_location": sum(1 for r in records if not r["location"]),
            "duplicate_rows_skipped": len(duplicates),
            "duplicates_sample": duplicates[:20],
            "unresolved_rows": len(unresolved),
            "unresolved_sample": unresolved[:20],
        },
    )
    print(f"components: {n}")
    print(f"boards: {json.dumps(dict(sorted(group_counts.items())), ensure_ascii=False)}")
    print(f"with location: {sum(1 for r in records if r['location'])}, without: {sum(1 for r in records if not r['location'])}")
    print(f"duplicate rows skipped: {len(duplicates)}, unresolved: {len(unresolved)}")
    print(f"refs used on >1 board: {sum(1 for v in by_ref.values() if len(v) > 1)} (e.g. {list(k for k,v in by_ref.items() if len(v)>1)[:8]})")
    print(f"section sanity: {section_for(25)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
