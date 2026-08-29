import os
import time
from typing import Any
from google import genai
from google.genai import types
from .base import BaseGeminiClient

class DirectGeminiClient(BaseGeminiClient):
    """Google AI SDK を直接呼び出す Gemini API クライアント。"""
    def __init__(self):
        self.default_model = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
        self.initial_delay = float(os.getenv("GEMINI_RETRY_DELAY", "2.0"))
        self._client = self._get_genai_client()

    def _get_genai_client(self) -> genai.Client:
        """環境変数 GEMINI_API_KEY を使用して genai.Client を初期化します"""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Error: GEMINI_API_KEY environment variable is not set.")
        return genai.Client(api_key=api_key)

    def generate_content(
        self,
        contents: Any,
        config: types.GenerateContentConfig | None = None,
        model: str | None = None,
        **kwargs: Any
    ) -> types.GenerateContentResponse:
        """堅牢な指数バックオフリトライとタイムアウト制御を備えた中央集約的なコンテンツ生成。"""
        from .request import GeminiRequest
        if isinstance(contents, GeminiRequest):
            actual_contents = contents.build()
        else:
            actual_contents = contents

        # response_schema の決定論的クレンジング処理
        if config and getattr(config, "response_schema", None) is not None:
            import copy
            from pydantic import BaseModel, TypeAdapter
            from edd_agent_tools.schema_utils import clean_pydantic_schema
            
            clean_schema = clean_pydantic_schema(config.response_schema)
            try:
                if isinstance(clean_schema, type) and issubclass(clean_schema, BaseModel):
                    schema_dict = clean_schema.model_json_schema()
                else:
                    schema_dict = TypeAdapter(clean_schema).json_schema()
                
                # 1. $defs / $ref をインライン展開 (Gemini API は $defs を解釈できないため)
                defs = schema_dict.pop("$defs", {})
                def resolve_refs(node):
                    if isinstance(node, dict):
                        if "$ref" in node:
                            ref_name = node["$ref"].split("/")[-1]
                            if ref_name in defs:
                                return resolve_refs(copy.deepcopy(defs[ref_name]))
                        return {k: resolve_refs(v) for k, v in node.items()}
                    elif isinstance(node, list):
                        return [resolve_refs(item) for item in node]
                    return node

                schema_dict = resolve_refs(schema_dict)

                # 2. additionalProperties, anyOf[..., null] 等のサニタイズ (titleはフィールド名の可能性があるため削除しない)
                def sanitize_schema(d):
                    if isinstance(d, dict):
                        d.pop("additionalProperties", None)
                        if "anyOf" in d and len(d["anyOf"]) == 2:
                            types_in_anyof = [x.get("type") for x in d["anyOf"] if isinstance(x, dict)]
                            if "null" in types_in_anyof:
                                non_null_type = [t for t in types_in_anyof if t != "null"]
                                if non_null_type:
                                    d["type"] = non_null_type[0]
                                    d.pop("anyOf", None)
                        # Gemini API Strict Mode: object型のrequiredをpropertiesの全キーに設定
                        if d.get("type") == "object" and "properties" in d:
                            d["required"] = list(d["properties"].keys())

                        for v in list(d.values()):
                            sanitize_schema(v)
                    elif isinstance(d, list):
                        for item in d:
                            sanitize_schema(item)
                            
                sanitize_schema(schema_dict)
                config.response_schema = schema_dict
            except Exception as e:
                print(f"警告: response_schema の JSON Schema 変換に失敗しました: {e}")
                config.response_schema = clean_schema

        target_model = model or self.default_model
        delay = self.initial_delay
        
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=actual_contents,
                    config=config,
                    **kwargs
                )
                return response
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    break
                
                print(f"⚠️ Gemini API Error (Attempt {attempt+1}/{self.max_retries+1}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
                
        raise Exception(f"Gemini API 呼び出しが {self.max_retries+1} 回の試行後に失敗しました。最後のエラー: {last_exception}")
