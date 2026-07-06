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

        # 2. module_type が skill (または指定なし) の場合、不要な steps は強制除去
        m_type = design_data.get("module_type", "skill")
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

        return design_data

    def _clean_name(self, name: str) -> str:
        return name.lower().replace("_", "-").replace(" ", "-")
