"""
GovLens application configuration.

Loads settings from environment variables (with .env support via python-dotenv).
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Server
        self.host: str = os.getenv("GOVLENS_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("GOVLENS_PORT", "8000"))

        # Data
        self.data_path: str = os.getenv(
            "GOVLENS_DATA_PATH", "data/sample_contracts.json"
        )

        # LLM
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

        # Chatbot
        self.chat_streaming: bool = os.getenv("CHAT_STREAMING", "false").lower() == "true"
        self.chat_history_backend: str = os.getenv("CHAT_HISTORY_BACKEND", "memory")
        self.chat_cache_backend: str = os.getenv("CHAT_CACHE_BACKEND", "memory")
        self.chat_provenance: bool = os.getenv("CHAT_PROVENANCE", "false").lower() == "true"
        self.chat_cost_tracking: bool = os.getenv("CHAT_COST_TRACKING", "false").lower() == "true"
        self.chat_observability: bool = os.getenv("CHAT_OBSERVABILITY", "false").lower() == "true"
        self.chat_debug: bool = os.getenv("CHAT_DEBUG", "false").lower() == "true"
        self.chat_feature_flags: list = [
            f.strip()
            for f in os.getenv("CHAT_FEATURE_FLAGS", "").split(",")
            if f.strip()
        ]
        self.chat_max_message_length: int = int(os.getenv("CHAT_MAX_MESSAGE_LENGTH", "4000"))

        # Scraper
        self.scraper_pdf_dir: str = os.getenv("SCRAPER_PDF_DIR", "data/pdfs")
        self.scraper_delay: float = float(os.getenv("SCRAPER_DELAY", "0.5"))

        # Force mock provider when key is not configured
        if self.llm_provider != "mock" and not self._has_api_key():
            logger.warning(
                "LLM_PROVIDER=%s but no API key configured — forcing mock",
                self.llm_provider,
            )
            self.llm_provider = "mock"

    def _has_api_key(self) -> bool:
        """Check if the required API key for the provider is set."""
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider in ("anthropic", "claude"):
            return bool(self.anthropic_api_key)
        return False

    @property
    def is_degraded(self) -> bool:
        """True when running in mock/degraded mode (no real LLM)."""
        return self.llm_provider == "mock"

    @property
    def active_features(self) -> list:
        """List of active chatbot features."""
        features = []
        if self.chat_streaming:
            features.append("streaming")
        if self.chat_provenance:
            features.append("provenance")
        if self.chat_cost_tracking:
            features.append("cost_tracking")
        if self.chat_observability:
            features.append("observability")
        features.extend(self.chat_feature_flags)
        return list(set(features))


settings = Settings()
