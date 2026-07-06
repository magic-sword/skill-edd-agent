from pydantic import BaseModel

class PydanticModelParser:
    """Pydantic (V2) モデルを解析しアタッチされているバリデータからドキュメント用制約条件を抽出するユーティリティ。
    """
    @staticmethod
    def parse_constraints(model_cls: type[BaseModel]) -> list[str]:
        """Pydantic モデルに定義されたバリデータの docstring から制約文を決定論的に抽出します。

        Args:
            model_cls: 解析対象の Pydantic BaseModel 派生クラス。

        Returns:
            抽出された制約説明文のリスト。
        """
        constraints = []
        # model_cls から Pydantic デコレータ情報を取得
        decorators = getattr(model_cls, "__pydantic_decorators__", None)
        if not decorators:
            return constraints

        # model_validators の Docstring を抽出
        if hasattr(decorators, "model_validators"):
            for val_info in decorators.model_validators.values():
                func = getattr(val_info, "func", None)
                if func and func.__doc__:
                    doc = func.__doc__.strip()
                    if doc:
                        constraints.append(doc)

        # field_validators の Docstring を抽出
        if hasattr(decorators, "field_validators"):
            for val_info in decorators.field_validators.values():
                func = getattr(val_info, "func", None)
                if func and func.__doc__:
                    doc = func.__doc__.strip()
                    if doc:
                        fields_str = ", ".join(val_info.fields)
                        constraints.append(f"{fields_str}: {doc}")

        return constraints
