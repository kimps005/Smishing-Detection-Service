"""Temporary local launcher for checking the API when the configured MySQL is unavailable."""

import os
import sys
import types


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server"))


torch_lib = r"C:\Users\SAMSUNG\AppData\Local\Programs\Python\Python311\Lib\site-packages\torch\lib"
_torch_dll_handle = os.add_dll_directory(torch_lib)


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


if not hasattr(main.paddle_reader, "predict") and hasattr(main.paddle_reader, "ocr"):
    main.paddle_reader.predict = lambda image_path: main.paddle_reader.ocr(image_path, cls=True)


if __name__ == "__main__":
    uvicorn.run(main.app, host="127.0.0.1", port=8000)
