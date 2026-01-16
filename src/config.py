"""Configuration settings."""
import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
API_TRACES_INSTRUMENTATION_KEY = os.getenv("API_TRACES_INSTRUMENTATION_KEY")
# Use OTEL_EXPORTER_OTLP_ENDPOINT if available, otherwise fallback to ASPIRE_OTLP_ENDPOINT
ASPIRE_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("ASPIRE_OTLP_ENDPOINT", "http://smith-dashboard:18889")

# Rate limiting configuration
# Minimum interval in seconds between OpenAI API calls (default: 1.0 second)
RATE_LIMIT_INTERVAL_SECONDS = float(os.getenv("RATE_LIMIT_INTERVAL_SECONDS", "1.0"))