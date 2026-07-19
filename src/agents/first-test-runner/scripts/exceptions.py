"""first-test-runner スキルで利用するカスタム例外を定義するモジュール。"""

class TestFailedError(Exception):
    """テスト実行が失敗した場合に発生する例外。"""
    pass
