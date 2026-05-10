"""
配置管理模块

支持JSON配置文件、环境变量覆盖、多Provider配置。
配置加载优先级: 环境变量 > 命令行参数 > 配置文件 > 默认值
"""

import json
import os
import copy

# 默认配置
DEFAULT_CONFIG = {
    "provider": "openai",
    "providers": {
        "openai": {
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 120,
        },
        "anthropic": {
            "api_key": "",
            "base_url": "https://api.anthropic.com",
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 120,
        },
        "deepseek": {
            "api_key": "",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 120,
        },
        "gemini": {
            "api_key": "",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "model": "gemini-2.0-flash",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 120,
        },
        "ollama": {
            "api_key": "",
            "base_url": "http://localhost:11434",
            "model": "llama3",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 300,
        },
    },
    "agent": {
        "max_iterations": 20,
        "verbose": False,
        "system_prompt": "",
    },
    "sandbox": {
        "enabled": True,
        "timeout": 30,
        "allowed_commands": [],
        "blocked_commands": [
            "rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:",
            "chmod -R 777 /", "chown -R", "> /dev/sda",
            "wget.*|.*sh", "curl.*|.*sh",
        ],
        "working_directory": "",
    },
    "tools": {
        "file_ops": True,
        "shell": True,
        "git_ops": True,
        "web_search": True,
        "code_analysis": True,
    },
    "session": {
        "save_dir": "",
        "auto_save": True,
        "max_history": 100,
        "context_window": 8000,
    },
    "tui": {
        "theme": "dark",
        "syntax_highlight": True,
        "stream_output": True,
    },
}

# 配置文件搜索路径
CONFIG_SEARCH_PATHS = [
    "nexusagent.json",
    "nexusagent.config.json",
    ".nexusagent/config.json",
    os.path.expanduser("~/.nexusagent/config.json"),
    os.path.expanduser("~/.config/nexusagent/config.json"),
]

def _parse_bool(value):
    """将字符串解析为布尔值"""
    if isinstance(value, bool):
        return value
    return value.lower() in ("true", "1", "yes", "on")


# 环境变量映射
ENV_VAR_MAPPING = {
    "NEXUS_PROVIDER": ("provider", str),
    "NEXUS_OPENAI_API_KEY": ("providers.openai.api_key", str),
    "NEXUS_OPENAI_BASE_URL": ("providers.openai.base_url", str),
    "NEXUS_OPENAI_MODEL": ("providers.openai.model", str),
    "NEXUS_ANTHROPIC_API_KEY": ("providers.anthropic.api_key", str),
    "NEXUS_ANTHROPIC_MODEL": ("providers.anthropic.model", str),
    "NEXUS_DEEPSEEK_API_KEY": ("providers.deepseek.api_key", str),
    "NEXUS_DEEPSEEK_MODEL": ("providers.deepseek.model", str),
    "NEXUS_GEMINI_API_KEY": ("providers.gemini.api_key", str),
    "NEXUS_GEMINI_MODEL": ("providers.gemini.model", str),
    "NEXUS_OLLAMA_BASE_URL": ("providers.ollama.base_url", str),
    "NEXUS_OLLAMA_MODEL": ("providers.ollama.model", str),
    "NEXUS_MAX_ITERATIONS": ("agent.max_iterations", int),
    "NEXUS_VERBOSE": ("agent.verbose", _parse_bool),
    "NEXUS_SANDBOX_TIMEOUT": ("sandbox.timeout", int),
    "NEXUS_THEME": ("tui.theme", str),
}


def _deep_get(data, path, default=None):
    """通过点分隔路径获取嵌套字典值

    Args:
        data: 字典数据
        path: 点分隔路径，如 "providers.openai.api_key"
        default: 默认值

    Returns:
        对应路径的值，找不到则返回默认值
    """
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def _deep_set(data, path, value):
    """通过点分隔路径设置嵌套字典值

    Args:
        data: 字典数据
        path: 点分隔路径
        value: 要设置的值
    """
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _deep_merge(base, override):
    """深度合并两个字典，override中的值覆盖base中的值

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的新字典
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class Config:
    """配置管理器

    管理NexusAgent的所有配置，支持多层级配置加载和覆盖。

    Attributes:
        data: 配置数据字典
        config_path: 配置文件路径
    """

    def __init__(self, config_path=None, **overrides):
        """初始化配置管理器

        Args:
            config_path: 指定配置文件路径，为None则自动搜索
            **overrides: 直接覆盖的配置项
        """
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        self.config_path = config_path

        # 加载配置文件
        self._load_config_file(config_path)

        # 应用环境变量覆盖
        self._apply_env_vars()

        # 应用直接覆盖
        for key, value in overrides.items():
            if "." in key:
                _deep_set(self.data, key, value)
            elif key in self.data:
                self.data[key] = value

    def _load_config_file(self, config_path=None):
        """从文件加载配置

        Args:
            config_path: 指定路径，为None则搜索默认路径
        """
        paths_to_try = [config_path] if config_path else CONFIG_SEARCH_PATHS

        for path in paths_to_try:
            if path and os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        file_config = json.load(f)
                    self.data = _deep_merge(self.data, file_config)
                    self.config_path = path
                    return
                except (json.JSONDecodeError, IOError) as e:
                    # 静默忽略配置文件读取错误，使用默认配置
                    pass

    def _apply_env_vars(self):
        """应用环境变量覆盖"""
        for env_var, (path, converter) in ENV_VAR_MAPPING.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    _deep_set(self.data, path, converter(value))
                except (ValueError, TypeError):
                    pass

    def get(self, path, default=None):
        """获取配置值

        Args:
            path: 点分隔配置路径
            default: 默认值

        Returns:
            配置值
        """
        return _deep_get(self.data, path, default)

    def set(self, path, value):
        """设置配置值

        Args:
            path: 点分隔配置路径
            value: 配置值
        """
        _deep_set(self.data, path, value)

    @property
    def provider(self):
        """当前激活的Provider名称"""
        return self.data.get("provider", "openai")

    @property
    def provider_config(self):
        """当前激活的Provider配置"""
        provider_name = self.provider
        providers = self.data.get("providers", {})
        return providers.get(provider_name, {})

    def save(self, path=None):
        """保存配置到文件

        Args:
            path: 保存路径，为None则使用当前配置文件路径
        """
        save_path = path or self.config_path
        if not save_path:
            save_path = "nexusagent.json"

        # 确保目录存在
        dir_path = os.path.dirname(save_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def to_dict(self):
        """返回配置的字典副本"""
        return copy.deepcopy(self.data)

    def __repr__(self):
        return f"Config(provider={self.provider!r}, path={self.config_path!r})"
