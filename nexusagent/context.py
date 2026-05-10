"""
上下文管理模块

负责对话上下文的压缩、摘要和管理，防止上下文窗口溢出。
"""

import json
import os
from typing import List, Dict, Optional, Any

from nexusagent.utils import count_tokens_approx, truncate_text, generate_id


class ContextManager:
    """上下文管理器

    管理对话历史，在接近上下文窗口限制时自动压缩旧消息。

    Attributes:
        max_tokens: 最大token数
        messages: 消息列表
        summaries: 摘要列表
    """

    def __init__(self, max_tokens=8000):
        """初始化上下文管理器

        Args:
            max_tokens: 上下文窗口最大token数
        """
        self.max_tokens = max_tokens
        self.messages: List[Dict[str, Any]] = []
        self.summaries: List[str] = []
        self._system_prompt = ""
        self._total_tokens = 0

    def set_system_prompt(self, prompt: str):
        """设置系统提示词

        Args:
            prompt: 系统提示词
        """
        self._system_prompt = prompt
        self._recalculate_tokens()

    def add_message(self, role: str, content: str, **metadata):
        """添加消息到上下文

        Args:
            role: 消息角色 (user/assistant/tool/system)
            content: 消息内容
            **metadata: 额外元数据
        """
        message = {
            "id": generate_id("msg_"),
            "role": role,
            "content": content,
            "timestamp": __import__("time").time(),
        }
        message.update(metadata)
        self.messages.append(message)
        self._recalculate_tokens()

        # 检查是否需要压缩
        if self._total_tokens > self.max_tokens:
            self._compress()

    def add_tool_result(self, tool_name: str, result: str, tool_call_id: str = ""):
        """添加工具执行结果

        Args:
            tool_name: 工具名称
            result: 执行结果
            tool_call_id: 工具调用ID
        """
        self.add_message(
            role="tool",
            content=result,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )

    def get_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        """获取格式化的消息列表用于LLM API调用

        Args:
            include_system: 是否包含系统提示词

        Returns:
            消息列表，每项为 {"role": str, "content": str}
        """
        result = []

        # 添加系统提示词
        if include_system and self._system_prompt:
            system_content = self._system_prompt
            # 如果有历史摘要，附加到系统提示词
            if self.summaries:
                summary_text = "\n\n".join(self.summaries)
                system_content += f"\n\n[Previous conversation summaries]\n{summary_text}"
            result.append({"role": "system", "content": system_content})

        # 添加对话消息（排除内部元数据）
        for msg in self.messages:
            result.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        return result

    def get_context_info(self) -> Dict[str, Any]:
        """获取上下文使用信息

        Returns:
            包含token使用情况的字典
        """
        return {
            "total_tokens": self._total_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": round(self._total_tokens / self.max_tokens * 100, 1) if self.max_tokens > 0 else 0,
            "message_count": len(self.messages),
            "summary_count": len(self.summaries),
        }

    def clear(self):
        """清空所有消息和摘要"""
        self.messages.clear()
        self.summaries.clear()
        self._total_tokens = 0

    def clear_history(self):
        """清空历史消息但保留系统提示词"""
        self.messages.clear()
        self.summaries.clear()
        self._recalculate_tokens()

    def _recalculate_tokens(self):
        """重新计算总token数"""
        self._total_tokens = count_tokens_approx(self._system_prompt)
        for msg in self.messages:
            self._total_tokens += count_tokens_approx(msg["content"])

    def _compress(self):
        """压缩上下文，将旧消息转为摘要

        当上下文超过限制时，将最早的消息压缩为摘要，
        保留最近的消息以确保对话连贯性。
        """
        # 保留系统提示词的空间（约20%）
        available_tokens = int(self.max_tokens * 0.8)

        # 从最早的消息开始压缩，直到token数在限制内
        while self._total_tokens > available_tokens and len(self.messages) > 2:
            # 取出最早的消息
            old_messages = []
            removed_tokens = 0
            target_remove = int((self._total_tokens - available_tokens) * 0.5)

            while removed_tokens < target_remove and len(self.messages) > 2:
                msg = self.messages.pop(0)
                old_messages.append(msg)
                removed_tokens += count_tokens_approx(msg["content"])

            # 生成摘要
            if old_messages:
                summary = self._create_summary(old_messages)
                self.summaries.append(summary)

            self._recalculate_tokens()

    def _create_summary(self, messages: List[Dict]) -> str:
        """从消息列表创建摘要

        Args:
            messages: 要摘要的消息列表

        Returns:
            摘要文本
        """
        summary_parts = []
        current_speaker = None
        current_content = []

        for msg in messages:
            role = msg["role"]
            content = truncate_text(msg["content"], 200)

            if role != current_speaker:
                if current_content:
                    text = " ".join(current_content)
                    summary_parts.append(f"[{current_speaker}]: {text}")
                current_speaker = role
                current_content = [content]
            else:
                current_content.append(content)

        if current_content:
            text = " ".join(current_content)
            summary_parts.append(f"[{current_speaker}]: {text}")

        # 限制摘要长度
        full_summary = "\n".join(summary_parts)
        if len(full_summary) > 1000:
            full_summary = truncate_text(full_summary, 1000)

        return full_summary

    def to_dict(self) -> Dict:
        """序列化为字典

        Returns:
            包含所有状态的字典
        """
        return {
            "system_prompt": self._system_prompt,
            "messages": self.messages,
            "summaries": self.summaries,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ContextManager":
        """从字典反序列化

        Args:
            data: 序列化的数据

        Returns:
            ContextManager实例
        """
        manager = cls(max_tokens=data.get("max_tokens", 8000))
        manager._system_prompt = data.get("system_prompt", "")
        manager.messages = data.get("messages", [])
        manager.summaries = data.get("summaries", [])
        manager._recalculate_tokens()
        return manager
