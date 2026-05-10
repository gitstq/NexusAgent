<p align="center">
  <a href="#简体中文">简体中文</a> | <a href="#繁體中文">繁體中文</a> | <a href="#english">English</a>
</p>

---

<h1 align="center">
<pre>
 _   _  _   _  ____   ____  ____  _     ___  ____  _____
| | | || \ | ||  _ \ / ___||  _ \| |   / _ \|  _ \|_   _|
| | | ||  \| || | | |\___ \| |_) | |  | | | | |_) | | |
| |_| || |\  || |_| | ___) |  __/| |__| |_| |  _ <  | |
 \___/ |_| \_||____/ |____/|_|   |_____\___/|_| \_\ |_|

   T E R M I N A L   A I   C O D I N G   A G E N T
</pre>
</h1>

<p align="center">
  <strong>Multi-LLM Terminal AI Coding Agent | 多模型终端 AI 编程智能体</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.8+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/dependencies-zero-red" alt="Zero Dependencies">
</p>

---

<a id="简体中文"></a>

# 简体中文

## 🎉 项目介绍

**NexusAgent** 是一款运行在终端中的 AI 编程智能体，支持接入多种大语言模型（LLM），帮助开发者在命令行环境下完成代码编写、文件操作、Git 管理等日常编程任务。

它的核心理念是 **"零依赖、全功能"** —— 整个项目仅使用 Python 标准库实现，无需安装任何第三方包，开箱即用。无论你是使用 OpenAI、Claude、DeepSeek、Gemini，还是完全离线的 Ollama 本地模型，NexusAgent 都能无缝切换，为你提供一致的终端 AI 编程体验。

### 适用场景

- 在终端中快速完成代码编写与调试
- 结合本地模型（Ollama）实现完全离线的 AI 编程助手
- 在服务器等无图形界面的环境中使用 AI 辅助开发
- 需要一个轻量级、可定制的 AI Agent 框架进行二次开发

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **ReAct 推理引擎** | 采用"思考 -> 行动 -> 观察 -> 回答"的循环推理模式，让 AI 能够分步骤解决复杂编程问题 |
| 🛠️ **23 个内置工具** | 涵盖文件读写、Shell 执行、Git 操作、Web 搜索、代码分析等常用编程操作 |
| 🖥️ **curses TUI 终端界面** | 提供精美的终端 UI，支持 3 套主题（暗色/亮色/单色）、流式输出和 Markdown 渲染 |
| 🛡️ **沙箱安全执行** | 内置危险命令拦截（如 `rm -rf /`、Fork 炸弹等）和超时控制，保护系统安全 |
| 💾 **会话持久化** | 对话记录以 JSON 格式保存到本地，支持历史会话的恢复与管理 |
| 📏 **上下文智能管理** | 自动压缩和摘要旧消息，防止上下文窗口溢出，保持对话连贯性 |
| 📦 **零外部依赖** | 纯 Python 标准库实现，无需 `pip install` 任何第三方包 |

### 支持的 LM 提供商

| 提供商 | 模型示例 | 说明 |
|--------|----------|------|
| OpenAI | GPT-4o、GPT-4o-mini | 默认提供商 |
| Anthropic | Claude Sonnet 4、Claude Opus | Anthropic Claude 系列 |
| DeepSeek | DeepSeek Chat、DeepSeek Coder | 国产高性能模型 |
| Google Gemini | Gemini 2.5 Pro | Google 最新模型 |
| Ollama | Llama 3、Qwen 2、CodeLlama | 本地模型，完全免费离线 |

---

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本
- 至少一个 LLM 提供商的 API Key（使用 Ollama 则无需 API Key）

### 安装

```bash
# 方式一：通过 pip 直接从 GitHub 安装
pip install git+https://github.com/gitstq/NexusAgent.git

# 方式二：克隆仓库后以开发模式安装
git clone https://github.com/gitstq/NexusAgent.git
cd NexusAgent
pip install -e .
```

### 三步上手

```bash
# 第一步：初始化配置文件
nexusagent --init

# 第二步：编辑配置文件，填入你的 API Key
# 配置文件路径：当前目录下的 nexusagent.json

# 第三步：启动 NexusAgent
nexusagent --provider openai --api-key sk-xxx
```

