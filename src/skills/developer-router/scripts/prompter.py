from google.genai import types

def build_routing_prompt(prompt: str, existing_skills: list[dict]) -> list[types.ContentType]:
    """
    既存スキル一覧と機能要件から、ルーティング判定用の Gemini プロンプトを構築します。
    """
    # 既存スキル一覧のテキスト整形
    skills_text_list = []
    for s in existing_skills:
        skills_text_list.append(f"- スキル名: {s['name']}\n  説明: {s['description']}")
    skills_inventory_str = "\n".join(skills_text_list) if skills_text_list else "なし（既存スキルがまだ登録されていません）"

    system_instruction = (
        "あなたは極めて優秀なソフトウェアアーキテクトかつAIエージェント開発 of システム統制者です。\n"
        "提示された『既存の登録済みスキルの一覧（インベントリ）』と、ユーザーから提供された『新機能の要件プロンプト』をセマンティックに分析し、\n"
        "この開発を『既存スキルの連携によるワークフロー（workflow）』として実装すべきか、\n"
        "それとも『新規のPythonロジックを持つ単体のアトミックスキル（skill）』として新規にコード開発すべきかを判断してください。\n\n"
        "=== ルーティング判断ルール ===\n"
        "1. 新機能が『既存スキル一覧』に存在するツール（テストの実行、テストコードの生成、設計の作成など）を順次または並列に連携させて達成できるものである場合 ➔ 'workflow' を選択してください。\n"
        "   - その際、連携させるべき推奨既存スキルの名前を `recommended_dependencies` に含めてください。\n"
        "2. 既存のスキルの組み合わせだけでは実現不可能な、新しい特定のビジネスロジック（例: 文字列変換、新規APIアクセス、独自モデル判定など）を新しく Python コードとしてゼロから実装しなければならない場合 ➔ 'skill' を選択してください。\n"
        "   - その際、`recommended_dependencies` は空リスト `[]` にしてください。\n"
        "3. 要件があまりにも単純で自己完結したアトミックな機能である場合も、通常は 'skill' を選択します。\n"
    )

    contents_str = (
        f"=== 既存のスキル一覧 (Skills Inventory) ===\n"
        f"{skills_inventory_str}\n\n"
        f"=== 開発要件プロンプト (Requirement Prompt) ===\n"
        f"\"{prompt}\"\n\n"
        "判定結果と、その判定に至った極めて論理的かつ説得力のあるアーキテクチャ上の理由を、指定された JSON スキーマに従って出力してください。"
    )

    # ContentType 構造に準拠した形式で返却
    return [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"Instructions:\n{system_instruction}\n\nInput Context:\n{contents_str}")
            ]
        )
    ]
