"""Build the redistributable zip (no original PDF, no page-level text dumps).

Usage: python tools/build_dist.py
Output: dist/icom7300-assistant.zip
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from common import DATA, ROOT, SCHEMA_VERSION, write_json

DIST = ROOT / "dist"
PACKAGE = "icom7300-assistant"
ZIP_PATH = DIST / f"{PACKAGE}.zip"

INCLUDE_DIRS = ["skill", "mcp", "schema", "tools"]
ROOT_FILES = ["README.md", "README.ja.md", "README.en.md", "NOTICE"]
# These two manifests embed page-level text samples (up to 300 chars/page) and
# are deliberately kept out of the redistributable for copyright reasons.
EXCLUDE_MANIFEST = {"pdf_probe.json", "page_index.json", "build_report.json"}


def collect() -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for d in INCLUDE_DIRS:
        base = ROOT / d
        for p in sorted(base.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                out.append((p, f"{PACKAGE}/{p.relative_to(ROOT).as_posix()}"))
    for name in ROOT_FILES:
        p = ROOT / name
        if p.exists():
            out.append((p, f"{PACKAGE}/{name}"))
    # Ship the CodeBuddy project-level skill layout so unpacking at a
    # workspace root makes the skill discoverable immediately.
    cb_skill = ROOT / ".codebuddy" / "skills" / "icom-7300"
    if cb_skill.exists():
        for p in sorted(cb_skill.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                out.append((p, f"{PACKAGE}/{p.relative_to(ROOT).as_posix()}"))
    for p in sorted(DATA.glob("*.jsonl")):
        out.append((p, f"{PACKAGE}/data/{p.name}"))
    for p in sorted((DATA / "locale").glob("*.json")):
        out.append((p, f"{PACKAGE}/data/locale/{p.name}"))
    db = DATA / "manual.sqlite"
    if db.exists():
        out.append((db, f"{PACKAGE}/data/manual.sqlite"))
    for p in sorted((DATA / "manifest").glob("*.json")):
        if p.name not in EXCLUDE_MANIFEST:
            out.append((p, f"{PACKAGE}/data/manifest/{p.name}"))
    return out


def main() -> int:
    DIST.mkdir(exist_ok=True)
    files = collect()
    bad = [str(p) for p, _ in files if p.suffix.lower() == ".pdf" or "extracted" in p.parts]
    if bad:
        raise RuntimeError(f"refusing to ship manual content: {bad}")
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    report_arc = f"{PACKAGE}/data/manifest/build_report.json"
    report = {
        "package": ZIP_PATH.name,
        "schema_version": SCHEMA_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file_count": len(files) + 1,
        "includes_original_pdf": False,
        "includes_page_text_dumps": False,
        "excluded_manifests": sorted(EXCLUDE_MANIFEST),
        "exclusion_reason": "pdf_probe.json / page_index.json embed page-level verbatim samples; excluded for copyright. All shipped citations are short single-line quotes attached to records.",
        "contents": sorted([arc for _, arc in files] + [report_arc]),
    }
    report_json = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    write_json(DATA / "manifest" / "build_report.json", report)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src, arc in files:
            zf.write(src, arc)
        zf.writestr(report_arc, report_json)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        unique = len(set(zf.namelist())) == len(zf.namelist())
    print(f"built {ZIP_PATH} ({ZIP_PATH.stat().st_size} bytes, {report['file_count']} files, unique={unique})")
    print(f"original PDF included: {report['includes_original_pdf']}; page text dumps: {report['includes_page_text_dumps']}")
    return 0 if unique else 1


if __name__ == "__main__":
    raise SystemExit(main())
