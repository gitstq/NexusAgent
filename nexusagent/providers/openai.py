"""
OpenAI兼容Provider

支持OpenAI、DeepSeek等使用OpenAI兼容API的服务。
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import List, Dict, Optional, Iterator

from nexusagent.providers.base import BaseProvider, ProviderResponse


class OpenAIProvider(BaseProvider):
    """OpenAI兼容API Provider

    支持所有使用OpenAI Chat Completions API格式的服务，
    包括OpenAI官方、DeepSeek、Together AI、Groq等。

    API文档: https://platform.openai.com/docs/api-reference/chat
    """

    def __init__(self, **kwargs):
        """初始化OpenAI Provider

        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL（默认为OpenAI官方）
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成token数
            timeout: 超时时间
        """
        super().__init__(**kwargs)
        self.base_url = self.base_url.rstrip("/")
        # 确保base_url以/v1结尾（如果没有的话）
        if not self.base_url.endswith("/v1"):
            self.base_url = self.base_url + "/v1"

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NexusAgent/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_body(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        stream: bool = False,
        **kwargs,
    ) -> Dict:
        """构建请求体"""
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": stream,
        }

        # 添加工具定义
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        # 合并额外参数
        body.update(self.extra_params)
        return body

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        **kwargs,
    ) -> ProviderResponse:
        """发送聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具定义
            **kwargs: 额外参数

        Returns:
            ProviderResponse对象
        """
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        body = self._build_body(messages, tools, stream=False, **kwargs)

        try:
            _, response_text = self._make_request(url, body, headers)
            data = json.loads(response_text)
        except (json.JSONDecodeError, ConnectionError) as e:
            return ProviderResponse(
                content=f"Error: Failed to get response from {self.base_url}: {e}",
                finish_reason="error",
            )

        return self._parse_response(data)

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        **kwargs,
    ) -> Iterator[str]:
        """流式聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具定义
            **kwargs: 额外参数

        Yields:
            响应文本片段
        """
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        body = self._build_body(messages, tools, stream=True, **kwargs)

        json_data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            response = urllib.request.urlopen(req, timeout=self.timeout, context=ssl_ctx)
            buffer = ""
            for chunk in self._iter_response(response):
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"\n[Stream Error: {e}]"

    def _iter_response(self, response, chunk_size=1024):
        """迭代读取响应数据"""
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            yield chunk.decode("utf-8", errors="replace")

    def _parse_response(self, data: Dict) -> ProviderResponse:
        """解析API响应

        Args:
            data: API返回的JSON数据

        Returns:
            ProviderResponse对象
        """
        try:
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            # 解析工具调用
            tool_calls = []
            raw_tool_calls = message.get("tool_calls", [])
            if raw_tool_calls:
                tool_calls = self._parse_tool_calls(raw_tool_calls)

            # 解析使用情况
            usage = data.get("usage", {})

            return ProviderResponse(
                content=message.get("content", ""),
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason", ""),
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                raw_response=data,
                model=data.get("model", self.model),
            )
        except (KeyError, IndexError, TypeError) as e:
            return ProviderResponse(
                content=f"Error parsing response: {e}",
                finish_reason="error",
                raw_response=data,
            )
