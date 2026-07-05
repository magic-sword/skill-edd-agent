import os
import sys
import json
import hashlib
import datetime
import importlib.util
from .directory import SkillDirectory

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

    def update_meta(self, skill_name: str):
        """スキルまたはエージェントのメタデータを最新の状態に更新します（ハッシュ廃止に伴い、何もしません）。"""
        if self.data is None:
            self._load()
            
        cat, info = self._get_category_and_info(skill_name)
        if not cat:
            self.register_skill(skill_name)
            return
            
        if "file_hashes" in info:
            del info["file_hashes"]
            self.save()
            
        print(f"Updated metadata for {cat[:-1]} '{skill_name}' (hashes removed).")

    def load_handler(self, skill_name: str):
        """
        指定されたスキルまたはエージェントの scripts/handler.py を、
        一意の名前空間の下でキャッシュの干渉なくロードし、モジュールオブジェクトを返します。
        """
        if self.data is None:
            self._load()
            
        search_paths = self.data.get("search_paths", ["src/skills"])
        cat, skill_meta = self._get_category_and_info(skill_name)
        if not cat:
            raise ValueError(f"エラー: スキル/エージェント '{skill_name}' がレジストリに登録されていません。")
            
        skill_dir = self.get_skill_dir(skill_name)
        if not skill_dir:
            raise FileNotFoundError(
                f"エラー: '{skill_name}' の実体ディレクトリが探索パス {search_paths} 内に見つかりません。"
            )
            
        abs_skill_dir = os.path.abspath(skill_dir)
        script_abs_path = os.path.join(abs_skill_dir, "scripts", "handler.py")
        
        if not os.path.exists(script_abs_path):
            raise FileNotFoundError(f"エラー: scripts/handler.py が存在しません: {script_abs_path}")

        # 一意の名前空間（仮想FQDN）の組み立て
        # 一意の名前空間（仮想FQDN）の組み立て
        skill_name_under = skill_name.replace('-', '_')
        parent_pkg = f"edd_agent_tools.dynamic_skills.{skill_name_under}"
        package_name = f"{parent_pkg}.scripts"
        module_name = f"{package_name}.handler"

        # すでにロードされている場合はキャッシュを返す
        if module_name in sys.modules:
            return sys.modules[module_name]

        # 相対インポートを正常に解決するため sys.path を調整
        if abs_skill_dir not in sys.path:
            sys.path.insert(0, abs_skill_dir)

        # 仮想パッケージモジュールの動的登録 (相対インポート解決用)
        import types
        if parent_pkg not in sys.modules:
            sys.modules[parent_pkg] = types.ModuleType(parent_pkg)
        if package_name not in sys.modules:
            pkg_module = types.ModuleType(package_name)
            pkg_module.__path__ = [os.path.join(abs_skill_dir, "scripts")]
            pkg_module.__package__ = package_name
            sys.modules[package_name] = pkg_module

        # ロード実行
        spec = importlib.util.spec_from_file_location(module_name, script_abs_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {script_abs_path}")
            
        module = importlib.util.module_from_spec(spec)
        module.__package__ = package_name  # 相対インポートに必須
        sys.modules[module_name] = module
        
        spec.loader.exec_module(module)
        return module

    def load_tool(self, skill_name: str, function_name: str):
        """指定されたスキル/エージェントと関数名から Python スクリプトを動的ロードし、関数オブジェクトを返します。"""
        # load_handler を用いて安全にロード
        module = self.load_handler(skill_name)
        
        if not hasattr(module, function_name):
            raise AttributeError(f"エラー: モジュール '{module.__name__}' に関数 '{function_name}' が定義されていません。")
            
        return getattr(module, function_name)

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

    def get_skill_dir(self, skill_name: str) -> str | None:
        """指定されたスキルまたはエージェントの物理ディレクトリ絶対パスを探索して返します。"""
        if self.data is None:
            self._load()
        search_paths = self.data.get("search_paths", ["src/skills"])
        for path_entry in search_paths:
            possible_dir = os.path.abspath(os.path.join(os.getcwd(), path_entry, skill_name))
            if os.path.exists(possible_dir) and os.path.isdir(possible_dir):
                return possible_dir
        return None

    def get_skill_directory(self, name: str | None = None, design_path: str | None = None) -> "SkillDirectory":
        """
        指定された name または design_path から一元的に SkillDirectory オブジェクトを構築して返します。
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
            root_dir = self.get_skill_dir(target_name)
            if not root_dir:
                root_dir = os.path.abspath(os.path.join(os.getcwd(), "src", "skills", target_name))

        if not root_dir:
            raise ValueError("Error: Could not resolve skill directory path.")

        return SkillDirectory(root_dir)

    def get_tools(self, skill_names: list[str]):
        """
        指定されたスキル名（またはエージェント名）のリストに対応する
        ADKの FunctionTool のリストを動的ロード・構築して返します。
        """
        from google.adk.tools import FunctionTool
        
        if self.data is None:
            self._load()
            
        tools = []
        for skill_name in skill_names:
            # process_message を動的ロード
            process_func = self.load_tool(skill_name, "process_message")
            
            # メタデータから説明を取得
            skills_meta = self.get_registered_skills()
            meta = skills_meta.get(skill_name, {})
            description = meta.get("description", f"Execute {skill_name} skill")
            
            # 関数の属性を動的に書き換えることで、FunctionTool がツール名と説明を正しく解決できるようにする
            process_func.__name__ = skill_name.replace("-", "_")
            process_func.__doc__ = description
            
            tools.append(
                FunctionTool(
                    func=process_func
                )
            )
        return tools

    def load_input_schema(self, skill_name: str):
        """
        指定されたスキルの handler.py から Input スキーマ（Pydanticモデル）を動的ロードします。
        スキーマが存在しない、またはロードに失敗した場合は None を返します。
        """
        try:
            handler_module = self.load_handler(skill_name)
            return getattr(handler_module, "Input", None)
        except Exception:
            return None




