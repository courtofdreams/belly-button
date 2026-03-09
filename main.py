import os
from GoogleMAPService import GoogleMAPService
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

GOOGLE_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Define the area (Albany, CA) and type
Google_MAP_Service = GoogleMAPService(GOOGLE_API_KEY)

app = FastAPI(
    title="Google Places API",
    version="1.0.0",
)

@app.get('/api/google-places')
def get_google_places():
    # Example: Get restaurants in Albany, CA
    restaurants = Google_MAP_Service.get_restaurants("Albany, CA", 37.7749, -122.4194, radius=1000)
    return restaurants

def run():
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, env_file='.env')
