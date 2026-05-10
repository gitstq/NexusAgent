"""
NexusAgent核心引擎

实现ReAct（Reasoning + Acting）循环，是整个系统的核心调度器。
"""

import json
import time
from typing import List, Dict, Optional, Callable, Any

from nexusagent.config import Config
from nexusagent.context import ContextManager
from nexusagent.session import Session
from nexusagent.sandbox import Sandbox
from nexusagent.tools.registry import ToolRegistry, ToolResult
from nexusagent.providers import get_provider
from nexusagent.providers.base import ProviderResponse
from nexusagent.utils import Timer, generate_id, truncate_text, count_tokens_approx


# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """You are NexusAgent, an expert AI coding assistant running in a terminal environment.

You have access to a set of tools to help users with programming tasks. Follow these guidelines:

## Capabilities
- Read, write, and edit files
- Execute shell commands in a sandboxed environment
- Perform Git operations
- Search the web for information
- Analyze code structure

## Workflow
When given a task, follow this approach:
1. **Understand**: Analyze the user's request carefully
2. **Plan**: Think about the approach before taking action
3. **Execute**: Use tools step by step to accomplish the task
4. **Verify**: Check that your changes are correct
5. **Report**: Summarize what you did

## Rules
- Always read files before editing them
- Be precise with file paths
- Explain what you're doing as you work
- If something goes wrong, analyze the error and try to fix it
- When writing code, follow best practices and existing code style
- Keep changes minimal and focused
- Use shell commands only when necessary
- Respect the user's existing code and project structure

