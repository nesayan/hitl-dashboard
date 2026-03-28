from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"

    TAVILY_API_KEY: str = ""

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
