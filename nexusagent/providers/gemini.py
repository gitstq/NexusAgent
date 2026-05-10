"""
Google Gemini Provider

支持Google Gemini系列模型的API调用。
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
from typing import List, Dict, Iterator

from nexusagent.providers.base import BaseProvider, ProviderResponse


class GeminiProvider(BaseProvider):
    """Google Gemini Provider

    使用Google Generative AI API与Gemini系列模型交互。

    API文档: https://ai.google.dev/api/generate-content
    """

    def __init__(self, **kwargs):
        """初始化Gemini Provider

        Args:
            api_key: Google AI API密钥
            base_url: API基础URL
            model: 模型名称（如 gemini-2.0-flash）
            temperature: 温度参数
            max_tokens: 最大生成token数
            timeout: 超时时间
        """
        super().__init__(**kwargs)
        self.base_url = self.base_url.rstrip("/")

    def _build_url(self, action: str = "generateContent") -> str:
        """构建API URL

        Args:
            action: API动作（generateContent/streamGenerateContent）

        Returns:
            完整的API URL
        """
        params = urllib.parse.urlencode({"key": self.api_key})
        return f"{self.base_url}/models/{self.model}:{action}?{params}"

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "NexusAgent/0.1.0",
        }

    def _convert_messages(self, messages: List[Dict]) -> tuple:
        """将通用消息格式转换为Gemini格式

        Gemini API格式:
        - system instruction单独提取
        - contents数组包含role和parts
        - role为"user"或"model"

        Args:
            messages: 通用消息列表

        Returns:
            (system_instruction, contents) 元组
        """
        system_instruction = ""
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
                continue

            if role == "tool":
                # 工具结果
                if contents and contents[-1].get("role") == "user":
                    parts = contents[-1].get("parts", [])
                    parts.append({
                        "functionResponse": {
                            "name": msg.get("tool_name", ""),
                            "response": {"result": content},
                        }
                    })
                else:
                    contents.append({
                        "role": "user",
                        "parts": [{
                            "functionResponse": {
                                "name": msg.get("tool_name", ""),
                                "response": {"result": content},
                            }
                        }],
                    })
                continue

            # 映射角色
            gemini_role = "model" if role == "assistant" else "user"

            if role == "assistant" and msg.get("tool_calls"):
                # 包含工具调用的assistant消息
                parts = []
                if content:
                    parts.append({"text": content})
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    args = func.get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    parts.append({
                        "functionCall": {
                            "name": func.get("name", ""),
                            "args": args,
                        }
                    })
                contents.append({"role": gemini_role, "parts": parts})
            else:
                contents.append({"role": gemini_role, "parts": [{"text": content}]})

        return system_instruction, contents

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """将通用工具格式转换为Gemini格式

        Args:
            tools: 通用工具定义列表

        Returns:
            Gemini格式的工具声明列表
        """
        function_declarations = []
        for tool in tools:
            func = tool.get("function", {})
            function_declarations.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            })
        return [{"function_declarations": function_declarations}]

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
        url = self._build_url("generateContent")
        headers = self._build_headers()

        system_instruction, contents = self._convert_messages(messages)

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", self.temperature),
                "maxOutputTokens": kwargs.get("max_tokens", self.max_tokens),
            },
        }

        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        if tools:
            body["tools"] = self._convert_tools(tools)

        try:
            _, response_text = self._make_request(url, body, headers)
            data = json.loads(response_text)
        except (json.JSONDecodeError, ConnectionError) as e:
            return ProviderResponse(
                content=f"Error: Failed to get response from Gemini: {e}",
                finish_reason="error",
            )

        return self._parse_response(data)

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        **kwargs,
    ) -> ProviderResponse:
        """流式聊天请求

        Gemini的流式API返回完整的JSON数组，逐个解析。

        Args:
            messages: 消息列表
            tools: 可用工具定义

        Yields:
            响应文本片段
        """
        url = self._build_url("streamGenerateContent")
        headers = self._build_headers()
        headers["Accept"] = "text/event-stream"

        system_instruction, contents = self._convert_messages(messages)

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", self.temperature),
                "maxOutputTokens": kwargs.get("max_tokens", self.max_tokens),
            },
        }

        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

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
                # Gemini流式返回JSON数组，每个元素用逗号分隔
                while buffer:
                    # 尝试找到完整的JSON对象
                    text = self._extract_json_object(buffer)
                    if text is None:
                        break
                    buffer = buffer[len(text):].lstrip(", \n\r")
                    try:
                        data = json.loads(text)
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    yield part["text"]
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"\n[Stream Error: {e}]"

    def _extract_json_object(self, text: str) -> str:
        """从文本中提取第一个完整的JSON对象"""
        if not text.strip():
            return None

        depth = 0
        start = -1
        in_string = False
        escape = False

        for i, c in enumerate(text):
            if escape:
                escape = False
                continue
            if c == '\\' and in_string:
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue

            if c == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    return text[start:i + 1]

        return None

    def _iter_response(self, response, chunk_size=1024):
        """迭代读取响应数据"""
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            yield chunk.decode("utf-8", errors="replace")

    def _parse_response(self, data: Dict) -> ProviderResponse:
        """解析Gemini API响应

        Args:
            data: API返回的JSON数据

        Returns:
            ProviderResponse对象
        """
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                return ProviderResponse(
                    content="No response generated",
                    finish_reason="empty",
                    raw_response=data,
                )

            candidate = candidates[0]
            content_data = candidate.get("content", {})
            parts = content_data.get("parts", [])

            text_parts = []
            tool_calls = []

            for part in parts:
                if "text" in part:
                    text_parts.append(part["text"])
                elif "functionCall" in part:
                    fc = part["functionCall"]
                    tool_calls.append({
                        "id": f"call_{fc.get('name', '')}",
                        "name": fc.get("name", ""),
                        "arguments": json.dumps(fc.get("args", {})),
                    })

            usage_meta = data.get("usageMetadata", {})

            return ProviderResponse(
                content="\n".join(text_parts),
                tool_calls=tool_calls,
                finish_reason=candidate.get("finishReason", ""),
                usage={
                    "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                    "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                    "total_tokens": usage_meta.get("totalTokenCount", 0),
                },
                raw_response=data,
                model=data.get("modelVersion", self.model),
            )
        except (KeyError, IndexError, TypeError) as e:
            return ProviderResponse(
                content=f"Error parsing response: {e}",
                finish_reason="error",
                raw_response=data,
            )
