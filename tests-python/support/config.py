"""URLs of the system under test. Override with environment variables."""

import os

API_BASE_URL = os.environ.get("VITE_API_BASE_URL", "http://localhost:8081").rstrip("/")
WEB_BASE_URL = os.environ.get("PLAYWRIGHT_BASE_URL", "http://localhost:5180").rstrip("/")
ADMIN_BASE_URL = os.environ.get("ADMIN_BASE_URL", "http://localhost:5174").rstrip("/")

# Same password as the TS helpers and the JUnit tests.
DEFAULT_PASSWORD = "secret123"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
