import json
from typing import Any
from edd_agent_tools.evaluation.models import EvalDetailReport


class DiagnosisPrompter:
    """診断対象スキルのアセットおよびテスト失敗ログから Gemini 用プロンプトを生成するクラス。"""

    def build_prompt(
        self,
        skill_name: str,
        test_type: str,
        report: EvalDetailReport,
        design_content: str,
        spec_content: str,
        source_files: dict[str, str]
    ) -> str:
        """詳細なコンテキストと失敗ログを統合した診断プロンプトを構築します。"""
        
        # 失敗ケースのフォーマット
        failed_cases_formatted = []
        for i, fc in enumerate(report.failed_cases):
            fc_dict = {
                "case_index": i + 1,
                "eval_case_id": fc.eval_case_id,
                "function_name": fc.function_name,
                "inputs": fc.inputs,
                "expected": fc.expected,
                "actual": fc.actual,
                "error_type": fc.error_type,
                "error_message": fc.error_message,
                "traceback": fc.traceback
            }
            failed_cases_formatted.append(fc_dict)

        failed_cases_json = json.dumps(failed_cases_formatted, indent=2, ensure_ascii=False)

        # ソースコード一覧のフォーマット
        source_code_blocks = []
        for rel_path, content in source_files.items():
            source_code_blocks.append(f"### File: {rel_path}\n```python\n{content}\n```")
        source_code_str = "\n\n".join(source_code_blocks)

        prompt = f"""あなたは自己改善型AIエージェントの「根本原因診断および改善計画策定エンジン（Diagnostic Engine）」です。
提供されたテスト失敗レポート、設計仕様（design.json）、仕様書（SKILL.md）、実装ソースコードを多角的に分析し、テストを確実に合格させるための構造化された改善計画（ImprovementPlan）を策定してください。

---

## 1. 診断対象情報
* **スキル名**: `{skill_name}`
* **実行テスト種別**: `{test_type}`
* **テスト結果サマリー**: 全 {report.total} 件中 {report.passed} 件合格 / {report.failed} 件不合格（合格精度: {report.accuracy:.2%}）
* **サマリー詳細**: {report.details}

---

## 2. 不合格となったテストケース一覧 (Failed Cases)
```json
{failed_cases_json}
```

---

## 3. スキルの設計仕様 (assets/design.json)
```json
{design_content}
```

---

## 4. スキルの仕様書 (SKILL.md)
```markdown
{spec_content}
```

---

## 5. スキルの実装ソースコード (scripts/ 配下)
{source_code_str}

---

## 6. 診断および改善計画の策定ルール (厳守事項)
1. **場当たり的修正の禁止（単一真実源の維持）**:
   * `SKILL.md` のテキストだけを直接書き換える修正は**絶対に禁止**です。
   * トリガー説明（description）や入出力パラメータの不備が原因である場合は、`target_layer: "design"` を選択し、`design.json` を更新するための `design_patch` を提供してください（システムが後続で `skill-coder` & `skill-spec-writer` を呼び出し、一括再生成します）。
2. **ロジック層の修正**:
   * `scripts/nodes/*.py` の実装ミス（ゼロ除算、KeyError、型変換漏れ、未ハンドルの条件分岐など）が原因である場合は、`target_layer: "logic"` を選択し、修正対象ファイル名と修正指示（`logic_patch`）を提供してください。
3. **テスト期待値側の誤り**:
   * スキルの実装や設計が正しく、テストケース（evalset.json）側の期待値指定ミスや不合理なアサーションが原因である場合は、`target_layer: "test_case"` を選択してください。

---

## 7. 出力フォーマット
必ず以下の JSON 構造（ImprovementPlan スキーマ）のみを出力してください。Markdown のコードブロック ```json ... ``` で囲んで出力してください。

```json
{{
  "skill_name": "{skill_name}",
  "test_type": "{test_type}",
  "verdict": "needs_improvement",
  "target_layer": "design または logic または test_case または meta_skill",
  "failure_category": "trigger_mismatch または schema_validation または logic_exception または mock_unhandled または missing_implementation または test_expectation_bug",
  "root_cause": "なぜ失敗したのかの根本原因分析（詳細かつ論理的に記述）",
  "recommended_action": "後続フェーズで実行すべき推奨改善アクションの要約",
  "design_patch": {{
    "patch_type": "merge",
    "description": "更新後の説明文（必要な場合のみ）",
    "parameters_patch": null,
    "response_parameters_patch": null,
    "response_type_patch": null
  }},
  "logic_patch": {{
    "target_file": "scripts/nodes/ファイル名.py",
    "problematic_code_snippet": "修正対象の既存コード",
    "fix_instructions": "具体的な修正指示",
    "suggested_code": "修正後のコードスニペット"
  }},
  "test_case_patch": null
}}
```
"""
        return prompt
