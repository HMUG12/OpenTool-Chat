"""
OpenClass 入口 —— 开源实用工具箱

用法：
    python main.py              # 运行（需先构建前端）
    python main.py --dev        # 连接 frontend 的 vite 开发服务器
    python main.py --debug      # 开启 WebView 调试工具
"""
from __future__ import annotations

import sys
from pathlib import Path

# 保证以项目根目录运行时能导入 backend 包
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
