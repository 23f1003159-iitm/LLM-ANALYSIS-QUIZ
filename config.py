"""Configuration - Environment variables and constants."""

import os

from dotenv import load_dotenv

load_dotenv()

# API Keys
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# User credentials
SECRET_KEY = os.getenv("SECRET_KEY", "")
EMAIL = os.getenv("EMAIL", "")

# Quiz settings
QUIZ_TIMEOUT = int(os.getenv("QUIZ_TIMEOUT", "170"))  # 3 minutes - buffer
MAX_RETRIES = 1  # Retry once before moving on
