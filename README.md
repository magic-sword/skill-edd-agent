# Self-Evolving EDD Agent
**Google ADK 2.0 & Anthropic スキル標準に準拠した、AI エージェント自己進化・評価駆動開発（EDD）フレームワーク**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Google ADK 2.0](https://img.shields.io/badge/Google%20ADK-2.0-green.svg)](https://github.com/google/adk)
[![A2A v1.0.0](https://img.shields.io/badge/A2A-v1.0.0-orange.svg)](https://github.com/google/adk)

本プロジェクトは、AI エージェントが自らのスキル（手順書・ドメイン知識・決定論的スクリプト）を**自律的にテスト・診断・修復・進化させる自己進化システム（Self-Evolving Agentic Ecosystem）**を構築するためのフルスタック基盤です。

Google 『Agent Skills』ホワイトペーパー（May 2026）が提唱する **「Evaluation Gating（テスト全勝を必須とする品質防壁）」** を中核に据え、エージェントが壊れたコードやハルシネーションをライブラリにコミット・昇格することを決定論的に防止します。

---

## 💡 このプロジェクトで何ができるのか？

1. **自律的なスキルの設計・生成 (Autonomous Skill Authoring)**
   - 自然言語の指示から、Google ADK 2.0 & Anthropic 標準（Markdown-First & Progressive Disclosure）のスキル雛形と決定論的スクリプトを自動生成。
   - **EDD インバージョン**: 3正例＋3負例（計6ケース）のテストケース先行策定により、誤発火（Over-trigger）やハルシネーションを未然に防止。
2. **厳格な多層テスト評価防壁 (Evaluation Gating)**
   - Google ADK 2.0 公式評価器（`TrajectoryEvaluator`, `ResponseEvaluator`, `RubricBasedFinalResponseQualityV1Evaluator`）と完全統合。
   - 契約テスト、入出力検証、持続的信頼性（$pass^k$）、5〜15 スキル同時ロード時のコンテキスト汚染（Context Rot）検知、敵対的プロンプト注入耐性を自動評価。
3. **自律的な失敗診断と自己修復 (Self-Healing Loop)**
   - テスト失敗時に構造化診断ログ（`FailedCaseDetail`）を自動抽出し、エージェントがプロンプト（`SKILL.md`）やスクリプトをピンポイントで自己修復。
   - 依存関係の連鎖回帰テスト（Cascade Testing）を自動実行し、既存スキルへの悪影響ゼロを確認した上でのみ Tier 昇格。
4. **外部プロジェクト連携 (Workspace / Layered Linking)**
   - ローカルの別リポジトリ（業務プロジェクト等）から本リポジトリのスキル資産を透過的に利用。
   - **現場でスキルを進化させても、ローカルプロジェクトの Git 差分は完全にゼロ（クリーン）**。修正差分は本リポジトリ側にのみ現れ、即座に GitHub へ Pull Request を起票可能。
5. **A2A (Agent-to-Agent) & Agent Registry 即時公開**
   - A2A v1.0.0 互換サーバー（`python src/main.py`）により、外部エージェントと標準プロトコルで通信可能。
   - `agent-card.json` の自動同期、およびチェックサム・署名付きのレジストリ公開（`edd publish`）に対応。

---

## 🚀 クイックスタート (Quick Start)

### 1. インストール
```bash
git clone https://github.com/magic-sword/skill-edd-agent.git
cd skill-edd-agent
pip install -e edd-agent-tools
```

### 2. スキルを動かす (動的ディスパッチ CLI)
統合 CLI `edd` を使って、登録済みスキルを即座に実行できます：
```bash
# テキストを camelCase に変換
edd run case-converter --to camel "hello_world_example"

# 機密情報をサニタイズ (API キーのマスキング)
edd run secret-sanitizer --input "My secret is sk-1234567890abcdef"
```

### 3. スキルの自己改善・評価・Tier昇格を実行する
```bash
# 1. 契約テストおよび白書 4大 Eval Coverage チェックリストを実行
edd eval case-converter --coverage

# 2. テスト失敗時の構造化診断
edd diagnose case-converter

# 3. 最適化・連鎖回帰テスト・Tier 1 昇格
edd optimize case-converter --tier 1
```

### 4. 外部の自社プロジェクトから利用する (Workspace Link)
別リポジトリで本リポジトリのスキルを利用し、現場で進化させる最も推奨される運用方法です：
```bash
cd /path/to/my-local-project

# 1. 上流リポジトリをリンク (1コマンドで .edd.json 生成 & .gitignore 自動追記)
edd link /path/to/skill-edd-agent

# 2. リンク状態と利用可能スキルの確認
edd status

# 3. 現場でスキルを改善した後、上流リポジトリの Git 差分を確認してプッシュ
edd upstream status
edd upstream push --branch fix/improve-skill --message "fix: improve boundary cases" --pr
```
※ 詳しい手順は [外部プロジェクト連携ガイド](edd-agent-tools/src/edd_agent_tools/docs/workspace_linking_guide.md) をご覧ください。

---

## 🛠 組み込みスキル一覧 (Built-in Skills)

| スキル名 | 役割 / 機能 | Tier | 特徴 |
| :--- | :--- | :---: | :--- |
| **`case-converter`** | 識別子・文字列ケース相互変換 | Tier 1 | camel, snake, Pascal, kebab, CONSTANT 等の高速変換。Zero-dependency。 |
| **`secret-sanitizer`** | 機密情報検出・マスキング | **Tier 3** | APIキー、トークン、パスワード、JWT、IPアドレスを自動秘匿。全防壁突破。 |
| **`markdown-table-formatter`** | Markdown テーブル整形・整列 | Tier 1 | テーブルの列幅均一化とアライメント（左・中・右）パディング。 |
| **`text-statistics-analyzer`** | テキスト統計・読了時間計測 | Tier 1 | 文字数、単語数、文数、段落数、CJK/英語読了時間を決定論的に集計。 |
| **`skill-creator`** | スキル設計・雛形生成メタスキル | Tier 1 | EDD Inversion（3正例＋3負例）先行策定による対話型スキル作成。 |
| **`skill-evolver`** | 評価・診断・修復・Tier昇格メタスキル | Tier 1 | 多層評価、失敗コンテキスト診断、自律修復、連鎖回帰、Tier昇格を統合管理。 |
| **`skill-reviewer`** | スキル品質・過学習監査 (Critic) | Tier 1 | 白書品質基準、AST過学習スキャン、4大ルーブリックに基づく独立審査官。 |
| **`library-evolver`** | ライブラリ自己増殖メタスキル | Tier 1 | 白書 Section 6 Voyager パターン準拠。能力ギャップから新スキルを自律合成。 |
| **`trace-harvester`** | トレースからのスキル自動結晶化 | Tier 1 | 会話ログや実行トレースから再利用可能なスキル手順書・テストを自動抽出。 |

---

## 🏛️ アーキテクチャ (Two-Tier Architecture)

pytest や Ansible と同様、**「汎用不変ランタイム（pip: `edd-agent-tools`）」** と **「規約駆動コンテンツ（`src/skills/`）」** の疎結合分離モデルを採用しています。

```mermaid
flowchart TD
    subgraph PlatformLayer ["不変プラットフォーム層 (pip: edd-agent-tools)"]
        Validator["SkillValidator (AST/構文静的リンター)"]
        AdkEval["AdkEvalAdapter (Google ADK 2.0 純正 LLM Judge)"]
        SimRunner["SimulationEvalRunner (3大 Trajectory: EXACT / IN_ORDER / ANY_ORDER)"]
        ContractRunner["ContractTestRunner (pass^k 連続一貫性検証 & サンドボックス)"]
        CoLoadRunner["CoLoadedEvalRunner (Context Rot ベンチマーク)"]
        LinkManager["WorkspaceLinkManager (透過的マルチリポジトリ連携)"]
        StateEngine["SkillsState (Tier 1~3 管理 & DAG 解析)"]
        Optimizer["SkillOptimizer (自己改善ループ & Tier 昇格ゲート)"]
        UnifiedCLI["統合 CLI edd (CLI-as-an-API 動的ディスパッチ)"]
    end

    subgraph SkillAssets ["自己改善スキル資産層 (src/skills/)"]
        MetaSkills["skill-creator / skill-evolver / library-evolver"]
        DomainSkills["case-converter, secret-sanitizer, etc."]
    end

    PlatformLayer -->|SDK・テストハーネス・CLI提供| SkillAssets
    SkillAssets -->|自己改善ループ (SKILL.md / scripts / tests 修正)| SkillAssets
```

### 3段階の品質ラダー (The Read / Draft / Act Ladder)
* **Tier 1 (`READ_ONLY`)**: 静的検証（エラー0件）+ CLI契約テスト（100%合格）+ トリガー精度（90%以上）
* **Tier 2 (`DRAFT_ONLY`)**: ゴールデンデータセット評価（90%以上）+ 上位スキルの連鎖回帰テスト（100%パス）+ Co-loaded 共存テスト
* **Tier 3 (`ACTION_ALLOWED`)**: Trajectory 評価（`IN_ORDER` / `EXACT`）+ $pass^k$ 持続的一貫性（$k \ge 3$）+ 敵対的レッドチーミング + **人間の明示的承認（Human Sign-off: `--yes`）**

---

## 🤖 Google ADK 2.0 / A2A サーバーの起動

```bash
# 1. Google ADK 2.0 公式 CLI による対話実行 (App コンテナ経由)
adk run src

# 2. Google ADK 2.0 Web UI インスペクターの起動
adk web src

# 3. A2A (Agent-to-Agent) 互換 Web サーバーの起動 (ポート 8001)
python src/main.py
```

---

## 📚 ドキュメント一覧 (Documentation)

* 📖 **[外部プロジェクト連携ガイド](edd-agent-tools/src/edd_agent_tools/docs/workspace_linking_guide.md)**: ローカル業務プロジェクトでの利用と上流 Git 還元の完全ガイド。
* 📐 **[設計思想と設計哲学 (design_philosophy.md)](edd-agent-tools/src/edd_agent_tools/docs/design_philosophy.md)**: Two-Tier アーキテクチャ、単一真実源原則、リソース分離。
* 🧪 **[テストアーキテクチャ仕様 (test_architecture.md)](edd-agent-tools/src/edd_agent_tools/docs/test_architecture.md)**: Google ADK 2.0 公式 EvalSet SSOT と多層テスト評価仕様。
* 🛡️ **[開発ルール・システム制約 (AGENTS.md)](edd-agent-tools/src/edd_agent_tools/AGENTS.md)**: AI エージェントが遵守すべき開発制約とコード生成ルール。
* 🤝 **[貢献ガイドライン (CONTRIBUTING.md)](CONTRIBUTING.md)**: 開発者向けディレクトリ構成と PR 規約。

---

## 🧪 テストの実行

```bash
pytest tests/ -v
```

---

## 📄 ライセンス

本プロジェクトは [MIT ライセンス](LICENSE) の下で公開されています。
