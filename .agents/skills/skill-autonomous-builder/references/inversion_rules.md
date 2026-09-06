# EDD (Evaluation-Driven Development) インバージョン開発規約

本ドキュメントは、Google 『Agent Skills』ホワイトペーパー（May 2026）Section 4（Page 22〜24）に準拠した、評価駆動開発（EDD）インバージョン規約の単一真実源（SSOT）です。

---

## 1. インバージョン開発の原則 (Invert the Workflow)

通常の手順（プロンプト執筆 ➔ スクリプト作成 ➔ 後からテスト）は**厳禁**です。
白書 Page 22 に定められた通り、**`SKILL.md` 本文を書く前に、必ず Google ADK 2.0 公式 `EvalSet` スキーマに基づく評価ケース（単一真実源: SSOT）を確定**させます。

### なぜインバージョン開発を行うのか？
1. **仕様の明確化**: 入力発話、期待されるツール呼び出し（Trajectory）、および期待出力を先に確定させることで、スキルの機能境界が客観的に固定されます。
2. **ハルシネーションと曖昧さの未然防止**: エージェントが勝手な思い込みでプロンプトを肥大化させるのを防ぎます。
3. **Google ADK 2.0 純正ランタイムとの直結**: Google ADK 公式 CLI（`adk eval`）および `AgentEvaluator` とそのまま直結動作します。

---

## 2. 3正例 ＋ 3負例（計6ケース）の必須要件

白書 Page 22 の規定に基づき、すべてのスキルは **3 つの正例（Positive triggers）＋ 3 つの負例（Negative boundaries）の計 6 ケース** を必須とします。

* **正例 (Positive Triggers: 3件)**:
  - スキルが確実に発動すべき代表的なユーザー入力。
  - 多様な言い回し（Rephrasing stability）や引数パターンをカバーする。
* **負例 (Negative Boundaries: 3件)**:
  - スキルが**絶対に発動してはならない**隣接クエリ、一般的QA、またはスコープ外の入力。
  - エージェントが誤爆（Over-trigger）せず、スキルツールを一切呼び出さずに一般知識で直接回答すること、または適切な拒否を行うことを検証する。

---

## 3. ADK 2.0 純正 EvalSet スキーマ仕様 (`{skill_name}.test.json`)

```json
{
  "eval_set_id": "<skill-name>-eval-set",
  "eval_cases": [
    {
      "eval_case_id": "<skill-name>-pos-001",
      "conversation": [
        {
          "user_content": {
            "parts": [
              {
                "text": "具体的な正例のユーザー入力プロンプト"
              }
            ]
          }
        }
      ],
      "intermediate_data": {
        "tool_uses": [
          {
            "name": "run_skill_script",
            "args": {
              "skill_name": "<skill-name>",
              "file_path": "<primary_script>.py",
              "args": {
                "flag": "value"
              },
              "positional_args": ["arg1"]
            }
          }
        ]
      },
      "rubrics": [
        {
          "rubric_id": "clean_direct_output",
          "text": "余計な会話フィラーを含まず、決定論的スクリプトの実行結果を直接・正確に出力していること"
        }
      ]
    },
    {
      "eval_case_id": "<skill-name>-neg-001",
      "conversation": [
        {
          "user_content": {
            "parts": [
              {
                "text": "スキル発動対象外の一般的な質問"
              }
            ]
          }
        }
      ],
      "intermediate_data": {
        "tool_uses": []
      },
      "rubrics": [
        {
          "rubric_id": "direct_answer_no_tools",
          "text": "スキルツールを一切呼び出さず、一般的な知識で直接的かつ簡潔に回答していること"
        }
      ]
    }
  ]
}
```

---

## 4. 責務分離の原則 (Responsibility Separation)

* **Trajectory レイヤー (`intermediate_data.tool_uses`)**:
  - ツールの呼び出し有無、スクリプトパス（`file_path`）、位置引数（`positional_args`）、オプション引数（`args`）の厳密な検証を担当。
* **ルーブリック レイヤー (`rubrics`)**:
  - LLM の最終回答品質（正確性、簡潔性、会話フィラーの排除、負例時の適切な振る舞い）に純粋化。

---

## 5. Google ADK 2.0 公式 `test_config.json` の標準配備

各スキルの `tests/test_config.json` には、Progressive Disclosure（`list_skills` ➔ `load_skill` ➔ `run_skill_script`）を採用するエージェントを公平に評価するため、以下を標準配備します：

```json
{
  "criteria": [
    {
      "metric": "tool_trajectory_avg_score",
      "match_type": "IN_ORDER",
      "threshold": 1.0
    },
    {
      "metric": "rubric_based_final_response_quality_v1",
      "threshold": 0.9,
      "judge_model": "gemini-2.5-flash"
    }
  ]
}
```
