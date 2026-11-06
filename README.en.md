# IC-7300 Service Assistant (Skill + MCP dual mode)

> Language / 言語 / 语言: [中文](README.md) · [日本語](README.ja.md) · [English](README.en.md)

Turns the official Icom IC-7300 Service Manual (S-15218XZ-C1, 75 pages) into
searchable structured data, providing the chain
**symptom -> suspect region -> circuit stage -> designator / schematic page / test parameter**.

One dataset, two ways to use it:

| Mode | Best for | Contents |
|---|---|---|
| **Skill** | Fast, lightweight lookup in Claude Code / Cursor and similar clients | `SKILL.md` routing table + 11 progressively loaded `references/*.md` files |
| **MCP** | Exact designator lookup, cross-entity queries, verifiable citations | Dependency-free stdio server, 11 tools, every result carries `citations` (page + verbatim quote) |

Both modes are generated from the same `data/*.jsonl` and
`data/locale/icom7300.i18n.json`, so they cannot drift apart.

---

## Multilingual support (English / 日本語 / 中文)

Ask in **English, Japanese or Chinese**; the language is detected and the
answer is given **in that same language**.

| Example question | Detected | Answer language |
|---|---|---|
| `low tx power` | en | English |
| `送信出力が低い` / `送信出力低下` | ja | Japanese |
| `发射功率低` | zh | Chinese |

- Detection runs on **each question's text**: kana or Japanese kanji (発, 電, 送信) -> ja; simplified Chinese -> zh; lowercase English words -> en.
- Pure technical tokens (`Q1001`, `MAIN UNIT`, `USB`) do not change the current language. If undetectable, Chinese is the default.
- MCP can force a language with `lang`: `{"name":"diagnose","arguments":{"symptom":"...","lang":"en"}}`. `initialize` also accepts `locale` (or `_meta.locale` / `clientInfo.locale`) as the default.
- **Technical identifiers are never translated**: designators, part numbers, board names, page numbers and verbatim manual quotes stay as printed; only explanatory text is localised.
- Every answer carries the **disclaimer in the answer language**. All strings live in `data/locale/icom7300.i18n.json`; the full trilingual reference is `skill/icom-7300/references/i18n.md`.

---

## Quick start

### CodeBuddy (already configured in this project)

**Standards check**: the Skill content already matched the CodeBuddy / Agent Skills standard (`SKILL.md` + YAML frontmatter `name`/`description` + `references/` progressive disclosure), but it lived in `skill/icom-7300/`, **outside CodeBuddy's scan path**. The official spec requires skills to be created in the workspace `.codebuddy/skills/` directory. Fixed:

- `name` now equals the directory name (`icom-7300`); added `description_zh`, `description_en`, `metadata` and `disable: false`.
- The build now also emits a **project-level** `.codebuddy/skills/icom-7300/` copy, byte-identical to the distributable source.
- CodeBuddy Settings > Skills lists Project Skills / User Skills and offers "Import Skill".

**Ways to use it**:

| Method | How |
|---|---|
| Auto-trigger (recommended) | Ask: `IC-7300 发射功率低，帮我定位到电路和元件位号` / `送信出力が低いので回路と位番を特定して` / `Low TX power, locate the circuit and designators` |
| Manual invocation | Type `/icom-7300` in clients supporting slash commands |
| Visual management | CodeBuddy Settings > Skills: find `icom-7300` under Project Skills, or use "Import Skill" with `skill/icom-7300/` |
| Explicit context | Use `@` to reference `.codebuddy/skills/icom-7300/SKILL.md` or a `references/*.md` file |
| Rescan | Reload the workspace (or restart CodeBuddy) once after adding a skill |
| Combine with MCP | Add `mcp/server.py` for exact designator lookup and `citations`-backed results |

**Install locations** (`tools/install_skill.py` is idempotent: it only overwrites `SKILL.md` and `references/*.md`, never deletes other files):

| Target | Path | Command |
|---|---|---|
| CodeBuddy project level (done automatically here) | `<workspace>/.codebuddy/skills/icom-7300/` | `python tools/install_skill.py --target project` |
| CodeBuddy user level (all projects) | `~/.codebuddy/skills/icom-7300/` | `python tools/install_skill.py --target user` |
| Claude Code | `<workspace>/.claude/skills/icom-7300/` | `python tools/install_skill.py --target claude` |
| Cursor | `<workspace>/.cursor/skills/icom-7300/` | `python tools/install_skill.py --target cursor` |

