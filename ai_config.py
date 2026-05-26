# AI API Configuration
# ─────────────────────────────────────────────────────────────────────────────
# API keys are loaded from the .env file in the project root.
# Never hardcode keys in this file or commit .env to version control.
#
# To set up:
#   1. Copy .env.example to .env
#   2. Fill in your actual API keys in .env
#
# OpenAI key  → https://platform.openai.com/api-keys
# Gemini key  → https://makersuite.google.com/app/apikey
# ─────────────────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

# Load variables from .env file into environment
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Status print (visible in server log on startup) ──────────────────────────
_openai_ok = OPENAI_API_KEY.startswith("sk-") and len(OPENAI_API_KEY) > 20
_gemini_ok = GEMINI_API_KEY not in ("your-gemini-api-key-here", "") and len(GEMINI_API_KEY) > 20

print("🔑 AI API Keys Configuration Loaded")
print(f"   OpenAI : {'✅ Configured' if _openai_ok else '❌ Not configured'}")
print(f"   Gemini : {'✅ Configured' if _gemini_ok else '❌ Not configured'}")
if _gemini_ok:
    print("   → Gemini will be used for automatic scenario generation")
else:
    print("   → Set GEMINI_API_KEY in .env to enable automatic scenario generation")