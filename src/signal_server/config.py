from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    USER_REGION: str = "US_CA"
    ALLOW_POLYMARKET_EXECUTION: bool = False
    ALLOW_US_EXECUTION: bool = True
    IB_HOST: str = "127.0.0.1"
    IB_PORT: int = 4002
    IB_CLIENT_ID: int = 1
    RISK_FREE_RATE: float = 0.045

settings = Settings()
