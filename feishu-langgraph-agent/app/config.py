"""
Configuration — loaded from .env via pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Feishu
    feishu_app_id: str
    feishu_app_secret: str

    # LLM (OpenAI-compatible)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str
    llm_model: str = "gpt-4o"

    # Agent
    system_prompt: str = (
        "You are a helpful AI assistant integrated with Feishu. "
        "You can read and write Feishu documents and send messages. "
        "Always respond in the same language the user writes in."
    )


settings = Settings()
