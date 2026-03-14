
import logging
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_MAPS_API_KEY: str
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()