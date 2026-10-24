import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL") or None
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
CODE_EXEC_TIMEOUT = int(os.getenv("CODE_EXEC_TIMEOUT", "15"))

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", ".")).resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
MAX_FIX_ITERATIONS = int(os.getenv("MAX_FIX_ITERATIONS", "3"))

if not API_KEY:
    raise SystemExit(
        "[配置错误] 未检测到 OPENAI_API_KEY。\n"
        "请复制 .env.example 为 .env 并填入你的 API Key。"
    )
