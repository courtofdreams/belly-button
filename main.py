import os
from services.OpenAIService import OpenAIService
from services.GoogleService import GoogleService
from services.YelpService import YelpService
from services.RedditService import RedditService
from config import Settings
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = Settings()
google = GoogleService(settings.GOOGLE_MAPS_API_KEY)
openai = OpenAIService(settings.OPENAI_API_KEY)
yelp = YelpService(settings.YELP_API_KEY)
reddit = RedditService(
    reddit_client_id=settings.REDDIT_CLIENT_ID,
    reddit_client_secret=settings.REDDIT_CLIENT_SECRET,
    reddit_username=settings.REDDIT_USERNAME,
    reddit_password=settings.REDDIT_PASSWORD,
    anthropic_api_key=settings.ANTHROPIC_API_KEY
)

app = FastAPI(
    title="Belly Button API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/api/health')
def health_check():
    return {"status": "ok"}


@app.get('/api/recommendation')
def get_recommendation(keyword: str):
    google_places_data = google.run_pipeline(keyword)
    yelp_data = yelp.run_pipeline(keyword)
    reddit_data = reddit.run_pipeline(keyword)
    recommended_restaurants = openai.recommend_restaurants(
        google_places_data=google_places_data,
        yelp_llm_context=yelp_data,
        reddit_llm_context=reddit_data,  
    )
    
    enriched_recommendations = google.enrich_openai_results(recommended_restaurants)
    
    return {"result": enriched_recommendations}


def run():
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, env_file='.env')


