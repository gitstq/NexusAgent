"""
Git操作工具

提供Git版本控制相关操作功能。
"""

import os
import re
import json
from typing import Optional

from nexusagent.tools.registry import ToolRegistry, ToolResult
from nexusagent.sandbox import Sandbox


def register_git_tools(registry: ToolRegistry, sandbox: Sandbox = None):
    """注册Git操作工具到注册中心

    Args:
        registry: 工具注册中心
        sandbox: 沙箱实例
    """
    _sandbox = sandbox or Sandbox()

    def _git_status(directory: str = ".") -> ToolResult:
        """查看Git仓库状态"""
        result = _sandbox.execute("git status --porcelain=v1", cwd=directory)
        if result["exit_code"] != 0:
            return ToolResult(success=False, error=f"Not a git repository: {result['stderr']}")

        output = result["stdout"].strip()
        if not output:
            return ToolResult(output="Working tree clean. No changes.", success=True)

        # 解析状态
        staged = []
        modified = []
        untracked = []
        deleted = []
        renamed = []

        for line in output.split("\n"):
            if not line.strip():
                continue
            status = line[:2]
            filepath = line[3:].strip()

            if status.startswith("R"):
                renamed.append(filepath)
            elif status[0] in ("A", "M", "D"):
                staged.append(f"[{status[0]}] {filepath}")
            elif status[1] in ("M", "D"):
                modified.append(f"[{status[1]}] {filepath}")
            elif status == "??":
                untracked.append(filepath)

        parts = []
        if staged:
            parts.append("Staged changes:\n" + "\n".join(staged))
        if modified:
            parts.append("Modified (not staged):\n" + "\n".join(modified))
        if untracked:
            parts.append("Untracked files:\n" + "\n".join(untracked))
        if renamed:
            parts.append("Renamed:\n" + "\n".join(renamed))

        return ToolResult(output="\n\n".join(parts), success=True)

    registry.register_function(
        name="git_status",
        description="Show the working tree status of a Git repository.",
        function=_git_status,
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the git repository (default: current directory)",
                },
            },
        },
        category="git_ops",
    )

    def _git_diff(directory: str = ".", file_path: str = "", staged: bool = False) -> ToolResult:
        """查看Git差异"""
        cmd = "git diff"
        if staged:
            cmd += " --staged"
        if file_path:
            cmd += f" -- {file_path}"

        result = _sandbox.execute(cmd, cwd=directory, timeout=30)
        if result["exit_code"] != 0:
            return ToolResult(success=False, error=result["stderr"])

        output = result["stdout"].strip()
        if not output:
            return ToolResult(output="No differences found.", success=True)

        # 限制输出大小
        lines = output.split("\n")
        if len(lines) > 2000:
            output = "\n".join(lines[:2000])
            output += f"\n\n... (truncated, showing 2000 of {len(lines)} lines)"

        return ToolResult(output=output, success=True)

    registry.register_function(
        name="git_diff",
        description="Show changes between commits, commit and working tree, etc.",
        function=_git_diff,
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the git repository",
                },
                "file_path": {
                    "type": "string",
                    "description": "Specific file to diff",
                },
                "staged": {
                    "type": "boolean",
                    "description": "Show staged changes (default: false)",
                    "default": False,
                },
            },
        },
        category="git_ops",
    )

    def _git_log(directory: str = ".", count: int = 10) -> ToolResult:
        """查看Git提交历史"""
        cmd = (
            f"git log --oneline --decorate -n {count} "
            f"--format='%h %s (%an, %ar)'"
        )
        result = _sandbox.execute(cmd, cwd=directory)
        if result["exit_code"] != 0:
            return ToolResult(success=False, error=result["stderr"])

        output = result["stdout"].strip()
        if not output:
            return ToolResult(output="No commits found.", success=True)

        return ToolResult(output=f"Recent commits:\n{output}", success=True)

    registry.register_function(
        name="git_log",
        description="Show commit logs.",
        function=_git_log,
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the git repository",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of commits to show (default: 10)",
                    "default": 10,
                },
            },
        },
        category="git_ops",
    )

    def _git_add(directory: str = ".", file_path: str = ".") -> ToolResult:
        """添加文件到Git暂存区"""
        cmd = f"git add {file_path}"
        result = _sandbox.execute(cmd, cwd=directory)
        if result["exit_code"] != 0:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(output=f"Added '{file_path}' to staging area.", success=True)

    registry.register_function(
        name="git_add",
        description="Add file contents to the staging area.",
        function=_git_add,
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the git repository",
                },
                "file_path": {
                    "type": "string",
                    "description": "File or pattern to add (use '.' for all)",
                    "default": ".",
                },
            },
        },
        category="git_ops",
    )

    def _git_commit(directory: str = ".", message: str = "", files: str = "") -> ToolResult:
        """提交Git更改"""
        if not message:
            return ToolResult(success=False, error="Commit message is required")

        # 如果指定了文件，先add
        if files:
            add_result = _sandbox.execute(f"git add {files}", cwd=directory)
            if add_result["exit_code"] != 0:
                return ToolResult(success=False, error=f"Failed to stage files: {add_result['stderr']}")

        cmd = f"git commit -m {repr(message)}"
        result = _sandbox.execute(cmd, cwd=directory)
        if result["exit_code"] != 0:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(output=result["stdout"].strip(), success=True)

    registry.register_function(
        name="git_commit",
        description="Record changes to the repository.",
        function=_git_commit,
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the git repository",
                },
                "message": {
                    "type": "string",
                    "description": "Commit message",
                },
                "files": {
                    "type": "string",
                    "description": "Files to commit (optional, stages specified files first)",
                },
            },
            "required": ["message"],
        },
        category="git_ops",
    )

    def _git_branch(directory: str = "", create: str = "", delete: str = "", list_all: bool = False) -> ToolResult:
        """管理Git分支"""
        if create:
            cmd = f"git checkout -b {create}"
        elif delete:
            cmd = f"git branch -d {delete}"
        elif list_all:
            cmd = "git branch -a"
        else:
            cmd = "git branch"

        result = _sandbox.execute(cmd, cwd=directory or ".")
        if result["exit_code"] != 0:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(output=result["stdout"].strip(), success=True)

    registry.register_function(
        name="git_branch",
        description="List, create, or delete branches.",
        function=_git_branch,
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the git repository",
                },
                "create": {
                    "type": "string",
                    "description": "Create and switch to a new branch with this name",
                },
                "delete": {
                    "type": "string",
                    "description": "Delete a branch with this name",
                },
                "list_all": {
                    "type": "boolean",
                    "description": "List all branches including remotes",
                    "default": False,
                },
            },
        },
        category="git_ops",
    )

    def _git_show(directory: str = ".", ref: str = "HEAD") -> ToolResult:
        """查看Git对象内容"""
        cmd = f"git show --stat {ref}"
        result = _sandbox.execute(cmd, cwd=directory, timeout=30)
        if result["exit_code"] != 0:
            return ToolResult(success=False, error=result["stderr"])

        output = result["stdout"]
        lines = output.split("\n")
        if len(lines) > 500:
            output = "\n".join(lines[:500])
            output += f"\n\n... (truncated, showing 500 of {len(lines)} lines)"

        return ToolResult(output=output, success=True)

    registry.register_function(
        name="git_show",
        description="Show various types of Git objects (commits, tags, etc.).",
        function=_git_show,
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to the git repository",
                },
                "ref": {
                    "type": "string",
                    "description": "Git reference (commit hash, branch, tag, etc.)",
                    "default": "HEAD",
                },
            },
        },
        category="git_ops",
    )
