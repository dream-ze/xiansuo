from __future__ import annotations

import os
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

_proxy_env_lock = threading.RLock()
_path_initialized = False
_path_lock = threading.Lock()


def _ensure_xhs_paths() -> None:
    global _path_initialized
    if _path_initialized:
        return
    with _path_lock:
        if _path_initialized:
            return
        project_root = str(Path(__file__).resolve().parents[4])
        backend_root = str(Path(__file__).resolve().parents[3])
        for path_entry in (project_root, backend_root):
            if path_entry not in sys.path:
                sys.path.insert(0, path_entry)
        _path_initialized = True


@contextmanager
def direct_xhs_request_env() -> Iterator[None]:
    _ensure_xhs_paths()
    with _proxy_env_lock:
        original = {key: os.environ.get(key) for key in PROXY_ENV_KEYS}
        for key in PROXY_ENV_KEYS:
            os.environ.pop(key, None)
        try:
            yield
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
