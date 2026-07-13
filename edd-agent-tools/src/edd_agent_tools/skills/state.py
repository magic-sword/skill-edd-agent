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
            self.state_path = self.project_root / "skills_state.json"
        else:
            self.state_path = Path(state_path).resolve()
        
        # skills.json は常に skills_state.json と同一のディレクトリに固定出力する
        self.skills_json_path = self.state_path.parent / "skills.json"
            
        self.data: Optional[SkillsStateJson] = None

    def load(self) -> SkillsStateJson:
        """skills_state.json をロードし、メモリ上に保持します。存在しない場合はデフォルト構成で初期化します。"""
        if not self.state_path.exists():
            # デフォルトはカレントディレクトリ (.)、src/skills と src/agents を探索対象として初期化
            self.data = SkillsStateJson(
                entries=[
                    SkillEntry(path=Path(".")),
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

    def export_to_skills_json(self, filter_tier: Optional[SkillTier] = None) -> dict:
        """skills_state.json から 'skills' 属性を除外し、Tier による exclude フィルタリングを施した ADK公式の skills.json 用データを生成します。"""
        if self.data is None:
            self.load()
            
        # 1. 基準となる閾値（デフォルトは READ_ONLY）を設定
        threshold = SkillTier.READ_ONLY if filter_tier is None else filter_tier
        
        # 2. 基本データをディープコピーして辞書化
        data_dict = json.loads(self.data.model_dump_json())
        
        # 'skills' フィールドを完全に削除
        if "skills" in data_dict:
            del data_dict["skills"]
            
        # 3. 各項目のパス表記をポータブルに正規化
        if "entries" in data_dict:
            for entry in data_dict["entries"]:
                if "path" in entry:
                    entry["path"] = entry["path"].replace("\\", "/")
                    
        if "inherits" in data_dict:
            for inherit in data_dict["inherits"]:
                if "path" in inherit:
                    inherit["path"] = inherit["path"].replace("\\", "/")
                    
        # 4. 閾値以下のスキル（SANDBOXなど）をスキャンして自動 exclude 追加
        # 動的スキャンを実行 (すべての検出されたスキルの中で、Tier が閾値未満のものを exclude にマージ)
        discovered = self.scan_skills()
        exclude_set = set(data_dict.get("exclude", []))
        
        for logical_name, skill_obj in discovered.items():
            if skill_obj._tier < threshold:
                exclude_set.add(logical_name)
                
        data_dict["exclude"] = sorted(list(exclude_set))
        return data_dict

    def save(self, filter_tier: Optional[SkillTier] = None):
        """現在のメモリ状態を skills_state.json ファイルへ書き出し、かつ適正な構成で skills.json へマウントします。"""
        if self.data is None:
            raise RuntimeError("エラー: データがロードされていません。")
        
        # 1. skills_state.json を保存
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                f.write(self.data.model_dump_json(indent=2))
        except Exception as e:
            raise RuntimeError(f"エラー: {self.state_path} の保存に失敗しました: {e}")

        # 2. 公式用の skills.json データを生成して書き出し
        skills_json_data = self.export_to_skills_json(filter_tier=filter_tier)

        # skills.json のパスを解決して書き出し
        os.makedirs(os.path.dirname(self.skills_json_path), exist_ok=True)
        try:
            with open(self.skills_json_path, "w", encoding="utf-8") as f:
                json.dump(skills_json_data, f, indent=2, ensure_ascii=False)
            print(f"ℹ️ Updated ADK config '{self.skills_json_path}' with {len(skills_json_data.get('entries', []))} paths.")
        except Exception as e:
            raise RuntimeError(f"エラー: skills.json の更新に失敗しました: {e}")

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
        from .skill import Skill

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

                        # メタデータ (Tier) を注入した Skill インスタンスを構築
                        discovered_skills[logical_name] = Skill(
                            root_dir=str(skill_dir),
                            tier=int(tier)
                        )

        return discovered_skills

    def get_skill(self, name: Optional[str] = None, design_path: Optional[str] = None) -> "Skill":
        """指定された名前（name）または設計ファイルパス（design_path）から、メタデータ注入済みの Skill インスタンスを返します。
        
        Args:
            name: 取得したいスキルの論理名。
            design_path: 設計ファイル (design.json) またはその親ディレクトリのパス。
            
        Raises:
            ValueError: 解決に必要なパラメータが不足しているか、物理的に見つからない場合。
        """
        if name is None and design_path is None:
            raise ValueError("エラー: name または design_path のいずれかを指定する必要があります。")

        target_name = name
        skill_dir = None

        if design_path:
            # 1. design_path から物理ディレクトリと論理名を解決
            from .models import SkillDesign
            design_abs_path = Path(design_path).resolve()
            if design_abs_path.name == "design.json":
                if design_abs_path.parent.name == "assets":
                    skill_dir = design_abs_path.parent.parent
                else:
                    skill_dir = design_abs_path.parent
            elif design_abs_path.name == "assets":
                skill_dir = design_abs_path.parent
            else:
                skill_dir = design_abs_path
                
            try:
                design = SkillDesign.load_from_file(str(skill_dir / "assets" / "design.json"))
                target_name = design.name
            except Exception:
                pass

        # 2. スキャン結果から探索
        discovered = self.scan_skills()
        if target_name and target_name in discovered:
            return discovered[target_name]

        # 3. スキャン対象外だが、design_path から直接解決された場合 (スタンドアロン読み込み / 新規作成フォールバック)
        if skill_dir:
            from edd_agent_tools.skills import Skill
            tier = SkillTier.SANDBOX
            if target_name:
                if self.data is None:
                    self.load()
                if target_name in self.data.skills:
                    tier = self.data.skills[target_name].tier
                    
            return Skill(root_dir=str(skill_dir), tier=int(tier))
            
        # 4. パス解決もスキャンも失敗し、純粋な新規モジュール名 (name) のみが指定された場合の暫定パス自動解決
        if name:
            if self.data is None:
                self.load()
                
            # 最優先（インデックス 0）の探索エントリを書き出し先ベースフォルダとして決定論的に採用する
            if self.data.entries:
                base_dir = self.project_root / self.data.entries[0].path
            else:
                base_dir = self.project_root / "src/skills"
                    
            skill_dir = base_dir / name
            from edd_agent_tools.skills import Skill
            return Skill(root_dir=str(skill_dir), tier=int(SkillTier.SANDBOX))

        raise ValueError(f"エラー: スキル '{target_name or name or design_path}' を物理的に解決できません。")

    def list_skills(self) -> list["Skill"]:
        """現在スキャンされたすべての有効なスキルおよびエージェントの Skill オブジェクトリストを返します。"""
        return list(self.scan_skills().values())

    def register_skill(self, skill: "Skill") -> bool:
        """スキルまたはエージェントのオブジェクトをメタデータ（skills_state.json）へ新規登録・更新（保存）します。
        
        Tier 1 (READ_ONLY) 以上の合格スキルの場合のみ、skills_state.json に永続化され、
        自動的に skills.json へのマウント露出も行われます。
        Tier 0 (SANDBOX) のスキルを登録・永続化する処理は行いません（動的スキャンで解決するため）。
        """
        if self.data is None:
            self.load()
            
        # Tier 0 (SANDBOX) のスキルは、登録・永続化の対象外とする
        if skill._tier == SkillTier.SANDBOX:
            print(f"Skipped registration for '{skill.name}': Tier is SANDBOX (dynamic discovery only).")
            return False
            
        skill_name = skill.name
        skills_info = self.data.skills
        existing_info = skills_info.get(skill_name)
        current_tier = existing_info.tier if existing_info else None
        
        # すでに上位の権限が適用されている既存スキルはダウングレードや不要な上書きを防ぐためスキップ
        if skill._tier == SkillTier.READ_ONLY:
            if current_tier is not None and current_tier != SkillTier.SANDBOX:
                print(f"Skipped promotion to READ_ONLY for '{skill_name}': Current tier is {current_tier.name} (only SANDBOX can be promoted).")
                return False

        # メタデータを更新 (ProjectSkillInfo)
        skills_info[skill_name] = ProjectSkillInfo(
            tier=skill._tier
        )
        
        # 自身を保存。save() 内部で、自動的に合格スキルのみを skills.json にマウント更新する処理も実行されます。
        self.save()
        print(f"Saved/Registered skill '{skill_name}' at Tier {skill._tier.name}.")
        return True
