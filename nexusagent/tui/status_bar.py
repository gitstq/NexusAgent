"""
状态栏组件

显示Agent状态、Provider信息、token使用情况等。
"""

import curses
from typing import Dict, Any


class StatusBar:
    """TUI状态栏组件

    在界面底部显示当前状态信息。

    Attributes:
        window: curses窗口对象
        height: 状态栏高度
        theme: 主题对象
    """

    def __init__(self, window, height: int = 1, theme=None):
        """初始化状态栏

        Args:
            window: curses窗口
            height: 状态栏高度
            theme: 主题对象
        """
        self.window = window
        self.height = height
        self.theme = theme
        self._status_text = "Ready"
        self._provider = ""
        self._model = ""
        self._iteration = 0
        self._max_iterations = 20
        self._context_usage = 0
        self._context_max = 8000

    def update(self, status: str = "", **kwargs):
        """更新状态栏信息

        Args:
            status: 状态文本
            **kwargs: 其他状态信息
        """
        if status:
            self._status_text = status
        self._provider = kwargs.get("provider", self._provider)
        self._model = kwargs.get("model", self._model)
        self._iteration = kwargs.get("iteration", self._iteration)
        self._max_iterations = kwargs.get("max_iterations", self._max_iterations)
        self._context_usage = kwargs.get("context_usage", self._context_usage)
        self._context_max = kwargs.get("context_max", self._context_max)

    def draw(self):
        """绘制状态栏"""
        if not self.window:
            return

        max_y, max_x = self.window.getmaxyx()
        if max_y < 1 or max_x < 10:
            return

        self.window.erase()

        # 背景色
        if self.theme and self.theme._initialized:
            self.window.bkgd(self.theme.get_color("status_bar"))

        # 构建状态栏内容
        parts = []

        # 左侧: 状态
        status_icon = {
            "Ready": "[=]",
            "Thinking": "[~]",
            "Working": "[*]",
            "Error": "[!]",
        }.get(self._status_text, "[?]")

        parts.append(f" {status_icon} {self._status_text}")

        # 中间: Provider和模型
        if self._provider and self._model:
            parts.append(f" | {self._provider}/{self._model}")

        # 右侧: 迭代和上下文
        right_parts = []
        if self._iteration > 0:
            right_parts.append(f"Iter:{self._iteration}/{self._max_iterations}")
        if self._context_max > 0:
            usage_pct = min(100, int(self._context_usage / self._context_max * 100))
            right_parts.append(f"Ctx:{usage_pct}%")

        if right_parts:
            parts.append(" " * 3)
            parts.append(" | ".join(right_parts))

        status_line = "".join(parts)

        # 截断到窗口宽度
        if len(status_line) >= max_x:
            status_line = status_line[: max_x - 1]

        # 填充空白
        status_line = status_line.ljust(max_x - 1)

        # 绘制
        try:
            if self.theme and self.theme._initialized:
                self.window.addstr(0, 0, status_line, self.theme.get_color("status_bar"))
            else:
                self.window.addstr(0, 0, status_line, curses.A_REVERSE)
        except curses.error:
            pass

        self.window.noutrefresh()

    def set_status(self, status: str):
        """设置状态文本

        Args:
            status: 状态文本
        """
        self._status_text = status

    def resize(self, new_height: int = None):
        """调整状态栏大小

        Args:
            new_height: 新高度
        """
        if new_height:
            self.height = new_height
