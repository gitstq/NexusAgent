"""
工具函数模块

提供项目中通用的工具函数。
"""

import os
import sys
import time
import hashlib
import datetime
import json
import re
from typing import Optional


def ensure_dir(path):
    """确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        目录路径
    """
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path


def generate_id(prefix=""):
    """生成唯一ID

    Args:
        prefix: ID前缀

    Returns:
        带前缀的唯一ID字符串
    """
    timestamp = str(int(time.time() * 1000))[-8:]
    random_part = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    return f"{prefix}{timestamp}{random_part}" if prefix else f"{timestamp}{random_part}"


def truncate_text(text, max_length=500, suffix="..."):
    """截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def count_tokens_approx(text):
    """粗略估算文本的token数量

    使用简单的启发式方法：约4个字符≈1个token

    Args:
        text: 输入文本

    Returns:
        估算的token数量
    """
    if not text:
        return 0
    # 对于中文，大约1.5个字符≈1个token
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)


def format_timestamp(ts=None, fmt="%Y-%m-%d %H:%M:%S"):
    """格式化时间戳

    Args:
        ts: 时间戳（秒），为None则使用当前时间
        fmt: 格式字符串

    Returns:
        格式化后的时间字符串
    """
    if ts is None:
        ts = time.time()
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime(fmt)


def safe_json_dumps(obj, indent=2):
    """安全地将对象序列化为JSON字符串

    Args:
        obj: 要序列化的对象
        indent: 缩进空格数

    Returns:
        JSON字符串
    """
    def default_converter(o):
        if hasattr(o, '__dict__'):
            return o.__dict__
        if hasattr(o, 'to_dict'):
            return o.to_dict()
        return str(o)

    return json.dumps(obj, indent=indent, ensure_ascii=False, default=default_converter)


def sanitize_filename(name):
    """清理文件名，移除非法字符

    Args:
        name: 原始文件名

    Returns:
        清理后的安全文件名
    """
    # 移除或替换非法字符
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('._')
    if not name:
        name = "unnamed"
    return name[:255]


def detect_file_type(filepath):
    """根据文件扩展名检测文件类型

    Args:
        filepath: 文件路径

    Returns:
        文件类型字符串（如 "python", "javascript", "markdown" 等）
    """
    ext = os.path.splitext(filepath)[1].lower()
    type_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".ps1": "powershell",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".md": "markdown",
        ".rst": "rst",
        ".txt": "text",
        ".sql": "sql",
        ".r": "r",
        ".lua": "lua",
        ".vim": "vim",
        ".dockerfile": "dockerfile",
        ".makefile": "makefile",
    }
    return type_map.get(ext, "text")


def get_file_extension(filepath):
    """获取文件扩展名（不含点号）

    Args:
        filepath: 文件路径

    Returns:
        扩展名字符串
    """
    ext = os.path.splitext(filepath)[1].lower()
    return ext.lstrip(".")


def is_binary_file(filepath):
    """检测文件是否为二进制文件

    Args:
        filepath: 文件路径

    Returns:
        True如果是二进制文件
    """
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(8192)
        if not chunk:
            return False
        # 检查null字节
        if b'\x00' in chunk:
            return True
        # 检查高比例的非文本字节
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        non_text = sum(1 for b in chunk if b not in text_chars)
        return non_text / len(chunk) > 0.3
    except (IOError, OSError):
        return True


def format_file_size(size_bytes):
    """格式化文件大小为人类可读格式

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_terminal_size():
    """获取终端大小

    Returns:
        (rows, cols) 元组
    """
    try:
        size = os.get_terminal_size()
        return size.lines, size.columns
    except OSError:
        return 24, 80


def strip_ansi(text):
    """移除文本中的ANSI转义码

    Args:
        text: 可能包含ANSI码的文本

    Returns:
        清理后的纯文本
    """
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b\[.*?m')
    return ansi_escape.sub('', text)


class Timer:
    """简单的计时器上下文管理器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time

    @property
    def duration_str(self):
        """返回格式化的持续时间字符串"""
        if self.elapsed < 1:
            return f"{self.elapsed * 1000:.0f}ms"
        elif self.elapsed < 60:
            return f"{self.elapsed:.1f}s"
        else:
            minutes = int(self.elapsed // 60)
            seconds = self.elapsed % 60
            return f"{minutes}m {seconds:.0f}s"
