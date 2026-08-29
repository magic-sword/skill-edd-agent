import json
from typing import Dict, Any
from edd_agent_tools.evaluation.models import EvalDetailReport


class DiagnosisPrompter:
    """テスト失敗レポートおよびスキル資産を分析し、LLM診断用プロンプトを構築するクラス。"""

    def build_prompt(
        self,
        skill_name: str,
        test_type: str,
        report: EvalDetailReport,
        design_content: str,
        spec_content: str,
        source_files: Dict[str, str]
    ) -> str:
        """診断プロンプトを構築します。"""
        failed_cases_formatted = []
        for fc in report.failed_cases:
            fc_dict = {
                "case_id": fc.case_id,
                "input_params": fc.input_params,
                "expected_output": fc.expected_output,
                "actual_output": fc.actual_output,
                "error_type": fc.error_type,
                "error_message": fc.error_message,
                "traceback": fc.traceback
            }
            failed_cases_formatted.append(fc_dict)

        failed_cases_json = json.dumps(failed_cases_formatted, indent=2, ensure_ascii=False)

        source_code_blocks = []
        for rel_path, content in source_files.items():
            source_code_blocks.append(f"### File: {rel_path}\n```python\n{content}\n```")
        source_code_str = "\n\n".join(source_code_blocks)

        prompt = f"""あなたは自己改善型AIエージェントの「根本原因診断および改善計画策定エンジン（Diagnostic Engine）」です。
提供されたテスト失敗レポート、仕様書（SKILL.md）、実装ソースコードを多角的に分析し、テストを確実に合格させるための構造化された改善計画（ImprovementPlan）を策定してください。

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

## 3. スキルの仕様書 (SKILL.md)
```markdown
{spec_content}
```

---

## 4. スキルの実装ソースコード (scripts/ 配下)
{source_code_str}

---

## 5. 診断および改善計画の策定ルール (厳守事項)
1. **仕様層（SKILL.md）の修正**:
   * トリガー説明（description）、意思決定ツリー、または手順指示の不備が原因である場合は、`target_layer: "spec"` を選択し、`spec_patch` を提供してください。
2. **ロジック層（scripts/）の修正**:
   * `scripts/*.py` の実装ミス（ゼロ除算、KeyError、型変換漏れ、未ハンドルの条件分岐など）が原因である場合は、`target_layer: "script"` を選択し、修正対象ファイル名と修正指示（`script_patch`）を提供してください。
3. **テスト期待値側の誤り**:
   * スキルの実装や仕様が正しく、テストケース（evalset.json）側の期待値指定ミスや不合理なアサーションが原因である場合は、`target_layer: "test_case"` を選択してください。

---

## 6. 出力フォーマット
必ず以下の JSON 構造（ImprovementPlan スキーマ）のみを出力してください。Markdown のコードブロック ```json ... ``` で囲んで出力してください。

```json
{{
  "skill_name": "{skill_name}",
  "test_type": "{test_type}",
  "verdict": "needs_improvement",
  "target_layer": "script",
  "failure_category": "logic_exception",
  "root_cause": "根本原因の詳細な分析サマリー",
  "recommended_action": "推奨される具体的アクション",
  "spec_patch": null,
  "script_patch": {{
    "target_file": "scripts/main.py",
    "problematic_code_snippet": "問題のあるコード",
    "fix_instructions": "具体的な修正指示",
    "suggested_code": "修正後コードスニペット"
  }},
  "test_case_patch": null
}}
```
"""
        return prompt
