"""
pytest configuration – sets environment variables before any test module is
imported, so Settings() picks them up at creation time.
"""
import os

# Core test env
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_alhasade_complete.db")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

# Raise rate limits so the full test suite doesn't self-throttle
os.environ["AUTH_RATE_LIMIT"] = "1000/minute"
os.environ["GENERATION_RATE_LIMIT"] = "1000/minute"
