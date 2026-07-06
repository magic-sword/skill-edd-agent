
# テンプレートファイル

セマンティックな指示で引数を解決できる、関数ノードテンプレートファイルを作成しておく

<pre>
{skill_class} = state.get_skill("{skill_name}")
{skill_name}_module = {skill_class}.load_module()
{skill_name}_tool = {skill_class}.get_tool
def run_designer_step(tool_context: ToolContext) -> str:
    # セマンティックな指示による引数解決でスキルを実行
    return xxx.run("引数を解決して、ツールを実行してください" , {skill_name}_tool ,({skill_name}_module.Input, tool_context) )
<pre>