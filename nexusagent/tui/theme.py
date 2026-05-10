"""
主题管理模块

管理TUI的颜色主题和样式。
"""

import curses


class Theme:
    """TUI主题管理器

    定义和管理终端UI的颜色方案。

    Attributes:
        name: 主题名称
        colors: 颜色定义字典
        styles: 样式定义字典
    """

    # 预定义主题
    THEMES = {
        "dark": {
            "name": "Dark",
            "background": curses.COLOR_BLACK,
            "foreground": curses.COLOR_WHITE,
            "user_msg": (curses.COLOR_CYAN, curses.COLOR_BLACK),
            "assistant_msg": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "tool_call": (curses.COLOR_YELLOW, curses.COLOR_BLACK),
            "tool_result": (curses.COLOR_GREEN, curses.COLOR_BLACK),
            "error": (curses.COLOR_RED, curses.COLOR_BLACK),
            "warning": (curses.COLOR_YELLOW, curses.COLOR_BLACK),
            "info": (curses.COLOR_BLUE, curses.COLOR_BLACK),
            "status_bar": (curses.COLOR_BLACK, curses.COLOR_WHITE),
            "input_field": (curses.COLOR_WHITE, curses.COLOR_BLUE),
            "border": curses.COLOR_CYAN,
            "highlight": (curses.COLOR_BLACK, curses.COLOR_CYAN),
            "scrollbar": curses.COLOR_CYAN,
            "code_block": (curses.COLOR_GREEN, curses.COLOR_BLACK),
            "thinking": (curses.COLOR_MAGENTA, curses.COLOR_BLACK),
            "success": (curses.COLOR_GREEN, curses.COLOR_BLACK),
            "header": (curses.COLOR_WHITE, curses.COLOR_BLUE),
        },
        "light": {
            "name": "Light",
            "background": curses.COLOR_WHITE,
            "foreground": curses.COLOR_BLACK,
            "user_msg": (curses.COLOR_BLUE, curses.COLOR_WHITE),
            "assistant_msg": (curses.COLOR_BLACK, curses.COLOR_WHITE),
            "tool_call": (curses.COLOR_MAGENTA, curses.COLOR_WHITE),
            "tool_result": (curses.COLOR_GREEN, curses.COLOR_WHITE),
            "error": (curses.COLOR_RED, curses.COLOR_WHITE),
            "warning": (curses.COLOR_YELLOW, curses.COLOR_WHITE),
            "info": (curses.COLOR_BLUE, curses.COLOR_WHITE),
            "status_bar": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "input_field": (curses.COLOR_BLACK, curses.COLOR_CYAN),
            "border": curses.COLOR_BLUE,
            "highlight": (curses.COLOR_WHITE, curses.COLOR_BLUE),
            "scrollbar": curses.COLOR_BLUE,
            "code_block": (curses.COLOR_MAGENTA, curses.COLOR_WHITE),
            "thinking": (curses.COLOR_MAGENTA, curses.COLOR_WHITE),
            "success": (curses.COLOR_GREEN, curses.COLOR_WHITE),
            "header": (curses.COLOR_WHITE, curses.COLOR_BLUE),
        },
        "mono": {
            "name": "Monochrome",
            "background": curses.COLOR_BLACK,
            "foreground": curses.COLOR_WHITE,
            "user_msg": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "assistant_msg": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "tool_call": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "tool_result": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "error": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "warning": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "info": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "status_bar": (curses.COLOR_BLACK, curses.COLOR_WHITE),
            "input_field": (curses.COLOR_BLACK, curses.COLOR_WHITE),
            "border": curses.COLOR_WHITE,
            "highlight": (curses.COLOR_BLACK, curses.COLOR_WHITE),
            "scrollbar": curses.COLOR_WHITE,
            "code_block": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "thinking": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "success": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "header": (curses.COLOR_BLACK, curses.COLOR_WHITE),
        },
    }

    def __init__(self, theme_name: str = "dark"):
        """初始化主题

        Args:
            theme_name: 主题名称
        """
        self.name = theme_name
        self._color_pairs = {}
        self._initialized = False

        if theme_name in self.THEMES:
            self.colors = self.THEMES[theme_name]
        else:
            self.colors = self.THEMES["dark"]
            self.name = "dark"

    def initialize(self, stdscr):
        """初始化curses颜色

        Args:
            stdscr: curses标准窗口
        """
        if not curses.has_colors():
            return

        curses.start_color()
        curses.use_default_colors()

        pair_id = 1
        for key, value in self.colors.items():
            if isinstance(value, tuple) and len(value) == 2:
                fg, bg = value
                try:
                    curses.init_pair(pair_id, fg, bg)
                    self._color_pairs[key] = pair_id
                    pair_id += 1
                except curses.error:
                    pass

        self._initialized = True

    def get_color(self, key: str) -> int:
        """获取颜色对ID

        Args:
            key: 颜色键名

        Returns:
            curses颜色对ID
        """
        return self._color_pairs.get(key, 0)

    def get_attr(self, key: str, bold: bool = False) -> int:
        """获取属性（颜色+样式）

        Args:
            key: 颜色键名
            bold: 是否加粗

        Returns:
            curses属性值
        """
        attr = self.get_color(key)
        if bold:
            attr |= curses.A_BOLD
        return attr

    @classmethod
    def available_themes(cls) -> list:
        """获取可用主题列表

        Returns:
            主题名称列表
        """
        return list(cls.THEMES.keys())

    def __repr__(self):
        return f"Theme(name={self.name!r})"
