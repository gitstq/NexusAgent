"""
Shell命令执行工具

提供安全的Shell命令执行功能，集成沙箱环境。
"""

from typing import Optional

from nexusagent.tools.registry import ToolRegistry, ToolResult
from nexusagent.sandbox import Sandbox


def register_shell_tools(registry: ToolRegistry, sandbox: Sandbox = None):
    """注册Shell执行工具到注册中心

    Args:
        registry: 工具注册中心
        sandbox: 沙箱实例（为None则创建默认实例）
    """
    _sandbox = sandbox or Sandbox()

    # ---- run_command ----
    def _run_command(
        command: str,
        timeout: int = 30,
        working_directory: str = "",
    ) -> ToolResult:
        """在沙箱中执行Shell命令"""
        try:
            cwd = working_directory or _sandbox.working_directory
            result = _sandbox.execute(command, timeout=timeout, cwd=cwd)

            output_parts = []
            if result["stdout"]:
                output_parts.append(result["stdout"])
            if result["stderr"]:
                output_parts.append(f"[stderr]\n{result['stderr']}")

            output = "\n".join(output_parts) if output_parts else "(no output)"

            # 添加执行信息
            info = f"\n[Exit code: {result['exit_code']}, Duration: {result['duration']}s"
            if result["timed_out"]:
                info += " (TIMED OUT)"
            info += "]"

            return ToolResult(
                output=output + info,
                success=(result["exit_code"] == 0),
                error=result["stderr"] if result["exit_code"] != 0 else "",
                metadata={
                    "exit_code": result["exit_code"],
                    "duration": result["duration"],
                    "timed_out": result["timed_out"],
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Command execution failed: {e}")

    registry.register_function(
        name="run_command",
        description=(
            "Execute a shell command in a sandboxed environment. "
            "The command has a timeout and dangerous commands are blocked. "
            "Returns stdout, stderr, exit code, and execution duration."
        ),
        function=_run_command,
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30, max: 300)",
                    "default": 30,
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for the command",
                },
            },
            "required": ["command"],
        },
        category="shell",
    )

    # ---- run_python ----
    def _run_python(code: str, timeout: int = 30) -> ToolResult:
        """执行Python代码"""
        try:
            result = _sandbox.execute_with_tempfile(
                code=code,
                interpreter="python3",
                suffix=".py",
                timeout=timeout,
            )

            output_parts = []
            if result["stdout"]:
                output_parts.append(result["stdout"])
            if result["stderr"]:
                output_parts.append(f"[stderr]\n{result['stderr']}")

            output = "\n".join(output_parts) if output_parts else "(no output)"

            info = f"\n[Exit code: {result['exit_code']}, Duration: {result['duration']}s"
            if result["timed_out"]:
                info += " (TIMED OUT)"
            info += "]"

            return ToolResult(
                output=output + info,
                success=(result["exit_code"] == 0),
                error=result["stderr"] if result["exit_code"] != 0 else "",
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Python execution failed: {e}")

    registry.register_function(
        name="run_python",
        description=(
            "Execute Python code in a temporary file. "
            "Useful for running scripts, calculations, or data processing. "
            "The code runs in a sandboxed environment with timeout."
        ),
        function=_run_python,
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30)",
                    "default": 30,
                },
            },
            "required": ["code"],
        },
        category="shell",
    )
