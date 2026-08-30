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

## 2. コア設計思想 (Core Design Philosophy)

```mermaid
flowchart TD
    subgraph Core_Concepts [3つのコア思想]
        A["1. 単一真実源 (Markdown-First)"] --> A1["SKILL.md が仕様とプロンプトの唯一の真実源"]
        B["2. 3層リソース分離 (Progressive Disclosure)"] --> B1["scripts/ (実行), references/ (知識), assets/ (素材)"]
        C["3. 4段階品質保証パイプライン (Stage-Gate)"] --> C1["論理抽出 ➔ 決定論的結合 ➔ 静的リンター ➔ 多層EDDテスト"]
    end
```

1.  **単一真実源の原則 (Markdown-First)**
    *   スキルの仕様定義はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化し、可読性と保守性を最大化。
2.  **3層リソース分離 (Progressive Disclosure)**
    *   コンテキストウィンドウを圧迫しない3層リソース構造：
        - `scripts/`: 直接実行可能な決定論的スクリプト
        - `references/`: LLMがオンデマンドで読む詳細ドキュメント・スキーマ
        - `assets/`: 成果物にコピー・流用するためのテンプレート・素材
3.  **4段階品質保証パイプライン (Stage-Gate)**
    *   **Stage 1**: `SkillLogicDraft` (Pydanticモデル) による論理・決定木・リソース計画の構造化抽出
    *   **Stage 2**: `SkillTemplateEngine` による決定論的テンプレートレンダリング
    *   **Stage 3**: `SkillValidator` による静的リンター（構文・実在整合性・Imperative文体）& 自動修復ループ
    *   **Stage 4**: 多層EDDテスト（Trigger 90%精度 + Contract + Golden + Trajectory + Judge）による Tier 昇格防壁

---

## 3. 実装スキル一覧 (Skills & Workflows)

### 🛠 メタスキル & ドメインスキル
| スキル名 | 役割 / 機能 | 特徴 |
| :--- | :--- | :--- |
| **`skill-creator`** | スキル設計・雛形生成・配布パッケージャ | Anthropic & Google ADK 準拠のスキル作成ガイド、意思決定ツリー設計、雛形自動生成、高速静的検証、および配布用 ZIP パッケージャ。 |
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

### Python API による自律スキル生成
```python
from edd_agent_tools.skills import create_skill

result = create_skill(
    prompt="PDFファイルの回転・結合・テキスト抽出を行う pdf-tools スキルを作成してください。",
    name="pdf-tools",
    pattern="workflow"
)
print(result)
```


### テストスイートの実行
```bash
pytest tests/ -v
```
