# edd-agent-tools package
# 【名前空間デッドロック防止のための先行インポート】
# google.adk と google.genai が同一の 'google' 名前空間を共有する仕様上、
# 起動後の探索パス変動により、インポート順序（adk -> genai）でインポートロックが
# 競合してデッドロックする現象を防止するため、ライブラリのロード時にこれらを一括して先行インポートします。
try:
    from google import genai
    from google.adk.tools import ToolContext
except ImportError:
    pass

__version__ = "0.1.0"

from .models import Parameter, SkillDesign