Multiple targets: `--target project user claude`; list all paths: `--list`; other workspace: `--workspace C:/path/to/project`.
The redistributable already contains `.codebuddy/skills/icom-7300/` — unpack that `.codebuddy/` directory at a workspace root and it works immediately.

`SKILL.md` is a ~4 KB routing table; details load on demand from `references/`.

### MCP mode

Requires only the **Python 3.9+ standard library** — no SDK installation. Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "icom7300": {
      "command": "python",
      "args": ["C:/path/to/icom7300-assistant/mcp/server.py"]
    }
  }
}
```

Use forward slashes on Windows; specify an absolute interpreter path if `python` is not on PATH.
The server implements JSON-RPC 2.0 over stdio and supports `2024-11-05`, `2025-03-26`, `2025-06-18` and `2025-11-25`.

Verify:

```bash
python tools/smoke_test_mcp.py     # 48 end-to-end checks, including all three languages
python tools/validate.py           # data quality gate
```

### Tools

| Tool | Purpose |
|---|---|
| `diagnose(symptom, lang?)` | Symptom -> suspect regions + steps + 67 verbatim manual evidence items |
| `lookup_component(ref, board?)` | **Equality match** on designators; returns board, part number, coordinates, drawing pages; prompts disambiguation for cross-board reuse |
| `find_circuit(keyword)` / `trace_signal(RX\|TX)` | Locate stages in the signal chain |
| `get_measurements(kind, name)` | Specs, adjustment targets, check points; uncovered items return `null` |
| `get_net_labels(name)` | Power-net labels (nominal values flagged as inferred) |
| `get_adjustment(item)` | Numeric targets from SECTION 4 |
| `get_page_ref(section_id)` | Section -> physical PDF page range |
| `list_manual_gaps()` | Data the manual does not cover |
| `search_all(query)` | FTS5 full-text search across all entities |
| `list_fault_symptoms()` | Supported symptoms (JA / ZH / EN) |

---

## Three-level localisation example

Input: `low tx power`

1. **Suspect regions**: PA UNIT power amplifier / driver, RF UNIT gain control and YGR amp, ALC and power detection, TUNER UNIT and antenna feed.
2. **Circuit stage**: along the TX chain SECTION 3-3 -> 3-2 -> 3-1; `Q121` (driver) -> `Q131/Q132` (push-pull PA) -> `D961/D962` (SWR detectors) -> `IC981` (buffer) -> `IC1701` (tuner).
3. **Component level**: `lookup_component("Q131")` returns board `PA UNIT`, part number, `LOCATION` coordinates, the SECTION 5 page, `schematic_pages` (SECTION 10 p72-73), `board_layout_pages` (SECTION 7), plus a page-level verbatim quote.

Every result includes `citations: [{page, raw_text, ...}]` for verification against the manual.

---

## Data trustworthiness (core constraints)

| `coverage` | Meaning |
|---|---|
| `manual` | Taken from the PDF text layer, with page and verbatim fragment |
| `derived` | Fault tree / signal-chain ordering built on manual evidence, **not manual text** |
| `not_in_manual` | Data genuinely absent; value is `null`, **never filled in** |

Enforced rules:

- **Exact designators**: 2797 authoritative designators from SECTION 5. Fragmented diagram text is rebuilt from coordinates and accepted only if whitelisted or uniquely segmented. `Q1001 != Q1002`; 362 designators reused across boards require disambiguation; ambiguous candidates go to `unresolved` and are never guessed.
- **Traceable numbers**: a value is dropped unless its literal appears in the quoted page text. Part-number false positives (`R1231 … 561V (560)`) and board-layout ruler fragments (`01V/51V`) are excluded.
- **No fabricated test parameters**: `14V / 8V / 5V / 3R3V / H3R3V / T9V` are **power-net labels**. Nominal values inferred from a name are flagged `nominal_is_inferred`; they are neither measured values nor tolerances.
- **Internally consistent fault logic**: steps follow the SECTION 3/9 signal chain and power tree, outside-in; no voltage thresholds absent from the manual are asserted.

### Not covered by the manual (see `references/manual-gaps.md`)

1. Symptom troubleshooting table / fault tree (zero matches for `trouble/symptom/fault/failure`)
2. Component-level DC test-point voltage table
3. Test-point waveforms / oscilloscope captures
4. Power-net tolerances and measurement conditions
5. Voltage target for SECTION 4-6 `TUNER REFERENCE VOLTAGE ADJUSTMENT`
6. Per-designator functional descriptions; board coordinates for every part (131 rows lack LOCATION)
7. Automatic disambiguation of designators reused across boards

The 27 CP* check points have only designators, mostly marked `SHORT`; **no normal voltage is given**. Queries return "not in manual".

---

## Directory layout

```
README.md / README.ja.md / README.en.md / NOTICE
.codebuddy/skills/icom-7300/ # CodeBuddy project-level skill (auto-generated)
skill/icom-7300/           # portable Agent Skills source
  SKILL.md                  # trilingual routing table
  references/*.md           # 11 on-demand references (includes i18n.md)
mcp/server.py               # dependency-free MCP server
data/
  manual.sqlite             # exact lookup + FTS5 (stdlib only)
  components.jsonl          # 2797 components (SECTION 5)
  net_labels.jsonl          # 29 power-net labels
  measurements.jsonl        # 49 specs / adjustment values / check points
  signal_chain.jsonl        # 8 RX + 8 TX stages
  fault_tree.jsonl          # 9 symptoms / 33 steps / 67 evidence items
  manual_gaps.jsonl         # 8 uncovered items
  locale/icom7300.i18n.json # ZH / JA / EN strings, symptoms, steps, disclaimer
  manifest/*.json           # probe / parse / validation / build reports
schema/entities.schema.json # portable JSON Schema contract
tools/*.py                  # full reproducible pipeline
tools/install_skill.py       # one-command install for CodeBuddy / Claude / Cursor
dist/icom7300-assistant.zip # redistributable (generated by run_all.py, not committed)
```

`data/manifest/validation.json` is the quality-gate report: ~28,600 checks, 0 errors.

---

## Reproduce / adapt to other radios

The shipped `data/` + `mcp/` + `skill/` work out of the box with the Python 3.9+ standard library. The `tools/` scripts are for rebuilding from the source manual or porting to another model; **clients do not need to run them**.
To rebuild, place a licensed copy of the manual PDF at the project root (`Icom IC-7300 Service Manual.pdf`).

```bash
pip install pypdf pdfplumber fonttools   # only needed for a full rebuild
python tools/run_all.py                 # probe -> extract -> parse -> validate -> build -> package
python tools/verify_dist.py             # verify the package is self-contained
```

To port: replace the PDF -> update `SECTIONS` and `SCHEMATIC_SUBSECTIONS` in `tools/common.py` -> adjust parsers for the new chapter layout -> rewrite the reviewed constants in `build_knowledge.py` / `build_fault_tree.py` against the new page numbers and literals -> add trilingual strings to `data/locale/*.i18n.json` -> run `run_all.py`. The validator automatically rejects numbers without page-level quotes and designators outside the whitelist.

---

## Compliance

The manual is copyright **Icom Inc.** Its PDF permission bits allow `copy/extract` and `print` but deny `modify` and `assemble` (splitting/recombining pages). Therefore this package:

- contains no original PDF, no schematic page images and no page-level text dumps (`data/extracted/` is not shipped);
- contains only structured derived data plus **short single-line quotations** attached to records for verification;
- uses page numbers that point to the user's own licensed PDF.

See `NOTICE` for details.

---

## Disclaimer / 免責 / 免责承诺

**EN**: This Skill and the accompanying tools provide technical reference only and do not constitute a repair diagnosis. The provider accepts no liability for equipment damage, personal injury, or financial loss arising from incorrect technical judgement, misuse, or decisions based on this material. Actual faults must be assessed independently by qualified personnel using the official service manual and measured data.

**JA**：本 Skill および関連ツールは技術参考資料のみを提供し、修理上の結論を示すものではありません。技術的判断の誤り、誤操作、または本資料に基づく判断により生じた機器の損傷、人身事故、経済的損失について、提供者は一切の責任を負いません。実際の故障は、資格を有する技術者が公式サービスマニュアルと実測データに基づき自ら判断してください。

**ZH**：本 Skill 与相关工具仅提供技术参考，不构成维修结论。因技术判断错误、误操作或依据本资料作出决定而造成的设备损坏、人身伤害或经济损失，提供者不承担任何责任。实际故障请由具备资质的人员结合官方手册与实测数据自行判断。
