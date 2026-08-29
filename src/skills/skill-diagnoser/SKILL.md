---
name: "skill-diagnoser"
description: "テスト実行結果レポートとスキル定義・ソースコードを分析し、失敗原因の診断と構造化された改善計画（ImprovementPlan）を出力するメタスキル。"
---

# skill-diagnoser

テスト実行結果レポートとスキル定義・ソースコードを分析し、失敗原因の診断と構造化された改善計画（ImprovementPlan）を出力するメタスキル。

## 概要

本スキルは、自己改善型エージェント（Self-Improving Agent）における「診断・計画（Diagnosis & Planning）」フェーズを担うメタスキルです。
テストランナーが生成した `tests/results/latest_report.json`、スキルの設計仕様（`design.json`）、仕様書（`SKILL.md`）、および `scripts/` 配下の Python コードを多角的に分析し、最小限の安全な修正でテストを合格させるための根本原因と `ImprovementPlan` を策定します。

## トリガー条件

以下のような場面で呼び出されます：
- 新規開発または既存スキルのテスト実行（`first-test-runner` や `test-executor` 等）で失敗・不合格（accuracy < threshold）が検知されたとき。
- エージェントがスキルの自律的リファクタリングや改善方針を決定するとき。

## 利用可能な関数 (Tools)

### `diagnose_skill_failure`

テスト実行結果レポートとスキルの設計・コードを分析し、失敗の根本原因と構造化改善計画を出力します。

#### 入力パラメータ
| パラメータ名 | 型 | 必須 | デフォルト値 | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| `skill` | `str` | ✅ | - | 診断対象となるスキルの論理名。 |
| `report_path` | `str` | ❌ | `None` | テスト結果レポート（JSON）の絶対パス。省略時は最新の `latest_report.json` を自動参照。 |
| `test_type` | `str` | ❌ | `None` | 特定のテスト種別（`contract`, `trigger`, `judge`, `golden` 等）。省略時はレポート内の種別を使用。 |

#### 出力パラメータ
| パラメータ名 | 型 | 説明 |
| :--- | :--- | :--- |
| `status` | `str` | 診断処理の実行ステータス（`success` または `failed`）。 |
| `details` | `str` | 診断結果サマリーまたはエラーメッセージ。 |
| `plan` | `dict` | 策定された構造化改善計画（`ImprovementPlan`）。 |
