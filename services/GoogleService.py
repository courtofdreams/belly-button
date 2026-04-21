import re
import math
import requests
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

nltk.download("vader_lexicon", quiet=True)

class GoogleService:

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._sia = SentimentIntensityAnalyzer()


    def extract_location(self, query: str) -> str:
        """
        Parse the location out of a natural-language query.
        Looks for 'in <Location>' pattern; falls back to the last word.

        Examples:
            "Best Taco Shop in San Francisco" → "San Francisco"
        """
        match = re.search(r"\bin\s+(.+)$", query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return query.strip().split()[-1]

    def price_level_to_dollar_signs(self, price_level: str) -> str:
        mapping = {
            "PRICE_LEVEL_UNSPECIFIED": "N/A",
            "PRICE_LEVEL_FREE":        "Free",
            "PRICE_LEVEL_INEXPENSIVE": "$",
            "PRICE_LEVEL_MODERATE":    "$$",
            "PRICE_LEVEL_EXPENSIVE":   "$$$",
            "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
        }
        return mapping.get(price_level, "N/A")

    def _parse_places(self, places: list) -> dict:
        """
        Shared helper to parse a list of raw place dicts from the Google Places API
        into the standard results format keyed by place_id.

        Args:
            places: Raw list of place objects from the API response.

        Returns:
            dict keyed by place_id, each value containing:
            name, place_id, rating, userRatingCount, reviews, reviewSummary,
            location, formattedAddress, priceLevel, typeLabel
        """
        results = {}
        for place in places:
            place_name       = place.get("displayName", {}).get("text")
            place_id         = place.get("id")
            rating           = place.get("rating", "N/A")
            user_rating_count = place.get("userRatingCount", 0)
            type_label       = place.get("googleMapsTypeLabel", {"text": "N/A"})

            print(f"--- {place_name} ({rating} stars) ---")

            reviews = [
                {
                    "rating": review.get("rating", "N/A"),
                    "text":   review.get("text", {}).get("text", ""),
                }
                for review in place.get("reviews", [])
            ]

            results[place_id] = {
                "name":             place_name,
                "place_id":         place_id,
                "rating":           rating,
                "userRatingCount":  user_rating_count,
                "reviews":          reviews,
                "reviewSummary":    place.get("reviewSummary", "N/A"),
                "location":         place.get("location", None),
                "formattedAddress": place.get("formattedAddress", "N/A"),
                "priceLevel":       self.price_level_to_dollar_signs(
                                        place.get("priceLevel", "PRICE_LEVEL_UNSPECIFIED")
                                    ),
                "typeLabel":        type_label.get("text", "N/A"),
            }

        return results


    def search_by_keyword(self, keyword: str, max_results: int = 10) -> dict:
        """
        Search for places by a free-text keyword query using the Google Places
        Text Search API (v1).

        Args:
            keyword:     Free-text search string (e.g. "Ice Cream Shop in San Francisco").
            max_results: Maximum number of results to return (1–20).

        Returns:
            dict keyed by place_id with parsed place data.
        """
        payload = {
            "textQuery":      keyword,
            "maxResultCount": max_results,
        }
        headers = {
            "Content-Type":   "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.displayName,places.rating,places.reviews,places.id,"
                "places.userRatingCount,places.formattedAddress,places.location,"
                "places.reviewSummary,places.priceLevel,places.googleMapsTypeLabel"
            ),
        }

        response = requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        places = response.json().get("places", [])
        return self._parse_places(places)
    
    def search_by_location(self, latitude: float, longitude: float, radius: int = 1000) -> dict:
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

    def get_restaurants(self, latitude: float, longitude: float, radius: int = 1000) -> dict:
        """
        Fetch nearby restaurants using the Google Places Nearby Search API (v1).

        Args:
            latitude:  Latitude of the search center.
            longitude: Longitude of the search center.
            radius:    Search radius in meters (default 1000).

        Returns:
            dict keyed by place_id with parsed place data.
        """
        payload = {
            "includedTypes":     ["restaurant"],
            "maxResultCount":    10,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius,
                }
            },
        }
        headers = {
            "Content-Type":   "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.displayName,places.rating,places.reviews,places.id,"
                "places.userRatingCount,places.formattedAddress,places.location,"
                "places.reviewSummary,places.priceLevel,places.googleMapsTypeLabel"
            ),
        }

        response = requests.post(
            "https://places.googleapis.com/v1/places:searchNearby",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        places = response.json().get("places", [])
        return self._parse_places(places)

    def compute_score(self, place: dict) -> float:
        """
        Basic heuristic score: 70% rating + 30% log(review_count).

        Args:
            place: Single restaurant dict from search results.

        Returns:
            float score
        """
        rating       = place.get("rating", 0)
        review_count = place.get("userRatingCount", 0)
        return 0.7 * rating + 0.3 * math.log1p(review_count)

    def recommend_restaurants(self, restaurants: dict, top_k: int = 4) -> list[dict]:
        """
        Heuristic-based recommendation: filter by minimum rating and review count,
        then rank by weighted score (rating + review volume).

        Args:
            restaurants: dict from search_by_keyword() or get_restaurants().
            top_k:       Number of top results to return (default 4).

        Returns:
            list[dict] of top_k restaurants sorted by score descending.
        """
        filtered = [
            place for place in restaurants.values()
            if place.get("rating", 0) >= 4.0
            and place.get("userRatingCount", 0) >= 50
        ]
        return sorted(filtered, key=self.compute_score, reverse=True)[:top_k]

    def analyze_review_sentiment(self, text: str) -> dict:
        """
        Run VADER sentiment analysis on a single review text.

        Args:
            text: Review text string.

        Returns:
            dict with keys: compound (float), label ("positive" | "neutral" | "negative")
        """
        if not text or not text.strip():
            return {"compound": 0.0, "label": "neutral"}

        scores   = self._sia.polarity_scores(text)
        compound = scores["compound"]
        label    = "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral"
        return {"compound": compound, "label": label}

    def aggregate_restaurant_sentiment(self, reviews: list[dict]) -> dict:
        """
        Aggregate review-level VADER sentiment into a restaurant-level summary.

        Args:
            reviews: list[dict] with a "text" key per review.

        Returns:
            dict with keys: sentiment_score, positive_count, neutral_count,
                            negative_count, review_count
        """
        if not reviews:
            return {
                "sentiment_score": 0.0,
                "positive_count":  0,
                "neutral_count":   0,
                "negative_count":  0,
                "review_count":    0,
            }

        compounds      = []
        positive_count = neutral_count = negative_count = 0

        for review in reviews:
            result = self.analyze_review_sentiment(review.get("text", ""))
            compounds.append(result["compound"])
            if result["label"] == "positive":
                positive_count += 1
            elif result["label"] == "negative":
                negative_count += 1
            else:
                neutral_count += 1

        return {
            "sentiment_score": round(sum(compounds) / len(compounds), 4),
            "positive_count":  positive_count,
            "neutral_count":   neutral_count,
            "negative_count":  negative_count,
            "review_count":    len(reviews),
        }

    def add_sentiment_to_restaurants(self, restaurants: dict) -> dict:
        """
        Enrich each restaurant in the results dict with sentiment fields.

        Args:
            restaurants: dict from search_by_keyword() or get_restaurants().

        Returns:
            dict with sentiment_score, positive_count, neutral_count,
            negative_count, review_count added to each restaurant entry.
        """
        return {
            place_id: {**info, **self.aggregate_restaurant_sentiment(info.get("reviews", []))}
            for place_id, info in restaurants.items()
        }

    # -------------------------------------------------------------------------
    # 4. Sentiment-Enhanced Recommendation
    # -------------------------------------------------------------------------

    def _compute_score_sentiment(self, place: dict) -> float:
        """
        Sentiment-enhanced heuristic score:
        50% rating + 20% log(review_count) + 30% sentiment_score.

        Args:
            place: Restaurant dict that already has sentiment fields attached.

        Returns:
            float score
        """
        return (
            0.5 * place.get("rating", 0)
            + 0.2 * math.log1p(place.get("userRatingCount", 0))
            + 0.3 * place.get("sentiment_score", 0)
        )

    def recommend_restaurants_with_sentiment(self, restaurants: dict, top_k: int = 4) -> list[dict]:
        """
        Sentiment-enhanced heuristic recommendation: adds VADER sentiment to
        each restaurant then ranks by the combined score.

        Args:
            restaurants: dict from search_by_keyword() or get_restaurants().
            top_k:       Number of top results to return (default 4).

        Returns:
            list[dict] of top_k restaurants sorted by final_score descending,
            with sentiment fields and final_score added.
        """
        enriched = self.add_sentiment_to_restaurants(restaurants)

        filtered = []
        for place in enriched.values():
            if place.get("rating", 0) < 4.0:
                continue
            if place.get("userRatingCount", 0) < 50:
                continue
            place["final_score"] = self._compute_score_sentiment(place)
            filtered.append(place)

        return sorted(filtered, key=lambda x: x["final_score"], reverse=True)[:top_k]

    # -------------------------------------------------------------------------
    # 5. Full Pipeline
    # -------------------------------------------------------------------------

    def run_pipeline(self, query: str, max_results: int = 10, top_k: int = 4) -> list[dict]:
        """
        Run the full pipeline end-to-end from a natural-language query.
        Location is automatically extracted from the query string.

        Steps:
            1. search_by_keyword()                   — fetch places from Google
            2. recommend_restaurants_with_sentiment() — score & rank

        Args:
            query:       Full user query (e.g. "Best Restaurant in San Francisco").
            max_results: Number of places to fetch from Google (default 10).
            top_k:       Number of top results to return (default 4).

        Returns:
            list[dict] of top_k recommended restaurants with all enriched fields.
        """
        results = self.search_by_keyword(query, max_results=max_results)

        if not results:
            return []

        return self.recommend_restaurants_with_sentiment(results, top_k=top_k)
    
    
    def enrich_openai_results(
        self, openai_results: list[dict], location: str = "San Francisco"
    ) -> list[dict]:
        """
        Take the list[dict] returned by OpenAIService.recommend_restaurants()
        and enrich each entry with full Google Maps details fetched by name.

        Args:
            openai_results: list[dict] from OpenAIService.recommend_restaurants(),
                            each must have a "name" key.
            location:       City/neighbourhood passed to search_by_name()
                            (default "San Francisco").

        Returns:
            list[dict] in the same order, each merged with the Google Maps place
            dict. If a restaurant could not be found, the original OpenAI dict is
            returned unchanged with "google_maps_status": "not found" added.
        """
        enriched = []
        for restaurant in openai_results:
            # if restaurant.get("userRatingCount"): ## if the restaurant already has userRatingCount, we assume it's already enriched with Google Maps data and skip the lookup
            #     enriched.append(restaurant)
            #     continue
            name       = restaurant.get("name", "")
            place_info = self.search_by_name(name, location=location)

            if place_info:
                merged = {
                    **restaurant,
                    **place_info,
                    "name": place_info.get("name") or name,
                    "google_maps_status": "found",
                }
            else:
                merged = {
                    **restaurant,
                    "google_maps_status": "not found",
                }

            enriched.append(merged)

        return enriched
    
    def run_pipeline_by_location(self, lat: float, lng: float, max_results: int = 10, top_k: int = 4) -> list[dict]:
        """
        Run the full pipeline end-to-end from a natural-language query.
        Location is automatically extracted from the query string.

        Steps:
            1. search_by_location()                  — fetch places from Google
            2. recommend_restaurants_with_sentiment() — score & rank

        Args:
            lat:         Latitude of the location.
            lng:         Longitude of the location.
            max_results: Number of places to fetch from Google (default 10).
            top_k:       Number of top results to return (default 4).

        Returns:
            list[dict] of top_k recommended restaurants with all enriched fields.
        """
        results = self.search_by_location(lat, lng, radius=1000)

        if not results:
            return []

        return self.recommend_restaurants_with_sentiment(results, top_k=top_k)
    
    def search_by_name(self, name: str, location: str = "San Francisco") -> dict | None:
        """
        Look up a single restaurant by name using the Places Text Search API.
        Use this to enrich OpenAI-recommended restaurant names with full
        Google Maps details (address, rating, reviews, price level, etc).

        Args:
            name:     Restaurant name exactly as returned by OpenAI
                      (e.g. "Tartine Manufactory").
            location: City/neighbourhood to narrow the search (default "San Francisco").

        Returns:
            Single place dict with keys: name, place_id, rating, userRatingCount,
            reviews, reviewSummary, location, formattedAddress, priceLevel, typeLabel,
            sentiment_score, positive_count, neutral_count, negative_count, review_count,
            website, phone, openingHours.
            Returns None if no match is found.
        """
        query = f"{name} {location}"
        payload = {
            "textQuery":      query,
            "maxResultCount": 1,
        }
        headers = {
            "Content-Type":   "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.displayName,places.rating,places.reviews,places.id,"
                "places.userRatingCount,places.formattedAddress,places.location,"
                "places.reviewSummary,places.priceLevel,places.googleMapsTypeLabel,"
                "places.websiteUri,places.nationalPhoneNumber,places.regularOpeningHours"
            ),
        }

        response = requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        places = response.json().get("places", [])

        if not places:
            print(f"No Google Maps result found for: '{name}'")
            return None

        parsed = self._parse_places(places)
        place  = next(iter(parsed.values()))

        # Enrich with sentiment while we have the reviews
        sentiment = self.aggregate_restaurant_sentiment(place.get("reviews", []))
        place.update(sentiment)

        # Attach extra fields from the raw response
        raw = places[0]
        place["website"] = raw.get("websiteUri", "N/A")
        place["phone"]   = raw.get("nationalPhoneNumber", "N/A")
        hours = raw.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
        place["openingHours"] = hours

        print(f"Found: {place['name']} ({place['rating']} \u2605, {place['formattedAddress']})")
        return place