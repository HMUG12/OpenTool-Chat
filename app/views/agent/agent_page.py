"""
🤖 AI Agent — 左历史 + 右聊天工作区 | SSE 流式 | Markdown | 键鼠代理 | 文件解析

(文件经修改：MessageBubble 使用 QTextBrowser 支持 HTML/code block，支持自动换行与入场动画)
"""
from __future__ import annotations

import json
import re
import html as html_mod
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QFileDialog, QSplitter,
    QScrollArea, QSizePolicy, QMessageBox, QDialog, QApplication,
    QAbstractItemView, QTextBrowser, QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl, QThread, QEvent, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QFont, QDragEnterEvent, QDropEvent, QColor, QIcon, QTextCursor,
    QKeyEvent, QResizeEvent, QTextOption
)

from qfluentwidgets import (
    PrimaryPushButton, PushButton, FluentIcon,
    SwitchButton, ComboBox, LineEdit,  # qfluentwidgets ComboBox/LineEdit
    InfoBar, InfoBarPosition, BodyLabel, StrongBodyLabel,
    isDarkTheme, ToolButton,
)
from qfluentwidgets.components.dialog_box import MessageBoxBase

from app.database.db_manager import db
from app.database.crypto import decrypt
from app.utils.signal_bus import signal_bus

# ═══════════════════════════════════════════════════════════════
# 文件解析器
# ═══════════════════════════════════════════════════════════════

def _read_text_file(path: str) -> str | None:
    """读取文本文件，自动检测编码（UTF-8 → GBK）。"""
    encodings = ["utf-8", "gbk", "gb2312", "latin-1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None


def parse_file(path: str) -> str | None:
    """
    解析文件内容（.txt / .pdf / .docx）。
    返回文本内容，失败返回 None。
    """
    ext = Path(path).suffix.lower()

    if ext == ".txt":
        return _read_text_file(path)

    if ext == ".pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
            return "\n\n".join(parts) if parts else None
        except Exception:
            return None

    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(path)
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(parts) if parts else None
        except Exception:
            return None

    # fallback：当 txt 读
    return _read_text_file(path)


# ═══════════════════════════════════════════════════════════════
# Markdown → 简易 HTML（无 markdown 库时的降级渲染）
# ═══════════════════════════════════════════════════════════════


def _escape_html(text: str) -> str:
    return html_mod.escape(text)


def render_markdown(text: str) -> str:
    """将 Markdown 文本转换为 HTML。优先使用 markdown 库。"""
    try:
        import markdown
        return markdown.markdown(
            text,
            extensions=["fenced_code", "codehilite", "tables", "nl2br"]
        )
    except ImportError:
        pass

    # ── 简易降级渲染 ──
    t = _escape_html(text)

    # 代码块 ```
    t = re.sub(r"```(\w*)\n(.*?)```", r'<pre><code>\2</code></pre>', t, flags=re.DOTALL)
    # 行内代码 `...`
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    # **粗体**
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    # *斜体*
    t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)
    # ### 标题
    t = re.sub(r"^### (.+)$", r"<h4>\1</h4>", t, flags=re.MULTILINE)
    t = re.sub(r"^## (.+)$", r"<h3>\1</h3>", t, flags=re.MULTILINE)
    t = re.sub(r"^# (.+)$", r"<h2>\1</h2>", t, flags=re.MULTILINE)
    # 无序列表
    t = re.sub(r"^- (.+)$", r"<li>\1</li>", t, flags=re.MULTILINE)
    # 换行 → <br>
    t = t.replace("\n", "<br>")

    return f"<div style='font-size:16px; line-height:1.8;'>{t}</div>"


# ═══════════════════════════════════════════════════════════════
# 消息气泡 Widget
# ═══════════════════════════════════════════════════════════════


