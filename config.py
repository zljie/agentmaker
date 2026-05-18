"""
配置管理
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 加载 .env 文件（如果存在）
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# 服务器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5011"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# LLM 配置 (从环境变量读取)
LLM_CONFIG = {
    "model_name": os.getenv("LLM_MODEL_NAME", "deepseek-chat"),
    "api_key": os.getenv("LLM_API_KEY", ""),
    "api_base": os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1"),
    "temperature": 0.7,
    "max_tokens": 4096,
}

# 检查 LLM API Key
if not LLM_CONFIG["api_key"]:
    print("=" * 60)
    print("WARNING: LLM_API_KEY is not set!")
    print("Please set LLM_API_KEY in .env or environment variable.")
    print("Currently running in MOCK mode.")
    print("=" * 60)

# AgentScope 配置
AGENTSCOPE_CONFIG = {
    "max_iters": 10,
    "stream": True,
}
