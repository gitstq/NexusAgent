"""
NexusAgent - 多LLM终端AI编程智能体

一个纯Python零外部依赖的终端AI编程助手，支持多LLM后端。
"""

__version__ = "0.1.0"
__author__ = "NexusAgent Team"
__description__ = "Multi-LLM Terminal AI Coding Agent"

from nexusagent.agent import NexusAgent
from nexusagent.config import Config
from nexusagent.session import Session

__all__ = ["NexusAgent", "Config", "Session", "__version__"]
