from pydantic import model_validator
from pydantic_settings import BaseSettings

import logging

APP_PACKAGES = ["modules", "services", "routes", "database", "app", "__main__"]

def setup_logging(level=logging.INFO):
    """Configure logging so only app loggers emit at the given level. Third-party loggers stay at WARNING."""
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)

    # Root logger: WARNING to silence third-party packages
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.addHandler(handler)

    # App loggers: INFO (or whatever level is passed)
    for pkg in APP_PACKAGES:
        pkg_logger = logging.getLogger(pkg)
        pkg_logger.setLevel(level)


class Settings(BaseSettings):
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"

    TAVILY_API_KEY: str = ""

    PORT: int = 80

    model_config = {
        "env_file": "core/.env",
        "env_file_encoding": "utf-8",
    }

    @model_validator(mode="after")
    def check_required_fields(self) -> "Settings":
        missing = [
            name
            for name, field in Settings.model_fields.items()
            if field.default == "" and not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        return self


settings = Settings()
