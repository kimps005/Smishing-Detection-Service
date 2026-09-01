"""Temporary local launcher for checking the API when the configured MySQL is unavailable."""

import os
import sys
import types
import importlib.util
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server"))


torch_spec = importlib.util.find_spec("torch")
if torch_spec is None or not torch_spec.submodule_search_locations:
    raise RuntimeError("PyTorch가 설치되어 있지 않습니다.")
torch_lib = Path(next(iter(torch_spec.submodule_search_locations))) / "lib"
_torch_dll_handle = None
if os.name == "nt" and torch_lib.is_dir():
    _torch_dll_handle = os.add_dll_directory(str(torch_lib))


class _Cursor:
    def __init__(self):
        self._rows = []

    def execute(self, query, params=None):
        normalized = " ".join(str(query).split()).upper()
        if normalized.startswith("SELECT URL, COUNT"):
            self._rows = []
        elif normalized.startswith("SELECT VALUE"):
            self._rows = [(0.0,)]
        elif normalized.startswith("SELECT COUNT"):
            self._rows = [(0,)]
        else:
            self._rows = []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def close(self):
        pass


class _Connection:
    def cursor(self):
        return _Cursor()

    def commit(self):
        pass

    def close(self):
        pass


db_config = types.ModuleType("db_config")
db_config.get_db_conn = lambda: _Connection()
sys.modules["db_config"] = db_config

import uvicorn
import torch
import main


if __name__ == "__main__":
    uvicorn.run(main.app, host="127.0.0.1", port=8000)
