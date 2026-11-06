# IC-7300 保守支援ツール（Skill + MCP デュアルモード）

> 言語 / Language / 语言：[中文](README.md) · [日本語](README.ja.md) · [English](README.en.md)

Icom IC-7300 公式サービスマニュアル（S-15218XZ-C1、75 ページ）を構造化データ化し、
**故障現象 → 疑わしい領域 → 回路ブロック → 部品位番 / 回路図ページ / 測定パラメータ** の切り分けを実現します。

同じデータを 2 通りの方法で利用できます。

| モード | 用途 | 内容 |
|---|---|---|
| **Skill** | Claude Code / Cursor 等のクライアントで軽量・高速に参照 | `SKILL.md` ルーティング表 + 11 個の按需ロード `references/*.md` |
| **MCP** | 位番の完全一致検索、エンティティ横断、検証可能な引用 | 外部依存なし stdio Server、11 ツール、全結果に `citations`（ページ + 原文） |

両モードは同一の `data/*.jsonl` と `data/locale/icom7300.i18n.json` から生成され、内容が乖離しません。

---

## 多言語対応（日本語 / 中文 / English）

質問は**日本語・中国語・英語**で受け付け、自動判別して**同じ言語で回答**します。

| 質問例 | 判定 | 回答言語 |
|---|---|---|
| `送信出力が低い` / `送信出力低下` | ja | 日本語 |
| `发射功率低` | zh | 中文 |
| `low tx power` | en | English |

- 言語は**各質問のテキスト**から判定します。仮名または日本語漢字（「発」「電」「送信」等）で ja、簡体字で zh、小文字の英単語で en と判定します。
- `Q1001`、`MAIN UNIT`、`USB` のような技術トークンだけでは言語を変更しません。判別できない場合は中国語が既定です。
- MCP では `lang` で明示指定できます：`{"name":"diagnose","arguments":{"symptom":"...","lang":"ja"}}`。`initialize` の `locale`（または `_meta.locale` / `clientInfo.locale`）で既定言語も設定できます。
- **技術識別子は翻訳しません**。位番・型番・基板名・ページ番号・マニュアル原文はそのまま保持し、説明文のみローカライズします。
- すべての回答に対応言語の**免責宣言**が付きます。三言語の文案は `data/locale/icom7300.i18n.json`、完全な対照表は `skill/icom-7300/references/i18n.md` にあります。

---

## クイックスタート

### CodeBuddy（本プロジェクトでは設定済み）

**規範チェック**：Skill の中身は CodeBuddy / Agent Skills 標準（`SKILL.md` + YAML frontmatter の `name`/`description` + `references/` の段階的開示）に適合していましたが、配置が `skill/icom-7300/` だったため **CodeBuddy のスキャン対象外**でした。公式仕様では Skill は作業領域の `.codebuddy/skills/` に置く必要があります。以下を修正済みです。

- `name` をディレクトリ名と一致する `icom-7300` に統一し、`description_zh` / `description_en` / `metadata` / `disable: false` を追加。
- ビルド時に**プロジェクトレベル** `.codebuddy/skills/icom-7300/` を自動生成（配布元とバイト単位で同一）。
- 設定画面の Skills で Project Skills / User Skills を管理でき、「Skill をインポート」も利用できます。

**使い方一覧**：

| 方法 | 操作 |
|---|---|
| 自動起動（推奨） | `IC-7300 发射功率低，帮我定位到电路和元件位号` / `送信出力が低いので回路と位番を特定して` / `Low TX power, locate the circuit` と質問する |
| 手動呼び出し | スラッシュコマンド対応クライアントで `/icom-7300` |
| 可視化管理 | CodeBuddy 設定 → Skills で `icom-7300` を確認、「Skill をインポート」で `skill/icom-7300/` を指定 |
| コンテキスト指定 | 入力欄で `@` から `.codebuddy/skills/icom-7300/SKILL.md` や `references/*.md` を参照 |
| 再スキャン | 作業領域を再読み込み／CodeBuddy を再起動（Skill 追加後は一度必要） |
| MCP 併用 | 精密な位番検索・`citations` 付き結果には `mcp/server.py` も登録 |

**インストール先とコマンド**（`tools/install_skill.py` は冪等で、`SKILL.md` と `references/*.md` のみ上書き）：

| 対象 | パス | コマンド |
|---|---|---|
| CodeBuddy プロジェクト級（自動設定済み） | `<workspace>/.codebuddy/skills/icom-7300/` | `python tools/install_skill.py --target project` |
| CodeBuddy ユーザー級（全プロジェクト） | `~/.codebuddy/skills/icom-7300/` | `python tools/install_skill.py --target user` |
| Claude Code | `<workspace>/.claude/skills/icom-7300/` | `python tools/install_skill.py --target claude` |
| Cursor | `<workspace>/.cursor/skills/icom-7300/` | `python tools/install_skill.py --target cursor` |

