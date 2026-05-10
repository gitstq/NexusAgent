"""
TUI主应用

使用curses库构建的终端用户界面主应用。
"""

import curses
import sys
import os
import threading
import time
from typing import Optional, Callable

from nexusagent.tui.theme import Theme
from nexusagent.tui.chat_view import ChatView
from nexusagent.tui.status_bar import StatusBar
from nexusagent.agent import NexusAgent
from nexusagent.config import Config
from nexusagent.session import Session


class InputHandler:
    """输入处理器

    管理用户输入的读取和编辑。

    Attributes:
        window: curses窗口
        buffer: 输入缓冲区
        cursor_pos: 光标位置
        history: 输入历史
        history_index: 历史索引
    """

    def __init__(self, window):
        """初始化输入处理器

        Args:
            window: curses窗口
        """
        self.window = window
        self.buffer = ""
        self.cursor_pos = 0
        self.history: list = []
        self.history_index = -1
        self._prompt = "> "

    def get_line(self) -> str:
        """获取一行用户输入

        Returns:
            用户输入的字符串
        """
        self.buffer = ""
        self.cursor_pos = 0
        self.history_index = -1

        self._draw_input()

        while True:
            try:
                key = self.window.getch()
            except curses.error:
                continue

            if key == curses.KEY_ENTER or key == 10 or key == 13:
                # Enter
                line = self.buffer
                if line.strip():
                    self.history.append(line)
                self._clear_input()
                return line

            elif key == 27:
                # Escape - 清空输入
                self.buffer = ""
                self.cursor_pos = 0
                self._draw_input()

            elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                # Backspace
                if self.cursor_pos > 0:
                    self.buffer = (
                        self.buffer[: self.cursor_pos - 1]
                        + self.buffer[self.cursor_pos:]
                    )
                    self.cursor_pos -= 1
                    self._draw_input()

            elif key == curses.KEY_DC:
                # Delete
                if self.cursor_pos < len(self.buffer):
                    self.buffer = (
                        self.buffer[: self.cursor_pos]
                        + self.buffer[self.cursor_pos + 1:]
                    )
                    self._draw_input()

            elif key == curses.KEY_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                    self._draw_input()

            elif key == curses.KEY_RIGHT:
                if self.cursor_pos < len(self.buffer):
                    self.cursor_pos += 1
                    self._draw_input()

            elif key == curses.KEY_HOME:
                self.cursor_pos = 0
                self._draw_input()

            elif key == curses.KEY_END:
                self.cursor_pos = len(self.buffer)
                self._draw_input()

            elif key == curses.KEY_UP:
                # 历史上一条
                if self.history and self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.buffer = self.history[-(self.history_index + 1)]
                    self.cursor_pos = len(self.buffer)
                    self._draw_input()

            elif key == curses.KEY_DOWN:
                # 历史下一条
                if self.history_index > 0:
                    self.history_index -= 1
                    self.buffer = self.history[-(self.history_index + 1)]
                    self.cursor_pos = len(self.buffer)
                elif self.history_index == 0:
                    self.history_index = -1
                    self.buffer = ""
                    self.cursor_pos = 0
                self._draw_input()

            elif key == curses.KEY_RESIZE:
                # 窗口大小变化
                self._draw_input()

            elif 32 <= key <= 126 or key > 255:
                # 可打印字符
                try:
                    char = chr(key)
                    self.buffer = (
                        self.buffer[: self.cursor_pos]
                        + char
                        + self.buffer[self.cursor_pos:]
                    )
                    self.cursor_pos += 1
                    self._draw_input()
                except (ValueError, OverflowError):
                    pass

            elif key == 9:
                # Tab - 暂不处理自动补全
                pass

    def _draw_input(self):
        """绘制输入行"""
        if not self.window:
            return

        max_y, max_x = self.window.getmaxyx()
        if max_y < 1 or max_x < 4:
            return

        try:
            self.window.erase()
            self.window.move(0, 0)

            # 绘制提示符
            self.window.addstr(0, 0, self._prompt, curses.A_BOLD)

            # 绘制输入内容
            available_width = max_x - len(self._prompt) - 1
            if available_width > 0:
                # 如果内容超过可用宽度，显示光标附近的部分
                display_text = self.buffer
                if len(display_text) > available_width:
                    start = max(0, self.cursor_pos - available_width + 1)
                    display_text = display_text[start: start + available_width]

                self.window.addstr(0, len(self._prompt), display_text)

            # 移动光标
            display_cursor = self.cursor_pos
            if len(self.buffer) > available_width and available_width > 0:
                display_cursor = min(
                    self.cursor_pos,
                    available_width - 1,
                )
            self.window.move(0, len(self._prompt) + display_cursor)

            self.window.noutrefresh()
        except curses.error:
            pass

    def _clear_input(self):
        """清空输入行"""
        self.buffer = ""
        self.cursor_pos = 0
        if self.window:
            try:
                self.window.erase()
                self.window.move(0, 0)
                self.window.addstr(0, 0, self._prompt, curses.A_BOLD)
                self.window.noutrefresh()
            except curses.error:
                pass


