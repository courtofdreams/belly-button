import os
from OpenAIService import OpenAIService
from GoogleMAPService import GoogleMAPService
from config import Settings
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = Settings()
Google_MAP_Service = GoogleMAPService(settings.GOOGLE_MAPS_API_KEY)
OpenAIService = OpenAIService(settings.OPENAI_API_KEY)

app = FastAPI(
    title="Belly Button API",
    version="1.0.0",
)

# origins = [
#     "http://localhost:3000",
#     "http://localhost:5173"
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/api/google-places')
def get_google_places(lat: float, lng:float,  radius: int = 1000):
    restaurants = Google_MAP_Service.get_restaurants(lat, lng, radius=radius)
    return restaurants

@app.get('/api/health')
def health_check():
    return {"status": "ok"}

@app.get('/api/restaurants-recommendation')
def get_restaurants_recommendation(lat: float, lng: float, radius: int = 1000):
    restaurants = Google_MAP_Service.get_restaurants(lat, lng, radius)
    recommended_restaurants = OpenAIService.recommend_restaurants(google_places_data=restaurants)
    return {"result": recommended_restaurants}

def run():
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, env_file='.env')
