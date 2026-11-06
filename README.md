# IC-7300 维修辅助工具（Skill + MCP 双模式）

> 语言 / 言語 / Language：[中文](README.md) · [日本語](README.ja.md) · [English](README.en.md)

把 Icom IC-7300 官方 Service Manual（S-15218XZ-C1，75 页）结构化为可检索数据，实现
**故障现象 → 故障区域 → 电路模块 → 元件位号 / 图纸页码 / 测试参数** 的定位链。

同一份数据两种用法：

| 模式 | 适用 | 内容 |
|---|---|---|
| **Skill** | Claude Code / Cursor 等客户端，轻量快速查询 | `SKILL.md` 路由表 + 11 个按需加载的 `references/*.md` |
| **MCP** | 精确位号检索、跨实体关联、可验证引用 | 零依赖 stdio Server，11 个工具，全部结果带 `citations`（页码 + 原文） |

两种模式由同一份 `data/*.jsonl` 与 `data/locale/icom7300.i18n.json` 生成，内容不会漂移。

---

## 多语言支持（中文 / 日本語 / English）

提问可用**中文、日文、英文**，系统自动识别并**用同一种语言回答**。

| 提问示例 | 识别结果 | 回答语言 |
|---|---|---|
| `发射功率低` | zh | 中文 |
| `送信出力が低い` / `送信出力低下` | ja | 日本語 |
| `low tx power` | en | English |

- 语言按**每次提问的文本**自动判定；日文含假名或日文汉字（如「発」「電」「送信」）即识别为 ja，简体中文识别为 zh，小写英文词识别为 en。
- 纯技术标识（`Q1001`、`MAIN UNIT`、`USB`）不会改变当前语言；无法判断时默认中文。
- MCP 可用 `lang` 参数强制指定：`{"name":"diagnose","arguments":{"symptom":"...","lang":"ja"}}`；也可在 `initialize` 中传 `locale`（或 `_meta.locale` / `clientInfo.locale`）设置默认语言。
- **技术标识一律不翻译**：元件位号、料号、板名、页码、手册原文引用保持原样，仅说明性文字本地化。
- 所有回答都携带对应语言的**免责声明**；三语文案集中在 `data/locale/icom7300.i18n.json`，完整对照见 `skill/icom-7300/references/i18n.md`。

---

## 快速开始

### CodeBuddy（本项目已自动配置）

**规范检查结论**：Skill 内容符合 CodeBuddy / Agent Skills 通用标准（`SKILL.md` + YAML frontmatter 的 `name`/`description` + `references/` 渐进披露），但原先放在 `skill/icom-7300/`，**不在 CodeBuddy 扫描路径内**，所以识别不到。现已修正：

- `name` 与目录名统一为 `icom-7300`，补齐 `description_zh` / `description_en` / `metadata` / `disable: false`。
- 构建时同步生成**项目级** `.codebuddy/skills/icom-7300/`（`SKILL.md` + 11 个 `references/*.md`），与分发源逐字节一致。
- CodeBuddy 官方文档：Skill 应建立在工作区的 `.codebuddy/skills/` 目录下；设置页可管理 Project Skills / User Skills 并「导入 Skill」。

**使用方式一览**：

| 方式 | 操作 |
|---|---|
| 自动触发（推荐） | 直接提问：`IC-7300 发射功率低，帮我定位到电路和元件位号` / `送信出力が低いので回路を特定して` / `Low TX power, locate the circuit` |
| 手动调用 | 在支持斜杠命令的客户端输入 `/icom-7300` |
| 可视化管理 | CodeBuddy 设置 → Skills，在 Project Skills 中查看 `icom-7300`；也可用「导入 Skill」导入 `skill/icom-7300/` |
| 引用上下文 | 输入框 `@` 引用 `.codebuddy/skills/icom-7300/SKILL.md` 或某个 `references/*.md` |
| 让 CodeBuddy 重新扫描 | 重载/重开工作区（或重启 CodeBuddy）；新增 skill 后需要一次重新加载 |
| 配合 MCP | 需要精确位号/带 `citations` 的结果时，在 MCP 设置里同时接入 `mcp/server.py`（见下） |

**安装位置与命令**（`tools/install_skill.py` 幂等，只覆盖 `SKILL.md` 与 `references/*.md`，不删除目标目录其它内容）：

| 目标 | 路径 | 命令 |
|---|---|---|
| CodeBuddy 项目级（当前项目，已自动完成） | `<工作区>/.codebuddy/skills/icom-7300/` | `python tools/install_skill.py --target project` |
| CodeBuddy 用户级（所有项目） | `~/.codebuddy/skills/icom-7300/` | `python tools/install_skill.py --target user` |
| Claude Code | `<工作区>/.claude/skills/icom-7300/` | `python tools/install_skill.py --target claude` |
| Cursor | `<工作区>/.cursor/skills/icom-7300/` | `python tools/install_skill.py --target cursor` |

