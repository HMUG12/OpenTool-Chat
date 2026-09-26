"""
配置持久化 —— 单个 JSON 文件，跟随程序目录（便携模式）。

刻意保持极简：工具箱不需要复杂的配置体系，
一份扁平的 key-value JSON 足够，且方便用户手工编辑与迁移。
"""
from __future__ import annotations

import json
from typing import Any

from .paths import config_file, ensure_runtime_dirs

_DEFAULTS: dict[str, Any] = {
    "theme": "system",
    "lastCategory": "all",
}


class Config:
    def __init__(self) -> None:
        ensure_runtime_dirs()
        self._path = config_file()
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._data.update(raw)
        except (json.JSONDecodeError, OSError):
            # 配置损坏不应阻断启动，回落到默认值
            self._data = dict(_DEFAULTS)

    def save(self) -> bool:
        """写盘；失败返回 False（不抛异常，避免把界面操作带崩）。"""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, _DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> bool:
        self._data[key] = value
        return self.save()

    def snapshot(self) -> dict[str, Any]:
        return dict(self._data)


config = Config()
