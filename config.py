"""Configuration management — loads API keys and paths from .env."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

# Project paths
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# Product Hunt
PHUNT_API_TOKEN = os.getenv("PHUNT_API_TOKEN", "")

# MiMo LLM
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "")

# MiMo TTS
MIMO_TTS_API_KEY = os.getenv("MIMO_TTS_API_KEY", "")
MIMO_TTS_BASE_URL = os.getenv("MIMO_TTS_BASE_URL", "")

# 通义万相
TONGYI_API_KEY = os.getenv("TONGYI_API_KEY", "")


def validate_config():
    """Check that all required API keys are set."""
    missing = []
    if not PHUNT_API_TOKEN:
        missing.append("PHUNT_API_TOKEN")
    if not MIMO_API_KEY:
        missing.append("MIMO_API_KEY")
    if not MIMO_BASE_URL:
        missing.append("MIMO_BASE_URL")
    if not TONGYI_API_KEY:
        missing.append("TONGYI_API_KEY")
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}\nCopy .env.example to .env and fill in your API keys.")