如果你想用 **Ollama 本地模型**（完全免费，无需 API Key）：

```bash
# 确保已安装并运行 Ollama（https://ollama.ai）
ollama pull llama3

# 启动 NexusAgent
nexusagent --provider ollama --model llama3
```

---

## 📖 详细使用指南

### 命令行参数

```bash
# 启动 TUI 交互界面（默认模式）
nexusagent

# 指定 LLM 提供商和模型
nexusagent --provider deepseek --api-key your-key --model deepseek-chat
nexusagent --provider anthropic --api-key your-key --model claude-sonnet-4-20250514
nexusagent --provider gemini --api-key your-key --model gemini-2.5-pro

# 单次查询模式（非交互式，适合脚本集成）
nexusagent --prompt "用 Python 写一个快速排序"

# 非 TUI 的 REPL 模式（轻量交互）
nexusagent --non-interactive

# 使用自定义配置文件
nexusagent --config /path/to/myconfig.json

# 指定 TUI 主题（dark / light / mono）
nexusagent --theme light

# 查看版本信息
nexusagent --version
```

### REPL 模式内置命令

在非 TUI 的 REPL 模式下，支持以下斜杠命令：

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/status` | 查看当前 Agent 状态（提供商、模型、上下文使用量等） |
| `/reset` | 清空对话上下文 |
| `/save` | 手动保存当前会话 |
| `/clear` | 清屏 |
| `exit` / `quit` | 退出程序 |

### 环境变量配置

除了命令行参数和配置文件，你还可以通过环境变量设置 API Key：

```bash
export NEXUS_OPENAI_API_KEY=sk-xxx
export NEXUS_ANTHROPIC_API_KEY=sk-ant-xxx
export NEXUS_DEEPSEEK_API_KEY=sk-xxx
export NEXUS_GEMINI_API_KEY=xxx
export NEXUS_PROVIDER=openai
```

### 配置文件详解

运行 `nexusagent --init` 后会生成 `nexusagent.json` 配置文件，完整示例如下：

```json
{
  "provider": "openai",
  "providers": {
    "openai": {
      "model": "gpt-4o",
      "api_key": "",
      "base_url": "https://api.openai.com/v1"
    },
    "anthropic": {
      "model": "claude-sonnet-4-20250514",
      "api_key": ""
    },
    "deepseek": {
      "model": "deepseek-chat",
      "api_key": "",
      "base_url": "https://api.deepseek.com/v1"
    },
    "gemini": {
      "model": "gemini-2.5-pro",
      "api_key": ""
    },
    "ollama": {
      "model": "llama3",
      "base_url": "http://localhost:11434"
    }
  },
  "agent": {
    "max_iterations": 20,
    "verbose": false
  },
  "sandbox": {
    "enabled": true,
    "timeout": 30
  },
  "tui": {
    "theme": "dark"
  }
}
```

**配置项说明：**

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `provider` | 默认 LLM 提供商 | `openai` |
| `providers.*.model` | 各提供商使用的模型 | （见上方示例） |
| `providers.*.api_key` | 各提供商的 API Key | （留空则从环境变量读取） |
| `providers.*.base_url` | 自定义 API 地址（可用于代理或兼容接口） | （见上方示例） |
| `agent.max_iterations` | ReAct 循环最大迭代次数 | `20` |
| `agent.verbose` | 是否输出详细推理日志 | `false` |
| `sandbox.enabled` | 是否启用沙箱安全检查 | `true` |
| `sandbox.timeout` | Shell 命令超时时间（秒） | `30` |
| `tui.theme` | TUI 主题（`dark` / `light` / `mono`） | `dark` |

### 会话管理

```bash
# 列出所有历史会话
nexusagent --list-sessions

# 恢复指定会话
nexusagent --session <session-id>

# 指定会话保存目录
nexusagent --save-dir /path/to/sessions
```

会话数据默认保存在 `~/.nexusagent/sessions/` 目录下，每个会话为一个 JSON 文件，包含完整的对话历史和上下文信息。

---

## 💡 设计思路与迭代规划

### 架构设计

NexusAgent 的核心架构围绕 **ReAct（Reasoning + Acting）** 范式构建：

```
用户输入
  |
  v
