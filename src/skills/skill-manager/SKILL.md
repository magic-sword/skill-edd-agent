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

### 1. スキルレジストリ (`src/skills_registry.json`)
全スキルのメタデータを一括管理する中央ファイルです。

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

* `tier`: スキルの現在の信頼度レベル（1, 2, 3）。
* `last_tested`: 最後にテスト検証に合格したタイムスタンプ。
* `file_hashes`: スキルディレクトリ配下にある各ファイルの名前と、その時点でのSHA-256ハッシュ値（変更検知に利用されます）。

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

* `allowed_tools`: 許可するツールの名前のリスト。`*` は全ツール（制限なし）を意味します。

