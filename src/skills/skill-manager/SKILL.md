---
name: skill-manager
description: スキルのTier（Read-Only, Draft-Only, Action-Allowed）を管理し、権限ポリシーを取得・変更するためのスキル。
---

# スキル管理スキル

このスキルは、ワークスペース内の各スキルの信頼性を示す「Tier」を一括管理します。また、各Tierに応じたツール利用権限のポリシーを提供し、エージェントが安全にツールを動作できるように支援します。

## 管理対象のTier
1. **Tier 1 (Read-Only)**: 安全な読み込みツールのみ許可。
2. **Tier 2 (Draft-Only)**: 読み込みに加え、ファイルへのドラフト編集を許可（シェルの実行は不可）。
3. **Tier 3 (Action-Allowed)**: 外部連携やシェルコマンド実行を含むすべての操作を許可。

## トリガー条件
以下のいずれかの表現または類似するユーザー指示によってスキルがトリガーされます。

* 「スキルのTier情報を管理・表示して」
* 「[スキル名] のTierを [1|2|3] に変更して」
* 「現在の全スキルのTier一覧をリストアップして」
* 「[スキル名] の現在のTierを取得して」

## 使用手順

1. **スキルの登録 / Tierの更新**:
   エージェントまたは外部ワークフローは `scripts/manage_skills.py` を実行して、スキルのステータスを変更または取得します。

   * **新規スキルの登録**:
     ```bash
     python src/skills/skill-manager/scripts/manage_skills.py register <スキル名>
     ```
   
   * **Tierの変更 (昇格・降格)**:
     ```bash
     python src/skills/skill-manager/scripts/manage_skills.py set-tier <スキル名> <1|2|3>
     ```
   
   * **現在のTierの取得**:
     ```bash
     python src/skills/skill-manager/scripts/manage_skills.py get-tier <スキル名>
     ```
   
   * **登録スキル一覧の表示**:
     ```bash
     python src/skills/skill-manager/scripts/manage_skills.py list
     ```

   * **ファイル変更の検知に伴うメタデータ（ハッシュ）更新**:
     ```bash
     python src/skills/skill-manager/scripts/manage_skills.py update-meta <スキル名>
     ```

2. **エージェントからの動的権限制御 (Python API)**:
   Pythonコードから `scripts/security.py` に含まれる API をインポートして使用することで、ADK のツールセットを Tier に応じて動的に制限できます。

## 管理ファイルの構成

### 1. スキルレジストリ・メタファイル (`src/skills_registry.json`)
全スキルの信頼性（Tier）および整合性を一括管理する中央メタファイル（Single Source of Truth）です。外部エージェントやポリシー制限モジュールは、このファイルを参照して各スキルの権限を動的に評価します。

#### ファイル構造と構成項目
```json
{
  "skills": {
    "skill-generator": {
      "tier": 3,
      "last_tested": "2026-06-30T08:30:00Z",
      "file_hashes": {
        "SKILL.md": "sha256...",
        "scripts/generate_skill.py": "sha256..."
      }
    }
  }
}
```

*   `skills`: 登録されているスキル名をキーとするオブジェクト。
*   `tier`: スキルの現在の信頼度レベル（1 = Read-Only, 2 = Draft-Only, 3 = Action-Allowed）。
*   `last_tested`: スキルに対するテスト（トリガー評価や機能テストなど）に最後に合格したタイムスタンプ。
*   `file_hashes`: スキルのソースコード（`SKILL.md` や `scripts/` 配下のファイル）の完全性検証用ハッシュマップ（SHA-256）。

#### ライフサイクルと状態遷移ルール

スキルのメタデータは、開発・運用のフェーズに応じて以下のように遷移します。

1.  **初期登録 (新規スキルの追加)**
    *   新しく生成されたスキルは、デフォルトで **Tier 1 (Read-Only)** として登録されます。
    *   登録時にその時点での全ファイルのSHA-256ハッシュが計算され、`file_hashes` に記録されます。
2.  **試験合格による昇格 (Promotion)**
    *   `trigger-evaluator` などの評価ツールでテストを実行し、業界基準の合格ライン（トリガー精度 90% 以上など）をクリアすると、Tierの昇格が許可されます。
    *   昇格時に `last_tested` が現在時刻に更新され、最新のファイルハッシュが再記録されます。
3.  **ソースコード修正に伴う自動降格 (Demotion) と再試験**
    *   エージェントがスキルを実行する際、または管理スクリプトが定期実行される際、現在のファイルのハッシュ値と `skills_registry.json` に記録されたハッシュ値の比較が行われます。
    *   **ハッシュ値の不一致が検出された場合（＝許可なくコードが修正された場合）**、改ざんや未検証の機能追加とみなされ、**即座に Tier 1 (Read-Only) へ降格（または登録保留）** されます。
    *   再度 Tier を昇格させるには、再試験（トリガー精度・機能評価）に合格する必要があります。

### 2. 権限ポリシー定義 (`src/skills/skill-manager/assets/policy.json`)
各Tierにおいてエージェントに許可するツールのリストを定義します。

```json
{
  "tiers": {
    "1": {
      "name": "Read-Only",
      "allowed_tools": ["read_file", "list_dir", "view_file", "load_skill", "load_skill_resource", "list_skills"]
    },
    "2": {
      "name": "Draft-Only",
      "allowed_tools": ["read_file", "list_dir", "view_file", "load_skill", "load_skill_resource", "list_skills", "write_file", "edit_file"]
    },
    "3": {
      "name": "Action-Allowed",
      "allowed_tools": ["*"]
    }
  }
}
```

*   `allowed_tools`: 該当Tierで許可するツールの名前のリスト。`*` は全ツール（制限なし）を意味します。セキュリティフィルタはこの定義に基づいて、エージェントが利用可能なツールセットを動的にラップ・制限します。

## AIエージェント向け使用方法 (run_skill_script)

このスキルを実行する際は、`run_skill_script` ツールを使用して、必ず以下の引数構造（JSON）で実行してください。入力・出力はJSONファイルを介してパスでやり取りします。

```json
{
  "skill_name": "skill-manager",
  "file_path": "scripts/manage_skills.py",
  "args": {
    "--input_json": "/workspace/src/.workflow_tmp/<スキル名>/<入力ファイル名>.json",
    "--output_json": "/workspace/src/.workflow_tmp/<スキル名>/<出力ファイル名>.json"
  }
}
```

