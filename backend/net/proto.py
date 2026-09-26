"""
机房协同协议 —— 老师机与学生机之间的最小通信约定。

设计取向：
  1. 只用标准库（socket / http.server / urllib），不引入新依赖 —— 绿色版
     与国产系统环境里不需要额外安装任何东西；
  2. 传输用「HTTP + 长轮询」而非 WebSocket：实现简单、穿透性好，
     秒级延迟对课堂指令完全够用；
  3. 配对码 + token 双保险：6 位配对码只用于第一次握手，之后一律用
     随机 token，避免配对码被反复试探。

消息体统一为 JSON 字典：
  action   指令动作（见 ACTIONS）
  payload  动作参数
  seq      指令序号（学生机据此去重，避免重复执行）
  timeout  期望完成时间（秒）
"""
from __future__ import annotations

import json
import secrets
import time
from typing import Any

PROTOCOL_VERSION = 1
MAGIC = "OpenClassBox.lan"

DEFAULT_HTTP_PORT = 38900
DISCOVERY_PORT = 38901

POLL_HOLD_SECONDS = 20.0   # 长轮询最长挂起时间
REPORT_INTERVAL = 5.0      # 学生机心跳间隔

# 支持的远程动作
ACTIONS = (
    "checkup",    # 一键体检
    "repair",     # 一键修复（payload.key 指定单项，空为全部）
    "cleanup",    # 磁盘清理（payload.keys 指定项，空为默认项）
    "kill",       # 结束进程（payload.pid）
    "power",      # 电源操作（payload.mode: shutdown/restart/lock）
    "message",    # 弹消息（payload.text）
    "push_file",  # 下发文件（payload.name + 内容由 /api/file 传输）
    "pull_file",  # 回收文件（payload.paths 目录列表）
    "wallpaper",  # 统一换壁纸（payload.path，学生机本地路径或已下发文件）
)

ACTION_NAMES: dict[str, str] = {
    "checkup": "一键体检",
    "repair": "一键修复",
    "cleanup": "磁盘清理",
    "kill": "结束进程",
    "power": "电源操作",
    "message": "发消息",
    "push_file": "下发文件",
    "pull_file": "回收文件",
    "wallpaper": "统一壁纸",
}


def pairing_code() -> str:
    """生成 6 位配对码（老师机展示，学生机输入）。"""
    return f"{secrets.randbelow(1_000_000):06d}"


def make_token() -> str:
    """生成节点令牌。"""
    return secrets.token_hex(16)


def dumps(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def loads(raw: bytes | str) -> dict[str, Any]:
    """宽松解析：任何异常都退化为空字典，绝不抛出。"""
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        data = json.loads(text)
    except (ValueError, UnicodeDecodeError, AttributeError):
        return {}
    return data if isinstance(data, dict) else {}


def now_ms() -> int:
    return int(time.time() * 1000)
