"""
代码分析工具

提供代码静态分析、依赖分析、结构分析等功能。
"""

import os
import re
import ast
import json
from typing import Optional

from nexusagent.tools.registry import ToolRegistry, ToolResult
from nexusagent.sandbox import Sandbox


def register_code_analysis_tools(
    registry: ToolRegistry, sandbox: Sandbox = None
):
    """注册代码分析工具到注册中心

    Args:
        registry: 工具注册中心
        sandbox: 沙箱实例
    """
    _sandbox = sandbox or Sandbox()

    def _analyze_python(path: str) -> ToolResult:
        """分析Python文件结构

        Args:
            path: Python文件路径

        Returns:
            分析结果
        """
        if not os.path.isfile(path):
            return ToolResult(success=False, error=f"File not found: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()

            tree = ast.parse(source, filename=path)

            analysis = {
                "file": path,
                "language": "python",
                "total_lines": source.count("\n") + 1,
                "classes": [],
                "functions": [],
                "imports": [],
                "issues": [],
            }

            # 分析导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        analysis["imports"].append(f"{module}.{alias.name}")

            # 分析类和函数
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [],
                        "bases": [],
                        "docstring": ast.get_docstring(node) or "",
                    }
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            class_info["bases"].append(base.id)
                        elif isinstance(base, ast.Attribute):
                            class_info["bases"].append(
                                f"{base.value.id}.{base.attr}"
                                if isinstance(base.value, ast.Name)
                                else str(base.attr)
                            )
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "name": item.name,
                                "line": item.lineno,
                                "args": [a.arg for a in item.args.args],
                                "docstring": ast.get_docstring(item) or "",
                            }
                            class_info["methods"].append(method_info)
                    analysis["classes"].append(class_info)

                elif isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "args": [a.arg for a in node.args.args],
                        "docstring": ast.get_docstring(node) or "",
                        "decorators": [],
                    }
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Name):
                            func_info["decorators"].append(dec.id)
                        elif isinstance(dec, ast.Attribute):
                            func_info["decorators"].append(dec.attr)
                        elif isinstance(dec, ast.Call):
                            if isinstance(dec.func, ast.Name):
                                func_info["decorators"].append(dec.func.id)
                    analysis["functions"].append(func_info)

            # 基本问题检测
            if not analysis["imports"]:
                analysis["issues"].append("No imports found")
            for func in analysis["functions"]:
                if not func["docstring"]:
                    analysis["issues"].append(
                        f"Function '{func['name']}' (line {func['line']}) missing docstring"
                    )
            for cls in analysis["classes"]:
                if not cls["docstring"]:
                    analysis["issues"].append(
                        f"Class '{cls['name']}' (line {cls['line']}) missing docstring"
                    )

            # 格式化输出
            output_parts = [
                f"Python Analysis: {path}",
                f"Lines: {analysis['total_lines']}",
                f"Classes: {len(analysis['classes'])}",
                f"Functions: {len(analysis['functions'])}",
                f"Imports: {len(analysis['imports'])}",
                "",
            ]

            if analysis["imports"]:
                output_parts.append("Imports:")
                for imp in analysis["imports"]:
                    output_parts.append(f"  - {imp}")
                output_parts.append("")

            if analysis["classes"]:
                output_parts.append("Classes:")
                for cls in analysis["classes"]:
                    bases = f"({', '.join(cls['bases'])})" if cls["bases"] else ""
                    output_parts.append(f"  class {cls['name']}{bases} [line {cls['line']}]")
                    if cls["docstring"]:
                        output_parts.append(f"    {cls['docstring'][:80]}")
                    for method in cls["methods"]:
                        args = ", ".join(method["args"])
                        output_parts.append(
                            f"    def {method['name']}({args}) [line {method['line']}]"
                        )
                output_parts.append("")

            if analysis["functions"]:
                output_parts.append("Functions:")
                for func in analysis["functions"]:
                    args = ", ".join(func["args"])
                    decs = f"@{', @'.join(func['decorators'])} " if func["decorators"] else ""
                    output_parts.append(
                        f"  {decs}def {func['name']}({args}) [line {func['line']}]"
                    )
                    if func["docstring"]:
                        output_parts.append(f"    {func['docstring'][:80]}")
                output_parts.append("")

            if analysis["issues"]:
                output_parts.append("Issues:")
                for issue in analysis["issues"]:
                    output_parts.append(f"  ! {issue}")

            return ToolResult(output="\n".join(output_parts), success=True)

        except SyntaxError as e:
            return ToolResult(
                success=False,
                error=f"Python syntax error at line {e.lineno}: {e.msg}",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Analysis failed: {e}")

    registry.register_function(
        name="analyze_python",
        description=(
            "Analyze a Python file structure: classes, functions, imports, "
            "inheritance, docstrings, and basic issues."
        ),
        function=_analyze_python,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the Python file to analyze",
                },
            },
            "required": ["path"],
        },
        category="code_analysis",
    )

    def _count_lines(directory: str = ".", file_pattern: str = "*.py") -> ToolResult:
        """统计代码行数"""
        import fnmatch

        total_lines = 0
        total_files = 0
        file_stats = []

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in (
                "__pycache__", "node_modules", ".git", "venv", ".venv",
                "dist", "build",
            )]

            for filename in files:
                if not fnmatch.fnmatch(filename, file_pattern):
                    continue

                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        lines = sum(1 for _ in f)
                    total_lines += lines
                    total_files += 1
                    file_stats.append((filepath, lines))
                except (PermissionError, OSError):
                    continue

        # 按行数排序
        file_stats.sort(key=lambda x: x[1], reverse=True)

        output_parts = [
            f"Code line count for '{file_pattern}' in {directory}",
            f"Total files: {total_files}",
            f"Total lines: {total_lines}",
            "",
            "Top files by line count:",
        ]

        for filepath, lines in file_stats[:20]:
            output_parts.append(f"  {lines:>6}  {filepath}")

        if len(file_stats) > 20:
            output_parts.append(f"  ... and {len(file_stats) - 20} more files")

        return ToolResult(output="\n".join(output_parts), success=True)

    registry.register_function(
        name="count_lines",
        description=(
            "Count lines of code in files matching a pattern. "
            "Shows total statistics and top files by line count."
        ),
        function=_count_lines,
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory to scan",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File glob pattern (default: '*.py')",
                    "default": "*.py",
                },
            },
        },
        category="code_analysis",
    )

    def _find_references(
        path: str, symbol: str, directory: str = "."
    ) -> ToolResult:
        """查找符号引用"""
        import fnmatch

        if not os.path.isfile(path):
            return ToolResult(success=False, error=f"File not found: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read file: {e}")

        # 查找定义位置
        pattern = re.compile(rf'\b{re.escape(symbol)}\b')
        definitions = []
        for i, line in enumerate(source.split("\n"), 1):
            # 检查是否是定义
            for prefix in ["def ", "class ", "self.", "import ", "from "]:
                if prefix + symbol in line or symbol in line.split(prefix)[-1]:
                    definitions.append((i, line.strip()))
                    break

        # 在同目录下查找引用
        references = []
        search_dir = os.path.dirname(path) or directory
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in (
                "__pycache__", "node_modules", ".git", "venv", ".venv",
            )]
            for filename in files:
                if not filename.endswith((".py", ".js", ".ts", ".go", ".rs", ".java")):
                    continue
                filepath = os.path.join(root, filename)
                if filepath == path:
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if pattern.search(line):
                                references.append((filepath, i, line.strip()))
                                if len(references) > 50:
                                    break
                except (PermissionError, OSError):
                    continue
            if len(references) > 50:
                break

        output_parts = [
            f"Symbol references for '{symbol}'",
            f"Defined in: {path}",
            "",
        ]

        if definitions:
            output_parts.append("Definitions:")
            for line_num, line in definitions:
                output_parts.append(f"  Line {line_num}: {line}")
            output_parts.append("")

        if references:
            output_parts.append(f"References (found {len(references)}):")
            for filepath, line_num, line in references[:30]:
                rel_path = os.path.relpath(filepath, search_dir)
                output_parts.append(f"  {rel_path}:{line_num}: {line[:100]}")
            if len(references) > 30:
                output_parts.append(f"  ... and {len(references) - 30} more")
        else:
            output_parts.append("No references found in nearby files.")

        return ToolResult(output="\n".join(output_parts), success=True)

    registry.register_function(
        name="find_references",
        description=(
            "Find where a symbol (function, class, variable) is defined and used. "
            "Searches the file for definitions and nearby files for references."
        ),
        function=_find_references,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the source file",
                },
                "symbol": {
                    "type": "string",
                    "description": "Symbol name to search for",
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search for references",
                },
            },
            "required": ["path", "symbol"],
        },
        category="code_analysis",
    )

    def _tree_sitter_parse(path: str) -> ToolResult:
        """使用AST解析文件并显示语法树（简化版）"""
        if not path.endswith(".py"):
            return ToolResult(success=False, error="Only Python files are supported")

        if not os.path.isfile(path):
            return ToolResult(success=False, error=f"File not found: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()

            tree = ast.parse(source, filename=path)

            def _node_to_str(node, indent=0):
                prefix = "  " * indent
                if isinstance(node, ast.Module):
                    lines = [f"{prefix}Module"]
                elif isinstance(node, ast.ClassDef):
                    lines = [f"{prefix}ClassDef: {node.name} (line {node.lineno})"]
                elif isinstance(node, ast.FunctionDef):
                    args = [a.arg for a in node.args.args]
                    lines = [f"{prefix}FunctionDef: {node.name}({', '.join(args)}) (line {node.lineno})"]
                elif isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                    lines = [f"{prefix}Import: {', '.join(names)}"]
                elif isinstance(node, ast.ImportFrom):
                    names = [a.name for a in node.names]
                    lines = [f"{prefix}ImportFrom: {node.module} [{', '.join(names)}]"]
                elif isinstance(node, ast.Assign):
                    targets = [ast.dump(t) for t in node.targets]
                    lines = [f"{prefix}Assign: {targets[0][:50]}"]
                elif isinstance(node, ast.Expr):
                    lines = [f"{prefix}Expr"]
                elif isinstance(node, ast.If):
                    lines = [f"{prefix}If"]
                elif isinstance(node, ast.For):
                    lines = [f"{prefix}For"]
                elif isinstance(node, ast.While):
                    lines = [f"{prefix}While"]
                elif isinstance(node, ast.With):
                    lines = [f"{prefix}With"]
                elif isinstance(node, ast.Try):
                    lines = [f"{prefix}Try"]
                elif isinstance(node, ast.Return):
                    lines = [f"{prefix}Return"]
                elif isinstance(node, ast.Raise):
                    lines = [f"{prefix}Raise"]
                else:
                    lines = [f"{prefix}{type(node).__name__}"]

                for child in ast.iter_child_nodes(node):
                    lines.extend(_node_to_str(child, indent + 1))
                return lines

            tree_str = "\n".join(_node_to_str(tree))
            return ToolResult(output=f"AST for {path}:\n{tree_str}", success=True)

        except SyntaxError as e:
            return ToolResult(
                success=False,
                error=f"Syntax error at line {e.lineno}: {e.msg}",
            )

    registry.register_function(
        name="tree_sitter_parse",
        description=(
            "Parse a Python file and display its AST (Abstract Syntax Tree). "
            "Useful for understanding code structure."
        ),
        function=_tree_sitter_parse,
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the Python file",
                },
            },
            "required": ["path"],
        },
        category="code_analysis",
    )
