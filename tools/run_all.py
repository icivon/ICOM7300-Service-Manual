"""One-command reproduction of the whole pipeline (from source PDF to zip).

Requirements for a FULL rebuild: pypdf, pdfplumber, fonttools.
Using the shipped package needs only the Python standard library.

Usage: python tools/run_all.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from common import DATA, MANUAL_PDF, ROOT

STEPS = [
    ("PDF 类型探测", "tools/probe_pdf.py", [str(MANUAL_PDF), str(DATA / "manifest" / "pdf_probe.json")]),
    ("文字层提取", "tools/extract_text.py", [str(MANUAL_PDF), str(DATA / "extracted")]),
    ("§5 元件主表", "tools/parse_parts_list.py", []),
    ("图纸坐标重组", "tools/parse_diagrams.py", []),
    ("知识数据构建", "tools/build_knowledge.py", []),
    ("故障树构建", "tools/build_fault_tree.py", []),
    ("SQLite 索引", "tools/build_db.py", []),
    ("Skill 生成", "tools/build_skill.py", []),
    ("数据质量闸门", "tools/validate.py", []),
    ("MCP 端到端测试", "tools/smoke_test_mcp.py", []),
    ("分发包构建", "tools/build_dist.py", []),
    ("分发包自包含验证", "tools/verify_dist.py", []),
]


def main() -> int:
    for i, (label, script, args) in enumerate(STEPS, start=1):
        print(f"[{i:>2}/{len(STEPS)}] {label} ...", flush=True)
        proc = subprocess.run(
            [sys.executable, str(ROOT / script), *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        for line in (proc.stdout or "").splitlines():
            print("      " + line)
        if proc.returncode != 0:
            print(f"FAILED at step {i}: {label}", file=sys.stderr)
            for line in (proc.stderr or "").splitlines()[-20:]:
                print("      " + line, file=sys.stderr)
            return proc.returncode
    print("\nAll steps completed: dist/icom7300-assistant.zip is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
