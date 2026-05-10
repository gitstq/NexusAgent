"""
Web搜索工具

提供网络搜索功能，支持多种搜索方式。
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import re
from typing import Optional

from nexusagent.tools.registry import ToolRegistry, ToolResult


def register_web_search_tools(registry: ToolRegistry):
    """注册Web搜索工具到注册中心

    Args:
        registry: 工具注册中心
    """

    def _web_search(query: str, num_results: int = 5) -> ToolResult:
        """通过DuckDuckGo进行网络搜索

        使用DuckDuckGo的即时回答API和HTML搜索结果。
        不需要API密钥。

        Args:
            query: 搜索查询
            num_results: 返回结果数量

        Returns:
            搜索结果
        """
        results = []

        # 方法1: 使用DuckDuckGo即时回答API
        try:
            instant_url = (
                "https://api.duckduckgo.com/?"
                + urllib.parse.urlencode({
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                })
            )
            req = urllib.request.Request(
                instant_url,
                headers={"User-Agent": "NexusAgent/0.1.0"},
            )
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

            response = urllib.request.urlopen(req, timeout=15, context=ssl_ctx)
            data = json.loads(response.read().decode("utf-8"))

            # 即时回答
            abstract = data.get("Abstract", "")
            if abstract:
                results.append({
                    "title": data.get("Heading", ""),
                    "url": data.get("AbstractURL", ""),
                    "snippet": abstract,
                })

            # 相关主题
            for topic in data.get("RelatedTopics", [])[:num_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic.get("Text", "")[:100],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                    })

        except Exception:
            pass

        # 方法2: 如果即时回答不够，尝试HTML搜索
        if len(results) < 2:
            try:
                html_url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
                req = urllib.request.Request(
                    html_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                    },
                )
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

                response = urllib.request.urlopen(req, timeout=15, context=ssl_ctx)
                html = response.read().decode("utf-8", errors="replace")

                # 解析搜索结果
                # DuckDuckGo HTML结果格式: <a class="result__a" href="...">title</a>
                # <a class="result__snippet" ...>snippet</a>
                title_pattern = re.compile(
                    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                    re.DOTALL,
                )
                snippet_pattern = re.compile(
                    r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                    re.DOTALL,
                )

                titles = title_pattern.findall(html)
                snippets = snippet_pattern.findall(html)

                for i, (url, title) in enumerate(titles[:num_results]):
                    # 清理HTML标签
                    title_clean = re.sub(r'<[^>]+>', '', title).strip()
                    snippet_clean = ""
                    if i < len(snippets):
                        snippet_clean = re.sub(r'<[^>]+>', '', snippets[i]).strip()

                    # 去重
                    if not any(r.get("url") == url for r in results):
                        results.append({
                            "title": title_clean,
                            "url": url,
                            "snippet": snippet_clean,
                        })

            except Exception:
                pass

        if not results:
            return ToolResult(
                output=f"No results found for: {query}\n"
                       f"Note: Web search requires internet access.",
                success=True,
            )

        # 格式化输出
        output_parts = [f"Search results for: {query}\n"]
        for i, r in enumerate(results[:num_results], 1):
            output_parts.append(f"{i}. {r['title']}")
            if r["url"]:
                output_parts.append(f"   URL: {r['url']}")
            if r["snippet"]:
                output_parts.append(f"   {r['snippet'][:200]}")
            output_parts.append("")

        return ToolResult(output="\n".join(output_parts), success=True)

    registry.register_function(
        name="web_search",
        description=(
            "Search the web for information. Uses DuckDuckGo search engine. "
            "Returns titles, URLs, and snippets of matching pages."
        ),
        function=_web_search,
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        category="web_search",
    )

    def _fetch_url(url: str, max_length: int = 10000) -> ToolResult:
        """获取URL内容"""
        try:
            # 确保有协议
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

            response = urllib.request.urlopen(req, timeout=20, context=ssl_ctx)
            content = response.read().decode("utf-8", errors="replace")

            # 移除HTML标签获取纯文本
            text = _html_to_text(content)

            # 截断
            if len(text) > max_length:
                text = text[:max_length] + f"\n\n... (truncated at {max_length} characters)"

            return ToolResult(
                output=f"URL: {url}\n\n{text}",
                success=True,
                metadata={"url": url, "content_length": len(content)},
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Failed to fetch URL: {e}")

    registry.register_function(
        name="fetch_url",
        description=(
            "Fetch and read the content of a URL. "
            "Returns the page content as text (HTML tags removed)."
        ),
        function=_fetch_url,
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum content length in characters (default: 10000)",
                    "default": 10000,
                },
            },
            "required": ["url"],
        },
        category="web_search",
    )


def _html_to_text(html: str) -> str:
    """简单的HTML到纯文本转换

    Args:
        html: HTML字符串

    Returns:
        纯文本
    """
    # 移除script和style标签及其内容
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 替换常见HTML实体
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")

    # 将块级标签替换为换行
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?(p|div|h[1-6]|li|tr|td|th|pre|blockquote)[^>]*>', '\n', text, flags=re.IGNORECASE)

    # 移除所有其他HTML标签
    text = re.sub(r'<[^>]+>', '', text)

    # 清理多余空白
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)

    return text.strip()