[上下文管理器] -- 管理对话历史和 token 预算
  |
  v
[LLM Provider] -- 统一接口适配多模型后端
  |
  v
[ReAct 循环] -- 思考 -> 行动 -> 观察 -> 回答
  |                    |
  |                    v
  |              [工具注册中心] -- 23 个内置工具
  |                    |
  |                    v
  |              [沙箱执行环境] -- 安全检查 + 超时控制
  |
  v
最终回答 + 会话持久化
```

### 设计原则

1. **零依赖优先**：仅使用 Python 标准库，降低安装门槛，提高可移植性
2. **安全第一**：沙箱机制默认开启，危险命令自动拦截
3. **可扩展性**：工具注册中心支持自定义工具的动态注册
4. **渐进式体验**：从简单的 REPL 到功能完整的 TUI，按需选择

### 迭代规划

- [x] v0.1.0 - 核心功能：ReAct 引擎、5 大类工具、TUI 界面、沙箱安全
- [ ] v0.2.0 - 增强体验：MCP 协议支持、更多工具、会话搜索
- [ ] v0.3.0 - 生态扩展：插件系统、工具市场、多 Agent 协作
- [ ] v1.0.0 - 稳定发布：完善文档、性能优化、全面测试覆盖

---

## 📦 打包与部署指南

### 本地开发安装

```bash
git clone https://github.com/gitstq/NexusAgent.git
cd NexusAgent
pip install -e .

# 验证安装
nexusagent --version
```

### 构建 Distribution 包

```bash
# 安装构建工具
pip install build

# 构建 sdist 和 wheel
python -m build

# 构建产物位于 dist/ 目录
ls dist/
# nexusagent-0.1.0.tar.gz
# nexusagent-0.1.0-py3-none-any.whl
```

### 在服务器上部署

```bash
# 直接安装
pip install git+https://github.com/gitstq/NexusAgent.git

# 或上传 wheel 包后离线安装
pip install nexusagent-0.1.0-py3-none-any.whl
```

### 使用 Ollama 实现完全离线部署

```bash
# 1. 安装 Ollama（https://ollama.ai）
# 2. 拉取模型
ollama pull llama3
ollama pull qwen2.5-coder

# 3. 安装 NexusAgent（无需网络，使用本地 wheel 包）
pip install nexusagent-0.1.0-py3-none-any.whl

# 4. 启动
nexusagent --provider ollama --model llama3
```

> 由于 NexusAgent 零外部依赖，wheel 包体积极小，非常适合离线环境部署。

---

## 🤝 贡献指南

欢迎任何形式的贡献！无论是提交 Bug、改进文档，还是贡献新功能。

### 贡献流程

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交改动：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 **Pull Request**

### 开发规范

- 代码风格遵循 PEP 8
- 提交信息建议使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式
- 新增工具需在 `nexusagent/tools/` 目录下创建对应模块，并通过 `ToolRegistry` 注册
- 新增 LLM 提供商需在 `nexusagent/providers/` 目录下创建对应模块，继承 `BaseProvider`
- 确保所有新增代码仅使用 Python 标准库

### 报告问题

如果遇到 Bug 或有功能建议，请在 [Issues](https://github.com/gitstq/NexusAgent/issues) 页面提交。

---

## 📄 开源协议

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

```
MIT License

Copyright (c) 2025 NexusAgent Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

<a id="繁體中文"></a>

# 繁體中文

## 🎉 專案介紹

**NexusAgent** 是一款運行在終端中的 AI 程式設計智慧體，支援接入多種大型語言模型（LLM），協助開發者在命令列環境中完成程式碼撰寫、檔案操作、Git 管理等日常開發任務。

其核心理念是 **「零依賴、全功能」** —— 整個專案僅使用 Python 標準函式庫實作，無須安裝任何第三方套件，開箱即用。無論你使用的是 OpenAI、Claude、DeepSeek、Gemini，還是完全離線的 Ollama 本地模型，NexusAgent 都能無縫切換，提供一致的終端 AI 程式設計體驗。

### 適用場景

- 在終端中快速完成程式碼撰寫與除錯
- 結合本地模型（Ollama）實現完全離線的 AI 程式設計助手
- 在伺服器等無圖形介面的環境中使用 AI 輔助開發
- 需要一個輕量級、可自訂的 AI Agent 框架進行二次開發

