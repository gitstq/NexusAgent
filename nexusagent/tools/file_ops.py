"""
文件操作工具

提供文件读取、写入、编辑、搜索和目录列表等功能。
"""

import os
import re
import difflib
from typing import Optional

from nexusagent.tools.registry import ToolRegistry, ToolResult


def register_file_tools(registry: ToolRegistry):
    """注册所有文件操作工具到注册中心

    Args:
        registry: 工具注册中心
    """

    # ---- read_file ----
    registry.register_function(
        name="read_file",
        description=(
            "Read the contents of a file. "
            "Returns the file content as text. "
            "Supports specifying line range with offset and limit parameters."
        ),
        function=_read_file,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-based, default: 1)",
                    "default": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default: 2000)",
                    "default": 2000,
                },
            },
            "required": ["path"],
        },
        category="file_ops",
    )

    # ---- write_file ----
    registry.register_function(
        name="write_file",
        description=(
            "Write content to a file. Creates the file if it doesn't exist, "
            "overwrites if it does. Creates parent directories as needed."
        ),
        function=_write_file,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
        category="file_ops",
    )

    # ---- edit_file ----
    registry.register_function(
        name="edit_file",
        description=(
            "Edit a file by replacing a specific section. "
            "Search for the old_str section and replace it with new_str. "
            "Only the first match is replaced. Include enough context in old_str "
            "to uniquely identify the section to replace."
        ),
        function=_edit_file,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to edit",
                },
                "old_str": {
                    "type": "string",
                    "description": "The text to search for (must be unique in the file)",
                },
                "new_str": {
                    "type": "string",
                    "description": "The replacement text",
                },
            },
            "required": ["path", "old_str", "new_str"],
        },
        category="file_ops",
    )

    # ---- search_files ----
    registry.register_function(
        name="search_files",
        description=(
            "Search for a pattern in files within a directory. "
            "Uses regex pattern matching. Returns matching lines with file paths."
        ),
        function=_search_files,
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File glob pattern to filter files (e.g., '*.py')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 50)",
                    "default": 50,
                },
            },
            "required": ["pattern"],
        },
        category="file_ops",
    )

    # ---- list_directory ----
    registry.register_function(
        name="list_directory",
        description=(
            "List files and directories in a given path. "
            "Returns a tree-like listing of the directory contents."
        ),
        function=_list_directory,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively (default: false)",
                    "default": False,
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum recursion depth (default: 3)",
                    "default": 3,
                },
            },
            "required": ["path"],
        },
        category="file_ops",
    )

    # ---- create_directory ----
    registry.register_function(
        name="create_directory",
        description="Create a directory and any necessary parent directories.",
        function=_create_directory,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to create",
                },
            },
            "required": ["path"],
        },
        category="file_ops",
    )

    # ---- delete_file ----
    registry.register_function(
        name="delete_file",
        description="Delete a file or empty directory.",
        function=_delete_file,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory to delete",
                },
            },
            "required": ["path"],
        },
        category="file_ops",
    )

    # ---- file_info ----
    registry.register_function(
        name="file_info",
        description="Get information about a file or directory (size, type, permissions, etc.).",
        function=_file_info,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory",
                },
            },
            "required": ["path"],
        },
        category="file_ops",
    )


# ============================================================
# 工具实现函数
# ============================================================

