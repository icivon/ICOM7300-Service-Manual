"""Probe a service-manual PDF to determine its type (text / scanned / hybrid).

Usage: python tools/probe_pdf.py <pdf> [json_out]

Outputs a JSON report containing page count, metadata, bookmarks, per-page text
length, embedded image counts, page sizes, and a page-type classification.
This is step 1 of the data-preparation pipeline: no OCR or parsing decisions
should be made before this report is reviewed.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


def image_xobjects(page) -> tuple[int, list[tuple[int, int]]]:
    """Count image XObjects and collect their pixel dimensions without decoding."""
    count = 0
    sizes: list[tuple[int, int]] = []
    try:
        resources = page.get("/Resources") or {}
        xobjects = resources.get("/XObject")
        if xobjects is None:
            return 0, []
        xobjects = xobjects.get_object()
        for ref in xobjects.values():
            obj = ref.get_object()
            if obj.get("/Subtype") == "/Image":
                count += 1
                sizes.append((int(obj.get("/Width", 0)), int(obj.get("/Height", 0))))
    except Exception:
        return count, sizes
    return count, sizes


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python probe_pdf.py <pdf> [json_out]", file=sys.stderr)
        return 2
    pdf_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    reader = PdfReader(str(pdf_path))
    meta = {k: str(v) for k, v in (reader.metadata or {}).items()}
    bookmarks: list[dict] = []

    def walk(items, depth=0):
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                try:
                    page_no = reader.get_destination_page_number(item) + 1
                except Exception:
                    page_no = None
                bookmarks.append(
                    {"title": str(item.title), "page": page_no, "depth": depth}
                )

    try:
        walk(reader.outline)
    except Exception as exc:
        bookmarks.append({"title": f"<outline error: {exc}>", "page": None, "depth": 0})

    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            text = ""
            print(f"page {idx}: extract_text failed: {exc}", file=sys.stderr)
        n_img, img_sizes = image_xobjects(page)
        box = page.mediabox
        chars = len(text.strip())
        largest = max((w * h for w, h in img_sizes), default=0)
        if chars >= 200 and largest < 1_000_000:
            kind = "text"
        elif chars >= 200:
            kind = "text+image"
        elif chars > 0 and n_img:
            kind = "sparse-text+image"
        elif n_img:
            kind = "image-only"
        else:
            kind = "empty/vector"
        pages.append(
            {
                "page": idx,
                "chars": chars,
                "images": n_img,
                "max_image_px": largest,
                "width_pt": round(float(box.width), 1),
                "height_pt": round(float(box.height), 1),
                "type": kind,
                "sample": " | ".join(text.strip().splitlines()[:6])[:300],
            }
        )

    kinds = Counter(p["type"] for p in pages)
    total_chars = sum(p["chars"] for p in pages)
    report = {
        "file": str(pdf_path),
        "size_bytes": pdf_path.stat().st_size,
        "encrypted": reader.is_encrypted,
        "metadata": meta,
        "page_count": len(pages),
        "bookmark_count": len(bookmarks),
        "bookmarks": bookmarks[:200],
        "total_text_chars": total_chars,
        "page_type_counts": dict(kinds),
        "pages": pages,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ("pages", "bookmarks")},
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"\nbookmarks (first 40): {json.dumps(bookmarks[:40], ensure_ascii=False)}")
    print(f"\nsampled pages:")
    step = max(1, len(pages) // 12)
    for p in pages[::step][:12]:
        print(f"  p{p['page']:>3} {p['type']:<18} chars={p['chars']:<6} imgs={p['images']:<3} :: {p['sample'][:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
