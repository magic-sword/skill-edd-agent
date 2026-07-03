import os
import sys
import json
import hashlib
import datetime
import importlib.util

class SkillRegistry:
    """skills_registry.json のデータ構造をカプセル化し、読み込み・保存・更新・動的ツールロードを管理するクラス"""
    
    def __init__(self, registry_path: str = "/workspace/src/skills_registry.json"):
        self.registry_path = os.path.abspath(registry_path)
        self.data = None

    def load(self) -> dict:
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
            raise RuntimeError("エラー: レジストリがロードされていません。先に load() を呼び出してください。")
            
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"エラー: レジストリの保存に失敗しました: {e}")

    def calculate_skill_hashes(self, skill_name: str) -> dict[str, str]:
        """指定されたスキルの Python ファイルや SKILL.md のハッシュ値を計算します。"""
        if self.data is None:
            self.load()
            
        search_paths = self.data.get("search_paths", ["src/skills"])
        skill_dir = None
        for path_entry in search_paths:
            possible_dir = os.path.abspath(os.path.join("/workspace", path_entry, skill_name))
            if os.path.exists(possible_dir) and os.path.isdir(possible_dir):
                skill_dir = possible_dir
                break
                
        hashes = {}
        if not skill_dir:
            return hashes
            
        for root, _, files in os.walk(skill_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, skill_dir)
                if "__pycache__" in rel_path or rel_path.endswith(".pyc") or ".git" in rel_path:
                    continue
                hasher = hashlib.sha256()
                try:
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
                    hashes[rel_path] = hasher.hexdigest()
                except Exception:
                    pass
        return hashes

    def register_skill(self, skill_name: str):
        """スキルを新規登録します（デフォルトは Tier 1）。"""
        if self.data is None:
            self.load()
            
        skills_info = self.data.setdefault("skills", {})
        if skill_name in skills_info:
            print(f"Skill '{skill_name}' already registered.")
            return
            
        hashes = self.calculate_skill_hashes(skill_name)
        skills_info[skill_name] = {
            "tier": 1,
            "last_tested": None,
            "file_hashes": hashes
        }
        self.save()
        print(f"Registered skill '{skill_name}' at Tier 1.")

    def set_tier(self, skill_name: str, tier: int):
        """指定されたスキルの Tier を設定・更新します。"""
        if tier not in [0, 1, 2, 3]:
            raise ValueError("Error: Tier must be 0, 1, 2, or 3.")
            
        if self.data is None:
            self.load()
            
        skills_info = self.data.setdefault("skills", {})
        now_str = datetime.datetime.now().isoformat() + "Z"
        
        hashes = self.calculate_skill_hashes(skill_name)
        skills_info[skill_name] = {
            "tier": tier,
            "last_tested": now_str,
            "file_hashes": hashes
        }
        self.save()
        print(f"Set tier of '{skill_name}' to {tier}.")

    def list_skills(self):
        """登録されている全スキルの一覧を表示します。"""
        if self.data is None:
            self.load()
            
        print(f"{'Skill Name':<25} | {'Tier':<5} | {'Last Tested':<25}")
        print("-" * 63)
        for name, info in sorted(self.data.get("skills", {}).items()):
            last_tested = info.get("last_tested") or "Never"
            print(f"{name:<25} | {info['tier']:<5} | {last_tested:<25}")

    def update_meta(self, skill_name: str):
        """スキルのファイルハッシュメタデータを最新の状態に更新します。"""
        if self.data is None:
            self.load()
            
        skills_info = self.data.get("skills", {})
        if skill_name not in skills_info:
            self.register_skill(skill_name)
            return
            
        hashes = self.calculate_skill_hashes(skill_name)
        skills_info[skill_name]["file_hashes"] = hashes
        self.save()
        print(f"Updated file hashes for skill '{skill_name}'.")

    def load_tool(self, skill_name: str, function_name: str):
        """指定されたスキルと関数名から Python スクリプトを動的ロードし、関数オブジェクトを返します。"""
        if self.data is None:
            self.load()
            
        search_paths = self.data.get("search_paths", ["src/skills"])
        skills_info = self.data.get("skills", {})
        
        if skill_name not in skills_info:
            raise ValueError(f"エラー: スキル '{skill_name}' がレジストリに登録されていません。")
            
        skill_meta = skills_info[skill_name]
        file_hashes = skill_meta.get("file_hashes", {})
        
        script_rel_path = None
        for file_path in file_hashes.keys():
            if file_path.startswith("scripts/") and file_path.endswith(".py"):
                script_rel_path = file_path
                break
                
        if not script_rel_path:
            raise FileNotFoundError(
                f"エラー: スキル '{skill_name}' のメタデータ内に実行可能な Python スクリプト (scripts/*.py) が登録されていません。"
            )
            
        # search_paths からスキルディレクトリを動的特定
        skill_dir = None
        for path_entry in search_paths:
            possible_dir = os.path.abspath(os.path.join("/workspace", path_entry, skill_name))
            if os.path.exists(possible_dir) and os.path.isdir(possible_dir):
                skill_dir = possible_dir
                break
                
        if not skill_dir:
            raise FileNotFoundError(
                f"エラー: スキル '{skill_name}' の実体ディレクトリが探索パス {search_paths} 内に見つかりません。"
            )
            
        script_abs_path = os.path.join(skill_dir, script_rel_path)
        if not os.path.exists(script_abs_path):
            raise FileNotFoundError(f"エラー: 特定されたスクリプトファイルが存在しません: {script_abs_path}")
            
        # 動的インポート
        module_name = skill_name.replace("-", "_")
        
        if module_name in sys.modules:
            module = sys.modules[module_name]
        else:
            spec = importlib.util.spec_from_file_location(module_name, script_abs_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        
        if not hasattr(module, function_name):
            raise AttributeError(f"エラー: モジュール '{module_name}' に関数 '{function_name}' が定義されていません。")
            
        return getattr(module, function_name)