## Tool Usage
- Use the most specific tool for each task
- Provide clear parameters to tools
- Check tool results before proceeding
- If a tool fails, try alternative approaches
"""


class AgentStep:
    """Agent执行步骤

    记录Agent在ReAct循环中的每一步。

    Attributes:
        step_id: 步骤ID
        step_type: 步骤类型 (thinking/action/observation/answer)
        content: 步骤内容
        tool_name: 工具名称（action类型）
        tool_args: 工具参数（action类型）
        result: 执行结果
        duration: 执行时长
        timestamp: 时间戳
    """

    def __init__(self, step_type: str, content: str = "", **kwargs):
        self.step_id = generate_id("step_")
        self.step_type = step_type
        self.content = content
        self.tool_name = kwargs.get("tool_name", "")
        self.tool_args = kwargs.get("tool_args", {})
        self.result = kwargs.get("result", "")
        self.duration = kwargs.get("duration", 0)
        self.timestamp = time.time()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "result": str(self.result)[:1000] if self.result else "",
            "duration": self.duration,
            "timestamp": self.timestamp,
        }


class NexusAgent:
    """NexusAgent核心引擎

    实现ReAct循环，协调LLM推理和工具调用。

    ReAct循环流程:
    1. 接收用户输入
    2. 将上下文发送给LLM
    3. LLM返回思考/工具调用/回答
    4. 如果是工具调用，执行工具并将结果加入上下文
    5. 重复2-4直到LLM给出最终回答
    6. 返回最终回答

    Attributes:
        config: 配置管理器
        context: 上下文管理器
        session: 会话管理器
        sandbox: 沙箱环境
        tool_registry: 工具注册中心
        provider: LLM Provider
        max_iterations: 最大迭代次数
        verbose: 是否输出详细日志
    """

    def __init__(
        self,
        config: Config = None,
        session: Session = None,
        verbose: bool = False,
        on_step: Callable = None,
    ):
        """初始化Agent

        Args:
            config: 配置管理器
            session: 会话管理器
            verbose: 是否输出详细日志
            on_step: 步骤回调函数 on_step(step: AgentStep)
        """
        self.config = config or Config()
        self.verbose = verbose or self.config.get("agent.verbose", False)
        self.on_step = on_step

        # 初始化组件
        self.sandbox = Sandbox(
            timeout=self.config.get("sandbox.timeout", 30),
            working_directory=self.config.get("sandbox.working_directory", ""),
            blocked_commands=self.config.get("sandbox.blocked_commands", []),
            enabled=self.config.get("sandbox.enabled", True),
        )

        self.tool_registry = ToolRegistry()
        self._register_default_tools()

        # 初始化Provider
        provider_config = self.config.provider_config
        self.provider = get_provider(
            self.config.provider,
            **provider_config,
        )

        # 初始化上下文和会话
        self.session = session or Session(
            save_dir=self.config.get("session.save_dir", ""),
        )
        if not self.session.context.messages:
            self.context = self.session.context
        else:
            self.context = self.session.context

        # 设置上下文窗口
        max_tokens = self.config.get("session.context_window", 8000)
        self.context.max_tokens = max_tokens

        # 设置系统提示词
        system_prompt = self.config.get("agent.system_prompt", "")
        if not system_prompt:
            system_prompt = DEFAULT_SYSTEM_PROMPT
        self.context.set_system_prompt(system_prompt)

        # Agent参数
        self.max_iterations = self.config.get("agent.max_iterations", 20)

        # 执行历史
        self.steps: List[AgentStep] = []
        self._iteration_count = 0

    def _register_default_tools(self):
        """注册默认工具集"""
        tools_config = self.config.get("tools", {})

        if tools_config.get("file_ops", True):
            from nexusagent.tools.file_ops import register_file_tools
            register_file_tools(self.tool_registry)

        if tools_config.get("shell", True):
            from nexusagent.tools.shell import register_shell_tools
            register_shell_tools(self.tool_registry, self.sandbox)

        if tools_config.get("git_ops", True):
            from nexusagent.tools.git_ops import register_git_tools
            register_git_tools(self.tool_registry, self.sandbox)

        if tools_config.get("web_search", True):
            from nexusagent.tools.web_search import register_web_search_tools
            register_web_search_tools(self.tool_registry)

        if tools_config.get("code_analysis", True):
            from nexusagent.tools.code_analysis import register_code_analysis_tools
            register_code_analysis_tools(self.tool_registry, self.sandbox)

    def chat(self, user_message: str) -> str:
        """处理用户消息并返回回复

        这是Agent的主入口方法，执行完整的ReAct循环。

        Args:
            user_message: 用户输入的消息

        Returns:
            Agent的最终回复
        """
        # 重置迭代计数
        self._iteration_count = 0
        self.steps = []

        # 添加用户消息到上下文
        self.context.add_message("user", user_message)

        # 记录步骤
        self._emit_step("thinking", f"Processing user request...")

        # ReAct循环
        while self._iteration_count < self.max_iterations:
            self._iteration_count += 1

            if self.verbose:
                self._emit_step("thinking", f"Iteration {self._iteration_count}/{self.max_iterations}")

            # 调用LLM
            messages = self.context.get_messages()
            tools_schema = self.tool_registry.get_tool_schemas()

            try:
                response = self.provider.chat(messages, tools=tools_schema)
            except ConnectionError as e:
                error_msg = f"LLM connection error: {e}"
                self._emit_step("thinking", error_msg)
                return f"Sorry, I encountered an error: {error_msg}\n\nPlease check your API configuration."

            # 记录LLM响应
            if self.verbose:
                self._emit_step("thinking", f"LLM response: {response.finish_reason}")

            # 处理工具调用
            if response.has_tool_calls:
                # 添加assistant消息（包含工具调用）
                assistant_msg = {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                }
                self.context.add_message("assistant", response.content, tool_calls=response.tool_calls)

                # 执行每个工具调用
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args_str = tool_call.get("arguments", "{}")

                    # 解析参数
                    try:
                        if isinstance(tool_args_str, str):
                            tool_args = json.loads(tool_args_str)
                        else:
                            tool_args = tool_args_str
                    except json.JSONDecodeError:
                        tool_args = {}

                    self._emit_step("action", f"Calling {tool_name}...", tool_name=tool_name, tool_args=tool_args)

                    # 执行工具
                    with Timer() as t:
                        result = self.tool_registry.execute(tool_name, **tool_args)

                    # 记录结果
                    self._emit_step(
                        "observation",
                        str(result),
                        tool_name=tool_name,
                        result=str(result),
                        duration=t.duration,
                    )

                    # 将工具结果添加到上下文
                    self.context.add_tool_result(
                        tool_name=tool_name,
                        result=str(result),
                        tool_call_id=tool_call.get("id", ""),
                    )

                # 继续循环
                continue

            # 没有工具调用，检查是否有最终回答
            if response.content:
                # 添加assistant回复
                self.context.add_message("assistant", response.content)
                self._emit_step("answer", response.content)

                # 自动保存会话
                if self.config.get("session.auto_save", True):
                    self.session.touch()
                    self.session.save()

                return response.content

            # 空响应
            if response.finish_reason == "length":
                self._emit_step("thinking", "Response truncated due to length limit")
                self.context.add_message("assistant", "[Response truncated]")
                return "My response was truncated. Please ask me to continue."

            # 未知情况，退出循环
            break

        # 达到最大迭代次数
        self._emit_step("thinking", f"Reached maximum iterations ({self.max_iterations})")
        return (
            "I've reached the maximum number of iterations. "
            "The task may be too complex or there might be an issue. "
            "Please try breaking it into smaller steps."
        )

    def chat_stream(self, user_message: str):
        """流式处理用户消息

        Args:
            user_message: 用户输入的消息

        Yields:
            (event_type, content) 元组
            event_type: "thinking" | "action" | "observation" | "text" | "tool_call" | "done"
        """
        self._iteration_count = 0
        self.steps = []
        self.context.add_message("user", user_message)

        while self._iteration_count < self.max_iterations:
            self._iteration_count += 1
            messages = self.context.get_messages()
            tools_schema = self.tool_registry.get_tool_schemas()

            try:
                # 尝试流式输出
                full_response = ""
                tool_calls_data = []

                yield ("thinking", f"Iteration {self._iteration_count}...")

                try:
                    for chunk in self.provider.chat_stream(messages, tools=tools_schema):
                        full_response += chunk
                        yield ("text", chunk)
                except NotImplementedError:
                    # Provider不支持流式，回退到普通调用
                    response = self.provider.chat(messages, tools=tools_schema)
                    full_response = response.content
                    if full_response:
                        yield ("text", full_response)
                    if response.has_tool_calls:
                        tool_calls_data = response.tool_calls

                # 如果没有工具调用，直接返回
                if not tool_calls_data and full_response:
                    self.context.add_message("assistant", full_response)
                    if self.config.get("session.auto_save", True):
                        self.session.save()
                    yield ("done", "")
                    return

                # 如果有工具调用（流式模式下需要解析）
                # 在流式模式下，工具调用通常在完整响应中
                # 这里我们使用非流式API来获取工具调用
                if not tool_calls_data:
                    response = self.provider.chat(messages, tools=tools_schema)
                    if response.has_tool_calls:
                        tool_calls_data = response.tool_calls
                        full_response = response.content

                if tool_calls_data:
                    self.context.add_message(
                        "assistant", full_response,
                        tool_calls=tool_calls_data,
                    )

                    for tool_call in tool_calls_data:
                        tool_name = tool_call.get("name", "")
                        tool_args_str = tool_call.get("arguments", "{}")
                        try:
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                        except json.JSONDecodeError:
                            tool_args = {}

                        yield ("tool_call", f"Calling {tool_name}...")

                        with Timer() as t:
                            result = self.tool_registry.execute(tool_name, **tool_args)

                        yield ("observation", str(result))

                        self.context.add_tool_result(
                            tool_name=tool_name,
                            result=str(result),
                            tool_call_id=tool_call.get("id", ""),
                        )

                    continue

                yield ("done", "")
                return

            except ConnectionError as e:
                yield ("error", f"Connection error: {e}")
                return

        yield ("error", "Maximum iterations reached")

    def _emit_step(self, step_type: str, content: str, **kwargs):
        """发射步骤事件

        Args:
            step_type: 步骤类型
            content: 步骤内容
            **kwargs: 额外参数
        """
        step = AgentStep(step_type, content, **kwargs)
        self.steps.append(step)

        if self.on_step:
            try:
                self.on_step(step)
            except Exception:
                pass

        if self.verbose:
            prefix = {
                "thinking": "[Think]",
                "action": "[Action]",
                "observation": "[Observe]",
                "answer": "[Answer]",
            }.get(step_type, "[Info]")
            print(f"  {prefix} {content[:200]}")

    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态

        Returns:
            状态信息字典
        """
        return {
            "provider": self.config.provider,
            "model": self.config.provider_config.get("model", ""),
            "tools": self.tool_registry.get_tool_names(),
            "context": self.context.get_context_info(),
            "session_id": self.session.session_id,
            "iteration": self._iteration_count,
            "max_iterations": self.max_iterations,
        }

    def reset(self):
        """重置Agent状态"""
        self.context.clear_history()
        self.steps.clear()
        self._iteration_count = 0

    def switch_provider(self, provider_name: str, **config):
        """切换LLM Provider

        Args:
            provider_name: Provider名称
            **config: Provider配置
        """
        self.provider = get_provider(provider_name, **config)
        self.config.set("provider", provider_name)