---

## ✨ 核心特性

| 特性 | 說明 |
|------|------|
| 🧠 **ReAct 推理引擎** | 採用「思考 -> 行動 -> 觀察 -> 回答」的循環推理模式，讓 AI 能夠分步驟解決複雜程式設計問題 |
| 🛠️ **23 個內建工具** | 涵蓋檔案讀寫、Shell 執行、Git 操作、Web 搜尋、程式碼分析等常用程式設計操作 |
| 🖥️ **curses TUI 終端介面** | 提供精美的終端 UI，支援 3 套主題（暗色/亮色/單色）、串流輸出與 Markdown 渲染 |
| 🛡️ **沙箱安全執行** | 內建危險指令攔截（如 `rm -rf /`、Fork 炸彈等）與逾時控制，保護系統安全 |
| 💾 **會話持久化** | 對話記錄以 JSON 格式儲存至本機，支援歷史會話的復原與管理 |
| 📏 **上下文智慧管理** | 自動壓縮與摘要舊訊息，防止上下文視窗溢出，維持對話連貫性 |
| 📦 **零外部依賴** | 純 Python 標準函式庫實作，無須 `pip install` 任何第三方套件 |

### 支援的 LLM 提供商

| 提供商 | 模型範例 | 說明 |
|--------|----------|------|
| OpenAI | GPT-4o、GPT-4o-mini | 預設提供商 |
| Anthropic | Claude Sonnet 4、Claude Opus | Anthropic Claude 系列 |
| DeepSeek | DeepSeek Chat、DeepSeek Coder | 高效能模型 |
| Google Gemini | Gemini 2.5 Pro | Google 最新模型 |
| Ollama | Llama 3、Qwen 2、CodeLlama | 本地模型，完全免費離線 |

---

## 🚀 快速開始

### 環境需求

- Python 3.8 或以上版本
- 至少一個 LLM 提供商的 API Key（使用 Ollama 則無需 API Key）

### 安裝

```bash
# 方式一：透過 pip 直接從 GitHub 安裝
pip install git+https://github.com/gitstq/NexusAgent.git

# 方式二：複製倉庫後以開發模式安裝
git clone https://github.com/gitstq/NexusAgent.git
cd NexusAgent
pip install -e .
```

### 三步上手

```bash
# 第一步：初始化設定檔
nexusagent --init

# 第二步：編輯設定檔，填入你的 API Key
# 設定檔路徑：當前目錄下的 nexusagent.json

# 第三步：啟動 NexusAgent
nexusagent --provider openai --api-key sk-xxx
```

如果你想使用 **Ollama 本地模型**（完全免費，無需 API Key）：

```bash
# 確保已安裝並執行 Ollama（https://ollama.ai）
ollama pull llama3

# 啟動 NexusAgent
nexusagent --provider ollama --model llama3
```

---

## 📖 詳細使用指南

### 命令列參數

```bash
# 啟動 TUI 互動介面（預設模式）
nexusagent

# 指定 LLM 提供商和模型
nexusagent --provider deepseek --api-key your-key --model deepseek-chat
nexusagent --provider anthropic --api-key your-key --model claude-sonnet-4-20250514
nexusagent --provider gemini --api-key your-key --model gemini-2.5-pro

# 單次查詢模式（非互動式，適合腳本整合）
nexusagent --prompt "用 Python 寫一個快速排序"

# 非 TUI 的 REPL 模式（輕量互動）
nexusagent --non-interactive

# 使用自訂設定檔
nexusagent --config /path/to/myconfig.json

# 指定 TUI 主題（dark / light / mono）
nexusagent --theme light

# 查看版本資訊
nexusagent --version
```

### REPL 模式內建指令

在非 TUI 的 REPL 模式下，支援以下斜線指令：

| 指令 | 說明 |
|------|------|
| `/help` | 顯示說明資訊 |
| `/status` | 查看目前 Agent 狀態（提供商、模型、上下文使用量等） |
| `/reset` | 清空對話上下文 |
| `/save` | 手動儲存目前會話 |
| `/clear` | 清除畫面 |
| `exit` / `quit` | 結束程式 |

### 環境變數設定

