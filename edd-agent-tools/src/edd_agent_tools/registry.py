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

    def save(self):
        """レジストリファイルを保存します。"""
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

    def detect_category(self, skill_name: str) -> str:
        """指定されたスキル名/エージェント名が属するフォルダからカテゴリ(skills または agents)を判定します。"""
        if self.data is None:
            self._load()
        search_paths = self.data.get("search_paths", ["src/skills"])
        for path_entry in search_paths:
            possible_dir = os.path.abspath(os.path.join(os.getcwd(), path_entry, skill_name))
            if os.path.exists(possible_dir) and os.path.isdir(possible_dir):
                if "agents" in path_entry:
                    return "agents"
        return "skills"  # デフォルト

    def register_skill(self, skill_name: str) -> bool:
        """スキルまたはエージェントを新規登録します（新規は常に Tier 0 から開始）。"""
        if self.data is None:
            self._load()
            
        cat = self.detect_category(skill_name)
        skills_info = self.data.setdefault(cat, {})
        if skill_name in skills_info:
            print(f"{cat[:-1].capitalize()} '{skill_name}' already registered. Current tier: {skills_info[skill_name].get('tier')}")
            return False
            
        skills_info[skill_name] = {
            "tier": 0,
            "last_tested": None
        }
        self.save()
        print(f"Registered {cat[:-1]} '{skill_name}' at Tier 0.")
        return True

    def set_tier(self, skill_name: str, tier: int) -> bool:
        """指定されたスキルまたはエージェントの Tier を設定・更新します。"""
        if tier not in [0, 1, 2, 3]:
            raise ValueError("Error: Tier must be 0, 1, 2, or 3.")
            
        if self.data is None:
            self._load()
            
        cat, info = self._get_category_and_info(skill_name)
        if not cat:
            cat = self.detect_category(skill_name)
            
        skills_info = self.data.setdefault(cat, {})
        now_str = datetime.datetime.now().isoformat() + "Z"
        
        existing_info = info if info else {}
        current_tier = existing_info.get("tier")
        
        # Tier 1 への更新のとき、現在の Tier が 0 の場合のみ許可する。
        # すでに Tier 1 以上の既存スキルはダウングレードや不要な上書きを防ぐためスキップ。
        if tier == 1:
            if current_tier is not None and current_tier != 0:
                print(f"Skipped promotion to Tier 1 for '{skill_name}': Current tier is {current_tier} (only Tier 0 can be promoted).")
                return False
            
        skills_info[skill_name] = {
            **existing_info,
            "tier": tier,
            "last_tested": now_str
        }
        if "file_hashes" in skills_info[skill_name]:
            del skills_info[skill_name]["file_hashes"]
            
        self.save()
        print(f"Set tier of '{skill_name}' to {tier} ({cat}).")
        return True

    def list_skills(self):
        """登録されている全スキルおよびエージェントの一覧を表示します。"""
        if self.data is None:
            self._load()
            
        print(f"{'Category':<10} | {'Name':<25} | {'Tier':<5} | {'Last Tested':<25}")
        print("-" * 75)
        for cat in ["skills", "agents"]:
            for name, info in sorted(self.data.get(cat, {}).items()):
                last_tested = info.get("last_tested") or "Never"
                print(f"{cat[:-1].capitalize():<10} | {name:<25} | {info['tier']:<5} | {last_tested:<25}")



    # load_skill は廃止され、SkillDirectory.load() へ委譲されました。

    # load_tool は廃止されました。load_skill を呼び出してモジュールから属性を直接取得してください。

    def get_registered_skills(self) -> dict[str, dict]:
        """登録されているすべてのスキルおよびエージェントの情報をマージして返します。"""
        if self.data is None:
            self._load()
        skills = self.data.get("skills", {})
        agents = self.data.get("agents", {})
        merged = {}
        merged.update(skills)
        merged.update(agents)
        return merged

    def get_skill_info(self, name: str) -> RegisteredSkillInfo | None:
        """指定されたスキルまたはエージェントの登録メタデータを取得します。"""
        from .models import RegisteredSkillInfo
        cat, info = self._get_category_and_info(name)
        if info is not None:
            return RegisteredSkillInfo.model_validate(info)
        return None

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

        return Skill(root_dir)



    # load_input_schema は廃止されました。load_skill を呼び出して Input スキーマを直接取得してください。




