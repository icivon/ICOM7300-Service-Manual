"""Verify the redistributable zip is self-contained and policy-compliant.

Unzips into a temporary directory, checks that no manual content is shipped,
validates the Skill frontmatter and runs the MCP server FROM THE UNPACKED COPY.

Usage: python tools/verify_dist.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from common import ROOT
from smoke_test_mcp import Client

ZIP = ROOT / "dist" / "icom7300-assistant.zip"
PACKAGE = "icom7300-assistant"


def main() -> int:
    failures: list[str] = []

    def check(ok: bool, label: str, detail: str = "") -> None:
        print(("  PASS " if ok else "  FAIL ") + label + (f" :: {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(label)

    if not ZIP.exists():
        print(f"missing {ZIP}; run tools/build_dist.py first")
        return 1
    with zipfile.ZipFile(ZIP) as zf:
        names = zf.namelist()
        with tempfile.TemporaryDirectory() as tmp:
            zf.extractall(tmp)
            base = Path(tmp) / PACKAGE
            check(not [n for n in names if n.lower().endswith(".pdf")], "no original PDF in package")
            check(not [n for n in names if "extracted/" in n], "no page-level text dumps")
            readmes = {"README.md": "不承担任何责任", "README.ja.md": "一切の責任", "README.en.md": "accepts no liability"}
            check(
                all((base / n).exists() and tok in (base / n).read_text(encoding="utf-8") for n, tok in readmes.items()),
                "three README languages with full disclaimer",
            )
            check((base / "NOTICE").exists(), "NOTICE present")
            check((base / "data" / "manual.sqlite").exists(), "sqlite index present")
            check((base / "data" / "locale" / "icom7300.i18n.json").exists(), "trilingual i18n data present")
            check((base / "schema" / "entities.schema.json").exists(), "schema contract present")

            skill = base / "skill" / "icom-7300" / "SKILL.md"
            check(skill.exists(), "SKILL.md present")
            if skill.exists():
                text = skill.read_text(encoding="utf-8")
                check(text.startswith("---\n"), "SKILL.md YAML frontmatter")
                check("name: icom-7300\n" in text and "description:" in text, "frontmatter name + description")
                check("disable: false" in text and "metadata:" in text, "frontmatter CodeBuddy metadata")
                check(all(x in text for x in ("免责承诺", "免責", "Disclaimer", "责任", "責任", "liability")), "SKILL.md trilingual disclaimer")
                check(len(text.encode("utf-8")) < 8000, "SKILL.md stays small (progressive disclosure)")
            refs = list((base / "skill" / "icom-7300" / "references").glob("*.md"))
            check(len(refs) >= 11, "progressive-disclosure references", str(len(refs)))
            check((base / "skill" / "icom-7300" / "references" / "i18n.md").exists(), "trilingual reference shipped")
            cb_md = base / ".codebuddy" / "skills" / "icom-7300" / "SKILL.md"
            src_md = base / "skill" / "icom-7300" / "SKILL.md"
            check(
                cb_md.exists()
                and "name: icom-7300\n" in cb_md.read_text(encoding="utf-8")
                and cb_md.read_bytes() == src_md.read_bytes(),
                "CodeBuddy project-level skill shipped and in sync",
            )
            check((base / ".codebuddy" / "skills" / "icom-7300" / "references" / "i18n.md").exists(), "CodeBuddy references shipped")
            check((base / "tools" / "install_skill.py").exists(), "skill installer shipped")

            # The Skill must be usable without any IDE/MCP configuration: verify
            # the bundled script really queries the unpacked SQLite database.
            skill_script = base / "skill" / "icom-7300" / "scripts" / "query.py"
            cb_script = base / ".codebuddy" / "skills" / "icom-7300" / "scripts" / "query.py"
            check(skill_script.exists(), "offline query script shipped")
            check(
                cb_script.exists() and skill_script.exists() and cb_script.read_bytes() == skill_script.read_bytes(),
                "CodeBuddy query script shipped and in sync",
            )
            check(
                "scripts/query.py" in (skill.read_text(encoding="utf-8") if skill.exists() else ""),
                "SKILL.md documents the offline query script",
            )
            if skill_script.exists():
                proc = subprocess.run(
                    [sys.executable, str(skill_script), "ref", "DS1"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                )
                ok = proc.returncode == 0
                if ok:
                    try:
                        payload = json.loads(proc.stdout)
                        ok = payload.get("count") == 2 and {
                            r["board"] for r in payload["results"]
                        } == {"FRONT UNIT", "DISPLAY UNIT"}
                    except (ValueError, KeyError, TypeError):
                        ok = False
                check(ok, "unpacked query script returns exact designator evidence", (proc.stderr or "")[-200:])

            val = json.loads((base / "data" / "manifest" / "validation.json").read_text(encoding="utf-8"))
            check(val.get("ok") is True and val.get("error_count") == 0, "shipped validation report clean")

            ds = json.loads((base / "data" / "manifest" / "dataset.json").read_text(encoding="utf-8"))
            check(bool(ds.get("source_sha256")), "source checksum recorded")

            server = base / "mcp" / "server.py"
            check(server.exists(), "MCP server present")
            if server.exists():
                c = Client(server_path=server)
                try:
                    init = c.call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "verify", "version": "1"}})
                    check(init["result"]["serverInfo"]["name"] == "icom-7300-service-assistant", "unpacked MCP server handshake")
                    tools = c.call("tools/list")["result"]["tools"]
                    check(len(tools) == 11, "unpacked server exposes 11 tools")
                    d = c.tool("diagnose", {"symptom": "开机无显示"})
                    check(bool(d["results"]) and bool(d["citations"]), "unpacked diagnose works with citations")
                    ja = c.tool("diagnose", {"symptom": "送信出力が低い"})
                    en = c.tool("diagnose", {"symptom": "low tx power"})
                    check(ja["language"] == "ja" and "責任" in ja["disclaimer"], "unpacked ja answer + disclaimer")
                    check(en["language"] == "en" and "liability" in en["disclaimer"], "unpacked en answer + disclaimer")
                    comp = c.tool("lookup_component", {"ref": "Q1001"})
                    check(bool(comp["results"]) and all(x["ref"] == "Q1001" for x in comp["results"]), "unpacked exact designator lookup")
                finally:
                    c.close()

    print(f"\n{len(failures)} failures")
    for f in failures:
        print("  -", f)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