除了命令列參數和設定檔，你還可以透過環境變數設定 API Key：

```bash
export NEXUS_OPENAI_API_KEY=sk-xxx
export NEXUS_ANTHROPIC_API_KEY=sk-ant-xxx
export NEXUS_DEEPSEEK_API_KEY=sk-xxx
export NEXUS_GEMINI_API_KEY=xxx
export NEXUS_PROVIDER=openai
```

### 設定檔詳解

執行 `nexusagent --init` 後會產生 `nexusagent.json` 設定檔，完整範例如下：

```json
{
  "provider": "openai",
  "providers": {
    "openai": {
      "model": "gpt-4o",
      "api_key": "",
      "base_url": "https://api.openai.com/v1"
    },
    "anthropic": {
      "model": "claude-sonnet-4-20250514",
      "api_key": ""
    },
    "deepseek": {
      "model": "deepseek-chat",
      "api_key": "",
      "base_url": "https://api.deepseek.com/v1"
    },
    "gemini": {
      "model": "gemini-2.5-pro",
      "api_key": ""
    },
    "ollama": {
      "model": "llama3",
      "base_url": "http://localhost:11434"
    }
  },
  "agent": {
    "max_iterations": 20,
    "verbose": false
  },
  "sandbox": {
    "enabled": true,
    "timeout": 30
  },
  "tui": {
    "theme": "dark"
  }
}
```

**設定項說明：**

| 設定項 | 說明 | 預設值 |
|--------|------|--------|
| `provider` | 預設 LLM 提供商 | `openai` |
| `providers.*.model` | 各提供商使用的模型 | （見上方範例） |
| `providers.*.api_key` | 各提供商的 API Key | （留空則從環境變數讀取） |
| `providers.*.base_url` | 自訂 API 位址（可用於代理或相容介面） | （見上方範例） |
| `agent.max_iterations` | ReAct 迴圈最大迭代次數 | `20` |
| `agent.verbose` | 是否輸出詳細推理日誌 | `false` |
| `sandbox.enabled` | 是否啟用沙箱安全檢查 | `true` |
| `sandbox.timeout` | Shell 指令逾時時間（秒） | `30` |
| `tui.theme` | TUI 主題（`dark` / `light` / `mono`） | `dark` |

### 會話管理

```bash
# 列出所有歷史會話
nexusagent --list-sessions

# 復原指定會話
nexusagent --session <session-id>

# 指定會話儲存目錄
nexusagent --save-dir /path/to/sessions
```

會話資料預設儲存在 `~/.nexusagent/sessions/` 目錄下，每個會話為一個 JSON 檔案，包含完整的對話歷史與上下文資訊。

---

## 💡 設計思路與迭代規劃

### 架構設計

NexusAgent 的核心架構圍繞 **ReAct（Reasoning + Acting）** 範式構建：

```
使用者輸入
  |
  v
[上下文管理器] -- 管理對話歷史和 token 預算
  |
  v
[LLM Provider] -- 統一介面適配多模型後端
  |
  v
[ReAct 迴圈] -- 思考 -> 行動 -> 觀察 -> 回答
  |                    |
  |                    v
  |              [工具註冊中心] -- 23 個內建工具
  |                    |
  |                    v
  |              [沙箱執行環境] -- 安全檢查 + 逾時控制
  |
  v
最終回答 + 會話持久化
```

### 設計原則

1. **零依賴優先**：僅使用 Python 標準函式庫，降低安裝門檻，提高可攜性
2. **安全第一**：沙箱機制預設開啟，危險指令自動攔截
3. **可擴充性**：工具註冊中心支援自訂工具的動態註冊
4. **漸進式體驗**：從簡單的 REPL 到功能完整的 TUI，按需選擇

### 迭代規劃

- [x] v0.1.0 - 核心功能：ReAct 引擎、5 大類工具、TUI 介面、沙箱安全
- [ ] v0.2.0 - 體驗增強：MCP 協議支援、更多工具、會話搜尋
- [ ] v0.3.0 - 生態擴展：外掛系統、工具市集、多 Agent 協作
- [ ] v1.0.0 - 穩定發布：完善文件、效能最佳化、全面測試覆蓋

---

## 📦 打包與部署指南

### 本機開發安裝

