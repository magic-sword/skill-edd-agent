import json
from typing import Any
from pydantic import BaseModel, create_model
from google.genai import types
from edd_agent_tools import GeminiClient, SkillsState
from .schemas import TestParameterCase, TestParameterSet, EvalSet, EvalConfig
from .strategy import get_output_mode_strategy

class TestGenerator:
    """対象スキルに対応する評価用の単体テストスイートを自律生成するジェネレータークラス。

    スキルの仕様書および入力スキーマからテストケースを抽出し、
    評価用のテストデータセットファイルおよび設定ファイルを生成・保存します。

    Attributes:
        _skill_obj: レジストリから取得したスキルオブジェクト。
        _client: Gemini API 呼び出しを行うクライアント。
    """

    def __init__(self, skill_name: str):
        """TestGenerator を初期化します。

        Args:
            skill_name: 単体テストを生成する対象のスキル名。
        """
        self._skill_obj = SkillsState().get_skill(skill_name)
        self._client = GeminiClient()

    def generate_and_save(self) -> str:
        """単体テストケースを自律生成し、評価用アセットファイルとして保存します。

        Returns:
            str: 生成された評価セットファイルの絶対パス。

        Raises:
            FileNotFoundError: 仕様書やテンプレートファイルが見つからない場合。
            Exception: Gemini API 呼び出しやスキーマ動的構築の過程でエラーが発生した場合。
        """
        # 1. 直接仕様書をロード
        skill_content = self._skill_obj.load_spec()
        input_schema, pydantic_schema_str = self._extract_input_schema()

        # 出力モード戦略オブジェクトをライフサイクル内で一元化
        strategy = get_output_mode_strategy(skill_content)

        # 2. プロンプトの組み立て
        prompt = self._build_prompt(skill_content, pydantic_schema_str, strategy)

        # 3. Gemini API への問い合わせによるテストケースの生成
        param_set = self._request_test_cases(prompt, input_schema)

        # 4. 評価ファイル（JSON）のフォーマットと保存 (戦略を注入してポリモーフィズムを適用)
        eval_set_path = self._save_assets(param_set, strategy)
        return eval_set_path

    def _extract_input_schema(self) -> tuple[type[BaseModel] | None, str]:
        """ターゲットスキルから Input スキーマを抽出し、JSON Schema 文字列表現を生成します。

        Returns:
            tuple: (Inputクラスオブジェクト または None, PydanticスキーマのJSON文字列表現 または 空文字)
        """
        try:
            skill_module = self._skill_obj.load_module()
            input_schema = getattr(skill_module, "Input", None)
            if input_schema and issubclass(input_schema, BaseModel):
                schema_str = json.dumps(
                    input_schema.model_json_schema(), ensure_ascii=False, indent=2
                )
                return input_schema, schema_str
        except Exception:
            pass
        return None, ""

    def _build_prompt(self, skill_content: str, schema_str: str, strategy: Any) -> str:
        """スコアリングおよび出力モードに応じた最終指示プロンプトを構築します。

        Args:
            skill_content: ターゲットスキルの仕様書テキスト。
            schema_str: ターゲットスキルの入力スキーマ表現。
            strategy: 出力モードに対応する戦略オブジェクト。

        Returns:
            str: 置換・構築が完了した最終プロンプトテキスト。
        """
        # 自身のスキルアセットからテンプレートをロード
        eval_unit_tester_skill = SkillsState().get_skill("eval-unit-tester")
        prompt_template = eval_unit_tester_skill.load_asset("test_case_gen_prompt.txt")

        # 戦略オブジェクトにプロンプト構築責任を委譲（ポリモーフィズム）
        return strategy.build_prompt(
            template=prompt_template,
            skill_content=skill_content,
            schema_str=schema_str
        )

    def _build_dynamic_response_schema(self, input_schema: type[BaseModel] | None) -> type[TestParameterSet]:
        """構造化出力用に対象スキルの Input スキーマを内包したテストセット Pydantic モデルを動的構築します。

        Args:
            input_schema: 対象スキルの Input スキーマアノテーション。

        Returns:
            type[TestParameterSet]: 動的構築された Pydantic のモデルクラス（TestParameterSet またはその派生）。
        """
        if not input_schema:
            return TestParameterSet

        try:
            # Ellipsis (...) を指定することで、基底モデルの Field 定義 (description 等) を引き継ぎ、型のみを変更
            dynamic_case_model = create_model(
                'DynamicTestParameterCase',
                __base__=TestParameterCase,
                input_parameters=(input_schema, ...)
            )
            # 同様に TestParameterSet から継承し、リスト要素の型だけを上書き
            dynamic_set_model = create_model(
                'DynamicTestParameterSet',
                __base__=TestParameterSet,
                cases=(list[dynamic_case_model], ...)
            )
            return dynamic_set_model
        except Exception:
            return TestParameterSet

    def _request_test_cases(self, prompt: str, input_schema: type[BaseModel] | None) -> TestParameterSet:
        """Gemini API を呼び出し、スキーマに即したテストデータセットを構造化出力させます。

        Args:
            prompt: 送信するプロンプト指示テキスト。
            input_schema: ターゲットスキルのInputアノテーション。

        Returns:
            TestParameterSet: レスポンススキーマに準拠してパースされたテストケースセットオブジェクト。
        """
        # メタプログラミング（スキーマ構築）の責務を別メソッドに分離
        target_set_class = self._build_dynamic_response_schema(input_schema)

        # パッケージ共通の Fluent API を使用してリクエストを構築・実行
        response = (
            self._client.request(prompt)
            .execute(
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=target_set_class,
                    temperature=0.2
                )
            )
        )

        parameter_data = json.loads(response.text)
        param_set = target_set_class.model_validate(parameter_data)
        return param_set

    def _save_assets(self, param_set: TestParameterSet, strategy: Any) -> str:
        """生成されたテストケースセットを評価セットJSONおよび構成JSONとして正しい場所に保存します。

        Args:
            param_set: 生成されたテストケースデータセット。
            strategy: 出力モードに対応する戦略オブジェクト。

        Returns:
            str: 保存された評価セット（*.evalset.json）の絶対パス。
        """
        skill_name = self._skill_obj.name
        skill_name_underscore = skill_name.replace('-', '_')

        # OOP: 各テストケースが自らを安全な EvalCase モデルオブジェクトへと自己マッピング
        eval_cases = [
            case.to_eval_case(tool_name=skill_name_underscore, index=i, strategy=strategy)
            for i, case in enumerate(param_set.cases)
        ]

        # 評価セットデータ構造全体のモデルクラス化
        eval_set = EvalSet(
            eval_set_id=f"{skill_name_underscore}_eval_set",
            name=f"{skill_name} evaluation set",
            description=f"{skill_name} skill unit tests",
            eval_cases=eval_cases
        )

        # SkillEvalオブジェクトを通じてモデルをダンプして保存
        eval_obj = self._skill_obj.get_eval("unit")
        eval_set_path = eval_obj.save_eval_set(eval_set.model_dump())

        # 徹底したポリモーフィズム: 戦略クラスから最適な評価構成設定を型安全に取得
        config = strategy.get_eval_config(eval_set_path)
        eval_obj.save_config(config.model_dump())

        return eval_set_path
