"""Shared helpers for the IC-7300 service-manual data pipeline.

Every record emitted by this pipeline carries provenance. A value without a
page reference and the original text fragment is rejected by validate.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "data" / "extracted"
PAGES = EXTRACTED / "pages"
DATA = ROOT / "data"
SCHEMA = ROOT / "schema"
MANUAL_PDF = ROOT / "Icom IC-7300 Service Manual.pdf"

DEVICE_MODEL = "Icom IC-7300"
MANUAL_ID = "S-15218XZ-C1"
SCHEMA_VERSION = "1.0.0"

COVERAGE = ("manual", "derived", "not_in_manual")

# Section boundaries come from the 23 PDF bookmarks (see pdf_probe.json).
SECTIONS = [
    {"id": "front", "title": "FRONT COVER / INTRODUCTION / TOC", "page_start": 1, "page_end": 3},
    {"id": "1", "title": "SPECIFICATIONS", "page_start": 4, "page_end": 5},
    {"id": "2", "title": "INSIDE VIEWS", "page_start": 6, "page_end": 9},
    {"id": "3", "title": "CIRCUIT DESCRIPTION", "page_start": 10, "page_end": 15},
    {"id": "4", "title": "ADJUSTMENT PROCEDURE", "page_start": 16, "page_end": 21},
    {"id": "5", "title": "PARTS LIST", "page_start": 22, "page_end": 40},
    {"id": "6", "title": "MECHANICAL PARTS", "page_start": 41, "page_end": 46},
    {"id": "7", "title": "BOARD LAYOUTS", "page_start": 47, "page_end": 56},
    {"id": "8", "title": "GENERAL WIRING", "page_start": 57, "page_end": 58},
    {"id": "9", "title": "BLOCK DIAGRAM", "page_start": 59, "page_end": 61},
    {"id": "10", "title": "SCHEMATIC DIAGRAM", "page_start": 62, "page_end": 73},
    {"id": "back", "title": "ADDRESS / BACK COVER", "page_start": 74, "page_end": 75},
]

SCHEMATIC_SUBSECTIONS = [
    {"board": "FRONT UNIT", "page_start": 62, "page_end": 62},
    {"board": "MAIN UNIT", "page_start": 63, "page_end": 68},
    {"board": "RF UNIT", "page_start": 69, "page_end": 69},
    {"board": "TUNER UNIT", "page_start": 70, "page_end": 71},
    {"board": "PA UNIT", "page_start": 72, "page_end": 73},
]


def section_for(page: int) -> str:
    for s in SECTIONS:
        if s["page_start"] <= page <= s["page_end"]:
            return s["title"]
    return "UNKNOWN"


def page_text(page: int) -> str:
    return (PAGES / f"p{page:04d}.txt").read_text(encoding="utf-8")


def page_lines(page: int) -> list[str]:
    return page_text(page).splitlines()


def source(page: int, raw_text: str, **extra: Any) -> dict:
    return {
        "section": section_for(page),
        "page": page,
        "raw_text": raw_text.strip(),
        **extra,
    }


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
