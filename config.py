from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv(Path(__file__).resolve().parent / ".env")

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
AGENTS_DIR = ROOT / "agents"
PBIX_PATH = DATA_DIR / "finalbi.pbix"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_NAME = "llama-3.3-70b-versatile"

THRESHOLD_ALERT = 0.10
THRESHOLD_VARIATION = 0.15


if __name__ == "__main__":
    print(f"ROOT={ROOT}")
    print(f"DATA_DIR={DATA_DIR}")
    print(f"OUTPUT_DIR={OUTPUT_DIR}")
