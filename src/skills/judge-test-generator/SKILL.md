---
name: judge-test-generator
description: "design.jsonおよびSKILL.mdから、複数の詳細な評価ルーブリック基準（criterion, description, weight）と検証用引数（inputs）のペアを自動設計し、[skill_name]_judge.evalset.jsonとして書き出すスキル。"
---

# スキル仕様書: judge-test-generator

## 概要

指定されたスキル設計情報から、LLM-as-Judge評価用のルーブリックとテストケースを自動生成し、ファイルに保存します。

### 主な機能
* 指定されたスキルの設計情報（design.jsonおよびSKILL.md）を分析します。
* LLM-as-Judge評価用の詳細な評価ルーブリック基準（criterion, description, weight）を自動設計します。
* 検証用引数（inputs）のペアを自動設計し、テストケースを生成します。
* 生成されたルーブリックとテストケースをJSON形式（例: [skill_name]_judge.evalset.json）でファイルに保存します。

### 内部処理の流れ
1. 対象スキルの`design.json`と`SKILL.md`のパスを解決し、ファイルが存在することを確認します。
2. 解決したパスから`design.json`と`SKILL.md`の内容を読み込みます。
3. 読み込んだスキル設計情報を基に、LLMがルーブリックとテストケースを生成するためのプロンプトを構築します。
4. 構築したプロンプトと定義済みの`JudgeCaseSet`スキーマを使用して、Gemini APIに構造化されたテストケースの生成をリクエストします。
5. Gemini APIから返されたJSONレスポンスを`JudgeCaseSet`モデルでバリデーションします。
6. バリデーション済みのテストケースセットを、指定された`output_path`にJSON形式でファイルとして書き出します。


---

## トリガー条件

このスキルは、以下の条件やプロンプトでトリガーされます。

- 「`my-skill`の評価ルーブリックとテストケースを生成して」
- 「`design.json`と`SKILL.md`を元に、`my-skill`のジャッジテストを`/path/to/output.json`に作成して」
- 「指定されたスキル設計情報から、LLM評価用のテストセットを生成したい」

---

## 公開関数

### generate_tests

指定されたスキルのdesign.jsonおよびSKILL.mdを分析し、多角的なチェック項目（ルーブリック）を含むテストケースを生成して指定されたパスに書き出します。

#### 実行方法
${skill_name} は、与えられたパラメータに基づいて特定のタスクを**決定論的に実行**するツールです。LLMが推論を挟まず、直接このツールを呼び出して指示通りの操作を行います。

利用例：
${skill_name}(`skill_name`, `output_path`)

#### 入力パラメータ
| パラメータ名 | 型 | 必須 | デフォルト値 | 説明 |
|---|---|---|---|---|
| skill_name | str | はい | - | テストケースを生成する対象スキルの名前。 |
| output_path | str | はい | - | 生成されたルーブリックテストファイルを保存する絶対パス。 |


#### 出力仕様
* **出力モード**: `VALUE_ONLY` (プレーンテキスト（値のみ）)
* **戻り値の型**: `bool`

スキル実行結果を示す単一のテキストメッセージが返されます。


---



---

**開発者向け注記**:
この仕様書は `skill-spec-writer` スキルによって自動生成されました。
最新の情報は `design.json` を参照し、変更は `design.json` に直接加えてください。