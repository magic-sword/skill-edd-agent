# Agent Skill 設計思想 (Design Philosophy)

本プロジェクトにおける Google ADK 2.0 および Anthropic 標準（Markdown-First & Progressive Disclosure）スキルの設計思想とベストプラクティスを記録します。

---

## 0. プロジェクトの目的と設計哲学 (Project Vision & Core Purpose)

### 🎯 プロジェクトの北極星 (North Star)
本プロジェクトの究極の目的は、**「AI エージェントが自らのスキル（手順書・ドメイン知識・決定論的スクリプト）を自律的にテスト・診断・修復・進化させる自己進化システム（Self-Evolving Agentic Ecosystem）」** の構築です。

### ⚖️ 最重要トレードオフの原則 (The Core Trade-off)
一般的なソフトウェア開発では「DRY原則（重複排除・共通ライブラリ化）」が重視されますが、本プロジェクトでは **「自己改善の局所性（Locality of Mutation）と安全な隔離（Isolation）」を DRY原則よりも上位の原則** として優先します。

* **なぜパッケージに個別処理を集約してはならないのか？**:
  1. **探索空間の極小化 (Search Space Localization)**: エージェントがバグを修正したり性能を改善する際、変更対象が `skills/<skill-name>/` 内に閉じていれば、迷走せず迅速・正確に修正を完了できます。
  2. **爆発半径の極小化 (Blast Radius Minimization)**: スキル内のスクリプトが自己改善の試行錯誤で一時的に壊れても、共通パッケージや他のスキルを巻き込んでシステム全体が停止するリスクをゼロにします。
  3. **サンドボックス評価の容易性 (Safe Sandboxing & Rollback)**: スキルが単一ディレクトリで完結しているため、仮想環境（`LocalWorkspaceEnv`）に安全に複製して何度でもテスト・評価・ロールバックが可能です。
  4. **ポータビリティの保証 (Drop-in Portability)**: スキルが外部パッケージに直接依存しないことで、Claude Code, Antigravity, Cursor, Google ADK 等のあらゆる環境へ zip 1つで即座に配布・利用できます。

---

## 1. コア思想

### ① 単一真実源の原則 (Single Source of Truth ➔ Markdown-First)
* 仕様書兼プロンプトである **`SKILL.md` を唯一の真実源** とし、自然言語（Markdown）とコード（Python）のシームレスな統合を図ります。

### ② Progressive Disclosure（3層リソース分離）
* コンテキストウィンドウの効率化と信頼性の両立を図るため、スキル資産を3層に分離します：
  1. **Level 1: YAML Frontmatter**（常時ロード: `name`, `description`）
  2. **Level 2: SKILL.md 本文**（トリガー時ロード: 意思決定ツリー、手順、ガイドライン）
  3. **Level 3: 3層リソース**（オンデマンド実行・ロード）
     - `scripts/`: 決定論的Python/Bashスクリプト
     - `references/`: ドメイン知識・API仕様・スキーマ
     - `assets/`: 出力用テンプレート・素材
     - `tests/`: 契約テストおよびシミュレーション評価データ（`*.evalset.json`）

### ③ Google ADK 2.0 ネイティブ統合 (`SkillToolset`)
* 全スキルの Python 関数を直接 `FunctionTool` として一括展開するアンチパターン（Context Bloat）を排除し、Google ADK 2.0 標準の `SkillToolset` による Progressive Disclosure ライフサイクル（`list_skills` ➔ `load_skill` ➔ `load_skill_resource` ➔ `run_skill_script`）を採用。
* エージェント起動時のコンテキスト消費を極小化しつつ、決定論的スクリプトのブラックボックス実行と安全なパス解決を実現。

### ④ スキルの完全ポータビリティと個別ロジックの隔離 (Self-Evolution Isolation)
* 各スキルは単体で外部プラットフォーム（Claude Code, Antigravity, Cursor, ADK 等）へドロップイン可能な自己完結性を持つ。
* **自己改善エージェントの探索境界**:
  エージェントが特定のスキルを自律改善する際、修正対象の探索空間を `skills/<skill-name>/` 内に閉じることで、変更の局所化（Locality）と爆発半径（Blast Radius）の極小化を実現。
