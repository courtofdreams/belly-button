
import logging
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_MAPS_API_KEY: str
    OPENAI_API_KEY: str
    YELP_API_KEY: str
    ANTHROPIC_API_KEY: str
    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    REDDIT_USERNAME: str
    REDDIT_PASSWORD: str
    REDDIT_REDIRECT_URI: str
    
    class Config:
        env_file = ".env"

settings = Settings()