"""
ADK 2.0 ワークフロー向け動的解決共通ユーティリティモジュール。
"""
import json
import importlib.util
import sys
import os

REGISTRY_PATH = "/workspace/src/skills_registry.json"

def load_tool_from_skill(skill_name: str, function_name: str):
    """
    skills_registry.json の情報を活用し、
    登録されたスキルとそのアセットの完全性（ファイルハッシュ）情報をベースに、
    scripts/ 配下にある Python スクリプトからターゲット関数を動的に解決・ロードします。
    これで物理的なファイル配置位置やスクリプトファイル名へのハードコード依存を排除します。
    """
    if not os.path.exists(REGISTRY_PATH):
        raise FileNotFoundError(f"エラー: レジストリファイルが見つかりません: {REGISTRY_PATH}")
        
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception as e:
        raise RuntimeError(f"エラー: レジストリの読み込みに失敗しました: {e}")
        
    search_paths = registry.get("search_paths", ["src/skills"])
    skills_info = registry.get("skills", {})
    
    if skill_name not in skills_info:
        raise ValueError(f"エラー: スキル '{skill_name}' がレジストリに登録されていません。")
        
    skill_meta = skills_info[skill_name]
    file_hashes = skill_meta.get("file_hashes", {})
    
    # file_hashes の中から scripts/ で始まり .py で終わるファイルパスを特定
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
        
    # 動的インポート (モジュール名にハイフンが含まれるのを避けるため、スネークケースに変換)
    module_name = skill_name.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, script_abs_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    if not hasattr(module, function_name):
        raise AttributeError(f"エラー: モジュール '{module_name}' に関数 '{function_name}' が定義されていません。")
        
    return getattr(module, function_name)