class MessageBubble(QFrame):
    """聊天消息气泡 — 使用 QTextBrowser 支持 HTML/代码块；支持入场动画与宽度限制"""

    def __init__(self, role: str, content: str, parent=None, max_fraction_of_parent: float = 0.6):
        super().__init__(parent)
        self.setObjectName("messageBubble")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.max_fraction_of_parent = max_fraction_of_parent

        dark = isDarkTheme()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        # 使用 QTextBrowser 替代 QLabel，保证 HTML（含 <pre><code>）渲染
        self._text = QTextBrowser(self)
        self._text.setFrameStyle(QFrame.NoFrame)
        self._text.setReadOnly(True)
        self._text.setOpenExternalLinks(True)
        self._text.setAcceptRichText(True)
        self._text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        # 更好的换行策略
        self._text.document().setDefaultTextOption(QTextOption(QTextOption.WrapAtWordBoundaryOrAnywhere))
        self._text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        # 初始 stream buffer（用于流式拼接）
        self._stream_buffer = ""

        # 入场动画准备
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._has_shown = False

        if role == "user":
            layout.addStretch(1)
            self._text.setStyleSheet("""
                QTextBrowser {
                    background: #7C3AED; color: #FFFFFF;
                    border-radius: 14px; padding: 12px 20px; font-size: 16px;
                }
            """)
            # 用户消息显示为纯文本（转义）
            self._text.setHtml(f"<div>{_escape_html(content)}</div>")
            layout.addWidget(self._text, alignment=Qt.AlignmentFlag.AlignRight)

        elif role == "assistant":
            bg = "rgba(255,255,255,0.04)" if dark else "rgba(0,0,0,0.03)"
            color = "#E4E4E7" if dark else "#1E293B"
            self._text.setStyleSheet(f"""
                QTextBrowser {{
                    background: {bg}; color: {color};
                    border-radius: 14px; padding: 12px 20px; font-size: 16px;
                }}
                pre, code {{ font-family: monospace; }}
            """)
            # 可能是流式开始，content 可能为空
            if content:
                self._stream_buffer = content
                self._text.setHtml(render_markdown(content))
            else:
                self._text.setHtml("")
            layout.addWidget(self._text, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addStretch(1)

        elif role == "system":
            layout.addStretch(1)
            self._text.setStyleSheet("QTextBrowser { background: transparent; color: #94a3b8; font-size:16px; }")
            self._text.setHtml(_escape_html(content))
            self._text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._text)
            layout.addStretch(1)

        elif role == "error":
            layout.addStretch(1)
            self._text.setStyleSheet("""
                QTextBrowser {
                    background: rgba(239,68,68,0.10);
                    border: 1px solid rgba(239,68,68,0.30);
                    color: #EF4444; border-radius: 12px;
                    padding: 14px 22px; font-size: 16px;
                }
            """)
            self._text.setHtml(f"⚠️ {_escape_html(content)}")
            layout.addWidget(self._text)
            layout.addStretch(1)

        elif role == "timeout":
            layout.addStretch(1)
            card = QWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(10)

            self._timeout_label = QTextBrowser()
            self._timeout_label.setStyleSheet("""
                QTextBrowser {
                    background: rgba(245,158,11,0.12);
                    border: 1px solid rgba(245,158,11,0.35);
                    color: #F59E0B; border-radius: 12px;
                    padding: 14px 22px; font-size: 16px;
                }
            """)
            self._timeout_label.setHtml("⚠️ 请求超时，请检查网络或 Base URL 配置")
            card_layout.addWidget(self._timeout_label)

            self._retry_btn = QPushButton("🔄 重试")
            self._retry_btn.setFixedHeight(38)
            self._retry_btn.setStyleSheet("""
                QPushButton {
                    font-size: 15px; font-weight: bold;
                    background: #F59E0B; color: #FFFFFF;
                    border: none; border-radius: 8px; padding: 6px 20px;
                }
                QPushButton:hover { background: #D97706; }
            """)
            self._retry_btn.setFixedWidth(120)
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            btn_row.addWidget(self._retry_btn)
            btn_row.addStretch()
            card_layout.addLayout(btn_row)

            layout.addWidget(card)
            layout.addStretch(1)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_max_width()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._has_shown:
            self._has_shown = True
            self._run_entrance_animation()
        self._update_max_width()

    def _update_max_width(self):
        parent = self.parent() if self.parent() is not None else self.window()
        try:
            parent_width = parent.width()
        except Exception:
            parent_width = QApplication.primaryScreen().availableGeometry().width()
        max_w = max(300, int(parent_width * self.max_fraction_of_parent))
        max_w = min(max_w, 1000)
        self._text.setMaximumWidth(max_w)
        self.setMaximumWidth(max_w + self.layout().contentsMargins().left() + self.layout().contentsMargins().right())

    def _run_entrance_animation(self):
        try:
            self._opacity_effect.setOpacity(0.0)
            anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
            anim.setDuration(220)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        except Exception:
            pass

    # 流式追加：把 buffer 拼接并重新渲染 Markdown（render_markdown 返回 HTML）
    def append_content(self, delta: str) -> None:
        self._stream_buffer += delta
        try:
            self._text.setHtml(render_markdown(self._stream_buffer))
        except Exception:
            # 回退为文本追加（防止渲染异常阻塞流）
            cur = self._text.toPlainText()
            self._text.setPlainText(cur + delta)

    def finalize(self, content: str) -> None:
        self._stream_buffer = content
        try:
            self._text.setHtml(render_markdown(content))
        except Exception:
            self._text.setPlainText(content)

