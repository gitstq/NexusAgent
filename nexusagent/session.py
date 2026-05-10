"""
会话管理模块

负责会话的持久化存储、加载和历史记录管理。
"""

import json
import os
import time
from typing import List, Dict, Optional, Any

from nexusagent.utils import (
    ensure_dir, generate_id, format_timestamp,
    sanitize_filename, safe_json_dumps,
)
from nexusagent.context import ContextManager


class Session:
    """会话管理器

    管理对话会话的创建、保存、加载和列表。

    Attributes:
        session_id: 会话唯一ID
        title: 会话标题
        created_at: 创建时间
        updated_at: 更新时间
        context: 上下文管理器
        metadata: 会话元数据
    """

    def __init__(
        self,
        session_id: str = None,
        title: str = "",
        save_dir: str = "",
        context_manager: ContextManager = None,
    ):
        """初始化会话

        Args:
            session_id: 会话ID，为None则自动生成
            title: 会话标题
            save_dir: 会话保存目录
            context_manager: 上下文管理器实例
        """
        self.session_id = session_id or generate_id("sess_")
        self.title = title or f"Session {self.session_id[-8:]}"
        self.created_at = time.time()
        self.updated_at = self.created_at
        self.context = context_manager or ContextManager()
        self.metadata: Dict[str, Any] = {
            "provider": "",
            "model": "",
            "iterations": 0,
        }
        self._save_dir = save_dir or os.path.expanduser("~/.nexusagent/sessions")

    @property
    def save_path(self) -> str:
        """获取会话文件的完整路径"""
        filename = f"{self.session_id}.json"
        return os.path.join(self._save_dir, filename)

    def update_title(self, title: str):
        """更新会话标题

        Args:
            title: 新标题
        """
        self.title = sanitize_filename(title)[:100]
        self.updated_at = time.time()

    def touch(self):
        """更新会话的最后修改时间"""
        self.updated_at = time.time()

    def save(self, save_dir: str = None):
        """保存会话到磁盘

        Args:
            save_dir: 指定保存目录，为None则使用默认目录
        """
        if save_dir:
            self._save_dir = save_dir

        ensure_dir(self._save_dir)

        data = {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context": self.context.to_dict(),
            "metadata": self.metadata,
        }

        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Failed to save session: {e}")

    def load(self, session_id: str = None, save_dir: str = None) -> bool:
        """从磁盘加载会话

        Args:
            session_id: 要加载的会话ID，为None则使用当前ID
            save_dir: 会话目录

        Returns:
            是否加载成功
        """
        if session_id:
            self.session_id = session_id
        if save_dir:
            self._save_dir = save_dir

        filepath = self.save_path
        if not os.path.isfile(filepath):
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.session_id = data.get("session_id", self.session_id)
            self.title = data.get("title", self.title)
            self.created_at = data.get("created_at", self.created_at)
            self.updated_at = data.get("updated_at", self.updated_at)
            self.metadata = data.get("metadata", {})
            self.context = ContextManager.from_dict(data.get("context", {}))
            return True
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"Warning: Failed to load session: {e}")
            return False

    def delete(self) -> bool:
        """删除会话文件

        Returns:
            是否删除成功
        """
        try:
            if os.path.isfile(self.save_path):
                os.remove(self.save_path)
                return True
        except IOError:
            pass
        return False

    @classmethod
    def list_sessions(cls, save_dir: str = None) -> List[Dict[str, Any]]:
        """列出所有保存的会话

        Args:
            save_dir: 会话目录

        Returns:
            会话信息列表
        """
        session_dir = save_dir or os.path.expanduser("~/.nexusagent/sessions")
        sessions = []

        if not os.path.isdir(session_dir):
            return sessions

        for filename in os.listdir(session_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(session_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                sessions.append({
                    "session_id": data.get("session_id", ""),
                    "title": data.get("title", "Untitled"),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "message_count": len(data.get("context", {}).get("messages", [])),
                })
            except (json.JSONDecodeError, IOError):
                continue

        # 按更新时间倒序排列
        sessions.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        return sessions

    @classmethod
    def create_new(cls, title: str = "", save_dir: str = "") -> "Session":
        """创建新会话的便捷方法

        Args:
            title: 会话标题
            save_dir: 保存目录

        Returns:
            新的Session实例
        """
        return cls(title=title, save_dir=save_dir)

    def __repr__(self):
        return (
            f"Session(id={self.session_id!r}, title={self.title!r}, "
            f"messages={len(self.context.messages)})"
        )
