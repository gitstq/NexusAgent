#!/usr/bin/env python3
"""
NexusAgent 安装脚本
"""

from setuptools import setup, find_packages

with open("nexusagent/__init__.py", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split('"')[1]
            break
    else:
        version = "0.1.0"

setup(
    name="nexusagent",
    version=version,
    description="Multi-LLM Terminal AI Coding Agent",
    author="NexusAgent Team",
    python_requires=">=3.8",
    packages=find_packages(include=["nexusagent*"]),
    entry_points={
        "console_scripts": [
            "nexusagent=nexusagent.cli:main",
        ],
    },
    install_requires=[],
    extras_require={
        "yaml": ["pyyaml>=6.0"],
        "full": ["pyyaml>=6.0"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Environment :: Console :: Curses",
    ],
)