多目标一次安装：`python tools/install_skill.py --target project user claude`；查看所有路径：`python tools/install_skill.py --list`；安装到别的工作区：追加 `--workspace C:/path/to/project`。

分发包已内置 `.codebuddy/skills/icom-7300/`，把包内 `.codebuddy/` 放到工作区根即可生效。`SKILL.md` 只有约 4 KB 的路由表，详细内容按故障现象按需加载 `references/`。

### MCP 模式

只需 Python 3.9+ **标准库**（无需 pip 安装任何 SDK）。在客户端 MCP 配置中加入：

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

Windows 路径使用正斜杠；若 `python` 不在 PATH，填解释器绝对路径。
Server 通过 stdio 实现 JSON-RPC 2.0，兼容 `2024-11-05` / `2025-03-26` / `2025-06-18` / `2025-11-25`。

验证：

```bash
python tools/smoke_test_mcp.py     # 48 项端到端检查（含中/日/英）
python tools/validate.py           # 数据质量闸门
```

### 工具清单

| 工具 | 作用 |
|---|---|
| `diagnose(symptom)` | 故障现象 → 可疑区域 + 排查步骤 + 67 条手册原文证据 |
| `lookup_component(ref, board?)` | **等值匹配**元件位号，返回板名/料号/坐标/图纸页；跨板重名提示消歧 |
| `find_circuit(keyword)` / `trace_signal(RX\|TX)` | 信号链定位 |
| `get_measurements(kind, name)` | 规格、调整目标值、检查点；未覆盖项返回 `null` |
| `get_net_labels(name)` | 电源网络标签（标称值标注为推断） |
| `get_adjustment(item)` | §4 调整程序的数值 |
| `get_page_ref(section_id)` | 章节 → PDF 物理页码 |
| `list_manual_gaps()` | 手册未覆盖清单 |
| `search_all(query)` | 跨实体 FTS5 全文检索 |
| `list_fault_symptoms()` | 支持的故障现象 |

---

## 三层定位示例

输入：`发射功率低`

1. **故障区域**：PA UNIT 功放 / 驱动级、RF UNIT 增益控制与 YGR AMP、ALC 与功率检测、TUNER UNIT 与天馈。
2. **电路定位**：沿 TX 链 §3-3 → §3-2 → §3-1；`Q121`（驱动）→ `Q131/Q132`（推挽功放）→ `D961/D962`（SWR 检波）→ `IC981`（缓冲）→ `IC1701`（天调）。
3. **元件级指引**：`lookup_component("Q131")` 返回板名 `PA UNIT`、料号、`LOCATION` 坐标、§5 页码 32/33 附近、`schematic_pages`（§10 p72–73）、`board_layout_pages`（§7），以及带页码的原文引用。

所有结果附 `citations: [{page, raw_text, ...}]`，可回查原手册。

---

## 数据可信度（核心约束）

| `coverage` | 含义 |
|---|---|
| `manual` | 直接来自 PDF 文字层，附页码与原文片段 |
| `derived` | 基于手册证据整理的故障树 / 信号链阶段顺序，**不是手册原文** |
| `not_in_manual` | 手册确实没有，值为 `null`，**禁止填补** |

已落实的硬规则：

- **位号精确**：§5 PARTS LIST 生成 2797 条权威位号；图纸页的碎片文字经坐标重组后，只有在白名单内或唯一切分才入库。`Q1001 ≠ Q1002`；362 个跨板重名位号必须消歧；歧义项进 `unresolved`，不猜测。
- **数值可追溯**：每条数值必须能在指定页的原文中找到字面量，否则丢弃。`R1231 … 561V (560)` 这类料号假阳性、`01V/51V` 板图刻度碎片均已剔除。
- **不编造测试参数**：手册里的 `14V / 8V / 5V / 3R3V / H3R3V / T9V` 是**电源网络标签**，其标称值由名称推断并显式标记 `nominal_is_inferred`，不是实测电压、不含允差。
- **故障逻辑不自相矛盾**：排查顺序沿 §3/§9 信号链与电源树，由外到内；不输出手册中不存在的电压阈值判断。

### 手册未覆盖（明确标注，见 `references/manual-gaps.md`）

