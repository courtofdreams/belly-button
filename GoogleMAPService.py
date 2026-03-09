



from unicodedata import name
from urllib import response
import requests

class GoogleMAPService:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_location(self, address):
        # Code to call Google Maps API and return location data
        pass

    def get_restaurants(self, origin, latitude, longitude, radius=500):
        payload = {
            "includedTypes": ["restaurant"],
            "maxResultCount": 10,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.rating,places.reviews,places.id"
        }
        url = "https://places.googleapis.com/v1/places:searchNearby"
        response = requests.post(url, json=payload, headers=headers)
        restaurants = response.json().get('places', [])
        
        for place in restaurants:
            name = place.get('displayName', {}).get('text')
            rating = place.get('rating', 'N/A')
            
            print(f"--- {name} ({rating} stars) ---")
            
            # Print the first review if it exists
            reviews = place.get('reviews', [])
            if reviews:
                print(f"Top Review: {reviews[0].get('text', {}).get('text')[:100]}...")

        return restaurants