複数指定：`--target project user claude`／パス一覧：`--list`／別作業領域：`--workspace C:/path/to/project`。
配布パッケージには `.codebuddy/skills/icom-7300/` が同梱されており、作業領域ルートに展開すれば即座に認識されます。

`SKILL.md` は約 4 KB のルーティング表で、詳細は故障現象に応じて `references/` を按需ロードします。

### MCP モード

必要なのは Python 3.9+ の**標準ライブラリのみ**（SDK のインストール不要）。クライアントの MCP 設定に追加します。

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

Windows のパスはスラッシュ区切りを使用してください。`python` が PATH に無い場合は絶対パスを指定します。
Server は stdio 上で JSON-RPC 2.0 を実装し、`2024-11-05` / `2025-03-26` / `2025-06-18` / `2025-11-25` に対応します。

検証：

```bash
python tools/smoke_test_mcp.py     # 48 項目の E2E チェック（三言語含む）
python tools/validate.py           # データ品質ゲート
```

### ツール一覧

| ツール | 機能 |
|---|---|
| `diagnose(symptom, lang?)` | 故障現象 → 疑わしい領域 + 切り分け手順 + 67 件のマニュアル原文証拠 |
| `lookup_component(ref, board?)` | 位番を**完全一致**で検索。基板名／型番／座標／回路図ページを返し、基板間共用は消去を促します |
| `find_circuit(keyword)` / `trace_signal(RX\|TX)` | 信号経路上の回路定位 |
| `get_measurements(kind, name)` | 仕様・調整目標値・チェックポイント。未記載項目は `null` |
| `get_net_labels(name)` | 電源ネット名（公称値は推定と明記） |
| `get_adjustment(item)` | §4 調整手順の数値 |
| `get_page_ref(section_id)` | 章 → PDF 物理ページ範囲 |
| `list_manual_gaps()` | マニュアル未記載項目 |
| `search_all(query)` | 全エンティティ横断 FTS5 全文検索 |
| `list_fault_symptoms()` | 対応する故障現象（日・中・英） |

---

## 三段階の定位例

入力：`送信出力が低い`

1. **疑わしい領域**：PA UNIT 電力増幅／ドライブ段、RF UNIT 利得制御と YGR AMP、ALC と電力検出、TUNER UNIT とアンテナ系。
2. **回路定位**：TX 経路 §3-3 → §3-2 → §3-1。`Q121`（ドライブ）→ `Q131/Q132`（プッシュプル）→ `D961/D962`（SWR 検波）→ `IC981`（バッファ）→ `IC1701`（チューナー）。
3. **部品レベル**：`lookup_component("Q131")` は基板 `PA UNIT`、型番、`LOCATION` 座標、§5 ページ、`schematic_pages`（§10 p72–73）、`board_layout_pages`（§7）、およびページ付き原文引用を返します。

すべての結果に `citations: [{page, raw_text, ...}]` が付き、原本で確認できます。

---

## データの信頼性（中核となる制約）

| `coverage` | 意味 |
|---|---|
| `manual` | PDF 文字レイヤーからの原文。ページと原文断片付き |
| `derived` | マニュアルの証拠に基づき整理した故障ツリー／信号経路の順序。**マニュアル原文ではない** |
| `not_in_manual` | マニュアルに実在しないデータ。値は `null` で**補完禁止** |

実装済みの厳格ルール：

- **位番の完全一致**：§5 PARTS LIST から 2797 件の権威ある位番を生成。回路図ページの分断された文字は座標再構成後、ホワイトリスト内または一意な分割の場合のみ採用。`Q1001 ≠ Q1002`。362 件の基板間共用位番は消去が必要で、曖昧な候補は `unresolved` とし推測しません。
- **数値の追跡可能性**：すべての数値は指定ページの原文に字面が存在しなければ破棄します。`R1231 … 561V (560)` のような型番、`01V/51V` の基板図目盛は除外済みです。
- **測定値を捏造しない**：`14V / 8V / 5V / 3R3V / H3R3V / T9V` は**電源ネット名**です。名称から推定した公称値には `nominal_is_inferred` を付け、実測値でも許容差でもありません。
- **矛盾しない故障邏輯**：切り分けは §3/§9 の信号経路と電源ツリーに沿って外部から内部へ。マニュアルに存在しない電圧しきい値判定は出力しません。

### マニュアル未記載（明記、詳細は `references/manual-gaps.md`）

1. 故障現象別の切り分け表／故障ツリー（全文で `trouble/symptom/fault/failure` 一致 0 件）
2. 部品レベルの DC テストポイント電圧表
3. テストポイント波形／オシロスコープ画面
4. 電源ネットの許容差と測定条件
5. §4-6 `TUNER REFERENCE VOLTAGE ADJUSTMENT` の電圧目標値
6. 位番ごとの機能説明、全部品の基板座標（131 行に LOCATION 無し）
7. 基板間共用位番の自動消去