def _read_file(path: str, offset: int = 1, limit: int = 2000) -> ToolResult:
    """读取文件内容"""
    try:
        if not os.path.isfile(path):
            return ToolResult(success=False, error=f"File not found: {path}")

        # 检查文件大小
        file_size = os.path.getsize(path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return ToolResult(
                success=False,
                error=f"File too large: {file_size} bytes (max 10MB)",
            )

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        start = max(0, offset - 1)
        end = min(start + limit, total_lines)
        selected_lines = lines[start:end]

        # 添加行号
        numbered = []
        for i, line in enumerate(selected_lines, start=start + 1):
            numbered.append(f"{i:>6}\t{line.rstrip()}")

        header = f"File: {path} (lines {start + 1}-{end} of {total_lines})\n"
        content = header + "\n".join(numbered)

        return ToolResult(output=content, success=True)

    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(success=False, error=f"Failed to read file: {e}")


def _write_file(path: str, content: str) -> ToolResult:
    """写入文件"""
    try:
        # 确保父目录存在
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        lines = content.count("\n") + 1
        size = len(content.encode("utf-8"))
        return ToolResult(
            output=f"Successfully wrote {lines} lines ({size} bytes) to {path}",
            success=True,
        )

    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(success=False, error=f"Failed to write file: {e}")


def _edit_file(path: str, old_str: str, new_str: str) -> ToolResult:
    """编辑文件（搜索替换）"""
    try:
        if not os.path.isfile(path):
            return ToolResult(success=False, error=f"File not found: {path}")

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # 搜索并替换
        count = content.count(old_str)
        if count == 0:
            # 尝试忽略空白差异
            old_normalized = re.sub(r'\s+', ' ', old_str).strip()
            content_normalized = re.sub(r'\s+', ' ', content)
            if old_normalized in content_normalized:
                return ToolResult(
                    success=False,
                    error=(
                        f"Exact match not found, but similar text exists. "
                        f"Please check whitespace differences."
                    ),
                )
            return ToolResult(
                success=False,
                error="Search string not found in file. Please provide the exact text to replace.",
            )

        if count > 1:
            return ToolResult(
                success=False,
                error=(
                    f"Found {count} matches. Please provide more context "
                    f"to uniquely identify the section to replace."
                ),
            )

        # 执行替换
        new_content = content.replace(old_str, new_str, 1)

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # 计算差异
        diff = difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
        diff_text = "".join(diff)

        return ToolResult(
            output=f"Successfully edited {path}\n\nDiff:\n{diff_text}",
            success=True,
        )

    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(success=False, error=f"Failed to edit file: {e}")


def _search_files(
    pattern: str,
    directory: str = ".",
    file_pattern: str = "*",
    max_results: int = 50,
) -> ToolResult:
    """在目录中搜索文件内容"""
    try:
        if not os.path.isdir(directory):
            return ToolResult(success=False, error=f"Directory not found: {directory}")

        # 编译正则表达式
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return ToolResult(success=False, error=f"Invalid regex pattern: {e}")

        # 文件扩展名过滤
        import fnmatch
        results = []
        searched = 0

        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in (
                    "__pycache__", "node_modules", ".git", "venv", ".venv",
                    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
                )
            ]

            for filename in files:
                if not fnmatch.fnmatch(filename, file_pattern):
                    continue

                filepath = os.path.join(root, filename)
                if not os.path.isfile(filepath):
                    continue

                # 跳过二进制文件
                if _is_binary(filepath):
                    continue

                searched += 1
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append(
                                    f"{filepath}:{line_num}: {line.rstrip()}"
                                )
                                if len(results) >= max_results:
                                    output = "\n".join(results)
                                    output += f"\n\n... (truncated, showing {max_results} of matching results)"
                                    return ToolResult(output=output, success=True)
                            if len(line) > 10000:
                                break  # 跳过超长行
                except (PermissionError, OSError):
                    continue

        if not results:
            return ToolResult(
                output=f"No matches found for '{pattern}' in {directory} "
                       f"(searched {searched} files)",
                success=True,
            )

        output = "\n".join(results)
        output += f"\n\nFound {len(results)} matches in {searched} files"
        return ToolResult(output=output, success=True)

    except Exception as e:
        return ToolResult(success=False, error=f"Search failed: {e}")


def _list_directory(
    path: str, recursive: bool = False, max_depth: int = 3
) -> ToolResult:
    """列出目录内容"""
    try:
        if not os.path.isdir(path):
            return ToolResult(success=False, error=f"Directory not found: {path}")

        lines = [f"Directory: {path}\n"]

        def _list_dir(current_path, prefix="", depth=0):
            if depth > max_depth:
                return
            try:
                entries = sorted(os.listdir(current_path))
            except PermissionError:
                lines.append(f"{prefix}[Permission Denied]\n")
                return

            for i, entry in enumerate(entries):
                if entry.startswith(".") and entry not in (".env",):
                    continue
                full_path = os.path.join(current_path, entry)
                is_last = (i == len(entries) - 1)
                connector = "`-- " if is_last else "|-- "

                if os.path.isdir(full_path):
                    lines.append(f"{prefix}{connector}{entry}/\n")
                    if recursive:
                        extension = "    " if is_last else "|   "
                        _list_dir(full_path, prefix + extension, depth + 1)
                else:
                    size = os.path.getsize(full_path)
                    lines.append(f"{prefix}{connector}{entry} ({size}B)\n")

        _list_dir(path, recursive=recursive)
        return ToolResult(output="".join(lines), success=True)

    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(success=False, error=f"Failed to list directory: {e}")


def _create_directory(path: str) -> ToolResult:
    """创建目录"""
    try:
        os.makedirs(path, exist_ok=True)
        return ToolResult(output=f"Directory created: {path}", success=True)
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(success=False, error=f"Failed to create directory: {e}")


def _delete_file(path: str) -> ToolResult:
    """删除文件或空目录"""
    try:
        if os.path.isfile(path):
            os.remove(path)
            return ToolResult(output=f"File deleted: {path}", success=True)
        elif os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
            return ToolResult(output=f"Directory deleted: {path}", success=True)
        else:
            return ToolResult(success=False, error=f"Path not found: {path}")
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {path}")
    except Exception as e:
        return ToolResult(success=False, error=f"Failed to delete: {e}")


def _file_info(path: str) -> ToolResult:
    """获取文件信息"""
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, error=f"Path not found: {path}")

        stat = os.stat(path)
        is_dir = os.path.isdir(path)
        is_file = os.path.isfile(path)

        info = {
            "path": path,
            "type": "directory" if is_dir else "file" if is_file else "other",
            "size_bytes": stat.st_size,
            "size_human": _format_size(stat.st_size),
            "modified": __import__("datetime").datetime.fromtimestamp(
                stat.st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "permissions": oct(stat.st_mode)[-3:],
        }

        if is_file:
            from nexusagent.utils import detect_file_type
            info["file_type"] = detect_file_type(path)

        output = "\n".join(f"{k}: {v}" for k, v in info.items())
        return ToolResult(output=output, success=True)

    except Exception as e:
        return ToolResult(success=False, error=f"Failed to get file info: {e}")


def _is_binary(filepath: str) -> bool:
    """检测是否为二进制文件"""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8192)
        if not chunk:
            return False
        if b"\x00" in chunk:
            return True
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        non_text = sum(1 for b in chunk if b not in text_chars)
        return non_text / len(chunk) > 0.3
    except (IOError, OSError):
        return True


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