* **過度なパッケージ集約の禁止 (Anti-Pattern)**:
  「共通化可能」という理由だけでスキル固有の個別処理を pip パッケージ（`edd-agent-tools`）へ移転・集約することを厳禁とする。パッケージは不変の評価・実行プラットフォームに徹し、個別業務ロジックはスキル内にカプセル化する。
* スキル内のスクリプトは外部ライブラリへの直接 import を排除し、Python 標準ライブラリのみ、または統合 CLI `edd` の subprocess 呼び出しで動作する疎結合な設計を徹底。

### ⑤ 4次元ネガティブ・ハーネス (`When NOT to Use` による過剰適用防止)
* 単なる適用条件（When to use）だけでなく、以下の4軸から客観的な除外条件（When NOT to use）を導出し、過剰適用（Over-tooling）や競合による誤発火を防止：
  1. **粒度境界 (Granularity)**: 単発のワンライナーや標準OSコマンドで完結する軽微なタスク。
  2. **技術的限界 (Out-of-Scope)**: ドメイン範囲外の高度な変換や別領域の処理。
  3. **ライフサイクル分離 (Lifecycle)**: 前後のフェーズ（作成、診断、評価、最適化）の住み分け。
  4. **インベントリ照合 (Inventory)**: 既存スキルで既にカバーされているタスク。

### ⑥ 4段階品質保証パイプライン (4-Stage Quality Gate)
* スキルの自律生成からマウントまでの品質を保証する4段階の防壁：
  - **Stage 1 (Authoring & Scaffolding)**: `SKILL.md` + 3層リソースの論理設計と雛形生成（エージェント + `skill-creator`）
  - **Stage 2 (Static Validation)**: `SkillValidator` による静的リンター（構文・実在整合性・Imperative文体・DAG依存関係）
  - **Stage 3 (Contract & Multi-Layer Evaluation)**: サンドボックス環境（`LocalWorkspaceEnv`）での契約テスト（I/O型検査）およびシミュレーション評価（Trigger / Trajectory / Golden）
  - **Stage 4 (Self-Healing Loop & Cascade Gating)**: 失敗診断（`SkillDiagnoser`）➔ 修正 ➔ 連鎖回帰テスト（`CascadeTestRunner`）➔ Tier 昇格

### ⑦ 動的ディスパッチ (Dynamic Dispatch) ＆ 統合 CLI (`edd`)
* スキルが自律的に増殖・追加されてもパッケージ本体の再インストールやコード修正を一切不要とするため、ファイルシステムベースの動的ディスカバリ（`edd run <skill-name>` / `edd <skill-name>`）を採用。
* エージェントの認知負荷を最小化し、スキル名と実行コマンドの 1:1 対応を実現。

---

## 2. システム・アーキテクチャのレイヤード構造

```
edd_agent_tools/
├── core/           # 共通ドメインモデル (Skill, SkillSpec, SkillTier), 状態管理 (SkillsState), Protocols
├── skills/         # パーサー, AST バリデータ (SkillValidator), 雛形生成 (SkillCreationEngine)
├── evaluation/     # 契約テスト (ContractTestRunner), シミュレーション, 診断 (SkillDiagnoser), 最適化 (SkillOptimizer)
├── adk/            # Google ADK 2.0 ネイティブ Toolset (EddSkillToolset)
├── mcp/            # FastMCP サーバー (edd-agent-mcp)
└── cli/            # 統合 CLI (edd run/init/validate/package/eval/tier-gate/diagnose/optimize/list)
```

---

## 3. スキルフォルダ構造の規約 (Standard Layout)

```
src/skills/{skill-name}/
  SKILL.md       # YAML Frontmatter ('This skill should be used when...') + Markdown仕様書 (SSOT)
  scripts/       # 決定論的スクリプト（直接実行可能・CLI対応・Zero-dependency）
    {skill_name}.py
  references/    # ドメイン知識・仕様・スキーマ（オンデマンド参照）
    guide.md
  assets/        # 出力用テンプレート・素材（任意・空ディレクトリ不可）
  tests/         # 評価データセット（{skill_name}_contract.evalset.json 等）
```
