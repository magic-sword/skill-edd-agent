---
name: developer-router
description: 要件プロンプトを分析し、単体スキル(skill)、ワークフロー(workflow)、または事前スキル開発提案(proposal)へ分類してルーティングするスキル。
---

# developer-router

## 概要
ユーザーから提供された要件プロンプトを分析し、開発の実現方法・難易度に応じて適切な開発ルート（`skill` / `workflow` / `proposal`）を分類・判定するインテリジェントルーターです。

### 主な機能
*   既存スキル（インベントリ）一覧のロードとセマンティックな理解。
*   要件プロンプトの難易度・依存度に応じた3段階ルーティング判定（`skill`, `workflow`, `proposal`）。
*   判定結果（`route`）およびその分析理由（`rationale`）の出力。
*   ワークフロー判定時（`workflow`）の推奨既存スキルリスト（`recommended_dependencies`）の自動抽出。
*   高難易度・不足要素が存在する判定時（`proposal`）の事前に開発しておくべき単体スキル提案（`proposed_skill`）。

## トリガー条件
このツールは以下のようなインテントで起動されます：
- 「この機能要件 '...' は単体スキルとワークフローのどちらで開発すべきですか？」
- 「機能要件を分析して適切な開発ルートを判定してください。」

## 入力パラメータ
| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| prompt | str | はい | 開発したい機能の要件プロンプト。 |

## 出力パラメータ (構造化JSON)
| パラメータ名 | 型 | 必須 | 説明 |
|---|---|---|---|
| route | str | はい | 判定された開発ルート（'skill', 'workflow', または 'proposal'）。 |
| rationale | str | はい | そのルートに決定した分析理由。 |
| recommended_dependencies | list[str] | はい | ワークフローの場合に推奨される既存スキル名のリスト。それ以外は空リスト。 |
| proposed_skill | dict | いいえ | route が 'proposal' の場合に提案される事前開発スキル情報（name, description）。それ以外は null。 |
