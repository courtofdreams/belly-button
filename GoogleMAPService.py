



from unicodedata import name
from urllib import response
import requests

class GoogleMAPService:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_location(self, address):
        # Code to call Google Maps API and return location data
        pass

    def price_level_to_dollar_signs(self, price_level):
        if price_level == "PRICE_LEVEL_UNSPECIFIED":
            return "N/A"
        elif price_level == "PRICE_LEVEL_FREE":
            return "Free"
        elif price_level == "PRICE_LEVEL_INEXPENSIVE":
            return "$"
        elif price_level == "PRICE_LEVEL_MODERATE":
            return "$$"
        elif price_level == "PRICE_LEVEL_EXPENSIVE":
            return "$$$"
        elif price_level == "PRICE_LEVEL_VERY_EXPENSIVE":
            return "$$$$"
        else:
            return "N/A"
                
    def get_restaurants(self, latitude, longitude, radius=1000) -> dict:
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
            "X-Goog-FieldMask": "places.displayName,places.rating,places.reviews,places.id,places.userRatingCount,places.formattedAddress,places.location,places.reviewSummary,places.priceLevel,places.googleMapsTypeLabel"
        }
        url = "https://places.googleapis.com/v1/places:searchNearby"
        response = requests.post(url, json=payload, headers=headers)
        restaurants = response.json().get('places', [])
        results = {}
        
        for place in restaurants:
            name = place.get('displayName', {}).get('text')            
            placeId = place.get('id')
            rating = place.get('rating', 'N/A')
            userRatingCount = place.get('userRatingCount', 0)
            typeLabel = place.get('googleMapsTypeLabel', { "text": "N/A" })
            
            print(f"--- {name} ({rating} stars) ---")
            
            # Print the first review if it exists
            reviews = []
            
            for review in place.get('reviews', []):
                reviews.append({
                    "rating": review.get('rating', 'N/A'),
                    "text": review.get('text', {}).get('text', '')
                })
            
            results[placeId] = {
                "name": name,
                "place_id": placeId,
                "rating": rating,
                "userRatingCount": userRatingCount,
                "reviews": reviews,
                "reviewSummary": place.get('reviewSummary', "N/A"),
                "location": place.get('location', None),
                "formattedAddress": place.get('formattedAddress', "N/A"),
                "priceLevel": self.price_level_to_dollar_signs(place.get('priceLevel', "N/A")),
                "typeLabel": typeLabel.get('text', "N/A")
            }   

        return results