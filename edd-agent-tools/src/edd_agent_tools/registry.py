import os
import sys
import json
import hashlib
import datetime
import importlib.util
from .skill import Skill

class SkillRegistry:
    """skills_registry.json のデータ構造をカプセル化し、読み込み・保存・更新・動的ツールロードを管理するクラス"""
    
    def __init__(self, registry_path: str = "/workspace/src/skills_registry.json"):
        self.registry_path = os.path.abspath(registry_path)
        self.data = None

    def _load(self) -> dict:
        """レジストリファイルをロードします。"""
        if not os.path.exists(self.registry_path):
            raise FileNotFoundError(f"エラー: レジストリファイルが見つかりません: {self.registry_path}")
            
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"エラー: レジストリの読み込みに失敗しました: {e}")
        return self.data

    def _save(self):
        """レジストリファイルを保存します。(内部用)"""
        if self.data is None:
            raise RuntimeError("エラー: レジストリがロードされていません。先に _load() を呼び出してください。")
            
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"エラー: レジストリの保存に失敗しました: {e}")

    def _get_category_and_info(self, name: str) -> tuple[str, dict] | tuple[None, None]:
        """指定された名前の登録カテゴリ(skills または agents)とメタデータを取得します。"""
        if self.data is None:
            self._load()
        for cat in ["skills", "agents"]:
            if name in self.data.get(cat, {}):
                return cat, self.data[cat][name]
        return None, None

    def register_skill(self, skill: "Skill") -> bool:
        """スキルまたはエージェントのオブジェクトをレジストリへ新規登録・更新（保存）します。"""
        if self.data is None:
            self._load()
            
        skill_name = skill.name
        from edd_agent_tools.models import ModuleType
        cat = "agents" if skill.metadata.module_type == ModuleType.WORKFLOW else "skills"

        skills_info = self.data.setdefault(cat, {})
        
        # 既存情報がある場合は取得
        existing_info = skills_info.get(skill_name, {})
        current_tier = existing_info.get("tier")
        
        # Tier 1 への更新のとき、現在の Tier が 0 の場合のみ許可する。
        # すでに Tier 1 以上の既存スキルはダウングレードや不要な上書きを防ぐためスキップ。
        if skill._tier == 1:
            if current_tier is not None and current_tier != 0:
                print(f"Skipped promotion to Tier 1 for '{skill_name}': Current tier is {current_tier} (only Tier 0 can be promoted).")
                return False

        skills_info[skill_name] = {
            "tier": skill._tier,
            "last_tested": skill._last_tested
        }
        self._save()
        print(f"Saved/Registered {cat[:-1]} '{skill_name}' at Tier {skill._tier} ({cat}).")
        return True

    def list_skills(self) -> list[Skill]:
        """登録されているすべてのスキルおよびエージェントの Skill オブジェクトリストを返します。"""
        if self.data is None:
            self._load()
        skills_list = []
        for cat in ["skills", "agents"]:
            for name in self.data.get(cat, {}).keys():
                try:
                    skills_list.append(self.get_skill(name))
                except Exception:
                    pass
        return skills_list

    def _get_skill_dir(self, skill_name: str) -> str | None:
        """指定されたスキルまたはエージェントの物理ディレクトリ絶対パスを探索して返します。(内部用ヘルパー)"""
        if self.data is None:
            self._load()
        search_paths = self.data.get("search_paths", ["src/skills"])
        for path_entry in search_paths:
            possible_dir = os.path.abspath(os.path.join(os.getcwd(), path_entry, skill_name))
            if os.path.exists(possible_dir) and os.path.isdir(possible_dir):
                return possible_dir
        return None

    def get_skill(self, name: str | None = None, design_path: str | None = None) -> "Skill":
        """
        指定された name または design_path から一元的に Skill オブジェクトを構築して返します。
        """
        import os
        from edd_agent_tools.models import SkillDesign

        root_dir = None
        target_name = name

        if not target_name and design_path:
            abs_path = os.path.abspath(design_path)
            try:
                design_data = SkillDesign.load_from_file(abs_path)
                target_name = design_data.name
            except Exception:
                pass
            if not target_name:
                dir_name = os.path.dirname(abs_path)
                root_dir = os.path.dirname(dir_name) if os.path.basename(dir_name) == "assets" else dir_name

        if target_name:
            root_dir = self._get_skill_dir(target_name)
            if not root_dir:
                root_dir = os.path.abspath(os.path.join(os.getcwd(), "src", "skills", target_name))

        if not root_dir:
            raise ValueError("Error: Could not resolve skill directory path.")

        # レジストリ情報（Tier, テスト日時）を抽出して依存注入する
        tier = 0
        last_tested = None
        if target_name:
            cat, info = self._get_category_and_info(target_name)
            if info is not None:
                tier = info.get("tier", 0)
                last_tested = info.get("last_tested")

        return Skill(root_dir, tier=tier, last_tested=last_tested)