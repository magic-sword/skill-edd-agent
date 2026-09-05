"""
Unified Skill Entity and Test Suite Domain Model for edd-agent-tools

Anthropic Claude Skills (Markdown-First & Progressive Disclosure) および
Google ADK 2.0 準拠のスキルパッケージ管理ドメインクラス。
"""

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path
from typing import Literal, Any, Optional, List, Dict

from ..models.spec import SkillSpec, SkillPattern, ModuleType, SkillMetadata
from ..models.state import SkillTier


class SkillPackage:
    """Markdown-First & Progressive Disclosure に準拠したスキルパッケージ管理ドメインクラス。

    SKILL.md を単一真実源（Single Source of Truth）とし、
    3層リソース（scripts, references, assets）およびテスト環境（tests）を型安全にカプセル化します。
    """
    def __init__(self, root_dir: str | Path, tier: int = 0, last_tested: Optional[str] = None):
        self.root_dir = os.path.abspath(str(root_dir))
        self._tier = tier
        self._last_tested = last_tested
        self._spec: Optional[SkillSpec] = None
        self._metadata: Optional[SkillMetadata] = None
        self._tests = None

    @property
    def tier(self) -> int:
        """このスキルの Tier (0: SANDBOX, 1: READ_ONLY, 2: DRAFT_ONLY, 3: ACTION_ALLOWED)"""
        return self._tier

    def set_tier(self, tier: int):
        """このスキルの Tier を設定し、テスト時刻を更新します。"""
        if tier not in [0, 1, 2, 3]:
            raise ValueError("Error: Tier must be 0, 1, 2, or 3.")
        self._tier = tier
        self._last_tested = datetime.datetime.now().isoformat() + "Z"
        self._metadata = None

    @property
    def spec_path(self) -> str:
        """SKILL.md の絶対パス"""
        return os.path.join(self.root_dir, "SKILL.md")

    @property
    def scripts_dir(self) -> str:
        """scripts/ ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "scripts")

    @property
    def references_dir(self) -> str:
        """references/ ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "references")

    @property
    def assets_dir(self) -> str:
        """assets/ ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "assets")

    @property
    def examples_dir(self) -> str:
        """examples/ ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "examples")

    @property
    def tests_dir(self) -> str:
        """tests/ ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "tests")


    @property
    def spec(self) -> SkillSpec:
        """SKILL.md をパースした SkillSpec インスタンスを取得（キャッシュ付き）"""
        if self._spec is None:
            if not os.path.exists(self.spec_path):
                from ..models.spec import SkillFrontmatter
                self._spec = SkillSpec(
                    frontmatter=SkillFrontmatter(name=os.path.basename(self.root_dir), description=""),
                    title=os.path.basename(self.root_dir),
                    overview="",
                    body=""
                )
            else:
                self._spec = SkillSpec.load_from_file(self.spec_path)
        return self._spec

    @property
    def name(self) -> str:
        """スキル名"""
        try:
            return self.spec.name
        except Exception:
            return os.path.basename(self.root_dir)

    def load_spec(self) -> str:
        """SKILL.md の生テキストを取得します。"""
        if os.path.exists(self.spec_path):
            return Path(self.spec_path).read_text(encoding="utf-8")
        return ""

    @property
    def dependencies(self) -> List[str]:
        """このスキルが依存している他のスキル名のリスト"""
        try:
            return self.spec.dependencies
        except Exception:
            return []

    @property
    def description(self) -> str:
        """スキルの説明（Frontmatter の description）"""
        try:
            return self.spec.description
        except Exception:
            return ""

    @property
    def pattern(self) -> SkillPattern:
        """スキルパターン"""
        try:
            return self.spec.pattern
        except Exception:
            return SkillPattern.WORKFLOW

    @property
    def tests(self) -> "SkillTests":
        """テスト管理オブジェクト（SkillTests）を取得"""
        if self._tests is None:
            self._tests = SkillTests(self.root_dir)
        return self._tests

    # ==========================================
    # 3層リソース探索・取得メソッド群 (ADK 2.0 Resources 優先活用)
    # ==========================================

    def list_scripts(self) -> List[str]:
        """内包するスクリプト（ファイル名ベース）の一覧を取得"""
        if hasattr(self, "_adk_skill") and self._adk_skill is not None:
            return sorted(list(self._adk_skill.resources.scripts.keys()))
        scripts_dir = Path(self.root_dir) / "scripts"
        if not scripts_dir.exists():
            return []
        return sorted([f.name for f in scripts_dir.glob("*.py") if f.name != "__init__.py"])

    def list_references(self) -> List[str]:
        """内包する参照資料（ファイル名ベース）の一覧を取得"""
        if hasattr(self, "_adk_skill") and self._adk_skill is not None:
            all_refs = self._adk_skill.resources.references.keys()
            return sorted([r for r in all_refs if not r.startswith("examples/")])
        ref_dir = Path(self.root_dir) / "references"
        if not ref_dir.exists():
            return []
        return sorted([f.name for f in ref_dir.glob("*") if f.is_file()])

    def list_assets(self) -> List[str]:
        """内包するアセット（ファイル名ベース）の一覧を取得"""
        if hasattr(self, "_adk_skill") and self._adk_skill is not None:
            return sorted(list(self._adk_skill.resources.assets.keys()))
        assets_dir = Path(self.root_dir) / "assets"
        if not assets_dir.exists():
            return []
        return sorted([f.name for f in assets_dir.glob("*") if f.is_file()])

    def list_examples(self) -> List[str]:
        """内包する使用例・パターン例（ファイル名ベース）の一覧を取得"""
        if hasattr(self, "_adk_skill") and self._adk_skill is not None:
            all_refs = self._adk_skill.resources.references.keys()
            return sorted([r.replace("examples/", "") for r in all_refs if r.startswith("examples/")])
        ex_dir = Path(self.root_dir) / "examples"
        if not ex_dir.exists():
            return []
        return sorted([f.name for f in ex_dir.glob("*") if f.is_file()])

    def read_example(self, rel_path: str) -> str:
        """指定された使用例ファイルのコンテンツを読み込みます。"""
        target = Path(self.root_dir) / rel_path
        if not target.exists():
            cand = Path(self.root_dir) / "examples" / rel_path
            if cand.exists():
                target = cand
        if not target.exists():
            raise FileNotFoundError(f"Example '{rel_path}' not found in skill '{self.name}'.")
        return target.read_text(encoding="utf-8")

    def load_example(self, rel_path: str) -> str:
        """指定された使用例ファイルのコンテンツを読み込みます（read_example のエイリアス）。"""
        return self.read_example(rel_path)

    def read_reference(self, rel_path: str) -> str:
        """指定された参照資料のコンテンツを読み込みます。"""
        target = Path(self.root_dir) / rel_path
        if not target.exists():
            cand = Path(self.root_dir) / "references" / rel_path
            if cand.exists():
                target = cand
        if not target.exists():
            raise FileNotFoundError(f"Reference '{rel_path}' not found in skill '{self.name}'.")
        return target.read_text(encoding="utf-8")

    def load_reference(self, rel_path: str) -> str:
        """指定された参照資料のコンテンツを読み込みます（read_reference のエイリアス）。"""
        return self.read_reference(rel_path)

    def get_script_path(self, script_name: str) -> str:
        """指定されたスクリプトの絶対パスを返します。"""
        scripts_dir = Path(self.root_dir) / "scripts"
        cand = scripts_dir / script_name
        if cand.exists():
            return str(cand)
        cand_py = scripts_dir / f"{script_name}.py"
        if cand_py.exists():
            return str(cand_py)
        return str(cand)

    @property
    def adk_skill(self) -> Any:
        """Google ADK 2.0 純正の Skill (google.adk.skills.models.Skill) オブジェクトを取得（キャッシュ付き）"""
        if not hasattr(self, "_adk_skill") or self._adk_skill is None:
            try:
                from google.adk.skills import load_skill_from_dir
                self._adk_skill = load_skill_from_dir(Path(self.root_dir))
            except Exception:
                # SKILL.md 等が存在しない場合のフォールバック変換
                self._adk_skill = self.spec.to_adk_skill(self.root_dir)
        return self._adk_skill

    def to_adk_skill(self) -> Any:
        """google.adk.skills.models.Skill オブジェクトを返します（adk_skill のエイリアス）。"""
        return self.adk_skill

    @property
    def instructions(self) -> str:
        """ADK 互換 instructions (SKILL.md 本文)"""
        return self.spec.body

    @property
    def frontmatter(self) -> Any:
        """ADK 互換 frontmatter"""
        return self.adk_skill.frontmatter

    @property
    def resources(self) -> Any:
        """ADK 互換 resources"""
        return self.adk_skill.resources

    def get_metadata(self) -> SkillMetadata:
        """レジストリ・評価・仕様をマージした統合メタデータを返します。"""
        if self._metadata is None:
            self._metadata = SkillMetadata(
                name=self.name,
                tier=self.tier,
                last_tested=self._last_tested,
                module_type=ModuleType.SKILL,
                pattern=self.pattern,
                description=self.description,
                scripts=self.list_scripts(),
                references=self.list_references(),
                assets=self.list_assets(),
                examples=self.list_examples()
            )
        return self._metadata

    def load_resource(self, resource_rel_path: str) -> str:
        """指定された相対パスのリソースファイル内容を取得します。"""
        target_path = Path(self.root_dir) / resource_rel_path
        if not target_path.exists():
            raise FileNotFoundError(f"Resource '{resource_rel_path}' not found in skill '{self.name}'.")
        return target_path.read_text(encoding="utf-8")

    def execute_script(
        self,
        script_name: Optional[str] = None,
        args: Optional[Union[List[str], Dict[str, Any]]] = None,
        extra_env: Optional[Dict[str, str]] = None,
        timeout: int = 60,
        positional_args: Optional[List[str]] = None,
        short_options: Optional[Dict[str, Any]] = None,
        code_executor: Optional[Any] = None
    ) -> Dict[str, Any]:
        """スキルの scripts/ 配下の決定論的スクリプトを実行し、結果を返します。
        
        デフォルトでは完全隔離された高速・安全なサブプロセス（LocalSubprocessExecutor）により
        決定論的 CLI 実行を行い、マルチプロセッシングのハングやゾンビプロセスの発生を防止します。
        code_executor が明示的に注入された場合は、Google ADK 2.0 純正の SkillToolset に委譲します。
        """
        scripts = self.list_scripts()
        target_script = None

        if script_name:
            clean_name = script_name[len("scripts/"):] if script_name.startswith("scripts/") else script_name
            for s in scripts:
                if s == clean_name or s == f"{clean_name}.py" or os.path.basename(s) == clean_name:
                    target_script = os.path.join(self.scripts_dir, s)
                    break
        elif scripts:
            target_script = os.path.join(self.scripts_dir, scripts[0])

        if not target_script or not os.path.exists(target_script):
            raise FileNotFoundError(f"Could not resolve execution script in '{self.scripts_dir}'.")

        rel_path = f"scripts/{clean_name if script_name else os.path.basename(target_script)}"
        is_shell = target_script.endswith((".sh", ".bash"))

        # コマンドライン引数の正規化
        cmd_args = []
        if positional_args:
            cmd_args.extend(str(p) for p in positional_args)
        if short_options and isinstance(short_options, dict):
            for sk, sv in short_options.items():
                s_flag = f"-{sk}" if not sk.startswith("-") else sk
                if sv is True:
                    cmd_args.append(s_flag)
                elif sv is not False and sv is not None:
                    cmd_args.extend([s_flag, str(sv)])
        if isinstance(args, dict):
            for ak, av in args.items():
                flag = f"--{ak.replace('_', '-')}" if not ak.startswith("-") else ak
                if av is True:
                    cmd_args.append(flag)
                elif av is not False and av is not None:
                    cmd_args.extend([flag, str(av)])
        elif isinstance(args, list):
            cmd_args.extend(str(a) for a in args)

        # 追加の環境変数設定
        orig_env = {}
        if extra_env:
            for k, v in extra_env.items():
                orig_env[k] = os.environ.get(k)
                os.environ[k] = str(v)

        try:
            # 外部 CodeExecutor が明示的に指定された場合のみ ADK Toolset を介して実行
            if code_executor is not None:
                from google.adk.tools.skill_toolset import SkillToolset
                toolset = SkillToolset(skills=[self.adk_skill], code_executor=code_executor, script_timeout=timeout)

                class _AdkToolContext:
                    invocation_id = f"exec_{self.name}"
                    class _Invocation:
                        agent = None
                    _invocation_context = _Invocation()

                tool_args: Dict[str, Any] = {
                    "skill_name": self.name,
                    "file_path": rel_path
                }
                if args is not None:
                    tool_args["args"] = args
                if positional_args is not None:
                    tool_args["positional_args"] = positional_args
                if short_options is not None:
                    tool_args["short_options"] = short_options

                async def _invoke_adk_tool():
                    tools = await toolset.get_tools()
                    run_tool = next(t for t in tools if t.name == "run_skill_script")
                    return await run_tool.run_async(args=tool_args, tool_context=_AdkToolContext())

                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        res = pool.submit(asyncio.run, _invoke_adk_tool()).result()
                else:
                    res = asyncio.run(_invoke_adk_tool())

                stdout = res.get("stdout", "") if isinstance(res, dict) else str(res)
                stderr = res.get("stderr", "") if isinstance(res, dict) else ""
                status = res.get("status", "success") if isinstance(res, dict) else "success"
                return {
                    "skill_name": self.name,
                    "file_path": rel_path,
                    "status": "success" if status == "success" else "failed",
                    "exit_code": 0 if status == "success" else 1,
                    "stdout": stdout,
                    "stderr": stderr,
                    "script_path": target_script,
                    "executor": type(code_executor).__name__
                }

            # デフォルト: サブプロセスによる決定論的かつ安全・高速な CLI 実行
            cmd = ["bash", target_script] if is_shell else [sys.executable, target_script]
            cmd.extend(cmd_args)

            env = os.environ.copy()
            env["EDD_SKILL_NAME"] = self.name
            env["EDD_SKILL_ROOT"] = str(self.root_dir)

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.root_dir,
                env=env,
                timeout=timeout
            )

            status = "success" if proc.returncode == 0 else "failed"
            return {
                "skill_name": self.name,
                "file_path": rel_path,
                "status": status,
                "exit_code": proc.returncode,
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "script_path": target_script,
                "executor": "LocalSubprocessExecutor"
            }
        except subprocess.TimeoutExpired:
            return {
                "skill_name": self.name,
                "file_path": rel_path,
                "status": "failed",
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Script timed out after {timeout} seconds",
                "script_path": target_script,
                "error": "TimeoutExpired"
            }
        except Exception as e:
            return {
                "skill_name": self.name,
                "file_path": rel_path,
                "status": "failed",
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "script_path": target_script,
                "error": str(e)
            }
        finally:
            if orig_env:
                for k, v in orig_env.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

    def __repr__(self) -> str:
        return f"<SkillPackage name='{self.name}' tier={self.tier} path='{self.root_dir}'>"


class SkillTests:
    """スキルの tests/ ディレクトリ配下のテスト仕様データ（evalsets）および
    実行結果ログ（results）を型安全に管理・アクセスするためのドメインクラス。
    """

    def __init__(self, skill_root_dir: str | Path):
        self.skill_root_dir = os.path.abspath(str(skill_root_dir))
        self.tests_dir = os.path.join(self.skill_root_dir, "tests")
        self.results_dir = os.path.join(self.tests_dir, "results")
        self.fixtures_dir = os.path.join(self.tests_dir, "fixtures")

    @property
    def latest_report_path(self) -> str:
        """最新のテスト実行詳細レポート（JSON）の絶対パス。"""
        return os.path.join(self.results_dir, "latest_report.json")

    def get_evalset_path(self, test_type: str) -> Optional[str]:
        """指定されたテスト種別（trigger, contract, unit, golden, judge 等）の evalset ファイルパスを探索"""
        if not os.path.exists(self.tests_dir):
            return None

        import glob
        raw_name = os.path.basename(self.skill_root_dir)
        name_under = raw_name.replace('-', '_')
        name_hyphen = raw_name.replace('_', '-')

        # 1. Google ADK 2.0 公式 EvalSet 単一真実源 (SSOT: {skill_name}.test.json) を最優先探索
        for name in {raw_name, name_hyphen, name_under}:
            ssot_path = os.path.join(self.tests_dir, f"{name}.test.json")
            if os.path.isfile(ssot_path):
                return os.path.abspath(ssot_path)

        # 2. テスト種別指定がある場合のサブテストセット探索
        if test_type:
            for name in {raw_name, name_hyphen, name_under}:
                for sep in ["_", "-"]:
                    type_path = os.path.join(self.tests_dir, f"{name}{sep}{test_type}.test.json")
                    if os.path.isfile(type_path):
                        return os.path.abspath(type_path)

            for cand in [f"{test_type}.test.json", f"*{test_type}*.test.json"]:
                matches = glob.glob(os.path.join(self.tests_dir, cand))
                if matches:
                    return os.path.abspath(matches[0])

        # 3. 任意の *.test.json の探索
        any_matches = sorted(glob.glob(os.path.join(self.tests_dir, "*.test.json")))
        if any_matches:
            return os.path.abspath(any_matches[0])

        return None


    def save_report(
        self,
        report: Any,
        test_type: Optional[str] = None
    ) -> str:
        """テスト実行レポートを results/ 配下に保存し、latest_report.json も同時に更新"""
        from ..models.eval import EvalDetailReport
        os.makedirs(self.results_dir, exist_ok=True)

        if isinstance(report, dict):
            report_obj = EvalDetailReport.model_validate(report)
        else:
            report_obj = report

        resolved_test_type = test_type or getattr(report_obj, "test_type", None)
        json_data = report_obj.model_dump_json(indent=2) if hasattr(report_obj, "model_dump_json") else json.dumps(report, indent=2)

        if resolved_test_type:
            type_specific_path = os.path.join(self.results_dir, f"{resolved_test_type}_test_result.json")
            with open(type_specific_path, "w", encoding="utf-8") as f:
                f.write(json_data)

        with open(self.latest_report_path, "w", encoding="utf-8") as f:
            f.write(json_data)

        return self.latest_report_path

    def load_latest_report(self) -> Optional[Any]:
        """最新のテスト実行レポート（latest_report.json）をロード"""
        from ..models.eval import EvalDetailReport
        if not os.path.isfile(self.latest_report_path):
            return None

        try:
            with open(self.latest_report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EvalDetailReport.model_validate(data)
        except Exception:
            return None

    def load_report(self, test_type: str) -> Optional[Any]:
        """指定されたテスト種別の結果レポートをロード"""
        from ..models.eval import EvalDetailReport
        target_path = os.path.join(self.results_dir, f"{test_type}_test_result.json")
        if not os.path.isfile(target_path):
            return None

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EvalDetailReport.model_validate(data)
        except Exception:
            return None

    def list_reports(self) -> list[str]:
        """results/ 配下に存在する全レポートファイルの絶対パスリストを返します。"""
        import glob
        if not os.path.exists(self.results_dir):
            return []
        return [
            os.path.abspath(p)
            for p in glob.glob(os.path.join(self.results_dir, "*.json"))
        ]

    def list_evalsets(self) -> list[str]:
        """tests/ 配下に存在する全 *.test.json ファイルの絶対パスリストを返します。"""
        import glob
        if not os.path.exists(self.tests_dir):
            return []
        return sorted([os.path.abspath(p) for p in glob.glob(os.path.join(self.tests_dir, "*.test.json"))])


# Google ADK 2.0 純正 google.adk.skills.models.Skill との同名衝突を解消したエイリアス定義
Skill = SkillPackage

