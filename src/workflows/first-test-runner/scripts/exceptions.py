"""
first-test-runner 用の例外クラスを定義するモジュール。
"""

class TestFailedError(Exception):
    """テストの実行または評価が失敗したときに発生する例外。"""
    pass
