"""Quality gate for all derived data. Zero third-party dependencies.

Rules enforce the non-negotiable constraints of this project:
  * every numeric value must be traceable to a page AND the original text
  * designators must come from the SECTION 5 whitelist (Q1001 != Q1002)
  * inferred / absent data must be labelled, never filled in
  * derived fault logic must cite manual evidence for every step

Usage: python tools/validate.py [--report data/manifest/validation.json]
Exit code 1 on any error.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from common import COVERAGE, DATA, ROOT, SCHEMA_VERSION, read_jsonl, section_for, write_json

REF_RE = re.compile(r"^[A-Z]{1,3}[0-9]{1,5}[A-Z]?$")
KINDS = {"power_supply_spec", "regulator_rail", "net_label", "adjustment_target", "test_point"}


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks: Counter = Counter()
        self.counts: dict[str, int] = {}

    def check(self, ok: bool, label: str, msg: str) -> bool:
        self.checks[label] += 1
        if not ok:
            self.errors.append(f"[{label}] {msg}")
        return ok

    def run(self) -> None:
        whitelist_file = DATA / "manifest" / "ref_whitelist.json"
        if not whitelist_file.exists():
            self.errors.append("missing ref_whitelist.json - run parse_parts_list.py first")
            return
        # Rebuild the whitelist from the primary component table so a stale
        # manifest can never silently weaken designator validation.
        json.loads(whitelist_file.read_text(encoding="utf-8"))
        components = self.load("components")
        valid_refs = {c["ref"] for c in components}
        self.check(len(components) > 2000, "components.volume", f"only {len(components)} components parsed")

        seen_keys: set[str] = set()
        for i, c in enumerate(components):
            tag = f"components[{i}] {c.get('ref', '?')}"
            self.check(bool(REF_RE.match(c.get("ref", ""))), "components.ref_format", f"{tag}: bad ref")
            self.check(c.get("ref_key") == f"{c.get('board')}::{c.get('ref')}", "components.ref_key", f"{tag}: ref_key mismatch")
            self.check(c.get("ref_key") not in seen_keys, "components.unique", f"{tag}: duplicate ref_key")
            seen_keys.add(c.get("ref_key", ""))
            self.check(str(c.get("part_no", "")).isdigit(), "components.part_no", f"{tag}: bad part_no")
            self.check(bool(c.get("description")), "components.description", f"{tag}: empty description")
            self.check(c.get("coverage") in COVERAGE, "components.coverage", f"{tag}: bad coverage")
            loc = c.get("location")
            if loc is not None:
                self.check(
                    isinstance(loc.get("x"), (int, float)) and isinstance(loc.get("y"), (int, float)),
                    "components.location",
                    f"{tag}: bad location",
                )
            self.validate_source(c, tag)

        for name in ("net_labels", "measurements", "signal_chain", "fault_tree", "manual_gaps"):
            self.validate_entity(name, valid_refs)
        self.validate_i18n()
        self.validate_disclaimer()
        self.validate_codebuddy_skill()
        self.validate_distribution()
        self.validate_manifest()

    def load(self, name: str) -> list[dict]:
        rows = read_jsonl(DATA / f"{name}.jsonl")
        self.counts[name] = len(rows)
        return rows

    def validate_source(self, row: dict, tag: str) -> None:
        s = row.get("source")
        if not isinstance(s, dict):
            self.check(False, "provenance.source", f"{tag}: missing source")
            return
        page = s.get("page")
        self.check(isinstance(page, int) and 1 <= page <= 75, "provenance.page", f"{tag}: bad page {page!r}")
        self.check(bool(s.get("raw_text")), "provenance.raw_text", f"{tag}: empty raw_text")
        if isinstance(page, int) and 1 <= page <= 75:
            self.check(s.get("section") == section_for(page), "provenance.section", f"{tag}: section mismatch for p{page}")

    def number_in_raw(self, value, unit, raw: str) -> bool:
        """A numeric value may only be stored if the literal appears in the quote."""
        token = str(value).rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
        candidates = {token, str(value)}
        if isinstance(value, float):
            candidates.add(f"{value:.1f}")
        return any(c in raw for c in candidates)

    def validate_entity(self, name: str, valid_refs: set[str]) -> None:
        rows = self.load(name)
        if not rows:
            return  # generated in a later pipeline stage
        if name == "net_labels":
            for r in rows:
                tag = f"net_labels {r.get('name')}"
                self.check(r.get("coverage") in COVERAGE, "net_labels.coverage", tag)
                self.check(r.get("nominal_is_inferred") is True, "net_labels.inferred", f"{tag}: nominal must be flagged as inferred, never a measured value")
                self.check(bool(r.get("name")), "net_labels.name", tag)
                self.validate_source(r, tag)
        elif name == "measurements":
            for r in rows:
                tag = f"measurements {r.get('id')}"
                self.check(r.get("kind") in KINDS, "measurements.kind", tag)
                self.check(r.get("coverage") in COVERAGE, "measurements.coverage", tag)
                raw = (r.get("source") or {}).get("raw_text", "")
                value = r.get("value")
                if r.get("coverage") == "not_in_manual":
                    self.check(value is None and r.get("normal_voltage") is None, "measurements.no_fabrication", f"{tag}: not_in_manual record must not carry a value")
                elif isinstance(value, (int, float)):
                    self.check(self.number_in_raw(value, r.get("unit"), raw), "measurements.traceable_number", f"{tag}: value {value!r} not present in quoted text {raw[:80]!r}")
                self.validate_source(r, tag)
        elif name == "signal_chain":
            for r in rows:
                tag = f"signal_chain {r.get('direction')}#{r.get('order')}"
                self.check(r.get("direction") in ("RX", "TX"), "signal_chain.direction", tag)
                self.check(isinstance(r.get("order"), int) and r["order"] >= 1, "signal_chain.order", tag)
                self.check(bool(r.get("evidence")), "signal_chain.evidence", f"{tag}: no evidence")
                for ev in r.get("evidence", []):
                    self.check(isinstance(ev.get("page"), int), "signal_chain.evidence_page", tag)
                for ref in r.get("refs", []):
                    self.check(ref in valid_refs, "signal_chain.ref_whitelist", f"{tag}: ref {ref} not in whitelist")
        elif name == "fault_tree":
            for r in rows:
                tag = f"fault_tree {r.get('id')}"
                self.check(r.get("coverage") == "derived", "fault_tree.derived", f"{tag}: fault logic must be marked derived")
                self.check(bool(r.get("reasoning_basis")), "fault_tree.reasoning", tag)
                self.check(bool(r.get("suspects")), "fault_tree.suspects", tag)
                self.check(bool(r.get("manual_gaps")), "fault_tree.gaps", f"{tag}: must declare what the manual does not cover")
                for st in r.get("steps", []):
                    self.check(bool(st.get("evidence")), "fault_tree.step_evidence", f"{tag} step {st.get('order')}: no evidence")
                    for ev in st.get("evidence", []):
                        page = ev.get("page")
                        self.check(isinstance(page, int) and 1 <= page <= 75, "fault_tree.step_page", tag)
                        for ref in ev.get("refs", []):
                            self.check(ref in valid_refs, "fault_tree.ref_whitelist", f"{tag}: ref {ref} not in whitelist")
        elif name == "manual_gaps":
            for r in rows:
                self.check(r.get("coverage") == "not_in_manual", "manual_gaps.coverage", f"{r.get('id')}: must be not_in_manual")
                self.check(bool(r.get("detail")), "manual_gaps.detail", f"{r.get('id')}: missing detail")

    def validate_i18n(self) -> None:
        path = DATA / "locale" / "icom7300.i18n.json"
        if not path.exists():
            self.check(False, "i18n.file", "missing icom7300.i18n.json")
            return
        d = json.loads(path.read_text(encoding="utf-8"))
        langs = set(d.get("languages", []))
        self.check(langs == {"zh", "ja", "en"}, "i18n.languages", f"got {sorted(langs)}")
        for field in ("disclaimer", "instructions"):
            for lang in langs:
                self.check(bool(d.get(field, {}).get(lang)), f"i18n.{field}", f"{field}.{lang} missing")
        for group, minimum in (("notices", 20), ("tool_descriptions", 11)):
            entries = d.get(group, {})
            self.check(len(entries) >= minimum, f"i18n.{group}.count", f"only {len(entries)}")
            for key, val in entries.items():
                self.check(isinstance(val, dict) and langs.issubset(val), f"i18n.{group}", f"{key}: incomplete translations")
        faults = read_jsonl(DATA / "fault_tree.jsonl")
        loc = d.get("faults", {})
        self.check(set(loc) == {f["id"] for f in faults}, "i18n.faults.ids", "fault id mismatch with fault_tree.jsonl")
        for f in faults:
            entry = loc.get(f["id"], {})
            for field in ("symptom", "reasoning_basis"):
                self.check(langs.issubset(entry.get(field, {})), "i18n.faults.fields", f"{f['id']}.{field}")
            for field in ("aliases", "suspects"):
                for lang in langs:
                    self.check(bool(entry.get(field, {}).get(lang)), "i18n.faults.lists", f"{f['id']}.{field}.{lang}")
            for lang in langs:
                n = len(entry.get("steps", {}).get(lang, []))
                self.check(n == len(f["steps"]), "i18n.faults.steps", f"{f['id']}.{lang}: {n} vs {len(f['steps'])}")
        gaps = read_jsonl(DATA / "manual_gaps.jsonl")
        gloc = d.get("gaps", {})
        self.check(set(gloc) == {g["id"] for g in gaps}, "i18n.gaps.ids", "gap id mismatch")
        for gid, entry in gloc.items():
            for field in ("item", "detail"):
                self.check(langs.issubset(entry.get(field, {})), "i18n.gaps.fields", f"{gid}.{field}")
        stages = d.get("signal_stages", {})
        self.check(len(stages) == 16, "i18n.signal_stages.count", f"got {len(stages)}")
        for key, val in stages.items():
            self.check(langs.issubset(val), "i18n.signal_stages", f"{key}: incomplete")

    def validate_disclaimer(self) -> None:
        skill = ROOT / "skill" / "icom-7300" / "SKILL.md"
        text = skill.read_text(encoding="utf-8") if skill.exists() else ""
        for token in ("免责承诺", "免責", "Disclaimer", "责任", "責任", "liability"):
            self.check(token in text, "disclaimer.skill", f"SKILL.md missing {token!r}")
        i18n_md = ROOT / "skill" / "icom-7300" / "references" / "i18n.md"
        if i18n_md.exists():
            body = i18n_md.read_text(encoding="utf-8")
            self.check(all(x in body for x in ("不承担任何责任", "一切の責任", "accepts no liability")), "disclaimer.i18n_md", "trilingual undertaking missing")
        for name, token in (("README.md", "不承担任何责任"), ("README.ja.md", "一切の責任"), ("README.en.md", "accepts no liability")):
            p = ROOT / name
            self.check(p.exists() and token in p.read_text(encoding="utf-8"), "disclaimer.readme", f"{name} missing full undertaking")
        notice = ROOT / "NOTICE"
        self.check(
            notice.exists() and all(x in notice.read_text(encoding="utf-8") for x in ("Liability undertaking", "免责承诺", "免責承諾")),
            "disclaimer.notice", "NOTICE missing trilingual liability clause",
        )

    def validate_codebuddy_skill(self) -> None:
        """CodeBuddy scans `.codebuddy/skills/<name>/SKILL.md` only."""
        cb = ROOT / ".codebuddy" / "skills" / "icom-7300"
        src = ROOT / "skill" / "icom-7300"
        md = cb / "SKILL.md"
        self.check(md.exists(), "codebuddy.path", f"missing {md}")
        if not md.exists():
            return
        text = md.read_text(encoding="utf-8")
        self.check(text.startswith("---\n"), "codebuddy.frontmatter", "SKILL.md must start with YAML frontmatter")
        self.check("name: icom-7300\n" in text, "codebuddy.name", "name must match the directory name")
        self.check("description:" in text, "codebuddy.description", "description is required")
        self.check("disable: false" in text, "codebuddy.enabled", "skill must not be disabled")
        self.check("description_zh:" in text and "description_en:" in text, "codebuddy.localised", "localised descriptions missing")
        self.check("metadata:" in text, "codebuddy.metadata", "display metadata missing")
        self.check(len(text.split()) < 5000, "codebuddy.body_size", "SKILL.md body exceeds 5k words")
        self.check((cb / "references").is_dir(), "codebuddy.references", "references/ missing")
        # The CodeBuddy copy must be byte-identical to the distributable source.
        self.check(text == (src / "SKILL.md").read_text(encoding="utf-8"), "codebuddy.sync", "copy drifted from skill/icom-7300")
        src_refs = {p.name: p.read_bytes() for p in (src / "references").glob("*.md")}
        cb_refs = {p.name: p.read_bytes() for p in (cb / "references").glob("*.md")}
        self.check(bool(src_refs) and src_refs == cb_refs, "codebuddy.refs_sync", "references differ from source")

    def validate_distribution(self) -> None:
        dist = DATA / "dist"
        pdf_in_dist = list(dist.rglob("*.pdf")) if dist.exists() else []
        self.check(not pdf_in_dist, "distribution.no_pdf", f"original PDF must not be shipped: {pdf_in_dist}")

    def validate_manifest(self) -> None:
        p = DATA / "manifest" / "dataset.json"
        if not p.exists():
            return
        m = json.loads(p.read_text(encoding="utf-8"))
        self.check(m.get("schema_version") == SCHEMA_VERSION, "manifest.schema_version", "version mismatch")
        self.check(m.get("device_model") == "Icom IC-7300", "manifest.device_model", "wrong model")
        self.check(bool(m.get("source_sha256")), "manifest.source_sha256", "missing source checksum")


if __name__ == "__main__":
    v = Validator()
    v.run()
    report_path = DATA / "manifest" / "validation.json"
    write_json(
        report_path,
        {
            "ok": not v.errors,
            "error_count": len(v.errors),
            "errors": v.errors[:100],
            "checks": dict(sorted(v.checks.items())),
            "record_counts": v.counts,
        },
    )
    print(f"checks run: {sum(v.checks.values())}, records: {v.counts}, errors: {len(v.errors)}")
    for e in v.errors[:30]:
        print("  ERROR", e)
    print(f"report: {report_path}")
    sys.exit(1 if v.errors else 0)
