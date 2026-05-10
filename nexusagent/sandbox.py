"""
沙箱执行环境模块

提供安全的Shell命令执行环境，包含超时控制、危险命令拦截和资源限制。
"""

import os
import re
import subprocess
import signal
import tempfile
import shlex
from typing import Optional, Tuple, Dict, Any


class SandboxError(Exception):
    """沙箱执行错误"""
    pass


class CommandBlockedError(SandboxError):
    """命令被安全策略拦截"""
    pass


class CommandTimeoutError(SandboxError):
    """命令执行超时"""
    pass


class Sandbox:
    """沙箱执行环境

    提供安全的命令执行环境，包含以下安全措施：
    - 危险命令黑名单拦截
    - 执行超时控制
    - 工作目录限制
    - 输出大小限制

    Attributes:
        timeout: 默认超时时间（秒）
        working_directory: 工作目录
        blocked_patterns: 被拦截的命令模式列表
        max_output_size: 最大输出字节数
    """

    # 默认危险命令模式
    DEFAULT_BLOCKED_PATTERNS = [
        r"rm\s+(-[rfRF]+\s+)?/\s*$",           # rm -rf /
        r"rm\s+(-[rfRF]+\s+)?\*",               # rm -rf *
        r"mkfs\b",                                # 格式化文件系统
        r"dd\s+if=",                              # dd直接写磁盘
        r">\s*/dev/sd",                           # 直接写块设备
        r"chmod\s+(-R\s+)?777\s+/",              # chmod 777 /
        r"chown\s+(-R\s+)?",                      # chown -R
        r":\(\)\s*\{.*\}",                        # Fork炸弹
        r"shutdown\b",                            # 关机
        r"reboot\b",                              # 重启
        r"init\s+[06]",                           # 切换运行级别
        r"halt\b",                                # 停机
        r"poweroff\b",                            # 关机
        r"\|\s*sh\s*$",                           # 管道到sh
        r"\|\s*bash\s*$",                         # 管道到bash
        r"curl.*\|\s*(ba)?sh",                    # curl | bash
        r"wget.*\|\s*(ba)?sh",                    # wget | bash
        r"nc\s+-[el]",                            # netcat监听
        r"python\s+-m\s+http\.server",            # Python HTTP服务器（可选）
        r"nohup\b",                               # 后台运行
        r"\&\s*$",                                # 后台执行 &
        r"mv\s+/\s+",                             # 移动根目录
        r"cp\s+/\s+",                             # 拷贝根目录
    ]

    def __init__(
        self,
        timeout: int = 30,
        working_directory: str = "",
        blocked_commands: list = None,
        max_output_size: int = 1024 * 1024,  # 1MB
        enabled: bool = True,
    ):
        """初始化沙箱

        Args:
            timeout: 默认超时时间（秒）
            working_directory: 工作目录，为空则使用当前目录
            blocked_commands: 额外的被拦截命令模式
            max_output_size: 最大输出字节数
            enabled: 是否启用安全检查
        """
        self.timeout = timeout
        self.working_directory = working_directory or os.getcwd()
        self.max_output_size = max_output_size
        self.enabled = enabled

        # 编译危险命令模式
        self.blocked_patterns = []
        for pattern in (blocked_commands or []):
            try:
                self.blocked_patterns.append(re.compile(pattern))
            except re.error:
                pass

        # 添加默认模式
        for pattern in self.DEFAULT_BLOCKED_PATTERNS:
            try:
                self.blocked_patterns.append(re.compile(pattern))
            except re.error:
                pass

    def check_command(self, command: str) -> Optional[str]:
        """检查命令是否安全

        Args:
            command: 要检查的命令字符串

        Returns:
            如果命令不安全，返回原因字符串；安全则返回None
        """
        if not self.enabled:
            return None

        # 检查空命令
        if not command or not command.strip():
            return "Empty command"

        # 检查危险模式
        for pattern in self.blocked_patterns:
            if pattern.search(command):
                return f"Command matches blocked pattern: {pattern.pattern}"

        # 检查多命令连接中的危险命令
        # 处理 ; && || 等连接符
        parts = re.split(r'[;&|]', command)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            for pattern in self.blocked_patterns:
                if pattern.search(part):
                    return f"Command contains blocked sub-command: {pattern.pattern}"

        return None

    def execute(
        self,
        command: str,
        timeout: int = None,
        cwd: str = None,
        env: Dict[str, str] = None,
        input_data: str = None,
    ) -> Dict[str, Any]:
        """在沙箱中执行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间，为None则使用默认值
            cwd: 工作目录，为None则使用默认值
            env: 环境变量
            input_data: 标准输入数据

        Returns:
            执行结果字典:
            - exit_code: 退出码
            - stdout: 标准输出
            - stderr: 标准错误
            - duration: 执行时长（秒）
            - timed_out: 是否超时

        Raises:
            CommandBlockedError: 命令被拦截
            CommandTimeoutError: 命令超时
            SandboxError: 其他执行错误
        """
        import time
        start_time = time.time()

        # 安全检查
        block_reason = self.check_command(command)
        if block_reason:
            raise CommandBlockedError(f"Command blocked: {block_reason}")

        # 设置执行参数
        exec_timeout = timeout if timeout is not None else self.timeout
        exec_cwd = cwd or self.working_directory

        # 确保工作目录存在
        if not os.path.isdir(exec_cwd):
            try:
                os.makedirs(exec_cwd, exist_ok=True)
            except OSError:
                exec_cwd = os.getcwd()

        # 准备环境变量
        exec_env = None
        if env:
            exec_env = os.environ.copy()
            exec_env.update(env)

        # 准备输入
        stdin_data = input_data.encode("utf-8") if input_data else None

        result = {
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "duration": 0,
            "timed_out": False,
        }

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if stdin_data else subprocess.DEVNULL,
                cwd=exec_cwd,
                env=exec_env,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            try:
                stdout, stderr = proc.communicate(
                    input=stdin_data,
                    timeout=exec_timeout,
                )
                result["exit_code"] = proc.returncode
                result["stdout"] = stdout.decode("utf-8", errors="replace")[:self.max_output_size]
                result["stderr"] = stderr.decode("utf-8", errors="replace")[:self.max_output_size]
            except subprocess.TimeoutExpired:
                # 超时，终止进程组
                result["timed_out"] = True
                try:
                    if os.name != "nt":
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                    proc.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    proc.kill()
                    proc.wait()
                result["stderr"] = f"Command timed out after {exec_timeout} seconds"
                result["exit_code"] = -1

        except OSError as e:
            result["stderr"] = f"Execution error: {e}"
            result["exit_code"] = -1
        except Exception as e:
            result["stderr"] = f"Unexpected error: {e}"
            result["exit_code"] = -1

        result["duration"] = round(time.time() - start_time, 3)
        return result

    def execute_with_tempfile(
        self,
        code: str,
        interpreter: str = "python3",
        suffix: str = ".py",
        timeout: int = None,
    ) -> Dict[str, Any]:
        """通过临时文件执行代码

        Args:
            code: 代码内容
            interpreter: 解释器路径
            suffix: 临时文件后缀
            timeout: 超时时间

        Returns:
            执行结果字典
        """
        tmp_file = None
        try:
            # 创建临时文件
            fd, tmp_file = tempfile.mkstemp(suffix=suffix, dir=self.working_directory)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)

            # 执行
            command = f"{interpreter} {shlex.quote(tmp_file)}"
            return self.execute(command, timeout=timeout)

        finally:
            # 清理临时文件
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass

    def is_available(self) -> bool:
        """检查沙箱环境是否可用

        Returns:
            沙箱是否可用
        """
        try:
            result = self.execute("echo ok", timeout=5)
            return result["exit_code"] == 0
        except SandboxError:
            return False
