import re
import requests
from datetime import datetime, timedelta
from collections import defaultdict


class YelpService:

    CUTOFF_DAYS = 90  

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}


    def _extract_location(self, query: str) -> str:
        """
        Parse the location out of a natural-language query.
        Looks for 'in <Location>' pattern; falls back to the last word.

        Examples:
            "Best Restaurant in San Francisco" → "San Francisco"
            "Best Restaurant in AF"            → "AF"
        """
        match = re.search(r"\bin\s+(.+)$", query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return query.strip().split()[-1]


    def get_restaurants(self, location: str, term: str = "restaurants", limit: int = 20) -> list[dict]:
        """
        Search Yelp for restaurants matching `term` in `location`.

        Args:
            location: City or address string (e.g. "San Francisco")
            term:     Search term (e.g. "ice cream")
            limit:    Max results to return (max 50 per Yelp API)

        Returns:
            list[dict] with keys: id, name, rating, review_count, address, categories
        """
        response = requests.get(
            "https://api.yelp.com/v3/businesses/search",
            headers=self.headers,
            params={
                "term": term,
                "location": location,
                "limit": limit,
                "sort_by": "best_match",
            },
        )
        print("Status code:", response.status_code)
        data = response.json()

        if "businesses" not in data:
            print("API Error:", data)
            return []

        return [
            {
                "id": biz["id"],
                "name": biz["name"],
                "rating": biz["rating"],
                "review_count": biz["review_count"],
                "address": biz["location"]["address1"],
                "categories": [c["title"] for c in biz["categories"]],
            }
            for biz in data["businesses"]
        ]

    def get_business_details(self, business_id: str) -> dict:
        """
        Fetch enriched metadata for a single business (price, phone, URL).

        Args:
            business_id: Yelp business ID string

        Returns:
            dict with keys: id, name, rating, review_count, address,
                            categories, price, phone, url
        """
        response = requests.get(
            f"https://api.yelp.com/v3/businesses/{business_id}",
            headers=self.headers,
        )
        biz = response.json()
        return {
            "id": biz["id"],
            "name": biz["name"],
            "rating": biz["rating"],
            "review_count": biz["review_count"],
            "address": biz["location"]["address1"],
            "categories": [c["title"] for c in biz["categories"]],
            "price": biz.get("price", "N/A"),
            "phone": biz.get("phone", "N/A"),
            "url": biz["url"],
        }

    def enrich_restaurants(self, restaurants: list[dict]) -> list[dict]:
        """
        Enrich each restaurant dict with price, phone, and url.

        Args:
            restaurants: list[dict] from get_restaurants()

        Returns:
            list[dict] with enriched fields added
        """
        details = [self.get_business_details(r["id"]) for r in restaurants]
        print(f"Enriched {len(details)} restaurants")
        return details


    def get_reviews(self, business_id: str) -> list[dict]:
        """
        Fetch the 3 most recent reviews for a business.

        Args:
            business_id: Yelp business ID string

        Returns:
            list[dict] with keys: business_id, rating, date (datetime)
        """
        response = requests.get(
            f"https://api.yelp.com/v3/businesses/{business_id}/reviews",
            headers=self.headers,
            params={"limit": 3, "sort_by": "newest"},
        )
        reviews = response.json().get("reviews", [])
        return [
            {
                "business_id": business_id,
                "rating": r["rating"],
                "date": datetime.fromisoformat(r["time_created"]),
            }
            for r in reviews
        ]

    def get_recent_reviews(self, details: list[dict]) -> list[dict]:
        """
        Collect reviews for all businesses and apply the 3-month recency filter.

        Args:
            details: list[dict] from enrich_restaurants()

        Returns:
            list[dict] of reviews within the last CUTOFF_DAYS days
        """
        all_reviews = []
        for biz in details:
            all_reviews.extend(self.get_reviews(biz["id"]))

        cutoff_date = datetime.now() - timedelta(days=self.CUTOFF_DAYS)
        recent = [r for r in all_reviews if r["date"] >= cutoff_date]

        print(f"Reviews before filter : {len(all_reviews)}")
        print(f"Reviews after {self.CUTOFF_DAYS}-day filter: {len(recent)}")
        return recent


    def compute_buzz_scores(self, reviews: list[dict]) -> list[dict]:
        """
        Compute buzz scores per restaurant.

        Formula: buzz_score = 0.6 × recent_review_count_norm + 0.4 × avg_rating_norm

        Args:
            reviews: list[dict] from get_recent_reviews()

        Returns:
            list[dict] sorted by buzz_score descending, each with keys:
            business_id, recent_review_count, avg_rating, latest_review_date, buzz_score
        """
        if not reviews:
            print("⚠️  No reviews to score. Check data loading or recency filter.")
            return []

        grouped = defaultdict(lambda: {"ratings": [], "dates": []})
        for r in reviews:
            grouped[r["business_id"]]["ratings"].append(r["rating"])
            grouped[r["business_id"]]["dates"].append(r["date"])

        scores = [
            {
                "business_id": biz_id,
                "recent_review_count": len(v["ratings"]),
                "avg_rating": sum(v["ratings"]) / len(v["ratings"]),
                "latest_review_date": max(v["dates"]),
            }
            for biz_id, v in grouped.items()
        ]

        counts = [s["recent_review_count"] for s in scores]
        ratings = [s["avg_rating"] for s in scores]
        count_range = max(counts) - min(counts) or 1e-9
        rating_range = max(ratings) - min(ratings) or 1e-9

        for s in scores:
            count_norm = (s["recent_review_count"] - min(counts)) / count_range
            rating_norm = (s["avg_rating"] - min(ratings)) / rating_range
            s["buzz_score"] = round(0.6 * count_norm + 0.4 * rating_norm, 4)

        return sorted(scores, key=lambda x: x["buzz_score"], reverse=True)

    def build_final(self, buzz_scores: list[dict], details: list[dict]) -> list[dict]:
        """
        Merge buzz scores with restaurant metadata.

        Args:
            buzz_scores: list[dict] from compute_buzz_scores()
            details:     list[dict] from enrich_restaurants()

        Returns:
            list[dict] with all fields merged, sorted by buzz_score descending
        """
        detail_map = {d["id"]: d for d in details}
        merged = []
        for s in buzz_scores:
            biz = detail_map.get(s["business_id"], {})
            merged.append({
                **s,
                "name": biz.get("name"),
                "categories": biz.get("categories", []),
                "price": biz.get("price", "N/A"),
                "url": biz.get("url", ""),
            })
        print(f"Buzz scores computed for {len(merged)} restaurants")
        return merged


    def format_yelp_as_llm_context(self, final: list[dict], query: str, top_n: int = 5) -> str:
        """
        Format Yelp buzz-scored restaurants as a context string for the LLM.
        Mirrors Tubal's format_as_llm_context() for Reddit data so the
        orchestration layer receives consistent input from all three sources
        (Yelp / Google Maps / Reddit).

        Args:
            final:  list[dict] from build_final()
            query:  Original user query string
            top_n:  Number of top restaurants to include (default 5)

        Returns:
            Formatted context string ready for the orchestration layer
        """
        top = final[:top_n]

        context = f'Yelp restaurant recommendations for: "{query}"\n'
        context += f"Retrieved {len(top)} restaurants (sorted by buzz score)\n"
        context += "Scoring: 60% recent review volume + 40% average rating (3-month window)\n"
        context += "=" * 60 + "\n\n"

        for i, row in enumerate(top, start=1):
            categories = (
                ", ".join(row["categories"])
                if isinstance(row["categories"], list)
                else row["categories"]
            )
            context += f"RESTAURANT {i}\n"
            context += f'  Name: {row["name"]}\n'
            context += f'  Buzz Score: {row["buzz_score"]} (0.0–1.0, higher = more buzz)\n'
            context += f'  Avg Rating: {row["avg_rating"]:.1f} / 5.0\n'
            context += f'  Recent Reviews (3mo): {int(row["recent_review_count"])}\n'
            context += f'  Latest Activity: {str(row["latest_review_date"])[:10]}\n'
            context += f"  Categories: {categories}\n"
            context += f'  Price: {row["price"]}\n'
            context += f'  Source: Yelp | {row["url"]}\n\n'

        return context


    def run_pipeline(self, query: str, limit: int = 20, top_n: int = 5) -> str:
        """
        Run the complete Yelp pipeline end-to-end and return the LLM context string.
        Location is automatically extracted from the query string.

        Args:
            query:  Full user query (e.g. "Best Restaurant in San Francisco")
            limit:  Number of businesses to fetch from Yelp (default 20)
            top_n:  Number of top results to include in LLM context (default 5)

        Returns:
            Formatted LLM context string
        """
        location = self._extract_location(query)
        print(f"── Extracted location: {location} ──\n")

        restaurants = self.get_restaurants(location, term=query, limit=limit)
        if not restaurants:
            return "No restaurants found."

        details = self.enrich_restaurants(restaurants)

        recent_reviews = self.get_recent_reviews(details)

        buzz_scores = self.compute_buzz_scores(recent_reviews)
        
        final = self.build_final(buzz_scores, details)
        
        return self.format_yelp_as_llm_context(final, query=query, top_n=top_n)