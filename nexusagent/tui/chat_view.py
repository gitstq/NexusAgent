"""
聊天视图组件

显示对话历史、工具调用和Agent响应。
"""

import curses
import time
import re
from typing import List, Dict, Tuple, Optional


class ChatMessage:
    """聊天消息显示项

    Attributes:
        role: 消息角色
        content: 消息内容
        timestamp: 时间戳
        is_streaming: 是否正在流式输出
    """

    def __init__(self, role: str, content: str, timestamp: float = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or time.time()
        self.is_streaming = False

    @property
    def prefix(self) -> str:
        """获取消息前缀"""
        prefixes = {
            "user": "You >",
            "assistant": "Agent >",
            "tool_call": "Tool >",
            "tool_result": "Result >",
            "system": "System >",
            "error": "Error >",
            "info": "Info >",
            "thinking": "Think >",
        }
        return prefixes.get(self.role, f"{self.role} >")

    @property
    def wrapped_lines(self) -> List[str]:
        """获取自动换行后的行列表"""
        return self.content.split("\n")


class ChatView:
    """聊天视图组件

    显示和滚动对话内容。

    Attributes:
        window: curses窗口
        messages: 消息列表
        scroll_offset: 滚动偏移
        theme: 主题对象
    """

    def __init__(self, window, theme=None):
        """初始化聊天视图

        Args:
            window: curses窗口
            theme: 主题对象
        """
        self.window = window
        self.theme = theme
        self.messages: List[ChatMessage] = []
        self.scroll_offset = 0
        self._max_scroll = 0
        self._content_lines: List[Tuple[int, str]] = []  # (color_key, text)
        self._dirty = True

    def add_message(self, role: str, content: str):
        """添加消息

        Args:
            role: 消息角色
            content: 消息内容
        """
        self.messages.append(ChatMessage(role, content))
        self._dirty = True
        self.scroll_to_bottom()

    def update_last_message(self, content: str):
        """更新最后一条消息（用于流式输出）

        Args:
            content: 新内容
        """
        if self.messages:
            self.messages[-1].content = content
            self.messages[-1].is_streaming = True
            self._dirty = True

    def append_to_last(self, text: str):
        """向最后一条消息追加文本

        Args:
            text: 追加的文本
        """
        if self.messages:
            self.messages[-1].content += text
            self.messages[-1].is_streaming = True
            self._dirty = True

    def clear(self):
        """清空所有消息"""
        self.messages.clear()
        self._content_lines.clear()
        self.scroll_offset = 0
        self._dirty = True

    def scroll_up(self, lines: int = 5):
        """向上滚动

        Args:
            lines: 滚动行数
        """
        self.scroll_offset = max(0, self.scroll_offset - lines)
        self._dirty = True

    def scroll_down(self, lines: int = 5):
        """向下滚动

        Args:
            lines: 滚动行数
        """
        self.scroll_offset = min(self._max_scroll, self.scroll_offset + lines)
        self._dirty = True

    def scroll_to_bottom(self):
        """滚动到底部"""
        self.scroll_offset = self._max_scroll
        self._dirty = True

    def scroll_to_top(self):
        """滚动到顶部"""
        self.scroll_offset = 0
        self._dirty = True

    def _rebuild_content_lines(self):
        """重建内容行列表"""
        self._content_lines = []
        max_x = self._get_width()

        for msg in self.messages:
            # 确定颜色
            color_map = {
                "user": "user_msg",
                "assistant": "assistant_msg",
                "tool_call": "tool_call",
                "tool_result": "tool_result",
                "error": "error",
                "thinking": "thinking",
                "info": "info",
                "system": "info",
            }
            color_key = color_map.get(msg.role, "assistant_msg")

            # 添加前缀行
            prefix = msg.prefix
            if msg.is_streaming:
                prefix += " ..."
            self._content_lines.append((color_key, prefix))

            # 添加内容行（自动换行）
            for line in msg.content.split("\n"):
                if not line:
                    self._content_lines.append((color_key, ""))
                    continue

                # 简单的自动换行
                if max_x > 4:
                    while len(line) > max_x - 4:
                        self._content_lines.append((color_key, "  " + line[: max_x - 4]))
                        line = line[max_x - 4:]
                self._content_lines.append((color_key, "  " + line))

            # 消息间空行
            self._content_lines.append(("default", ""))

        self._max_scroll = max(0, len(self._content_lines) - self._get_height())
        if self.scroll_offset > self._max_scroll:
            self.scroll_offset = self._max_scroll

        self._dirty = False

    def _get_height(self) -> int:
        """获取可用高度"""
        if not self.window:
            return 24
        try:
            max_y, _ = self.window.getmaxyx()
            return max(1, max_y)
        except curses.error:
            return 24

    def _get_width(self) -> int:
        """获取可用宽度"""
        if not self.window:
            return 80
        try:
            _, max_x = self.window.getmaxyx()
            return max(10, max_x)
        except curses.error:
            return 80

    def draw(self):
        """绘制聊天视图"""
        if not self.window:
            return

        if self._dirty:
            self._rebuild_content_lines()

        max_y, max_x = self.window.getmaxyx()
        if max_y < 1 or max_x < 10:
            return

        self.window.erase()

        # 设置背景
        if self.theme and self.theme._initialized:
            try:
                self.window.bkgd(self.theme.get_color("background"))
            except curses.error:
                pass

        # 计算可见行范围
        start = self.scroll_offset
        end = min(start + max_y, len(self._content_lines))

        for i in range(start, end):
            row = i - start
            if row >= max_y:
                break

            color_key, text = self._content_lines[i]

            # 截断超长行
            if len(text) >= max_x:
                text = text[: max_x - 1]

            # 填充到窗口宽度
            text = text.ljust(max_x - 1)

            try:
                if self.theme and self.theme._initialized:
                    attr = self.theme.get_color(color_key)
                    if color_key == "user_msg":
                        attr |= curses.A_BOLD
                    self.window.addstr(row, 0, text, attr)
                else:
                    attr = curses.A_NORMAL
                    if color_key == "user_msg":
                        attr = curses.A_BOLD
                    elif color_key == "error":
                        attr = curses.A_BOLD
                    self.window.addstr(row, 0, text, attr)
            except curses.error:
                pass

        # 绘制滚动条
        if self._max_scroll > 0 and max_y > 3:
            scroll_ratio = self.scroll_offset / max(1, self._max_scroll)
            bar_height = max(1, int(max_y * 0.2))
            bar_pos = int(scroll_ratio * (max_y - bar_height))

            scroll_char = curses.ACS_VLINE
            if self.theme and self.theme._initialized:
                try:
                    self.window.vline(
                        bar_pos, max_x - 1, scroll_char, bar_height,
                        self.theme.get_attr("scrollbar", bold=True),
                    )
                except curses.error:
                    pass

        self.window.noutrefresh()

    def handle_input(self, key: int) -> bool:
        """处理输入按键

        Args:
            key: 按键值

        Returns:
            是否处理了该按键
        """
        if key == curses.KEY_UP or key == curses.KEY_PPAGE:
            # Page Up
            self.scroll_up(10 if key == curses.KEY_PPAGE else 1)
            return True
        elif key == curses.KEY_DOWN or key == curses.KEY_NPAGE:
            # Page Down
            self.scroll_down(10 if key == curses.KEY_NPAGE else 1)
            return True
        elif key == curses.KEY_HOME:
            self.scroll_to_top()
            return True
        elif key == curses.KEY_END:
            self.scroll_to_bottom()
            return True

        return False

    def resize(self):
        """处理窗口大小变化"""
        self._dirty = True
