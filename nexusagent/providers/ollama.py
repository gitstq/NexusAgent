"""
Ollama本地模型Provider

支持Ollama本地部署的模型API调用。
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import List, Dict, Iterator

from nexusagent.providers.base import BaseProvider, ProviderResponse


class OllamaProvider(BaseProvider):
    """Ollama本地模型 Provider

    使用Ollama REST API与本地部署的模型交互。
    Ollama兼容OpenAI的Chat格式，但原生API更简单。

    API文档: https://github.com/ollama/ollama/blob/main/docs/api.md
    """

    def __init__(self, **kwargs):
        """初始化Ollama Provider

        Args:
            api_key: API密钥（Ollama通常不需要）
            base_url: Ollama服务地址（默认 http://localhost:11434）
            model: 模型名称（如 llama3, codellama, qwen2-coder）
            temperature: 温度参数
            max_tokens: 最大生成token数
            timeout: 超时时间
        """
        super().__init__(**kwargs)
        self.base_url = self.base_url.rstrip("/")

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NexusAgent/0.1.0",
        }
        return headers

    def _convert_messages(self, messages: List[Dict]) -> tuple:
        """将通用消息格式转换为Ollama格式

        Args:
            messages: 通用消息列表

        Returns:
            (system_prompt, ollama_messages) 元组
        """
        system_prompt = ""
        ollama_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = content
                continue

            if role == "tool":
                # 工具结果作为user消息
                ollama_messages.append({
                    "role": "user",
                    "content": f"[Tool Result - {msg.get('tool_name', 'unknown')}]:\n{content}",
                })
                continue

            # 映射角色
            ollama_role = "assistant" if role == "assistant" else "user"

            if role == "assistant" and msg.get("tool_calls"):
                # 包含工具调用的assistant消息
                tool_calls_text = "\n".join(
                    f"[Tool Call: {tc.get('function', {}).get('name', '')}({tc.get('function', {}).get('arguments', '{}')})]"
                    for tc in msg["tool_calls"]
                )
                full_content = content
                if tool_calls_text:
                    full_content = f"{content}\n{tool_calls_text}" if content else tool_calls_text
                ollama_messages.append({"role": ollama_role, "content": full_content})
            else:
                ollama_messages.append({"role": ollama_role, "content": content})

        return system_prompt, ollama_messages

    def is_available(self) -> bool:
        """检查Ollama服务是否可用

        Returns:
            服务是否可用
        """
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, headers=self._build_headers())
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            urllib.request.urlopen(req, timeout=5, context=ssl_ctx)
            return True
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """列出可用的本地模型

        Returns:
            模型名称列表
        """
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, headers=self._build_headers())
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            response = urllib.request.urlopen(req, timeout=10, context=ssl_ctx)
            data = json.loads(response.read().decode("utf-8"))
            models = data.get("models", [])
            return [m.get("name", "") for m in models]
        except Exception:
            return []

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        **kwargs,
    ) -> ProviderResponse:
        """发送聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具定义（Ollama原生支持有限）
            **kwargs: 额外参数

        Returns:
            ProviderResponse对象
        """
        url = f"{self.base_url}/api/chat"
        headers = self._build_headers()

        system_prompt, ollama_messages = self._convert_messages(messages)

        body = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }

        if system_prompt:
            # Ollama在messages中添加system消息
            ollama_messages.insert(0, {"role": "system", "content": system_prompt})

        # 如果有工具定义，附加到系统提示中
        if tools:
            tool_descriptions = self._tools_to_text(tools)
            if tool_descriptions:
                sys_msg = {"role": "system", "content": tool_descriptions}
                if ollama_messages and ollama_messages[0]["role"] == "system":
                    ollama_messages[0]["content"] += "\n\n" + tool_descriptions
                else:
                    ollama_messages.insert(0, sys_msg)

        body["messages"] = ollama_messages

        try:
            _, response_text = self._make_request(url, body, headers)
            data = json.loads(response_text)
        except (json.JSONDecodeError, ConnectionError) as e:
            return ProviderResponse(
                content=f"Error: Failed to get response from Ollama: {e}",
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
        url = f"{self.base_url}/api/chat"
        headers = self._build_headers()

        system_prompt, ollama_messages = self._convert_messages(messages)

        body = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }

        if system_prompt:
            ollama_messages.insert(0, {"role": "system", "content": system_prompt})

        if tools:
            tool_descriptions = self._tools_to_text(tools)
            if tool_descriptions:
                if ollama_messages and ollama_messages[0]["role"] == "system":
                    ollama_messages[0]["content"] += "\n\n" + tool_descriptions
                else:
                    ollama_messages.insert(0, {"role": "system", "content": tool_descriptions})

        body["messages"] = ollama_messages

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
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
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

    def _tools_to_text(self, tools: List[Dict]) -> str:
        """将工具定义转换为文本描述（用于不支持原生工具调用的模型）

        Args:
            tools: 工具定义列表

        Returns:
            工具描述文本
        """
        if not tools:
            return ""

        lines = ["You have access to the following tools. To use a tool, respond with a JSON block containing 'tool_name' and 'arguments':"]
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "")
            desc = func.get("description", "")
            params = func.get("parameters", {}).get("properties", {})
            lines.append(f"\n- {name}: {desc}")
            if params:
                lines.append("  Parameters:")
                for pname, pinfo in params.items():
                    ptype = pinfo.get("type", "string")
                    pdesc = pinfo.get("description", "")
                    lines.append(f"    - {pname} ({ptype}): {pdesc}")

        return "\n".join(lines)

    def _parse_response(self, data: Dict) -> ProviderResponse:
        """解析Ollama API响应

        Args:
            data: API返回的JSON数据

        Returns:
            ProviderResponse对象
        """
        try:
            message = data.get("message", {})
            content = message.get("content", "")

            # 尝试从内容中解析工具调用
            tool_calls = self._extract_tool_calls(content)

            # 如果解析到了工具调用，从content中移除
            if tool_calls:
                content = self._remove_tool_calls_from_content(content)

            return ProviderResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason="stop" if data.get("done") else "length",
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                },
                raw_response=data,
                model=data.get("model", self.model),
            )
        except (KeyError, TypeError) as e:
            return ProviderResponse(
                content=f"Error parsing response: {e}",
                finish_reason="error",
                raw_response=data,
            )

    def _extract_tool_calls(self, content: str) -> list:
        """从文本内容中提取工具调用

        Args:
            content: 可能包含工具调用的文本

        Returns:
            工具调用列表
        """
        import re
        tool_calls = []

        # 匹配JSON格式的工具调用
        json_pattern = r'\{[^{}]*"tool_name"\s*:\s*"([^"]+)"[^{}]*"arguments"\s*:\s*(\{[^{}]*\})[^{}]*\}'
        for match in re.finditer(json_pattern, content, re.DOTALL):
            tool_calls.append({
                "id": f"call_{match.group(1)}",
                "name": match.group(1),
                "arguments": match.group(2),
            })

        return tool_calls

    def _remove_tool_calls_from_content(self, content: str) -> str:
        """从内容中移除工具调用JSON块"""
        import re
        json_pattern = r'\{[^{}]*"tool_name"\s*:\s*"[^"]+"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}'
        return re.sub(json_pattern, "", content, flags=re.DOTALL).strip()
