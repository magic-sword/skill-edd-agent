#!/usr/bin/env python3
"""
Antigravity 自律最適化ループオーケストレーター (ADK 2.0 Optimizer Loop)

Antigravity CLI (`agy`) をサブプロセスとして繰り返し呼び出し、
各反復で独立したクリーンなセッション（Ephemeral Session）を起動して
Google ADK 2.0 のベストプラクティス準拠・車輪の再発明排除・ドキュメント最新化を自律的に反復します。
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


def run_pytest() -> bool:
    """pytest を実行し、すべてのテストがパスするか検証する。"""
    print("[Verifier] pytest を実行してリグレッションを検証中...")
    res = subprocess.run(["pytest"], capture_output=True, text=True)
    return res.returncode == 0


def rollback_git():
    """未コミットの破壊的変更を直前のコミットまで安全にロールバックする。"""
    print("[Rollback] テスト未通過または異常な未コミット変更を検知したため、直前のコミットへロールバックします...")
    subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)
    subprocess.run(["git", "clean", "-fd"], check=True)


def load_prompt_template(template_path: Path) -> str:
    """プロンプトテンプレートファイルを読み込む。"""
    if not template_path.exists():
        raise FileNotFoundError(f"プロンプトテンプレートが見つかりません: {template_path}")
    return template_path.read_text(encoding="utf-8")


def log_message(log_file: Path, message: str):
    """コンソール出力およびログファイルへの追記を行う。"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Antigravity CLI を用いた Google ADK 2.0 自律最適化ループオーケストレーター"
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
        "--model",
        type=str,
        default="",
        help="agy セッションで使用するモデル名 (省略時は agy デフォルト)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="agy を実行せず、プロンプトとコマンドの構成のみ検証して終了する",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=".adk_optimization_loop.log",
        help="実行ログの出力先ファイルパス",
    )

    args = parser.parse_args()

    workspace_root = Path(__file__).resolve().parents[4]
    skill_dir = Path(__file__).resolve().parents[1]
    template_path = skill_dir / "references" / "prompt_template.md"
    log_path = workspace_root / args.log_file

    os.chdir(workspace_root)

    log_message(log_path, "=" * 60)
    log_message(log_path, "ADK 2.0 自律最適化ループを開始します。")
    log_message(log_path, f"Workspace Root: {workspace_root}")
    log_message(log_path, f"Max Iterations: {args.max_iterations}")

    prompt_content = load_prompt_template(template_path)

    if args.dry_run:
        log_message(log_path, "[DRY-RUN] プロンプトテンプレートを正常に読み込みました。")
        log_message(log_path, f"[DRY-RUN] プロンプト文字数: {len(prompt_content)}")
        print("\n--- プロンプト先頭 500 文字 ---")
        print(prompt_content[:500] + "...\n")
        print("[DRY-RUN] 正常に終了しました。")
        return

    # 作業ツリーの状態確認
    initial_status = get_git_status()
    if initial_status:
        log_message(
            log_path,
            f"[Warning] 作業ツリーに未コミットの変更が存在します:\n{initial_status}",
        )
        log_message(
            log_path,
            "安全のため、未コミットの変更をコミットまたは退避 (stash) してから実行することを推奨します。",
        )

    consecutive_no_change = 0

    for iteration in range(1, args.max_iterations + 1):
        log_message(
            log_path,
            f"\n>>> [Iteration {iteration}/{args.max_iterations}] 新しいクリーンなセッションを開始します...",
        )
        before_commit = get_current_commit()

        # agy コマンドライン構築
        cmd = ["agy", "-p", prompt_content, "--dangerously-skip-permissions"]
        if args.model:
            cmd.extend(["--model", args.model])

        try:
            # 独立したサブプロセスとして agy CLI を実行 (Ephemeral Session)
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=args.timeout,
                cwd=workspace_root,
            )
            session_output = proc.stdout + "\n" + proc.stderr

            # ログ記録
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"\n--- Iteration {iteration} Output ---\n")
                f.write(session_output)
                f.write("\n------------------------------\n")

        except subprocess.TimeoutExpired:
            log_message(log_path, f"[Timeout] セッションが {args.timeout} 秒を超過過したため強制終了しました。")
            rollback_git()
            continue
        except Exception as e:
            log_message(log_path, f"[Error] agy 実行中に例外が発生しました: {e}")
            rollback_git()
            continue

        # 収束シグナルの検出
        if "OPTIMIZATION_COMPLETE" in session_output:
            log_message(
                log_path,
                "🎉 [Convergence] エージェントが OPTIMIZATION_COMPLETE シグナルを出力しました！"
            )
            log_message(
                log_path,
                "すべての ADK 2.0 最適化が完了し、改善点が解消されたと判定されました。"
            )
            break

        # テストの整合性チェック
        after_status = get_git_status()
        if after_status:
            # 未コミットの変更が残されている場合、pytest を実行
            if not run_pytest():
                log_message(log_path, "[Fail] テストが失敗したため、変更をロールバックします。")
                rollback_git()
                continue
            else:
                log_message(log_path, "[Notice] 未コミットの有効な変更が検知されました。自動コミットを実行します。")
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run(
                    ["git", "commit", "-m", f"refactor(adk): iteration {iteration} での最適化改修"],
                    check=True,
                )

        after_commit = get_current_commit()
        if after_commit != before_commit:
            log_message(log_path, f"✅ [Success] コミットが作成されました: {after_commit[:7]}")
            consecutive_no_change = 0
        else:
            log_message(log_path, "ℹ️ [No Change] この反復では新しいコミットは作成されませんでした。")
            consecutive_no_change += 1
            if consecutive_no_change >= 2:
                log_message(
                    log_path,
                    "2回連続で変更が発生しなかったため、これ以上の改善点はないと判断しループを終了します。",
                )
                break

    log_message(log_path, "\nADK 2.0 自律最適化ループが終了しました。")
    log_message(log_path, "=" * 60)


if __name__ == "__main__":
    main()
