import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from edd_agent_tools.skills.state import SkillsState
from edd_agent_tools.gemini import client, GeminiRequest
from edd_agent_tools.evaluation.models import (
    EvalCaseSet, EvalCase, TrajectoryEvalSet, TrajectoryEvalCase,
    ConversationTurn, SessionInput, ToolUse, IntermediateData
)


def _load_skill_context(skill_name: str) -> tuple[str, str]:
    """対象スキルの SKILL.md および scripts/ の要約コードを取得する。"""
    state = SkillsState()
    skill = state.get_skill(skill_name)
    if not skill:
        raise ValueError(f"Skill '{skill_name}' was not found in SkillsState.")

    skill_md = ""
    if skill.spec_path and Path(skill.spec_path).exists():
        skill_md = Path(skill.spec_path).read_text(encoding="utf-8")

    scripts_summary = []
    if Path(skill.scripts_dir).exists():
        for py_file in Path(skill.scripts_dir).glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            scripts_summary.append(f"### {py_file.name}\n```python\n{content}\n```")
    scripts_content = "\n\n".join(scripts_summary)

    return skill_md, scripts_content


class EvalSetGenerator:
    """多層評価テストセット（Trigger, Contract, Golden, Judge, Trajectory, Adversarial）を生成する自動ジェネレータ"""

    def __init__(self, gemini_client=None):
        self.client = gemini_client or client

    def generate_trigger_tests(self, skill_name: str, output_path: str) -> bool:
        """インテント分類用のトリガーテストケース（正例・負例発話）を生成する。"""
        skill_md, _ = _load_skill_context(skill_name)

        prompt = f"""あなたはAIエージェントのインテント判定（トリガー精度）を評価するテストエンジニアです。
以下のスキルの仕様書 (SKILL.md) を読み込み、このスキルが実行されるべき「正例プロンプト (positive)」と、実行されるべきでない「負例プロンプト (negative)」のテストケースを生成してください。

【対象スキル名】
{skill_name}

【SKILL.md】
{skill_md}

【出力要件】
以下の JSON 構造のみを出力してください（Markdownコードブロックは不要）：
{{
  "cases": [
    {{
      "name": "positive_case_1",
      "user_input": "具体的なユーザー発話",
      "expected_tools": ["{skill_name}"],
      "should_trigger": true
    }},
    {{
      "name": "negative_case_1",
      "user_input": "関連しない一般的な発話",
      "expected_tools": [],
      "should_trigger": false
    }}
  ]
}}
正例を3件以上、負例を3件以上作成してください。
"""
        req = GeminiRequest(prompt=prompt, client=self.client, temperature=0.2)
        res = req.execute()
        raw_text = res.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving trigger test cases: {e}", file=sys.stderr)
            return False

    def generate_contract_tests(self, skill_name: str, output_path: str) -> bool:
        """CLI引数・関数入出力仕様・境界値を検証する契約テストケースを生成する。"""
        skill_md, scripts_content = _load_skill_context(skill_name)

        prompt = f"""あなたはAIエージェントの契約駆動テスト（Contract Testing）を設計するエンジニアです。
以下のスキルの仕様書およびスクリプト実装に基づき、CLI実行引数、入力バリデーション、戻り値、境界値を検証するテストケースを生成してください。

【対象スキル名】
{skill_name}

【SKILL.md】
{skill_md}

【scripts/】
{scripts_content}

【出力要件】
以下の JSON 構造のみを出力してください：
{{
  "eval_set_id": "{skill_name}_contract_eval",
  "eval_cases": [
    {{
      "eval_case_id": "test_cli_help",
      "script_name": "scripts/{skill_name.replace('-', '_')}.py",
      "cli_args": ["--help"],
      "expected_exit_code": 0,
      "expected_stdout_contains": ["--help"]
    }},
    {{
      "eval_case_id": "test_normal_execution",
      "function_name": "run",
      "inputs": {{"input_val": "test_data"}},
      "expected": "success"
    }}
  ]
}}
CLI実行ケース2件以上、ロジック検証ケース2件以上を作成してください。
"""
        req = GeminiRequest(prompt=prompt, client=self.client, temperature=0.2)
        res = req.execute()
        raw_text = res.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving contract test cases: {e}", file=sys.stderr)
            return False

    def generate_golden_tests(self, skill_name: str, output_path: str) -> bool:
        """意味的ゴールデンアウトプットを検証するテストケースを生成する。"""
        skill_md, scripts_content = _load_skill_context(skill_name)

        prompt = f"""あなたはゴールデンデータセットを設計するQAエンジニアです。
以下のスキル仕様に基づき、意味的に正しい期待出力（Golden Output）を含むテストケースを生成してください。

【対象スキル名】
{skill_name}

【SKILL.md】
{skill_md}

【scripts/】
{scripts_content}

【出力要件】
以下の JSON 構造のみを出力してください：
{{
  "cases": [
    {{
      "name": "golden_standard_flow",
      "input_scenario": "ユーザー要件シナリオ",
      "expected_outputs": {{"result_contains": ["期待されるキーワードや構造"]}}
    }}
  ]
}}
"""
        req = GeminiRequest(prompt=prompt, client=self.client, temperature=0.2)
        res = req.execute()
        raw_text = res.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving golden test cases: {e}", file=sys.stderr)
            return False

    def generate_judge_tests(self, skill_name: str, output_path: str) -> bool:
        """LLMルーブリックジャッジ用の評価基準・テストケースを生成する。"""
        skill_md, scripts_content = _load_skill_context(skill_name)

        prompt = f"""あなたはLLM-as-a-Judgeの評価ルーブリックを設計する専門家です。
以下のスキル仕様に基づき、採点基準（ルーブリック）と評価シナリオを生成してください。

【対象スキル名】
{skill_name}

【SKILL.md】
{skill_md}

【出力要件】
以下の JSON 構造のみを出力してください：
{{
  "cases": [
    {{
      "name": "judge_quality_check",
      "input_prompt": "評価対象の指示プロンプト",
      "rubrics": [
        {{"criterion": "正確性 (Accuracy)", "weight": 0.4, "description": "指示通りの出力が行われているか"}},
        {{"criterion": "完全性 (Completeness)", "weight": 0.3, "description": "必要な要素が欠落していないか"}},
        {{"criterion": "簡潔性 (Conciseness)", "weight": 0.3, "description": "不要な冗長性がないか"}}
      ],
      "pass_threshold": 0.85
    }}
  ]
}}
"""
        req = GeminiRequest(prompt=prompt, client=self.client, temperature=0.2)
        res = req.execute()
        raw_text = res.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving judge test cases: {e}", file=sys.stderr)
            return False

    def generate_trajectory_tests(self, skill_name: str, output_path: str) -> bool:
        """Google ADK 準拠のツール呼び出し軌跡（Tool Trajectory）評価テストケースを生成する。"""
        skill_md, scripts_content = _load_skill_context(skill_name)

        prompt = f"""あなたは Google ADK 準拠のエージェント軌跡評価（Trajectory Evaluation）を設計するエンジニアです。
以下のスキル仕様に基づき、期待される中間ツール呼び出しシーケンス（intermediate_data.tool_uses）を含むテストケースを生成してください。

【対象スキル名】
{skill_name}

【SKILL.md】
{skill_md}

【出力要件】
以下の JSON 構造のみを出力してください：
{{
  "eval_set_id": "{skill_name}_trajectory_eval",
  "eval_cases": [
    {{
      "invocation_id": "inv_001",
      "user_content": {{"text": "標準的なユーザー指示プロンプト"}},
      "final_response": {{"text": "期待される最終返答サマリー"}},
      "intermediate_data": {{
        "tool_uses": [
          {{
            "name": "{skill_name}",
            "args": {{"input_val": "sample"}}
          }}
        ]
      }}
    }}
  ]
}}
"""
        req = GeminiRequest(prompt=prompt, client=self.client, temperature=0.2)
        res = req.execute()
        raw_text = res.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving trajectory test cases: {e}", file=sys.stderr)
            return False

    def generate_adversarial_tests(self, skill_name: str, output_path: str) -> bool:
        """敵対的・境界値・例外系入力に対する堅牢性テストケースを生成する。"""
        skill_md, scripts_content = _load_skill_context(skill_name)

        prompt = f"""あなたはAIエージェントの堅牢性・セキュリティを評価するレッドチームQAエンジニアです。
以下のスキル仕様に基づき、境界値、型不正、空文字、過剰データなどの敵対的・例外系テストケースを生成してください。

【対象スキル名】
{skill_name}

【SKILL.md】
{skill_md}

【出力要件】
以下の JSON 構造のみを出力してください：
{{
  "eval_set_id": "{skill_name}_adversarial_eval",
  "cases": [
    {{
      "name": "adv_empty_input",
      "input_data": "",
      "expected_behavior": "graceful_error_handling"
    }},
    {{
      "name": "adv_invalid_type",
      "input_data": 999999,
      "expected_behavior": "graceful_error_handling"
    }}
  ]
}}
"""
        req = GeminiRequest(prompt=prompt, client=self.client, temperature=0.2)
        res = req.execute()
        raw_text = res.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving adversarial test cases: {e}", file=sys.stderr)
            return False

    def generate_evalset(self, skill_name: str, test_type: str = "all", output_dir: Optional[str] = None) -> Dict[str, Any]:
        """指定されたスキルの評価セットを生成する統合エントリポイント。"""
        state = SkillsState()
        skill = state.get_skill(skill_name)
        if not skill:
            return {"status": "failed", "message": f"Skill '{skill_name}' not found."}

        if output_dir:
            base_out = Path(output_dir)
        else:
            base_out = Path(skill.root_dir) / "tests"
        base_out.mkdir(parents=True, exist_ok=True)

        generated_files = []
        types_to_run = ["trigger", "contract", "golden", "judge", "trajectory", "adversarial"] if test_type == "all" else [test_type]

        for t in types_to_run:
            out_path = base_out / f"{skill_name}_{t}.evalset.json"
            success = False
            if t == "trigger":
                success = self.generate_trigger_tests(skill_name, str(out_path))
            elif t == "contract":
                success = self.generate_contract_tests(skill_name, str(out_path))
            elif t == "golden":
                success = self.generate_golden_tests(skill_name, str(out_path))
            elif t == "judge":
                success = self.generate_judge_tests(skill_name, str(out_path))
            elif t == "trajectory":
                success = self.generate_trajectory_tests(skill_name, str(out_path))
            elif t == "adversarial":
                success = self.generate_adversarial_tests(skill_name, str(out_path))

            if success:
                generated_files.append(str(out_path))

        return {
            "status": "success" if generated_files else "failed",
            "generated_files": generated_files,
            "skill_name": skill_name
        }


def generate_evalset(skill_name: str, test_type: str = "all", output_dir: Optional[str] = None) -> Dict[str, Any]:
    """モジュールレベル関数"""
    gen = EvalSetGenerator()
    return gen.generate_evalset(skill_name, test_type=test_type, output_dir=output_dir)
