class DesignCleanser:
    """
    LLMが出力したラフな設計データ（dict）に対して、
    命名規則やワークフロー構造の決定論的な自動補正（クレンジング）を施す。
    """
    def clean(self, design_data: dict) -> dict:
        if not isinstance(design_data, dict):
            return design_data

        # 1. name を小文字ハイフン区切りにクレンジング
        if "name" in design_data and isinstance(design_data["name"], str):
            design_data["name"] = self._clean_name(design_data["name"])

        # 2. module_type が workflow だが、外部スキル（type: 'skill'）呼び出しが1つも含まれない場合は、強制的に skill とする
        m_type = design_data.get("module_type", "skill")
        if m_type == "workflow":
            steps = design_data.get("steps", [])
            has_external_skill = False
            if isinstance(steps, list):
                for step in steps:
                    if isinstance(step, dict) and step.get("type") == "skill":
                        has_external_skill = True
                        break
            if not has_external_skill:
                design_data["module_type"] = "skill"
                m_type = "skill"

        # 3. module_type が skill (または指定なし) の場合、不要な steps は強制除去
        if m_type != "workflow":
            design_data.pop("steps", None)

        # 3. 各ステップの name や target のクレンジング
        if "steps" in design_data and isinstance(design_data["steps"], list):
            for step in design_data["steps"]:
                if isinstance(step, dict):
                    if "name" in step and isinstance(step["name"], str):
                        step["name"] = self._clean_name(step["name"])
                    if "target" in step and isinstance(step["target"], str):
                        step["target"] = self._clean_name(step["target"])

        # 4. module_type が skill の場合の必須フィールド自動補完 (バリデーションエラー防止)
        if m_type == "skill":
            if not design_data.get("execution_type"):
                design_data["execution_type"] = "agent"
            if not design_data.get("output_mode"):
                design_data["output_mode"] = "STRUCTURED_JSON"
            if not design_data.get("functions"):
                # デフォルトの公開関数を1つ自動生成して補完
                func_name = design_data.get("name", "my-skill").replace("-", "_")
                desc = design_data.get("description", "スキル実行の窓口となる関数です。")
                design_data["functions"] = [
                    {
                        "name": func_name,
                        "description": desc,
                        "parameters": design_data.get("parameters", []),
                        "response_parameters": design_data.get("response_parameters")
                    }
                ]

        return design_data

    def _clean_name(self, name: str) -> str:
        return name.lower().replace("_", "-").replace(" ", "-")
