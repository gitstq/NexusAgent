"""
LLM Provider基类

定义所有LLM Provider的统一接口。
"""

import json
import time
from typing import List, Dict, Optional, Any, Iterator


class Message:
    """聊天消息

    Attributes:
        role: 消息角色 (system/user/assistant/tool)
        content: 消息内容
        name: 发送者名称（可选）
        tool_call_id: 工具调用ID（可选）
        tool_calls: 工具调用列表（可选）
    """

    def __init__(
        self,
        role: str,
        content: str = "",
        name: str = "",
        tool_call_id: str = "",
        tool_calls: list = None,
    ):
        self.role = role
        self.content = content
        self.name = name
        self.tool_call_id = tool_call_id
        self.tool_calls = tool_calls or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        """从字典创建消息"""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            name=data.get("name", ""),
            tool_call_id=data.get("tool_call_id", ""),
            tool_calls=data.get("tool_calls", []),
        )

    def __repr__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Message(role={self.role!r}, content={content_preview!r})"


class ProviderResponse:
    """Provider响应

    Attributes:
        content: 响应文本内容
        tool_calls: 工具调用列表
        finish_reason: 完成原因
        usage: token使用情况
        raw_response: 原始响应数据
        model: 使用的模型名称
    """

    def __init__(
        self,
        content: str = "",
        tool_calls: list = None,
        finish_reason: str = "",
        usage: Dict[str, int] = None,
        raw_response: Dict = None,
        model: str = "",
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.finish_reason = finish_reason
        self.usage = usage or {}
        self.raw_response = raw_response or {}
        self.model = model

    @property
    def has_tool_calls(self) -> bool:
        """是否有工具调用"""
        return len(self.tool_calls) > 0

    def __repr__(self):
        return (
            f"ProviderResponse(content={self.content[:50]!r}, "
            f"tool_calls={len(self.tool_calls)}, "
            f"finish_reason={self.finish_reason!r})"
        )


class BaseProvider:
    """LLM Provider基类

    所有LLM Provider必须继承此类并实现相应方法。

    Attributes:
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大生成token数
        timeout: 请求超时时间（秒）
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
        **kwargs,
    ):
        """初始化Provider

        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            temperature: 温度参数 (0.0-2.0)
            max_tokens: 最大生成token数
            timeout: 请求超时时间（秒）
            **kwargs: 其他Provider特定参数
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.extra_params = kwargs

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        **kwargs,
    ) -> ProviderResponse:
        """发送聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具定义列表
            **kwargs: 额外参数

        Returns:
            ProviderResponse响应对象
        """
        raise NotImplementedError("Subclasses must implement chat()")

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        **kwargs,
    ) -> Iterator[str]:
        """发送聊天请求并流式返回

        Args:
            messages: 消息列表
            tools: 可用工具定义列表
            **kwargs: 额外参数

        Yields:
            响应文本片段
        """
        raise NotImplementedError("Subclasses must implement chat_stream()")

    def _make_request(
        self,
        url: str,
        data: Dict,
        headers: Dict,
        method: str = "POST",
        stream: bool = False,
    ):
        """发送HTTP请求（使用urllib）

        Args:
            url: 请求URL
            data: 请求数据
            headers: 请求头
            method: HTTP方法
            stream: 是否流式请求

        Returns:
            (response_body, response_headers) 元组
        """
        import urllib.request
        import urllib.error
        import ssl

        # 准备请求数据
        json_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=json_data, headers=headers, method=method)

        # SSL上下文
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            response = urllib.request.urlopen(
                req, timeout=self.timeout, context=ssl_ctx
            )
            return response, response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            raise ConnectionError(
                f"HTTP {e.code}: {e.reason}\n{error_body}"
            )
        except urllib.error.URLError as e:
            raise ConnectionError(f"Connection error: {e.reason}")
        except Exception as e:
            raise ConnectionError(f"Request failed: {e}")

    def _parse_tool_calls(self, raw_tool_calls: list) -> list:
        """解析工具调用为统一格式

        Args:
            raw_tool_calls: 原始工具调用数据

        Returns:
            统一格式的工具调用列表
        """
        parsed = []
        for tc in raw_tool_calls:
            func = tc.get("function", {})
            parsed.append({
                "id": tc.get("id", ""),
                "name": func.get("name", ""),
                "arguments": func.get("arguments", "{}"),
            })
        return parsed

    def validate_config(self) -> bool:
        """验证Provider配置是否完整

        Returns:
            配置是否有效
        """
        return bool(self.api_key or self.base_url)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(model={self.model!r}, "
            f"base_url={self.base_url!r})"
        )