CP* チェックポイント（27 件）は位番のみで、多くは `SHORT` の表記だけです。**正常電圧はありません**。照会時は `マニュアル未記載` を返します。

---

## ディレクトリ構成

```
README.md / README.ja.md / README.en.md / NOTICE
.codebuddy/skills/icom-7300/ # CodeBuddy プロジェクト級 Skill（自動生成、展開即用）
skill/icom-7300/           # 汎用 Agent Skills 配布元
  SKILL.md                 # ルーティング表（三言語対応）
  references/*.md          # 11 個の按需ロード参考ファイル（i18n.md 含む）
mcp/server.py              # 外部依存なし MCP Server
data/
  manual.sqlite            # 精密検索 + FTS5（標準ライブラリのみ）
  components.jsonl         # 2797 件の部品（§5）
  net_labels.jsonl         # 29 件の電源ネット名
  measurements.jsonl       # 49 件の仕様／調整値／チェックポイント
  signal_chain.jsonl       # RX/TX 各 8 段階
  fault_tree.jsonl         # 9 症状 / 33 手順 / 67 証拠
  manual_gaps.jsonl        # 8 件の未記載項目
  locale/icom7300.i18n.json # 日・中・英の文案、症状、手順、免責
  manifest/*.json          # 検出・解析・検証・ビルドレポート
schema/entities.schema.json # JSON Schema 契約（他機種へ展開可能）
tools/*.py                 # 再現可能な全パイプライン
tools/install_skill.py      # CodeBuddy / Claude / Cursor へ一括インストール
dist/icom7300-assistant.zip # 配布パッケージ（run_all.py で生成、リポジトリには含めない）
```

`data/manifest/validation.json` は品質ゲートのレポートです（約 28600 件のチェック、エラー 0）。

---

## 再現 / 他機種への展開

配布パッケージの `data/` + `mcp/` + `skill/` はそのまま利用できます（Python 3.9+ 標準ライブラリのみ）。`tools/` は元マニュアルからの再生成・他機種への移行用で、**クライアント利用時は実行不要**です。
再生成には正規のマニュアル PDF をプロジェクト直下（`Icom IC-7300 Service Manual.pdf`）に置いてください。

```bash
pip install pypdf pdfplumber fonttools   # 再生成時のみ必要
python tools/run_all.py                 # 検出 → 抽出 → 解析 → 検証 → ビルド → 梱包
python tools/verify_dist.py             # 配布パッケージの自己完結性検証
```

移行手順：PDF を差し替え → `tools/common.py` の `SECTIONS` と `SCHEMATIC_SUBSECTIONS` を更新 → 章構成に合わせてパーサを調整 → `build_knowledge.py` / `build_fault_tree.py` の人手レビュー定数を原文ページと字面に合わせて書き換え → `data/locale/*.i18n.json` に三言語文案を追加 → `run_all.py` を実行。ページ原文に裏付けの無い数値とホワイトリスト外の位番は検証器が自動で拒否します。

---

## 準拠

原本の著作権は **Icom Inc.** に帰属します。PDF の権限ビットは `copy/extract` と `print` を許可する一方、`modify` と `assemble`（ページの分割・再結合）を禁止しています。
そのため本配布パッケージには：

- 元 PDF、回路図ページ画像、ページ単位の文字レイヤー全文（`data/extracted/`）は含みません；
- 構造化派生データと、検証用の**単行の短い引用**のみを含みます；
- ページ番号は利用者が用意した正規版 PDF を指します。

詳細は `NOTICE` を参照してください。

---

## 免責 / 免責承諾 / Disclaimer

**ZH**：本 Skill 与相关工具仅提供技术参考，不构成维修结论。因技术判断错误、误操作或依据本资料作出决定而造成的设备损坏、人身伤害或经济损失，提供者不承担任何责任。实际故障请由具备资质的人员结合官方手册与实测数据自行判断。

**JA**：本 Skill および関連ツールは技術参考資料のみを提供し、修理上の結論を示すものではありません。技術的判断の誤り、誤操作、または本資料に基づく判断により生じた機器の損傷、人身事故、経済的損失について、提供者は一切の責任を負いません。実際の故障は、資格を有する技術者が公式サービスマニュアルと実測データに基づき自ら判断してください。

**EN**: This Skill and the accompanying tools provide technical reference only and do not constitute a repair diagnosis. The provider accepts no liability for equipment damage, personal injury, or financial loss arising from incorrect technical judgement, misuse, or decisions based on this material. Actual faults must be assessed independently by qualified personnel using the official service manual and measured data.
