# Self-Evolving EDD Agent
**〜Anthropic公式標準の Markdown-First & Progressive Disclosure を備えた、Google ADKスキルの自己進化型 評価駆動開発（EDD）エージェント〜**

本プロジェクトは、Google の **Agent Development Kit (ADK) 2.0** および Anthropic の **Progressive Disclosure（段階的情報開示）** 設計思想を融合し、AIエージェントが自律的に新しいスキル（機能）を設計、開発、テスト、評価し、適切な Tier 状態管理を経て自身へマウント（統合）する **「自己進化型 評価駆動開発 (Self-Evolving EDD: Evaluation-Driven Development) エージェント」** です。

Kaggle Competition: [Vibe Coding Agents Capstone Project (Freestyle Track)](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project) 提出プロジェクト。

---

## 1. 背景と中核コンセプト (Background & Core Concept)

### 💡 ADKの思想への共感と課題意識
Googleの **ADK 2.0** が提唱する「スキル」によるエージェント構築は、エージェント開発の理想形です。段階的にスキルを適用することで、エージェントは強化学習のオプション（スキル）獲得と非常に近い形で、人間がメンテナンス可能かつ他エージェントに継承可能な「スキル」という形で知識を蓄積できます。

しかし、従来のスキル開発では以下のような課題がありました：
*   **多層ボイラープレートの肥大化**: 多層ラッパー（`models.py`, `handler.py`, `executor.py`, `nodes/`）が乱立し、トークン消費と保守負荷が増大。
*   **EDD（評価駆動開発）の難しさ**: AIの生成物を的確に検証し、ハルシネーションを防ぐハーネス（制約）を設計するのは人間にとっても極めて困難。

> [!IMPORTANT]
> **本プロジェクトの結論**
> エージェント開発者が何よりもまず優先して構築すべきなのは、**「評価駆動開発を自律的に行うメタエージェント」**です。
> 人間の自然言語指示（Vibe）を受け取り、エージェント自身が安全に **Markdown-First** かつ **3層リソース分離（Progressive Disclosure）** でスキルを生成・テスト・評価し、テストをクリアしたスキルだけを自律的に自身の武器（ツール）としてマウント（統合）する。これこそが、本プロジェクトが提案する **「自己進化型 EDD エージェント」** です。

---

## 2. 責務分離とコアアーキテクチャ (Two-Tier Architecture)

本システムは、**「不変のプラットフォーム基盤（pip: `edd-agent-tools`）」** と **「エージェントが自律的に所有・進化させるスキル資産（`src/skills/`）」** を厳密に分離しています。

```mermaid
flowchart TD
    subgraph PlatformLayer ["不変プラットフォーム層 (pip: edd-agent-tools)"]
        Validator["SkillValidator (AST/構文静的リンター)"]
        Runners["ContractTestRunner & SimulationEvalRunner (サンドボックス実行)"]
        StateEngine["SkillsState & DAG Validator (状態・Tier 1~3 管理)"]
        Packager["SkillPackager (安全な ZIP アーカイブ生成)"]
        ADKAdapter["ADK Adapter (create_adk_skill_toolset, EddSkillRegistry, EddSkillToolset)"]
        UnifiedCLI["統合 CLI edd (動的ディスパッチ)"]
    end

    subgraph SkillAssets ["自己改善スキル資産層 (src/skills/)"]
        Creator["skill-creator: スキル設計・Markdownテンプレート・雛形生成"]
        Evolver["skill-evolver: 失敗診断・自己修復ループ・Tier昇格"]
        DomainSkills["case-converter 等の実用ドメインスキル"]
    end

    PlatformLayer -->|基盤SDK・テストハーネス提供| SkillAssets
    SkillAssets -->|自己改善ループ (Markdown/Scripts/Assets修正)| SkillAssets
```

1.  **単一真実源の原則 (Markdown-First & Template Assets)**
    *   スキルの仕様定義はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化。パッケージ内部に公式標準の雛形テンプレート（4大パターン）を同梱し、外部プロジェクトからの拡張も可能。
2.  **3層リソース分離 (Progressive Disclosure)**
    *   コンテキストウィンドウを圧迫しない3層リソース構造：
        - `scripts/`: 直接実行可能な決定論的スクリプト（Zero-dependency, CLI対応）
        - `references/`: LLMがオンデマンドで読む詳細ドキュメント・スキーマ
        - `assets/`: 成果物にコピー・流用するためのテンプレート・素材
3.  **自己完結型 EDD テスト (Self-Contained Evaluation)**
    *   各スキルディレクトリ配下の `tests/*.evalset.json` に契約テスト・シミュレーション評価ケースを同梱し、局所的・決定論的に品質を検証。

---

## 3. 実装スキル一覧 (Skills & Workflows)

### 🛠 メタスキル & ドメインスキル
| スキル名 | 役割 / 機能 | 特徴 |
| :--- | :--- | :--- |
| **`skill-creator`** | スキル設計・雛形生成・配布パッケージャ | Anthropic & Google ADK 準拠の対話的スキル作成ガイド、`assets/templates/`（4大パターン）を活用した雛形生成、AST静的検証、配布用 ZIP パッケージャ、契約テスト完備。 |
| **`skill-evolver`** | 統合評価・失敗診断・自己修復・Tier昇格 | 契約テスト・シミュレーション評価の実行、失敗コンテキスト診断、自律的自己修復ループ、依存連鎖回帰テスト（Cascade Testing）、および Tier 1〜3 昇格判定を統合オーケストレーション。 |
| **`case-converter`** | テキストケース変換（ゴールデンサンプル） | camelCase, snake_case, PascalCase, kebab-case, CONSTANT_CASE, Title Case 等の相互変換を行う Zero-dependency 実用スキル。 |

---

## 4. クイックスタート (Quick Start)

### パッケージのインストール
```bash
pip install -e edd-agent-tools
```

### 統合 CLI (`edd`) によるスキル操作
```bash
# 1. スキルの直接実行 (動的ディスパッチ)
edd run case-converter --input "hello_world" --format camel
# またはスキル名を直接サブコマンドとして指定可能 (Git プラグイン方式)
edd case-converter --input "hello_world" --format camel

# 2. 新規スキル雛形の初期化
edd init my-new-skill --pattern workflow

# 3. 高度な静的バリデーション (Linter / AST 解析)
edd validate src/skills/my-new-skill

# 4. 配布用 ZIP パッケージング
edd package src/skills/my-new-skill --out dist

# 5. EDD 多層評価 & Tier 昇格 & 失敗診断 & 一括最適化
edd eval my-new-skill --type all
edd tier-gate my-new-skill --tier 1
edd diagnose my-new-skill
edd optimize my-new-skill --tier 1
```

### Google ADK 2.0 エージェント / A2A サーバーの起動
```bash
# A2A 互換サーバーの起動 (ポート 8001)
python src/main.py
```

### テストスイートの実行
```bash
pytest
```
