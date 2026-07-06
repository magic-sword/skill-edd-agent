import os
import re
import json
from pathlib import Path
from typing import Optional
from .models import SkillsStateJson, SkillEntry, InheritEntry, SkillTier, ProjectSkillInfo

class SkillsState:
    """skills_state.json のロード、保存、および ADK仕様に準拠したスキル探索（スキャン）を行う状態管理クラス。"""

    def __init__(self, state_path: Optional[Path] = None, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        
        if state_path is None:
            state_path = os.getenv("SKILLS_STATE_PATH")
            if state_path:
                state_path = Path(state_path)
            else:
                state_path = self.project_root / "skills_state.json"
        
        self.state_path = Path(state_path).resolve()
        self.data: Optional[SkillsStateJson] = None

    def load(self) -> SkillsStateJson:
        """skills_state.json をロードし、メモリ上に保持します。存在しない場合はデフォルト構成で初期化します。"""
        if not self.state_path.exists():
            # デフォルトは src/skills と src/agents を探索対象として初期化
            self.data = SkillsStateJson(
                entries=[
                    SkillEntry(path=Path("src/skills")),
                    SkillEntry(path=Path("src/agents"))
                ],
                inherits=[],
                exclude=[]
            )
            return self.data

        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                self.data = SkillsStateJson.model_validate_json(f.read())
        except Exception as e:
            raise RuntimeError(f"エラー: {self.state_path} の読み込みまたはバリデーションに失敗しました: {e}")
        return self.data

    def save(self):
        """現在のメモリ状態を skills_state.json ファイルへ書き出します。"""
        if self.data is None:
            raise RuntimeError("エラー: データがロードされていません。")
        
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                # 読みやすいようにインデントを揃えてJSON書き出し
                f.write(self.data.model_dump_json(indent=2))
        except Exception as e:
            raise RuntimeError(f"エラー: {self.state_path} の保存に失敗しました: {e}")

    def _extract_skill_name(self, skill_md_path: Path) -> Optional[str]:
        """SKILL.md のフロントマターから 'name' フィールド（論理名）を安全に抽出します。"""
        if not skill_md_path.exists():
            return None
        try:
            content = skill_md_path.read_text(encoding="utf-8")
            # 先頭の --- ... --- で囲まれたフロントマターを抽出
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if not match:
                return None
            frontmatter = match.group(1)
            for line in frontmatter.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    if key.strip() == "name":
                        # 囲みクォーテーション等を除去して返す
                        return val.strip().strip('"').strip("'")
        except Exception:
            pass
        return None

    def scan_skills(self) -> dict[str, "Skill"]:
        """登録された entries をスキャンし、有効なスキル/エージェントの論理名と Skill インスタンスの対応辞書を返します。
        
        ADK公式規則に準拠し、探索深度は直下（深さ0）または直下のサブフォルダ（深さ1）に制限され、
        exclude リストに含まれる論理名のスキルは除外されます。
        また、発見された各スキルには、skills_state.json からロードされた Tier メタデータが自動注入されます。
        """
        from edd_agent_tools.skill import Skill

        if self.data is None:
            self.load()

        discovered_skills = {}
        # 通常はローカルの exclude が適用される
        exclude_set = set(self.data.exclude)

        for entry in self.data.entries:
            # 基準ルートからの絶対パスを解決
            entry_abs_path = (self.project_root / entry.path).resolve()
            if not entry_abs_path.exists() or not entry_abs_path.is_dir():
                continue

            # スキャン処理 (ADK公式規則に準拠):
            # パス内に SKILL.md を持つフォルダを、深さ0（直下）または深さ1（直下のサブフォルダ）からのみ探します。
            possible_roots = []

            # 1. 探索エントリ自体がスキルフォルダである場合 (深さ0)
            if (entry_abs_path / "SKILL.md").exists():
                possible_roots.append(entry_abs_path)
            else:
                # 2. 探索エントリがスキルフォルダの親である場合 (深さ1のサブフォルダ走査)
                try:
                    for child in entry_abs_path.iterdir():
                        if child.is_dir() and (child / "SKILL.md").exists():
                            possible_roots.append(child)
                except Exception:
                    continue

            # 各候補フォルダから論理スキル名を抽出し、除外チェック後にマッピング
            for skill_dir in possible_roots:
                skill_md = skill_dir / "SKILL.md"
                logical_name = self._extract_skill_name(skill_md)
                
                # SKILL.md に有効な name が定義されていない場合は、ディレクトリ名を代替の論理名とする
                if not logical_name:
                    logical_name = skill_dir.name

                # 除外リストに該当しない場合のみ登録
                if logical_name not in exclude_set:
                    # 同名スキルが既に別のエントリで発見されている場合は、
                    # entries リストの順序（先勝ち）を維持して上書きを防ぐ
                    if logical_name not in discovered_skills:
                        # 登録された状態データから該当スキルの Tier を解決 (見つからない場合はデフォルトで SANDBOX: 0)
                        tier = SkillTier.SANDBOX
                        if logical_name in self.data.skills:
                            tier = self.data.skills[logical_name].tier
                        elif logical_name in self.data.agents:
                            tier = self.data.agents[logical_name].tier

                        # メタデータ (Tier) を注入した Skill インスタンスを構築
                        discovered_skills[logical_name] = Skill(
                            root_dir=str(skill_dir),
                            tier=int(tier)
                        )

        return discovered_skills

    def get_skill(self, name: str) -> "Skill":
        """指定された名前のスキル/エージェントをスキャンして、メタデータが注入済みの Skill インスタンスを返します。
        
        Args:
            name: 取得したいスキルの論理名。
            
        Raises:
            ValueError: 指定された名前のスキルがスキャン対象のパス内に物理的に見つからない場合。
        """
        discovered = self.scan_skills()
        if name not in discovered:
            raise ValueError(f"エラー: スキル '{name}' が登録された entries 内に物理的に見つかりません。")
        return discovered[name]
