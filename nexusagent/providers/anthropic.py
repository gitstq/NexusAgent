"""
Anthropic Claude Provider

支持Anthropic Claude系列模型的API调用。
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import List, Dict, Iterator

from nexusagent.providers.base import BaseProvider, ProviderResponse


class AnthropicProvider(BaseProvider):
    """Anthropic Claude Provider

    使用Anthropic Messages API与Claude系列模型交互。

    API文档: https://docs.anthropic.com/en/api/messages
    """

    # Anthropic API版本
    API_VERSION = "2023-06-01"

    def __init__(self, **kwargs):
        """初始化Anthropic Provider

        Args:
            api_key: Anthropic API密钥
            base_url: API基础URL
            model: 模型名称（如 claude-sonnet-4-20250514）
            temperature: 温度参数
            max_tokens: 最大生成token数
            timeout: 超时时间
        """
        super().__init__(**kwargs)
        self.base_url = self.base_url.rstrip("/")

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "NexusAgent/0.1.0",
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "anthropic-dangerous-direct-browser-access": "true",
        }

    def _convert_messages(self, messages: List[Dict]) -> tuple:
        """将通用消息格式转换为Anthropic格式

        Anthropic API要求:
        - system消息单独提取
        - 消息中不能有system角色
        - tool结果使用user角色+tool_result content block

        Args:
            messages: 通用消息列表

        Returns:
            (system_prompt, converted_messages, tool_results) 元组
        """
        system_prompt = ""
        converted = []
        tool_results = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = content
                continue

            if role == "tool":
                # 工具结果转换为Anthropic的tool_result格式
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id", ""),
                    "content": content,
                })
                continue

            if role == "assistant" and msg.get("tool_calls"):
                # 包含工具调用的assistant消息
                content_blocks = []
                if content:
                    content_blocks.append({"type": "text", "text": content})
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    args = func.get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": args,
                    })
                converted.append({"role": "assistant", "content": content_blocks})
                continue

            converted.append({"role": role, "content": content})

        # 将tool_results附加到最后一个user消息或创建新的
        if tool_results:
            if converted and converted[-1]["role"] == "user":
                last_content = converted[-1]["content"]
                if isinstance(last_content, str):
                    converted[-1]["content"] = [
                        {"type": "text", "text": last_content}
                    ]
                converted[-1]["content"].extend(tool_results)
            else:
                converted.append({"role": "user", "content": tool_results})

        return system_prompt, converted

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """将通用工具格式转换为Anthropic格式

        Args:
            tools: 通用工具定义列表

        Returns:
            Anthropic格式的工具列表
        """
        anthropic_tools = []
        for tool in tools:
            func = tool.get("function", {})
            parameters = func.get("parameters", {})
            anthropic_tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": parameters,
            })
        return anthropic_tools

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
        url = f"{self.base_url}/v1/messages"
        headers = self._build_headers()

        system_prompt, converted_messages = self._convert_messages(messages)

        body = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": False,
        }

        if system_prompt:
            body["system"] = system_prompt

        if tools:
            body["tools"] = self._convert_tools(tools)
            body["tool_choice"] = {"type": "auto"}

        try:
            _, response_text = self._make_request(url, body, headers)
            data = json.loads(response_text)
        except (json.JSONDecodeError, ConnectionError) as e:
            return ProviderResponse(
                content=f"Error: Failed to get response from Anthropic: {e}",
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

        Yields:
            响应文本片段
        """
        url = f"{self.base_url}/v1/messages"
        headers = self._build_headers()

        system_prompt, converted_messages = self._convert_messages(messages)

        body = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": True,
        }

        if system_prompt:
            body["system"] = system_prompt

        if tools:
            body["tools"] = self._convert_tools(tools)

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
                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type", "")

                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield text
                        elif event_type == "message_stop":
                            return
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
        """解析Anthropic API响应

        Args:
            data: API返回的JSON数据

        Returns:
            ProviderResponse对象
        """
        try:
            content_blocks = data.get("content", [])
            text_parts = []
            tool_calls = []

            for block in content_blocks:
                block_type = block.get("type", "")

                if block_type == "text":
                    text_parts.append(block.get("text", ""))

                elif block_type == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {})),
                    })

            usage = data.get("usage", {})

            return ProviderResponse(
                content="\n".join(text_parts),
                tool_calls=tool_calls,
                finish_reason=data.get("stop_reason", ""),
                usage={
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
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
