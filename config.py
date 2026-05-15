"""
配置管理
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 服务器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5001"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# LLM 配置 (从环境变量读取)
LLM_CONFIG = {
    "model_name": os.getenv("LLM_MODEL_NAME", "deepseek-chat"),
    "api_key": os.getenv("LLM_API_KEY", ""),
    "api_base": os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1"),
    "temperature": 0.7,
    "max_tokens": 4096,
}

# AgentScope 配置
AGENTSCOPE_CONFIG = {
    "max_iters": 10,
    "stream": True,
}
