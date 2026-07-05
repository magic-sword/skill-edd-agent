import os

def get_patched_env(env_vars: dict = None) -> dict:
    """
    多言語パッチ用 PYTHONPATH などの環境変数を一元的に構成した辞書オブジェクトを返します。
    """
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    patch_dir = os.path.join(current_file_dir, "patch")
    
    # edd-agent-tools の src ディレクトリのルートを特定
    edd_tools_src_dir = os.path.abspath(os.path.join(current_file_dir, "..", ".."))

    # ベース環境変数を構成
    patched_env = os.environ.copy()
    if env_vars:
        patched_env.update(env_vars)

    # PYTHONPATH を構成
    pythonpaths = [patch_dir, edd_tools_src_dir]
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    if current_pythonpath:
        for path in current_pythonpath.split(":"):
            if path and path not in pythonpaths:
                pythonpaths.append(path)
    patched_env["PYTHONPATH"] = ":".join(pythonpaths)
    
    return patched_env
