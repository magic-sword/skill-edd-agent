import re

class OutputParser:
    def parse_adk_eval_output(self, combined_output: str, return_code: int) -> dict:
        """
        adk eval コマンドの出力からテスト結果を解析します。
        """
        passed_match = re.search(r"Tests passed:\s*(\d+)", combined_output)
        failed_match = re.search(r"Tests failed:\s*(\d+)", combined_output)

        accuracy = 0.0
        parsed = False
        
        passed = 0
        failed = 0

        if passed_match and failed_match:
            passed = int(passed_match.group(1))
            failed = int(failed_match.group(1))
            total = passed + failed
            if total > 0:
                accuracy = passed / total
                parsed = True
        
        # 正規表現でパースできなかった場合のフォールバック判定
        if not parsed:
            if return_code == 0:
                accuracy = 1.0
            else:
                accuracy = 0.0

        return {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
            "accuracy": accuracy,
            "parsed_from_log": parsed
        }