1. 故障现象排查表 / 故障树（全册 `trouble/symptom/fault/failure` 命中 0）
2. 元件级 DC 测试点电压表
3. 测试点波形 / 示波器截图
4. 电源网络允差与测量条件
5. §4-6 `TUNER REFERENCE VOLTAGE ADJUSTMENT` 的电压目标值
6. 逐位号的功能说明、全部元件的板坐标（131 行无 LOCATION）
7. 跨板重名位号的自动消歧

CP* 检查点（27 个）在手册中只有位号，多数标 `SHORT`，**没有正常电压**。查询时返回 `手册未覆盖`。

---

## 目录结构

```
README.md / README.ja.md / README.en.md / NOTICE
.codebuddy/skills/icom-7300/ # CodeBuddy 项目级 Skill（自动生成，解压即用）
skill/icom-7300/           # 通用 Agent Skills 分发源
  SKILL.md                 # 路由表（渐进披露入口）
  references/*.md          # 11 个按需加载的参考文件
mcp/server.py              # 零依赖 MCP Server
data/
  manual.sqlite            # 精确检索 + FTS5（仅标准库）
  components.jsonl         # 2797 条元件（§5）
  net_labels.jsonl         # 29 条电源网络标签
  measurements.jsonl       # 49 条规格/调整值/检查点
  signal_chain.jsonl       # RX/TX 各 8 阶段
  fault_tree.jsonl         # 9 症状 / 33 步 / 67 条证据
  manual_gaps.jsonl        # 8 项手册未覆盖
  locale/icom7300.i18n.json # 中/日/英三语文案、症状、步骤与免责声明
  manifest/*.json          # 探测、解析、校验、构建报告
schema/entities.schema.json # JSON Schema 契约（跨机型复用）
tools/*.py                 # 完整可复现流水线
tools/install_skill.py      # 一键安装到 CodeBuddy / Claude / Cursor
dist/icom7300-assistant.zip # 可分发包（运行 run_all.py 生成，不入库）
```

`data/manifest/validation.json` 是质量闸门报告：约 28600 项检查、0 错误。

---

## 复现 / 扩展到其它机型

分发包中的 `data/` + `mcp/` + `skill/` 开箱即用（只需 Python 3.9+ 标准库）；`tools/` 内的脚本仅供参考与迁移，**客户端使用时不需要运行**。
若要从头重建，需自备正版手册 PDF 置于项目根目录（文件名 `Icom IC-7300 Service Manual.pdf`）。

```bash
pip install pypdf pdfplumber fonttools   # 仅重建流水线需要
python tools/run_all.py                 # 一键：探测 → 提取 → 解析 → 校验 → 构建 → 打包
python tools/verify_dist.py             # 校验分发包自包含
```

迁移步骤：替换手册 PDF → 更新 `tools/common.py` 的 `SECTIONS` 书签页码与 `SCHEMATIC_SUBSECTIONS` → 按新手册章节调整解析器规则 → 重写 `build_knowledge.py` / `build_fault_tree.py` 中的人工审阅常量（依据原文页码与字面量）→ 跑 `run_all.py`。校验器会自动拒绝没有页码原文支撑的数值和不在白名单内的位号。

---

## 合规

原手册版权归 **Icom Inc.** 所有。其 PDF 权限位允许 `copy/extract`、`print`，但**禁止 `modify`、`assemble`**（拆页重组）。
因此本分发包：

- 不含原 PDF、不含任何页面图像、不含按页文字层全文（`data/extracted/` 不分发）；
- 只含结构化派生数据，以及附在记录上的**单行短引用**用于证据核验；
- 页码指向使用者自备的正版手册 PDF。

详见 `NOTICE`。本工具为维修辅助，不替代官方手册与专业判断。

---

## 免责承诺 / 免責 / Disclaimer

**ZH**：本 Skill 与相关工具仅提供技术参考，不构成维修结论。因技术判断错误、误操作或依据本资料作出决定而造成的设备损坏、人身伤害或经济损失，提供者不承担任何责任。实际故障请由具备资质的人员结合官方手册与实测数据自行判断。

**JA**：本 Skill および関連ツールは技術参考資料のみを提供し、修理上の結論を示すものではありません。技術的判断の誤り、誤操作、または本資料に基づく判断により生じた機器の損傷、人身事故、経済的損失について、提供者は一切の責任を負いません。実際の故障は、資格を有する技術者が公式サービスマニュアルと実測データに基づき自ら判断してください。

**EN**: This Skill and the accompanying tools provide technical reference only and do not constitute a repair diagnosis. The provider accepts no liability for equipment damage, personal injury, or financial loss arising from incorrect technical judgement, misuse, or decisions based on this material. Actual faults must be assessed independently by qualified personnel using the official service manual and measured data.
