#!/usr/bin/env python3
"""
Antigravity 自律スキル構築ループオーケストレーター (Autonomous Skill Builder Loop)

Google 『Agent Skills』ホワイトペーパー（May 2026）のアーキテクチャに完全準拠し、
Antigravity CLI (`agy`) による独立子プロセス（Ephemeral Sessions）を活用して、
自然言語の要求から以下の4フェーズを自律的に進行・完了します：

  Phase 1: EDD インバージョン先行策定 (3正例 + 3負例の test.json & test_config.json)
  Phase 2: 3層リソース実装 (SKILL.md & scripts/、edd validate 合格)
  Phase 3: 多層評価 & 自己修復 ($pass^k$ 契約テスト、edd diagnose 自己修復)
  Phase 4: 連鎖回帰テスト & Tier 昇格 (Cascade Testing、目標 Tier 昇格確定)
"""

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path


def get_git_status() -> str:
    """現在の Git 作業ツリーの状態を取得する。"""
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    return res.stdout.strip()


def get_current_commit() -> str:
    """最新のコミットハッシュを取得する。"""
    res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    return res.stdout.strip()


def rollback_git():
    """直前のコミットまで安全にロールバックする。"""
    print("[Rollback] 異常な未コミット変更またはテスト失敗を検知したため、直前のコミットへロールバックします...")
    subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)
    subprocess.run(["git", "clean", "-fd"], check=True)


def log_message(log_file: Path, message: str):
    """コンソール出力およびログファイルへの追記を行う。"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def load_and_render_template(template_path: Path, variables: dict) -> str:
    """プロンプトテンプレートを読み込み、変数を置換する。"""
    if not template_path.exists():
        raise FileNotFoundError(f"テンプレートファイルが見つかりません: {template_path}")
    content = template_path.read_text(encoding="utf-8")
    for key, value in variables.items():
        content = content.replace(f"{{{key}}}", str(value))
    return content


def run_phase_session(
    cmd: list,
    timeout: int,
    workspace_root: Path,
    log_file: Path,
    phase_name: str
) -> tuple[bool, str]:
    """独立した agy 子プロセスを実行し、出力ログを記録する。"""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workspace_root,
        )
        session_output = proc.stdout + "\n" + proc.stderr
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"\n--- {phase_name} Output ---\n")
            f.write(session_output)
            f.write("\n------------------------------\n")
        return True, session_output
    except subprocess.TimeoutExpired:
        log_message(log_file, f"[Timeout] {phase_name} が {timeout} 秒を超過したため強制終了しました。")
        rollback_git()
        return False, "Timeout"
    except Exception as e:
        log_message(log_file, f"[Error] {phase_name} 実行中に例外が発生しました: {e}")
        rollback_git()
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="Google Agent Skills 白書準拠 自律スキル構築ループオーケストレーター"
    )
    parser.add_argument(
        "--skill-name",
        type=str,
        required=True,
        help="構築対象のスキル名 (kebab-case, 例: text-summarizer)",
    )
    parser.add_argument(
        "--description",
        type=str,
        required=True,
        help="スキルの要求仕様・機能目的の自然言語説明",
    )
    parser.add_argument(
        "--target-tier",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="目標とする品質 Tier (1: Read-Only, 2: Draft-Only, 3: Action-Allowed, デフォルト: 1)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="最大反復回数 (デフォルト: 10)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="各セッションのタイムアウト秒数 (デフォルト: 600秒)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="agy を実行せず、各フェーズのプロンプト構成と変数置換を検証して終了する",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=".skill_builder.log",
        help="実行ログの出力先ファイルパス",
    )

    args = parser.parse_args()

    # スキル名フォーマット検証
    skill_name = args.skill_name.strip().lower()
    if "_" in skill_name or " " in skill_name:
        print(f"Error: スキル名は kebab-case で指定してください (例: {skill_name.replace('_', '-').replace(' ', '-')})")
        sys.exit(1)

    primary_script = skill_name.replace("-", "_")

    workspace_root = Path(__file__).resolve().parents[4]
    skill_dir = Path(__file__).resolve().parents[1]
    templates_dir = skill_dir / "references" / "prompt_templates"
    log_path = workspace_root / args.log_file

    os.chdir(workspace_root)

    log_message(log_path, "=" * 60)
    log_message(log_path, "Google Agent Skills 自律スキル構築ループを開始します。")
    log_message(log_path, f"Skill Name: {skill_name}")
    log_message(log_path, f"Target Tier: Tier {args.target_tier}")
    log_message(log_path, f"Workspace Root: {workspace_root}")

    # テンプレート変数の準備
    variables = {
        "SKILL_NAME": skill_name,
        "SKILL_DESCRIPTION": args.description,
        "PRIMARY_SCRIPT": primary_script,
        "TARGET_TIER": args.target_tier,
    }

    phases = [
        ("Phase 1: EDD Inversion (3正例+3負例先行策定)", templates_dir / "phase1_inversion.md"),
        ("Phase 2: 3-Tier Resource Implementation (実装)", templates_dir / "phase2_implementation.md"),
        ("Phase 3: Multi-Layer Eval & Self-Healing (評価・自己修復)", templates_dir / "phase3_eval_and_heal.md"),
        ("Phase 4: Cascade Regression & Tier Promotion (連鎖回帰・昇格)", templates_dir / "phase4_tier_promotion.md"),
    ]

    if args.dry_run:
        log_message(log_path, "\n[DRY-RUN] 各フェーズのプロンプトテンプレート構成を検証します：")
        for phase_name, t_path in phases:
            prompt = load_and_render_template(t_path, variables)
            print(f"\n=== {phase_name} ===")
            print(f"Template: {t_path.name} (文字数: {len(prompt)})")
            print("--- 先頭 300 文字 ---")
            print(prompt[:300] + "...\n")
        print("[DRY-RUN] 全フェーズの構成検証が正常に完了しました。")
        return

    # 作業ツリーの状態確認
    initial_status = get_git_status()
    if initial_status:
        log_message(log_path, f"[Warning] 作業ツリーに未コミットの変更が存在します:\n{initial_status}")

    # フェーズ進行ループ
    for phase_idx, (phase_name, template_path) in enumerate(phases, start=1):
        log_message(log_path, f"\n>>> [{phase_name}] 新しいクリーンなセッションを開始します...")
        prompt = load_and_render_template(template_path, variables)
        before_commit = get_current_commit()

        cmd = ["agy", "-p", prompt, "--dangerously-skip-permissions"]

        success, output = run_phase_session(
            cmd=cmd,
            timeout=args.timeout,
            workspace_root=workspace_root,
            log_file=log_path,
            phase_name=phase_name
        )

        if not success:
            log_message(log_path, f"❌ [{phase_name}] セッションが失敗しました。")
            break

        after_commit = get_current_commit()
        if after_commit != before_commit:
            log_message(log_path, f"✅ [{phase_name}] 完了・コミット作成: {after_commit[:7]}")
        else:
            log_message(log_path, f"ℹ️ [{phase_name}] コミット変更なしでセッション完了。")

        if phase_idx == 4 and "BUILDER_COMPLETE" in output:
            log_message(log_path, "\n🎉 [Success] BUILDER_COMPLETE シグナルを受信しました！")
            log_message(
                log_path,
                f"スキル '{skill_name}' は EDD インバージョン、3層リソース実装、多層評価、"
                f"連鎖回帰テストをすべて通過し、Tier {args.target_tier} への昇格が完了しました！"
            )
            break

    log_message(log_path, "\n自律スキル構築ループが終了しました。")
    log_message(log_path, "=" * 60)


if __name__ == "__main__":
    main()
