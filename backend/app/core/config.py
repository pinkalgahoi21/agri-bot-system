from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / "model.defaults.env", ROOT / ".env", ROOT / "backend/.env"), extra="ignore", env_ignore_empty=True)
    LLM_PROVIDER: str = "google_genai"
    LLM_MODEL_DEFAULT: str
    LLM_MODEL_ROUTER: str | None = None
    LLM_MODEL_VISION: str | None = None
    LLM_MODEL_REASONING: str | None = None
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT: float = Field(default=60, gt=0)
    LLM_MAX_RETRIES: int = Field(default=3, ge=0, le=8)
    EMBEDDING_PROVIDER: str = "google_genai"
    EMBEDDING_MODEL: str
    GOOGLE_API_KEY: SecretStr | None = None
    STT_PROVIDER: str = "gemini"
    TTS_PROVIDER: str = "gtts"

    def name_for(self, role):
        return getattr(self, "LLM_MODEL_" + role.upper(), None) or self.LLM_MODEL_DEFAULT

    def credentials(self, provider):
        if provider != "google_genai":
            return {}
        if not self.GOOGLE_API_KEY or not self.GOOGLE_API_KEY.get_secret_value():
            raise ValueError("Set GOOGLE_API_KEY before using the Gemini provider.")
        return {"google_api_key": self.GOOGLE_API_KEY.get_secret_value()}


settings = Settings()
