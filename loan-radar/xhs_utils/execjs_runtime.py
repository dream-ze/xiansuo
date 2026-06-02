import os
import subprocess
import sys


def _ensure_node_in_path():
    if os.name != "nt":
        return

    _setup_node_path()

    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            os.environ.setdefault("EXECJS_RUNTIME", "Node")
            return
    except Exception:
        pass

    candidates = []
    if sys.executable:
        python_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(python_dir, "Lib", "site-packages", "playwright", "driver"))

    static_dir = os.environ.get("STATIC_DIR", "")
    if static_dir:
        resources_dir = os.path.dirname(static_dir)
        candidates.append(
            os.path.join(resources_dir, "tools", "python", "Lib", "site-packages", "playwright", "driver")
        )

    loan_radar_tools = os.environ.get("LOAN_RADAR_TOOLS_DIR", "")
    if loan_radar_tools:
        candidates.append(os.path.join(loan_radar_tools, "python", "Lib", "site-packages", "playwright", "driver"))

    for node_dir in candidates:
        node_exe = os.path.join(node_dir, "node.exe")
        if os.path.isfile(node_exe):
            current_path = os.environ.get("PATH", "")
            if node_dir.lower() not in current_path.lower():
                os.environ["PATH"] = node_dir + ";" + current_path
            os.environ["EXECJS_RUNTIME"] = "Node"
            _clear_execjs_binary_cache()
            return


def _setup_node_path():
    node_path_entries = []

    static_dir = os.environ.get("STATIC_DIR", "")
    if static_dir:
        node_modules = os.path.join(static_dir, "node_modules")
        if os.path.isdir(node_modules):
            node_path_entries.append(node_modules)

    if not node_path_entries:
        for candidate in (
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "node_modules"),
        ):
            candidate = os.path.normpath(candidate)
            if os.path.isdir(candidate):
                node_path_entries.append(candidate)
                break

    if node_path_entries:
        existing = os.environ.get("NODE_PATH", "")
        new_paths = os.pathsep.join(node_path_entries)
        if existing:
            os.environ["NODE_PATH"] = new_paths + os.pathsep + existing
        else:
            os.environ["NODE_PATH"] = new_paths


def _clear_execjs_binary_cache():
    try:
        import execjs._external_runtime as external_runtime
        for attr in ("_binary_cache",):
            for name in dir(external_runtime):
                obj = getattr(external_runtime, name, None)
                if obj is not None and hasattr(obj, attr):
                    try:
                        delattr(obj, attr)
                    except (AttributeError, TypeError):
                        pass
    except Exception:
        pass


_ensure_node_in_path()


def configure_hidden_execjs_subprocesses():
    if os.name != "nt":
        return

    try:
        import execjs._external_runtime as external_runtime
    except Exception:
        return

    current_popen = external_runtime.Popen
    if getattr(current_popen, "_loan_radar_hidden", False):
        return

    def hidden_popen(*args, **kwargs):
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
        return current_popen(*args, **kwargs)

    hidden_popen._loan_radar_hidden = True
    external_runtime.Popen = hidden_popen

    _patch_extract_result(external_runtime)


def _patch_extract_result(external_runtime):
    try:
        original_extract = external_runtime.ExternalRuntime.Context._extract_result
    except Exception:
        return

    if getattr(original_extract, "_loan_radar_patched", False):
        return

    def safe_extract(self, output):
        if output is None:
            raise external_runtime.ProgramError(
                "execjs: subprocess returned empty output. "
                "The JavaScript runtime may have crashed or is not properly configured."
            )
        return original_extract(self, output)

    safe_extract._loan_radar_patched = True
    external_runtime.ExternalRuntime.Context._extract_result = safe_extract
