"""
Provider包初始化

导出所有可用的LLM Provider。
"""

from nexusagent.providers.base import BaseProvider, ProviderResponse, Message
from nexusagent.providers.openai import OpenAIProvider
from nexusagent.providers.anthropic import AnthropicProvider
from nexusagent.providers.gemini import GeminiProvider
from nexusagent.providers.ollama import OllamaProvider

# Provider注册表
PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "deepseek": OpenAIProvider,    # DeepSeek使用OpenAI兼容接口
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


def get_provider(name: str, **config):
    """根据名称获取Provider实例

    Args:
        name: Provider名称
        **config: Provider配置参数

    Returns:
        Provider实例

    Raises:
        ValueError: 未知的Provider名称
    """
    provider_cls = PROVIDER_REGISTRY.get(name)
    if not provider_cls:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unknown provider: {name}. Available: {available}"
        )
    return provider_cls(**config)


__all__ = [
    "BaseProvider",
    "ProviderResponse",
    "Message",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
    "PROVIDER_REGISTRY",
    "get_provider",
]
