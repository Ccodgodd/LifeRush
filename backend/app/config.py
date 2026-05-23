import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

LOCAL_APP_DIR = Path(os.getenv("LOCALAPPDATA", Path.cwd())) / "LifeRushAI"
LOCAL_APP_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = LOCAL_APP_DIR / "lifrush.db"

class Settings(BaseSettings):
    # Core settings
    PROJECT_NAME: str = Field(default="LifeRush AI")
    DEBUG: bool = Field(default=False)
    # API
    API_V1_STR: str = Field(default="/api/v1")
    # Database
    DATABASE_URL: str = Field(default=f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")
    UPLOAD_DIR: str = Field(default="uploads")
    # JWT
    JWT_SECRET_KEY: str = Field(default="supersecretjwtkey")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    # API Keys
    GOOGLE_MAPS_API_KEY: str = Field(default="YOUR_GOOGLE_MAPS_API_KEY")
    OPENAI_API_KEY: str = Field(default="YOUR_OPENAI_API_KEY")
    SENDGRID_API_KEY: str = Field(default="YOUR_SENDGRID_API_KEY")
    TWILIO_ACCOUNT_SID: str = Field(default="YOUR_TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = Field(default="YOUR_TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER: str = Field(default="+1234567890")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
