"""Central settings for Fibi.

Keep model and timeout choices here so speed tuning is easy.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

PROJECT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PROJECT_DIR.parent
CONFIG_PATH = PROJECT_DIR / "config.json"
if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"
OLLAMA_MODEL_FALLBACKS = ["qwen2.5:3b", "qwen3:4b", "qwen3:8b"]
OLLAMA_TIMEOUT_SECONDS = 8

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = "nvidia/nemotron-mini-4b-instruct"
NVIDIA_TIMEOUT_SECONDS = 8
NVIDIA_MAX_TOKENS = 60
NVIDIA_TEMPERATURE = 0.7
FIBI_ALLOW_NVIDIA = False
CLOUD_PROVIDER = "disabled"
CLOUD_API_KEY = ""
CLOUD_BASE_URL = ""
CLOUD_MODEL = ""
CLOUD_TIMEOUT_SECONDS = 8
FIBI_PROVIDER = "ollama"
GEMINI_API_KEY = ""
FIBI_GEMINI_MODEL = ""
FIBI_GEMINI_TIMEOUT_SECONDS = 25
FIBI_GEMINI_FALLBACK_TO_OLLAMA = True
FIBI_GEMINI_STREAMING = False
FIBI_CLOUD_CONTEXT_PREVIEW = True


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


CONFIG = _load_config()

OLLAMA_URL = str(CONFIG.get("ollama_url", OLLAMA_URL)).rstrip("/")
OLLAMA_MODEL = str(CONFIG.get("ollama_model", CONFIG.get("fast_model", OLLAMA_MODEL)))
OLLAMA_TIMEOUT_SECONDS = int(CONFIG.get("ollama_timeout_seconds", OLLAMA_TIMEOUT_SECONDS))

NVIDIA_BASE_URL = str(os.getenv("NVIDIA_BASE_URL", CONFIG.get("nvidia_base_url", NVIDIA_BASE_URL))).rstrip("/")
NVIDIA_MODEL = str(os.getenv("NVIDIA_MODEL", CONFIG.get("nvidia_model", NVIDIA_MODEL)))
NVIDIA_TIMEOUT_SECONDS = int(os.getenv("NVIDIA_TIMEOUT_SECONDS", CONFIG.get("nvidia_timeout_seconds", NVIDIA_TIMEOUT_SECONDS)))
NVIDIA_MAX_TOKENS = int(os.getenv("NVIDIA_MAX_TOKENS", CONFIG.get("nvidia_max_tokens", NVIDIA_MAX_TOKENS)))
NVIDIA_TEMPERATURE = float(os.getenv("NVIDIA_TEMPERATURE", CONFIG.get("nvidia_temperature", NVIDIA_TEMPERATURE)))
FIBI_ALLOW_NVIDIA = str(os.getenv("FIBI_ALLOW_NVIDIA", CONFIG.get("fibi_allow_nvidia", FIBI_ALLOW_NVIDIA))).lower() in {"1", "true", "yes", "on"}
CLOUD_PROVIDER = str(os.getenv("CLOUD_PROVIDER", CONFIG.get("cloud_provider", CLOUD_PROVIDER))).lower()
CLOUD_API_KEY = str(os.getenv("CLOUD_API_KEY", CONFIG.get("cloud_api_key", CLOUD_API_KEY)))
CLOUD_BASE_URL = str(os.getenv("CLOUD_BASE_URL", CONFIG.get("cloud_base_url", CLOUD_BASE_URL))).rstrip("/")
CLOUD_MODEL = str(os.getenv("CLOUD_MODEL", CONFIG.get("cloud_model", CLOUD_MODEL)))
CLOUD_TIMEOUT_SECONDS = int(os.getenv("CLOUD_TIMEOUT_SECONDS", CONFIG.get("cloud_timeout_seconds", CLOUD_TIMEOUT_SECONDS)))
FIBI_PROVIDER = str(os.getenv("FIBI_PROVIDER", FIBI_PROVIDER)).strip().lower()
GEMINI_API_KEY = str(os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)).strip()
FIBI_GEMINI_MODEL = str(os.getenv("FIBI_GEMINI_MODEL", FIBI_GEMINI_MODEL)).strip()
FIBI_GEMINI_TIMEOUT_SECONDS = int(os.getenv("FIBI_GEMINI_TIMEOUT_SECONDS", FIBI_GEMINI_TIMEOUT_SECONDS))
FIBI_GEMINI_FALLBACK_TO_OLLAMA = str(
    os.getenv("FIBI_GEMINI_FALLBACK_TO_OLLAMA", FIBI_GEMINI_FALLBACK_TO_OLLAMA)
).lower() in {"1", "true", "yes", "on"}
FIBI_GEMINI_STREAMING = str(os.getenv("FIBI_GEMINI_STREAMING", FIBI_GEMINI_STREAMING)).lower() in {"1", "true", "yes", "on"}
FIBI_CLOUD_CONTEXT_PREVIEW = str(os.getenv("FIBI_CLOUD_CONTEXT_PREVIEW", FIBI_CLOUD_CONTEXT_PREVIEW)).lower() in {"1", "true", "yes", "on"}
