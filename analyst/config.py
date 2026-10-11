"""
config.py
---------
Central settings. Values come from environment variables (or a .env file)
so nothing secret is ever written into the code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

# SQLite database file created by build_database.py
DB_PATH = Path(os.getenv("DB_PATH", PROJECT_ROOT / "data" / "ecommerce.db"))

# Synthetic data with planted anomalies, loaded on top of the API data
SEED_SQL_PATH = PROJECT_ROOT / "data" / "seed_data.sql"

# Public API used for the extract step
API_BASE_URL = "https://dummyjson.com"
API_TIMEOUT_SECONDS = 10

# Record limits per endpoint. Carts stop at 20 because the seed file
# uses cart IDs 21 to 60.
API_LIMITS = {"products": 100, "carts": 20, "users": 100}

# LLM settings. The AI write-up is optional: without a key the app still
# runs every query and shows the results table.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "600"))

# Rows sent to the LLM are capped to keep prompts small and cheap
LLM_MAX_ROWS = 50