```bash
git clone https://github.com/gitstq/NexusAgent.git
cd NexusAgent
pip install -e .

# 驗證安裝
nexusagent --version
```

### 建構 Distribution 套件

```bash
# 安裝建構工具
pip install build

# 建構 sdist 和 wheel
python -m build

# 建構產物位於 dist/ 目錄
ls dist/
# nexusagent-0.1.0.tar.gz
# nexusagent-0.1.0-py3-none-any.whl
```

### 在伺服器上部署

```bash
# 直接安裝
pip install git+https://github.com/gitstq/NexusAgent.git

# 或上傳 wheel 套件後離線安裝
pip install nexusagent-0.1.0-py3-none-any.whl
```

### 使用 Ollama 實現完全離線部署

```bash
# 1. 安裝 Ollama（https://ollama.ai）
# 2. 拉取模型
ollama pull llama3
ollama pull qwen2.5-coder

# 3. 安裝 NexusAgent（無需網路，使用本地 wheel 套件）
pip install nexusagent-0.1.0-py3-none-any.whl

# 4. 啟動
nexusagent --provider ollama --model llama3
```

> 由於 NexusAgent 零外部依賴，wheel 套件體積極小，非常適合離線環境部署。

---

## 🤝 貢獻指南

歡迎任何形式的貢獻！無論是回報 Bug、改善文件，還是貢獻新功能。

### 貢獻流程

1. **Fork** 本倉庫
2. 建立特性分支：`git checkout -b feature/your-feature`
3. 提交變更：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 **Pull Request**

### 開發規範

- 程式碼風格遵循 PEP 8
- 提交訊息建議使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式
- 新增工具需在 `nexusagent/tools/` 目錄下建立對應模組，並透過 `ToolRegistry` 註冊
- 新增 LLM 提供商需在 `nexusagent/providers/` 目錄下建立對應模組，繼承 `BaseProvider`
- 確保所有新增程式碼僅使用 Python 標準函式庫

### 回報問題

