from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    transcription_model: str = "gpt-4o-mini-transcribe"
    summary_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NAVAMATN_",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
