---
name: skill-generator
description: 指定されたディレクトリに、ユーザーの指示に応じた新しいスキル（SKILL.md, scripts/****.py, references/*, assets/*, tests/****.evalset.json）を自動生成するスキル。
---

# スキル生成スキル

このスキルは、ユーザーの指定した要件や説明に基づいて、新しい Google ADK 互換のスキルを自律的かつ評価駆動（自己修復ループ付き）で生成します。

生成されるアセットは以下の通りです：
* `SKILL.md`（YAMLフロントマター、使用手順、権限レベルおよび評価手法）
* `scripts/****.py`（スキルが処理を実行するための実体スクリプト）
* `references/` 内のファイル（スクリプト実行時に参照する大容量の参考資料。レシピ、チェックリスト、仕様書など）
* `assets/` 内のファイル（プロンプトや設定などのアセット）
* `tests/****.evalset.json`（AgentEvaluator による評価に必要なデータセット）

## 使用手順

1. **スクリプトの実行**:
   エージェントは `scripts/generate_skill.py` を実行するために `EnvironmentToolset`（`Execute`）ツールを呼び出します。
   引数として、新しいスキルの生成先ディレクトリを指定する `--output_dir` と、作成したいスキルの説明や要件を指定する `--prompt` を渡します。必要に応じて使用するモデルを指定する `--model` も指定可能です。

   コマンドの実行例:
   ```bash
   python src/skills/skill-generator/scripts/generate_skill.py \
     --output_dir src/skills/cooking-helper \
     --prompt "レシピに従って料理をサポートするスキル"
   ```

2. **処理の確認**:
   スクリプトは、内部で動的に **開発者エージェント (SkillDeveloperAgent)** を起動します。このサブエージェントは自律的にファイルを書き出し、生成した Python スクリプトを実行するなどの「動作確認」を行い、初期エラーや不具合のないスキル一式を出力します。
   処理が正常に完了すると、指定のディレクトリに動作するスキル一式が出力されます。出力された結果をユーザーに報告してください。

## AIエージェント向け使用方法 (run_skill_script)

このスキルを実行する際は、`run_skill_script` ツールを使用して、必ず以下の引数構造（JSON）で実行してください。

```json
{
  "skill_name": "skill-generator",
  "file_path": "scripts/generate_skill.py",
  "args": {
    "--output_dir": "src/skills/<作成したいスキル名>",
    "--prompt": "<作成したいスキルの仕様要件や説明>"
  }
}
```