如果遇到 Bug 或有功能建議，請在 [Issues](https://github.com/gitstq/NexusAgent/issues) 頁面提交。

---

## 📄 開源協議

本專案基於 [MIT License](https://opensource.org/licenses/MIT) 開源。

```
MIT License

Copyright (c) 2025 NexusAgent Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

<a id="english"></a>

# English

## 🎉 Introduction

**NexusAgent** is a terminal-based AI coding agent that connects to multiple Large Language Models (LLMs), empowering developers to write code, manage files, run Git operations, and handle other everyday programming tasks directly from the command line.

Its core philosophy is **"zero dependencies, full functionality"** -- the entire project is built exclusively with the Python standard library, requiring no third-party packages. Whether you use OpenAI, Claude, DeepSeek, Gemini, or a fully offline Ollama local model, NexusAgent switches seamlessly and delivers a consistent terminal AI coding experience.

### Use Cases

- Rapid code writing and debugging in the terminal
- Building a fully offline AI coding assistant with local models (Ollama)
- AI-assisted development on headless servers and remote environments
- Using NexusAgent as a lightweight, customizable Agent framework for further development

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **ReAct Reasoning Engine** | Employs a "Think -> Act -> Observe -> Answer" loop, enabling the AI to tackle complex programming tasks step by step |
| 🛠️ **23 Built-in Tools** | Covers file I/O, shell execution, Git operations, web search, code analysis, and more |
| 🖥️ **curses TUI Interface** | A polished terminal UI with 3 themes (dark/light/mono), streaming output, and Markdown rendering |
| 🛡️ **Sandbox Execution** | Built-in dangerous command blocking (e.g., `rm -rf /`, fork bombs) and timeout control to keep your system safe |
| 💾 **Session Persistence** | Conversations are saved as JSON files locally, with full support for session history management and restoration |
| 📏 **Smart Context Management** | Automatically compresses and summarizes older messages to prevent context window overflow while maintaining conversation coherence |
| 📦 **Zero External Dependencies** | Implemented entirely with the Python standard library -- no `pip install` of any third-party package required |

### Supported LLM Providers

| Provider | Example Models | Notes |
|----------|---------------|-------|
| OpenAI | GPT-4o, GPT-4o-mini | Default provider |
| Anthropic | Claude Sonnet 4, Claude Opus | Anthropic Claude family |
| DeepSeek | DeepSeek Chat, DeepSeek Coder | High-performance models |
| Google Gemini | Gemini 2.5 Pro | Google's latest models |
| Ollama | Llama 3, Qwen 2, CodeLlama | Local models, completely free and offline |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or later
- An API key for at least one LLM provider (not needed for Ollama)

### Installation

```bash
# Option 1: Install directly from GitHub via pip
pip install git+https://github.com/gitstq/NexusAgent.git

# Option 2: Clone the repo and install in development mode
git clone https://github.com/gitstq/NexusAgent.git
cd NexusAgent
pip install -e .
```

### Up and Running in 3 Steps

```bash
# Step 1: Initialize the configuration file
nexusagent --init

# Step 2: Edit the config file and fill in your API key
# Config file location: nexusagent.json in the current directory

# Step 3: Launch NexusAgent
nexusagent --provider openai --api-key sk-xxx
```

To use **Ollama local models** (completely free, no API key needed):

```bash
# Make sure Ollama is installed and running (https://ollama.ai)
ollama pull llama3

# Launch NexusAgent
nexusagent --provider ollama --model llama3
```

---

## 📖 Detailed Usage Guide

### Command-Line Options

```bash
# Launch the TUI interactive interface (default mode)
nexusagent

# Specify an LLM provider and model
nexusagent --provider deepseek --api-key your-key --model deepseek-chat
nexusagent --provider anthropic --api-key your-key --model claude-sonnet-4-20250514
nexusagent --provider gemini --api-key your-key --model gemini-2.5-pro

# One-shot query mode (non-interactive, ideal for scripting)
nexusagent --prompt "Write a quicksort in Python"

# Non-TUI REPL mode (lightweight interaction)
nexusagent --non-interactive

# Use a custom configuration file
nexusagent --config /path/to/myconfig.json

# Set the TUI theme (dark / light / mono)
nexusagent --theme light

# Show version information
nexusagent --version
```

### Built-in REPL Commands

In non-TUI REPL mode, the following slash commands are available:

| Command | Description |
|---------|-------------|
| `/help` | Display help information |
| `/status` | View current Agent status (provider, model, context usage, etc.) |
| `/reset` | Clear conversation context |
| `/save` | Manually save the current session |
| `/clear` | Clear the screen |
| `exit` / `quit` | Exit the program |

### Environment Variables

In addition to CLI arguments and the config file, you can set API keys via environment variables:

```bash
export NEXUS_OPENAI_API_KEY=sk-xxx
export NEXUS_ANTHROPIC_API_KEY=sk-ant-xxx
export NEXUS_DEEPSEEK_API_KEY=sk-xxx
export NEXUS_GEMINI_API_KEY=xxx
export NEXUS_PROVIDER=openai
```

### Configuration File Reference

Running `nexusagent --init` generates a `nexusagent.json` config file. A full example:

```json
{
  "provider": "openai",
  "providers": {
    "openai": {
      "model": "gpt-4o",
      "api_key": "",
      "base_url": "https://api.openai.com/v1"
    },
    "anthropic": {
      "model": "claude-sonnet-4-20250514",
      "api_key": ""
    },
    "deepseek": {
      "model": "deepseek-chat",
      "api_key": "",
      "base_url": "https://api.deepseek.com/v1"
    },
    "gemini": {
      "model": "gemini-2.5-pro",
      "api_key": ""
    },
    "ollama": {
      "model": "llama3",
      "base_url": "http://localhost:11434"
    }
  },
  "agent": {
    "max_iterations": 20,
    "verbose": false
  },
  "sandbox": {
    "enabled": true,
    "timeout": 30
  },
  "tui": {
    "theme": "dark"
  }
}
```

**Configuration Reference:**

| Key | Description | Default |
|-----|-------------|---------|
| `provider` | Default LLM provider | `openai` |
| `providers.*.model` | Model to use for each provider | (see example above) |
| `providers.*.api_key` | API key for each provider | (leave empty to read from env vars) |
| `providers.*.base_url` | Custom API base URL (for proxies or compatible APIs) | (see example above) |
| `agent.max_iterations` | Maximum ReAct loop iterations | `20` |
| `agent.verbose` | Enable verbose reasoning logs | `false` |
| `sandbox.enabled` | Enable sandbox security checks | `true` |
| `sandbox.timeout` | Shell command timeout in seconds | `30` |
| `tui.theme` | TUI color theme (`dark` / `light` / `mono`) | `dark` |

### Session Management

```bash
# List all saved sessions
nexusagent --list-sessions

# Resume a specific session
nexusagent --session <session-id>

# Specify a custom session save directory
nexusagent --save-dir /path/to/sessions
```

Session data is saved by default in `~/.nexusagent/sessions/`. Each session is stored as a JSON file containing the full conversation history and context.

---

## 💡 Design Philosophy & Roadmap

### Architecture

NexusAgent's core architecture is built around the **ReAct (Reasoning + Acting)** paradigm:

```
User Input
  |
  v
[Context Manager] -- Manages conversation history and token budget
  |
  v
[LLM Provider] -- Unified interface adapting to multiple model backends
  |
  v
[ReAct Loop] -- Think -> Act -> Observe -> Answer
  |                    |
  |                    v
  |              [Tool Registry] -- 23 built-in tools
  |                    |
  |                    v
  |              [Sandbox] -- Safety checks + timeout control
  |
  v
Final Answer + Session Persistence
```

### Design Principles

1. **Zero Dependencies First**: Only the Python standard library is used, minimizing installation friction and maximizing portability
2. **Safety by Default**: The sandbox is enabled by default, automatically blocking dangerous commands
3. **Extensibility**: The tool registry supports dynamic registration of custom tools
4. **Progressive Experience**: Choose from a simple REPL to a full-featured TUI based on your needs

### Roadmap

- [x] v0.1.0 - Core: ReAct engine, 5 tool categories, TUI interface, sandbox security
- [ ] v0.2.0 - Enhanced: MCP protocol support, additional tools, session search
- [ ] v0.3.0 - Ecosystem: Plugin system, tool marketplace, multi-agent collaboration
- [ ] v1.0.0 - Stable: Comprehensive documentation, performance optimization, full test coverage

---

## 📦 Packaging & Deployment

### Local Development Setup

```bash
git clone https://github.com/gitstq/NexusAgent.git
cd NexusAgent
pip install -e .

# Verify installation
nexusagent --version
```

### Building Distribution Packages

```bash
# Install the build tool
pip install build

# Build sdist and wheel
python -m build

# Build artifacts are in the dist/ directory
ls dist/
# nexusagent-0.1.0.tar.gz
# nexusagent-0.1.0-py3-none-any.whl
```

### Deploying to a Server

```bash
# Direct install
pip install git+https://github.com/gitstq/NexusAgent.git

# Or upload the wheel package for offline install
pip install nexusagent-0.1.0-py3-none-any.whl
```

### Fully Offline Deployment with Ollama

```bash
# 1. Install Ollama (https://ollama.ai)
# 2. Pull models
ollama pull llama3
ollama pull qwen2.5-coder

# 3. Install NexusAgent (no internet needed, use local wheel)
pip install nexusagent-0.1.0-py3-none-any.whl

# 4. Launch
nexusagent --provider ollama --model llama3
```

> Thanks to its zero external dependencies, NexusAgent's wheel package is extremely small, making it ideal for air-gapped and offline deployments.

---

## 🤝 Contributing

Contributions of all kinds are welcome -- bug reports, documentation improvements, and new features alike.

### How to Contribute

1. **Fork** this repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push the branch: `git push origin feature/your-feature`
5. Open a **Pull Request**

### Development Guidelines

- Follow PEP 8 for code style
- Use [Conventional Commits](https://www.conventionalcommits.org/) format for commit messages
- New tools should be created as modules under `nexusagent/tools/` and registered via `ToolRegistry`
- New LLM providers should be created under `nexusagent/providers/` inheriting from `BaseProvider`
- All new code must use only the Python standard library

### Reporting Issues

If you encounter a bug or have a feature request, please open an issue on the [Issues](https://github.com/gitstq/NexusAgent/issues) page.

---

## 📄 License

This project is released under the [MIT License](https://opensource.org/licenses/MIT).

```
MIT License

Copyright (c) 2025 NexusAgent Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
