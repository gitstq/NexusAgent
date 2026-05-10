"""
工具注册中心

提供可扩展的工具注册、发现和调用机制。
"""

import json
import inspect
from typing import Callable, Dict, List, Optional, Any


class ToolResult:
    """工具执行结果

    Attributes:
        output: 输出文本
        success: 是否执行成功
        error: 错误信息（如果有）
        metadata: 额外元数据
    """

    def __init__(
        self,
        output: str = "",
        success: bool = True,
        error: str = "",
        metadata: Dict = None,
    ):
        self.output = output
        self.success = success
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {"output": self.output, "success": self.success}
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def __str__(self):
        if self.success:
            return self.output
        return f"Error: {self.error}\n{self.output}"

    def __repr__(self):
        return f"ToolResult(success={self.success}, output={self.output[:50]!r})"


class Tool:
    """工具定义

    封装一个可被Agent调用的工具，包含名称、描述、参数定义和执行函数。

    Attributes:
        name: 工具名称
        description: 工具描述
        parameters: JSON Schema格式的参数定义
        function: 执行函数
        category: 工具分类
    """

    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: Dict = None,
        category: str = "general",
    ):
        """初始化工具

        Args:
            name: 工具名称（唯一标识）
            description: 工具功能描述（供LLM理解）
            function: 工具执行函数
            parameters: JSON Schema格式的参数定义
            category: 工具分类
        """
        self.name = name
        self.description = description
        self.function = function
        self.parameters = parameters or {
            "type": "object",
            "properties": {},
            "required": [],
        }
        self.category = category

    def execute(self, **kwargs) -> ToolResult:
        """执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult执行结果
        """
        try:
            # 检查必需参数
            required = self.parameters.get("required", [])
            for param in required:
                if param not in kwargs:
                    return ToolResult(
                        output="",
                        success=False,
                        error=f"Missing required parameter: {param}",
                    )

            # 调用执行函数
            result = self.function(**kwargs)

            # 如果返回的不是ToolResult，自动包装
            if isinstance(result, ToolResult):
                return result
            elif isinstance(result, dict):
                return ToolResult(
                    output=json.dumps(result, ensure_ascii=False, indent=2),
                    success=True,
                )
            elif isinstance(result, str):
                return ToolResult(output=result, success=True)
            else:
                return ToolResult(output=str(result), success=True)

        except Exception as e:
            return ToolResult(
                output="",
                success=False,
                error=f"{type(e).__name__}: {e}",
            )

    def to_openai_schema(self) -> Dict:
        """转换为OpenAI function calling格式的工具定义

        Returns:
            OpenAI格式的工具定义字典
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self):
        return f"Tool(name={self.name!r}, category={self.category!r})"


class ToolRegistry:
    """工具注册中心

    管理所有可用工具的注册、查找和调用。

    Attributes:
        tools: 已注册的工具字典
    """

    def __init__(self):
        """初始化工具注册中心"""
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具

        Args:
            tool: Tool实例

        Raises:
            ValueError: 工具名称已存在
        """
        if tool.name in self.tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self.tools[tool.name] = tool

    def register_function(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: Dict = None,
        category: str = "general",
    ):
        """通过函数直接注册工具

        Args:
            name: 工具名称
            description: 工具描述
            function: 执行函数
            parameters: 参数定义
            category: 工具分类
        """
        tool = Tool(
            name=name,
            description=description,
            function=function,
            parameters=parameters,
            category=category,
        )
        self.register(tool)

    def unregister(self, name: str) -> bool:
        """取消注册工具

        Args:
            name: 工具名称

        Returns:
            是否成功取消
        """
        if name in self.tools:
            del self.tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        """获取工具

        Args:
            name: 工具名称

        Returns:
            Tool实例，未找到返回None
        """
        return self.tools.get(name)

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """执行工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            ToolResult执行结果
        """
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                output="",
                success=False,
                error=f"Unknown tool: {name}",
            )
        return tool.execute(**kwargs)

    def list_tools(self, category: str = None) -> List[Tool]:
        """列出所有工具

        Args:
            category: 按分类过滤

        Returns:
            工具列表
        """
        tools = list(self.tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_tool_schemas(self) -> List[Dict]:
        """获取所有工具的OpenAI格式schema

        Returns:
            工具schema列表
        """
        return [tool.to_openai_schema() for tool in self.tools.values()]

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称

        Returns:
            工具名称列表
        """
        return list(self.tools.keys())

    def get_categories(self) -> List[str]:
        """获取所有工具分类

        Returns:
            分类列表
        """
        categories = set()
        for tool in self.tools.values():
            categories.add(tool.category)
        return sorted(categories)

    def __len__(self):
        return len(self.tools)

    def __contains__(self, name: str) -> bool:
        return name in self.tools

    def __repr__(self):
        return f"ToolRegistry(tools={len(self.tools)})"
