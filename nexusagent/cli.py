"""
CLI入口模块

提供命令行参数解析和程序入口。
"""

import argparse
import sys
import os
import json

from nexusagent import __version__
from nexusagent.config import Config
from nexusagent.agent import NexusAgent
from nexusagent.session import Session
from nexusagent.utils import format_timestamp


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器

    Returns:
        ArgumentParser实例
    """
    parser = argparse.ArgumentParser(
        prog="nexusagent",
        description="NexusAgent - Multi-LLM Terminal AI Coding Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nexusagent                              # Start interactive TUI
  nexusagent --provider ollama            # Use Ollama local model
  nexusagent --provider deepseek          # Use DeepSeek
  nexusagent --model gpt-4o               # Specify model
  nexusagent --config myconfig.json       # Use custom config
  nexusagent --prompt "Hello"             # One-shot query
  nexusagent --non-interactive            # Simple REPL mode
  nexusagent --init                       # Create default config

Provider options:
  --provider openai      OpenAI (default)
  --provider anthropic   Anthropic Claude
  --provider deepseek    DeepSeek
  --provider gemini      Google Gemini
  --provider ollama      Ollama (local)
        """,
    )

    # 基本选项
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"NexusAgent v{__version__}",
    )
    parser.add_argument(
        "-c", "--config",
        type=str, default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create a default configuration file and exit",
    )

    # Provider选项
    parser.add_argument(
        "-p", "--provider",
        type=str, default=None,
        choices=["openai", "anthropic", "deepseek", "gemini", "ollama"],
        help="LLM provider to use",
    )
    parser.add_argument(
        "-m", "--model",
        type=str, default=None,
        help="Model name to use",
    )
    parser.add_argument(
        "--api-key",
        type=str, default=None,
        help="API key (or set NEXUS_<PROVIDER>_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        type=str, default=None,
        help="Custom API base URL",
    )

    # 运行模式
    parser.add_argument(
        "--non-interactive", "-n",
        action="store_true",
        help="Run in non-interactive (simple REPL) mode",
    )
    parser.add_argument(
        "--prompt",
        type=str, default=None,
        help="One-shot prompt (non-interactive)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    # Agent选项
    parser.add_argument(
        "--max-iterations",
        type=int, default=None,
        help="Maximum ReAct iterations (default: 20)",
    )
    parser.add_argument(
        "--no-sandbox",
        action="store_true",
        help="Disable sandbox security checks",
    )
    parser.add_argument(
        "--timeout",
        type=int, default=None,
        help="Shell command timeout in seconds (default: 30)",
    )

    # 会话选项
    parser.add_argument(
        "--session",
        type=str, default=None,
        help="Session ID to resume",
    )
    parser.add_argument(
        "--save-dir",
        type=str, default=None,
        help="Session save directory",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List saved sessions and exit",
    )

    # TUI选项
    parser.add_argument(
        "--theme",
        type=str, default=None,
        choices=["dark", "light", "mono"],
        help="TUI color theme",
    )

    return parser


def create_default_config(path: str = "nexusagent.json"):
    """创建默认配置文件

    Args:
        path: 配置文件路径
    """
    config = Config()
    config.save(path)
    print(f"Default configuration created: {path}")
    print("\nEdit the file to configure your API keys and preferences.")
    print("You can also use environment variables:")
    print("  NEXUS_OPENAI_API_KEY    - OpenAI API key")
    print("  NEXUS_ANTHROPIC_API_KEY - Anthropic API key")
    print("  NEXUS_DEEPSEEK_API_KEY  - DeepSeek API key")
    print("  NEXUS_GEMINI_API_KEY    - Google Gemini API key")
    print("  NEXUS_PROVIDER          - Default provider")


def list_sessions(save_dir: str = None):
    """列出保存的会话

    Args:
        save_dir: 会话目录
    """
    sessions = Session.list_sessions(save_dir)

    if not sessions:
        print("No saved sessions found.")
        return

    print(f"Found {len(sessions)} session(s):\n")
    print(f"{'ID':<20} {'Title':<30} {'Messages':<10} {'Updated'}")
    print("-" * 80)

    for sess in sessions:
        sid = sess["session_id"][-12:]
        title = sess["title"][:28]
        count = str(sess["message_count"])
        updated = format_timestamp(sess["updated_at"])
        print(f"{sid:<20} {title:<30} {count:<10} {updated}")


def run_interactive_repl(agent: NexusAgent):
    """运行交互式REPL（非TUI模式）

    Args:
        agent: NexusAgent实例
    """
    print("\nNexusAgent Interactive REPL")
    print("Type 'exit' or 'quit' to exit, '/help' for commands.\n")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # 处理命令
        if user_input.lower() in ("exit", "quit", "/quit"):
            print("Goodbye!")
            break
        elif user_input == "/help":
            print("Commands: /help, /status, /reset, /clear, /save, exit, quit")
            continue
        elif user_input == "/status":
            status = agent.get_status()
            print(f"Provider: {status['provider']}/{status['model']}")
            print(f"Context: {status['context']}")
            print(f"Tools: {', '.join(status['tools'])}")
            continue
        elif user_input == "/reset":
            agent.reset()
            print("Context reset.")
            continue
        elif user_input == "/save":
            agent.session.save()
            print(f"Session saved: {agent.session.session_id}")
            continue
        elif user_input == "/clear":
            print("\n" * 2)
            continue

        # 处理对话
        try:
            response = agent.chat(user_input)
            print(f"\nAgent> {response}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


def run_one_shot(agent: NexusAgent, prompt: str):
    """运行单次查询

    Args:
        agent: NexusAgent实例
        prompt: 用户提示
    """
    try:
        response = agent.chat(prompt)
        print(response)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main(argv=None):
    """程序主入口

    Args:
        argv: 命令行参数（为None则使用sys.argv）
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # 创建默认配置
    if args.init:
        config_path = args.config or "nexusagent.json"
        create_default_config(config_path)
        return 0

    # 列出会话
    if args.list_sessions:
        list_sessions(args.save_dir)
        return 0

    # 加载配置
    config_overrides = {}
    if args.provider:
        config_overrides["provider"] = args.provider
    if args.model:
        config_overrides[f"providers.{args.provider}.model"] = args.model if args.provider else f"providers.openai.model"
    if args.api_key:
        provider = args.provider or "openai"
        config_overrides[f"providers.{provider}.api_key"] = args.api_key
    if args.base_url:
        provider = args.provider or "openai"
        config_overrides[f"providers.{provider}.base_url"] = args.base_url
    if args.max_iterations:
        config_overrides["agent.max_iterations"] = args.max_iterations
    if args.no_sandbox:
        config_overrides["sandbox.enabled"] = False
    if args.timeout:
        config_overrides["sandbox.timeout"] = args.timeout
    if args.verbose:
        config_overrides["agent.verbose"] = True
    if args.theme:
        config_overrides["tui.theme"] = args.theme
    if args.save_dir:
        config_overrides["session.save_dir"] = args.save_dir

    config = Config(config_path=args.config, **config_overrides)

    # 创建或加载会话
    session = None
    if args.session:
        session = Session(session_id=args.session, save_dir=config.get("session.save_dir", ""))
        if not session.load(args.session):
            print(f"Warning: Could not load session {args.session}", file=sys.stderr)
            session = None

    # 创建Agent
    agent = NexusAgent(config=config, session=session, verbose=args.verbose)

    # 单次查询模式
    if args.prompt:
        run_one_shot(agent, args.prompt)
        return 0

    # 非交互式REPL模式
    if args.non_interactive:
        run_interactive_repl(agent)
        return 0

    # TUI模式（默认）
    try:
        from nexusagent.tui.app import TUIApp

        theme_name = config.get("tui.theme", "dark")
        app = TUIApp(agent=agent, config=config, theme_name=theme_name)
        app.run()
    except ImportError as e:
        print(f"Warning: TUI not available ({e}), falling back to REPL mode.", file=sys.stderr)
        run_interactive_repl(agent)
    except Exception as e:
        print(f"Error starting TUI: {e}", file=sys.stderr)
        print("Falling back to REPL mode.", file=sys.stderr)
        run_interactive_repl(agent)

    return 0


if __name__ == "__main__":
    sys.exit(main())
