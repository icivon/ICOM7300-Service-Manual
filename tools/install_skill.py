"""Install the IC-7300 Skill into CodeBuddy / Claude Code / Cursor.

CodeBuddy discovers skills ONLY under a `skills/<name>/` directory:
  project level : <workspace>/.codebuddy/skills/icom-7300/
  user level    : ~/.codebuddy/skills/icom-7300/
Claude Code and Cursor use their own skills directories.

Usage:
  python tools/install_skill.py --list
  python tools/install_skill.py --target project          # current workspace (CodeBuddy)
  python tools/install_skill.py --target user             # all workspaces (CodeBuddy)
  python tools/install_skill.py --target project claude cursor
  python tools/install_skill.py --target project --workspace C:/path/to/project

The copy is idempotent: only SKILL.md and references/*.md are overwritten.
Existing files in the target directory are never deleted.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from common import ROOT

SKILL_NAME = "icom-7300"


def targets(workspace: Path) -> dict[str, Path]:
    home = Path.home()
    return {
        "project": workspace / ".codebuddy" / "skills" / SKILL_NAME,
        "user": home / ".codebuddy" / "skills" / SKILL_NAME,
        "claude": workspace / ".claude" / "skills" / SKILL_NAME,
        "cursor": workspace / ".cursor" / "skills" / SKILL_NAME,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Install the IC-7300 service Skill")
    ap.add_argument("--target", nargs="+", choices=["project", "user", "claude", "cursor"], default=["project"])
    ap.add_argument("--workspace", type=Path, default=ROOT, help="workspace root (default: this project)")
    ap.add_argument("--source", type=Path, default=ROOT / "skill" / SKILL_NAME, help="source skill directory")
    ap.add_argument("--list", action="store_true", help="print target paths and exit")
    args = ap.parse_args()

    workspace = args.workspace.resolve()
    dest_map = targets(workspace)
    if args.list:
        for name, path in dest_map.items():
            print(f"{name:<8} {path}")
        print("\nsource   ", args.source.resolve())
        return 0

    src: Path = args.source.resolve()
    if not (src / "SKILL.md").exists():
        print(f"source skill not found: {src}", file=sys.stderr)
        return 1
    files = [src / "SKILL.md", *sorted((src / "references").glob("*.md"))]
    if len(files) < 2:
        print(f"source references missing under {src}", file=sys.stderr)
        return 1

    for name in args.target:
        dest = dest_map[name]
        (dest / "references").mkdir(parents=True, exist_ok=True)
        for p in files:
            rel = p.relative_to(src)
            shutil.copy2(p, dest / rel)
        print(f"[{name}] installed {len(files)} files -> {dest}")
        print(f"         entry: {dest / 'SKILL.md'}")

    print("\nVerification in CodeBuddy:")
    print("  1. Reload the workspace (or restart CodeBuddy) so Skills are rescanned.")
    print("  2. Settings > Skills: 'icom-7300' should appear under Project Skills / User Skills.")
    print("  3. Ask: 'IC-7300 发射功率低，帮我定位到电路和元件位号' (or JA/EN).")
    print("  4. Manual invocation where supported: /icom-7300")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