# ============================== 剩余文件内容保持不变 ==============================
# (下面内容为文件其余部分，未被修改 — 保留原样)


# ═══════════════════════════════════════════════════════════════
# SSE 流式 API 调用器
# ═══════════════════════════════════════════════════════════════

class SSEStreamer(QThread):
    """后台线程 — HTTP POST + SSE stream，逐 chunk 发信号。"""

    chunk_received = Signal(str)    # 增量文本
    stream_finished = Signal(str)   # 完整文本
    stream_error = Signal(str)      # 错误信息
    stream_timeout = Signal()       # 超时专用信号

    def __init__(self, base_url: str, api_key: str, model: str,
                 messages: list[dict], timeout: int = 10, parent=None):
        super().__init__(parent)
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._messages = messages
        self._timeout = timeout
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        url = f"{self._base_url}/chat/completions"
        body = json.dumps({
            "model": self._model,
            "messages": self._messages,
            "stream": True,
            "temperature": 0.7,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "text/event-stream",
        }

        for attempt in range(2):  # 最多 2 次（含一次重试）
            if self._cancelled:
                return
            try:
                req = Request(url, data=body, headers=headers)
                with urlopen(req, timeout=self._timeout) as resp:
                    full_text = ""
                    buffer = b""

                    while not self._cancelled:
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        buffer += chunk

                        # 按 SSE 协议解析行
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            if not line.startswith(b"data: "):
                                continue
                            data_str = line[6:].decode("utf-8", errors="replace")

                            if data_str == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0]["delta"]
                                text = delta.get("content", "")
                                if text:
                                    full_text += text
                                    self.chunk_received.emit(text)
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

                    self.stream_finished.emit(full_text)
                    return

            except URLError as e:
                if attempt == 0:
                    # 第一次失败，重试
                    time.sleep(1)
                    continue
                reason = str(e.reason) if hasattr(e, 'reason') else str(e)
                if "timeout" in reason.lower() or "timed out" in reason.lower():
                    self.stream_timeout.emit()
                else:
                    self.stream_error.emit(f"网络请求失败: {e}")
                return
            except Exception as e:
                self.stream_error.emit(f"请求异常: {e}")
                return

        self.stream_timeout.emit()

# (其余文件内容 unchanged...)
