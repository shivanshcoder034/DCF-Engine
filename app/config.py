"""Centralized configuration module for the DCF Valuation and Sensitivity Engine.

This module resolves filesystem paths using pathlib relative to the project root,
ensuring configuration does not depend on the current working directory.
Settings can be overridden via environment variables or a local .env file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Attempt to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False


# Root directory of the repository (parent of app/ directory)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
if _DOTENV_AVAILABLE:
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration and filesystem paths."""

    # Application Metadata
    app_name: str = "AI-Powered DCF Valuation and Sensitivity Engine"
    app_short_name: str = "DCF Valuation Engine"
    app_version: str = "0.4.0"
    app_phase: str = "Phase 4: Financial Forecasting & Projections Engine"

    # Environment
    environment: str = field(
        default_factory=lambda: os.getenv("APP_ENV", "development").lower()
    )
    debug: bool = field(
        default_factory=lambda: os.getenv("APP_DEBUG", "True").lower() in ("true", "1", "yes")
    )
    host: str = field(
        default_factory=lambda: os.getenv("APP_HOST", "localhost")
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("APP_PORT", "8501"))
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )

    # Core Directories (all based on PROJECT_ROOT via pathlib)
    project_root: Path = PROJECT_ROOT
    app_dir: Path = PROJECT_ROOT / "app"
    src_dir: Path = PROJECT_ROOT / "src"
    data_dir: Path = PROJECT_ROOT / os.getenv("DATA_DIR", "data")
    database_dir: Path = PROJECT_ROOT / os.getenv("DATABASE_DIR", "database")
    docs_dir: Path = PROJECT_ROOT / os.getenv("DOCS_DIR", "docs")

    # Database Configuration Foundation
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            f"sqlite:///{(PROJECT_ROOT / 'database' / 'dcf_engine.db').as_posix()}"
        )
    )

    def ensure_directories(self) -> None:
        """Ensure all required filesystem directories exist safely."""
        for path in (self.data_dir, self.database_dir, self.docs_dir):
            path.mkdir(parents=True, exist_ok=True)

    def summary(self) -> dict[str, str]:
        """Return a non-sensitive summary of application configuration."""
        return {
            "Application": self.app_name,
            "Version": self.app_version,
            "Phase": self.app_phase,
            "Environment": self.environment,
            "Debug Mode": str(self.debug),
            "Project Root": str(self.project_root),
            "Data Directory": str(self.data_dir),
            "Database Directory": str(self.database_dir),
            "Docs Directory": str(self.docs_dir),
            "Database URL (Type)": self.database_url.split(":")[0] if ":" in self.database_url else "unknown",
        }


# Global settings singleton
settings = AppConfig()

# Ensure directories exist upon importing config
settings.ensure_directories()
