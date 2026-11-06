"""Extract the native text layer of the service manual into reviewable plain text.

Usage: python tools/extract_text.py <pdf> <out_dir>

Produces:
  full_text.txt   - all pages, separated by === PAGE n === markers
  pages/pNNNN.txt - one file per page (for section-scoped Skill loading)
  page_index.json - per-page character count, detected section, keyword hits

No OCR is used. Every character originates from the PDF text layer (InDesign
export), so designators and numeric values can be traced back to a page.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

KEYWORDS = {
    "voltage_value": r"\b\d+(?:\.\d+)?\s?(?:V|mV|uV|dBm|dBu)\b",
    "test_point": r"(?i)\b(?:test\s?point|check\s?point|check\s?terminal|TP\d+|CP\d+)\b",
    "troubleshoot": r"(?i)\b(?:trouble|symptom|fault|failure|no\s+output|defect)\b",
    "adjustment": r"(?i)\b(?:adjust|alignment|calibrat|measure|setting)\w*\b",
    "signal_path": r"(?i)\b(?:RX|TX|IF|RF|AF|AGC|ALC|LO|ADC|DAC|FPGA|PA|ANT|TUNER)\b",
    "designator": r"\b(?:Q|D|IC|R|C|L|J|W|X|F|RL|DS|S)\d{2,5}[A-Z]?\b",
    "connector": r"\b[WJS]\d{3,4}\b",
    "board": r"(?i)\b(?:MAIN|RF|PA|FRONT|DISPLAY|TUNER|UNIT|BOARD)\b",
    "page_label": r"\b\d+-\d+\b",
}


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: python extract_text.py <pdf> <out_dir>", file=sys.stderr)
        return 2
    pdf_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    (out_dir / "pages").mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    enc = reader.trailer.get("/Encrypt")
    encryption = None
    if enc is not None:
        enc = enc.get_object()
        encryption = {
            "filter": str(enc.get("/Filter")),
            "V": enc.get("/V"),
            "R": enc.get("/R"),
            "P": enc.get("/P"),
            "empty_user_password": True,
        }
    if reader.is_encrypted:
        reader.decrypt("")

    bookmarks: list[dict] = []

    def walk(items, depth=0):
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                try:
                    pn = reader.get_destination_page_number(item) + 1
                except Exception:
                    pn = None
                bookmarks.append({"title": str(item.title), "page": pn, "depth": depth})

    walk(reader.outline)
    top = [b for b in bookmarks if b["depth"] == 0]

    def section_of(page_no: int) -> str:
        current = "FRONT MATTER"
        for b in top:
            if b["page"] and page_no >= b["page"]:
                current = b["title"]
        return current

    index = []
    chunks = []
    for n, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            print(f"page {n}: extract failed: {exc}", file=sys.stderr)
            text = ""
        (out_dir / "pages" / f"p{n:04d}.txt").write_text(text, encoding="utf-8")
        chunks.append(f"=== PAGE {n} ===\n{text}\n")
        hits = {k: len(re.findall(v, text)) for k, v in KEYWORDS.items()}
        index.append(
            {
                "page": n,
                "section": section_of(n),
                "chars": len(text.strip()),
                "hits": hits,
                "first_line": (text.strip().splitlines() or [""])[0][:120],
            }
        )

    (out_dir / "full_text.txt").write_text("\n".join(chunks), encoding="utf-8")
    (out_dir / "page_index.json").write_text(
        json.dumps(
            {"source": str(pdf_path), "encryption": encryption, "bookmarks": bookmarks, "pages": index},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("encryption:", json.dumps(encryption, ensure_ascii=False))
    print("bookmarks:", json.dumps(bookmarks, ensure_ascii=False))
    print("\nper-section totals:")
    totals: dict[str, dict] = {}
    for row in index:
        s = totals.setdefault(row["section"], {"pages": 0, "chars": 0, "hits": {}})
        s["pages"] += 1
        s["chars"] += row["chars"]
        for k, v in row["hits"].items():
            s["hits"][k] = s["hits"].get(k, 0) + v
    for name, s in totals.items():
        print(f"  {name:<32} pages={s['pages']:<3} chars={s['chars']:<7} hits={json.dumps(s['hits'])}")
    print("\ntop voltage-value pages:")
    for row in sorted(index, key=lambda r: -r["hits"]["voltage_value"])[:12]:
        print(f"  p{row['page']:>3} {row['section']:<28} V={row['hits']['voltage_value']:<4} TP={row['hits']['test_point']:<3} desig={row['hits']['designator']:<4} :: {row['first_line'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