class TUIApp:
    """TUI主应用

    管理整个终端UI的生命周期，包括布局、事件处理和渲染。

    Attributes:
        agent: NexusAgent实例
        theme: 主题
        chat_view: 聊天视图
        status_bar: 状态栏
        input_handler: 输入处理器
    """

    def __init__(
        self,
        agent: NexusAgent = None,
        config: Config = None,
        theme_name: str = "dark",
    ):
        """初始化TUI应用

        Args:
            agent: NexusAgent实例（为None则在run时创建）
            config: 配置
            theme_name: 主题名称
        """
        self._config = config or Config()
        self._agent = agent
        self._theme_name = theme_name
        self._running = False
        self._processing = False

        # curses组件（在run中初始化）
        self.stdscr = None
        self.theme = None
        self.chat_view = None
        self.status_bar = None
        self.input_handler = None

        # 布局参数
        self._input_height = 2
        self._status_height = 1
        self._border_width = 1

        # 命令处理
        self._commands = {
            "/quit": self._cmd_quit,
            "/exit": self._cmd_quit,
            "/q": self._cmd_quit,
            "/clear": self._cmd_clear,
            "/cls": self._cmd_clear,
            "/help": self._cmd_help,
            "/status": self._cmd_status,
            "/reset": self._cmd_reset,
            "/save": self._cmd_save,
            "/theme": self._cmd_theme,
            "/provider": self._cmd_provider,
            "/tools": self._cmd_tools,
            "/history": self._cmd_history,
        }

    def run(self):
        """启动TUI应用"""
        try:
            curses.wrapper(self._main_loop)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False

    def _main_loop(self, stdscr):
        """curses主循环

        Args:
            stdscr: curses标准窗口
        """
        self.stdscr = stdscr
        self._init_curses()
        self._init_components()
        self._init_agent()

        self._running = True

        # 显示欢迎信息
        self._show_welcome()

        while self._running:
            self._update_status("Ready")
            self._refresh()

            # 获取用户输入
            try:
                user_input = self.input_handler.get_line()
            except Exception:
                break

            if not user_input.strip():
                continue

            # 处理命令
            cmd = user_input.strip().lower()
            if cmd in self._commands:
                self._commands[cmd](user_input)
                continue

            # 处理Agent对话
            if not self._processing:
                self._process_input(user_input)

        self._cleanup()

    def _init_curses(self):
        """初始化curses设置"""
        # 基本设置
        curses.cbreak()
        curses.noecho()
        self.stdscr.keypad(True)
        self.stdscr.nodelay(False)

        # 隐藏光标
        try:
            curses.curs_set(1)
        except curses.error:
            pass

        # 初始化主题
        self.theme = Theme(self._theme_name)
        self.theme.initialize(self.stdscr)

        # 设置颜色
        if self.theme._initialized:
            try:
                self.stdscr.bkgd(self.theme.get_color("background"))
            except curses.error:
                pass

    def _init_components(self):
        """初始化UI组件"""
        max_y, max_x = self.stdscr.getmaxyx()

        # 计算布局
        chat_height = max_y - self._input_height - self._status_height - self._border_width * 2

        # 创建聊天视图窗口
        chat_win = curses.newwin(chat_height, max_x, 0, 0)
        chat_win.scrollok(True)
        chat_win.idlok(True)
        self.chat_view = ChatView(chat_win, self.theme)

        # 创建输入窗口
        input_y = chat_height + self._border_width
        input_win = curses.newwin(self._input_height, max_x, input_y, 0)
        input_win.keypad(True)
        self.input_handler = InputHandler(input_win)

        # 创建状态栏窗口
        status_y = max_y - self._status_height
        status_win = curses.newwin(self._status_height, max_x, status_y, 0)
        self.status_bar = StatusBar(status_win, self._status_height, self.theme)

    def _init_agent(self):
        """初始化Agent（如果尚未创建）"""
        if not self._agent:
            self._agent = NexusAgent(config=self._config)

        # 更新状态栏
        provider_config = self._config.provider_config
        self.status_bar.update(
            provider=self._config.provider,
            model=provider_config.get("model", "unknown"),
            max_iterations=self._agent.max_iterations,
        )

    def _process_input(self, user_input: str):
        """处理用户输入，调用Agent

        Args:
            user_input: 用户输入
        """
        self._processing = True
        self._update_status("Thinking")

        # 显示用户消息
        self.chat_view.add_message("user", user_input)
        self._refresh()

        # 添加Agent回复消息占位
        self.chat_view.add_message("assistant", "")
        self._refresh()

        try:
            # 使用流式输出
            full_response = ""
            for event_type, content in self._agent.chat_stream(user_input):
                if event_type == "text":
                    full_response += content
                    self.chat_view.update_last_message(full_response)
                    self._update_status("Responding")
                    self._refresh()

                elif event_type == "tool_call":
                    self.chat_view.add_message("tool_call", content)
                    self._update_status("Working")
                    self._refresh()

                elif event_type == "observation":
                    self.chat_view.add_message("tool_result", content[:500])
                    self._update_status("Thinking")
                    self._refresh()

                elif event_type == "thinking":
                    self.chat_view.add_message("thinking", content)
                    self._refresh()

                elif event_type == "error":
                    self.chat_view.add_message("error", content)
                    self._refresh()

                elif event_type == "done":
                    break

            # 如果没有流式输出，使用普通chat
            if not full_response:
                response = self._agent.chat(user_input)
                self.chat_view.update_last_message(response)

        except Exception as e:
            self.chat_view.add_message("error", f"Error: {e}")

        finally:
            self._processing = False
            self.chat_view.scroll_to_bottom()

        # 更新上下文使用情况
        ctx_info = self._agent.context.get_context_info()
        self.status_bar.update(
            context_usage=ctx_info.get("total_tokens", 0),
            context_max=ctx_info.get("max_tokens", 8000),
            iteration=self._agent._iteration_count,
        )

        self._update_status("Ready")
        self._refresh()

    def _refresh(self):
        """刷新所有UI组件"""
        try:
            self.chat_view.draw()
            self.status_bar.draw()
            self.input_handler._draw_input()
            curses.doupdate()
        except curses.error:
            pass

    def _update_status(self, status: str):
        """更新状态栏"""
        if self.status_bar:
            self.status_bar.set_status(status)
            self.status_bar.draw()

    def _show_welcome(self):
        """显示欢迎信息"""
        welcome = [
            "",
            "  NexusAgent v0.1.0",
            "  Multi-LLM Terminal AI Coding Agent",
            "",
            f"  Provider: {self._config.provider} / {self._config.provider_config.get('model', 'N/A')}",
            f"  Tools: {', '.join(self._agent.tool_registry.get_tool_names())}",
            "",
            "  Type /help for commands, or just start chatting.",
            "",
        ]
        for line in welcome:
            self.chat_view.add_message("info", line)
        self._refresh()

    def _handle_resize(self):
        """处理窗口大小变化"""
        if not self.stdscr:
            return

        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()

        # 重新计算布局
        chat_height = max_y - self._input_height - self._status_height - self._border_width * 2

        # 重新创建窗口
        self.chat_view.window.resize(chat_height, max_x)
        self.chat_view.window.mvwin(0, 0)

        input_y = chat_height + self._border_width
        self.input_handler.window.resize(self._input_height, max_x)
        self.input_handler.window.mvwin(input_y, 0)

        status_y = max_y - self._status_height
        self.status_bar.window.resize(self._status_height, max_x)
        self.status_bar.window.mvwin(status_y, 0)

        self.chat_view.resize()
        self._refresh()

    # ---- 命令处理 ----

    def _cmd_quit(self, args: str):
        """退出命令"""
        self._running = False

    def _cmd_clear(self, args: str):
        """清屏命令"""
        self.chat_view.clear()
        self._refresh()

    def _cmd_help(self, args: str):
        """帮助命令"""
        help_text = """Available commands:
  /help          - Show this help message
  /quit, /exit   - Exit NexusAgent
  /clear, /cls   - Clear the chat view
  /status        - Show current status
  /reset         - Reset conversation context
  /save          - Save current session
  /theme <name>  - Switch theme (dark/light/mono)
  /provider      - Show current provider info
  /tools         - List available tools
  /history       - Show conversation history count

Keyboard shortcuts:
  Up/Down        - Navigate input history
  PgUp/PgDn      - Scroll chat view
  Home/End       - Jump to top/bottom of chat
  Escape         - Clear current input"""
        self.chat_view.add_message("info", help_text)
        self._refresh()

    def _cmd_status(self, args: str):
        """状态命令"""
        if not self._agent:
            return
        status = self._agent.get_status()
        status_text = (
            f"Provider: {status['provider']}\n"
            f"Model: {status['model']}\n"
            f"Tools: {', '.join(status['tools'])}\n"
            f"Session: {status['session_id']}\n"
            f"Context: {status['context']}"
        )
        self.chat_view.add_message("info", status_text)
        self._refresh()

    def _cmd_reset(self, args: str):
        """重置命令"""
        if self._agent:
            self._agent.reset()
        self.chat_view.add_message("info", "Conversation context reset.")
        self._refresh()

    def _cmd_save(self, args: str):
        """保存命令"""
        if self._agent:
            self._agent.session.save()
            self.chat_view.add_message(
                "info",
                f"Session saved: {self._agent.session.session_id}",
            )
        self._refresh()

    def _cmd_theme(self, args: str):
        """切换主题"""
        parts = args.strip().split()
        if len(parts) > 1:
            theme_name = parts[1].lower()
            if theme_name in Theme.available_themes():
                self._theme_name = theme_name
                self.theme = Theme(theme_name)
                self.theme.initialize(self.stdscr)
                self.chat_view.theme = self.theme
                self.status_bar.theme = self.theme
                self.chat_view.add_message("info", f"Theme changed to: {theme_name}")
            else:
                available = ", ".join(Theme.available_themes())
                self.chat_view.add_message("info", f"Available themes: {available}")
        else:
            available = ", ".join(Theme.available_themes())
            self.chat_view.add_message("info", f"Current theme: {self._theme_name}\nAvailable: {available}")
        self._refresh()

    def _cmd_provider(self, args: str):
        """Provider信息"""
        if self._agent:
            info = (
                f"Current Provider: {self._config.provider}\n"
                f"Model: {self._config.provider_config.get('model', 'N/A')}\n"
                f"Base URL: {self._config.provider_config.get('base_url', 'N/A')}\n"
                f"Available: openai, anthropic, deepseek, gemini, ollama"
            )
            self.chat_view.add_message("info", info)
        self._refresh()

    def _cmd_tools(self, args: str):
        """列出工具"""
        if self._agent:
            tools = self._agent.tool_registry.list_tools()
            tool_list = "Available tools:\n"
            for tool in tools:
                tool_list += f"  - {tool.name}: {tool.description[:60]}\n"
            self.chat_view.add_message("info", tool_list.strip())
        self._refresh()

    def _cmd_history(self, args: str):
        """显示历史"""
        if self._agent:
            count = len(self._agent.context.messages)
            self.chat_view.add_message("info", f"Messages in context: {count}")
        self._refresh()

    def _cleanup(self):
        """清理资源"""
        if self._agent and self._config.get("session.auto_save", True):
            try:
                self._agent.session.save()
            except Exception:
                pass
