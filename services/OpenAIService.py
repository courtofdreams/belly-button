import os
from openai import OpenAI


class OpenAIService:
    def __init__(self, api_key, model="gpt-4"):
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    # ── Context Parsers ────────────────────────────────────────────────────────

    def parse_google_places_data(self, google_places_data: list[dict]) -> str:
        summary = ""
        for place in google_places_data:
            summary += f"Restaurant Id: {place.get('place_id', 'N/A')} | Rating: {place.get('rating', 'N/A')} | User Ratings: {place.get('userRatingCount', 0)}\n"
            summary += f"Restaurant Type: {place.get('typeLabel', 'N/A')}\n"
            summary += f"Price Level: {place.get('priceLevel', 'N/A')}\n"
            summary += f"Reviews: {place.get('reviewSummary', '')}\n"
            if place.get("sentiment_score") is not None:
                summary += f"Sentiment Score: {place.get('sentiment_score')} | Positive: {place.get('positive_count', 0)} | Neutral: {place.get('neutral_count', 0)} | Negative: {place.get('negative_count', 0)}\n"
            if place.get("final_score") is not None:
                summary += f"Final Score: {place.get('final_score')}\n"
            summary += "\n"
        return summary

    def parse_yelp_data(self, yelp_llm_context: str) -> str:
        """
        Accepts the string already produced by YelpAPIService.format_yelp_as_llm_context().
        Passed through as-is — it is already structured for LLM consumption.
        """
        return yelp_llm_context or ""

    def parse_reddit_data(self, reddit_llm_context: str) -> str:
        """
        Accepts the string already produced by RedditScraperService.format_as_llm_context().
        Passed through as-is — it is already structured for LLM consumption.
        """
        return reddit_llm_context or ""

    def recommend_restaurants(
        self,
        google_places_data: list[dict],
        yelp_llm_context: str = "",
        reddit_llm_context: str = "",
    ) -> list[dict]:
        """
        Recommend the top 3 restaurants by combining signals from Google Maps,
        Yelp, and Reddit.

        Args:
            google_places_data: dict keyed by place_id from GoogleMAPService
                                 (must include sentiment + final_score fields
                                  produced by recommend_restaurants_with_sentiment).
            yelp_llm_context:   Formatted string from YelpAPIService.format_yelp_as_llm_context().
            reddit_llm_context: Formatted string from RedditScraperService.format_as_llm_context().

        Returns:
            list[dict] — up to 3 unified restaurant dicts, each containing:
                - All original Google Maps fields (place_id, name, rating,
                  userRatingCount, priceLevel, formattedAddress, reviewSummary,
                  sentiment_score, final_score, …)
                - "yelp_context"   (str) relevant Yelp snippet for this restaurant
                - "reddit_context" (str) relevant Reddit snippet for this restaurant
                - "rank"           (int) 1-indexed final rank
        """
        google_context = self.parse_google_places_data(google_places_data)
        yelp_context   = self.parse_yelp_data(yelp_llm_context)
        reddit_context = self.parse_reddit_data(reddit_llm_context)
         
         #TODO: 3. Use the Reddit data for community signals: WHY a place is buzzing, quote evidence, mention count, and recency score.
         ##             REDDIT COMMUNITY DATA (community quotes, mention counts, recency):
        ## {reddit_context}

        prompt = f"""
            You are a local SF foodie who knows the most popular and hyped top 3 restaurants.

            ROLE
            You are a real-time restaurant recommendation agent that surfaces currently buzzing restaurants by combining Google Maps review signals, Yelp buzz scores, and Reddit community sentiment.

            OBJECTIVE
            Return a ranked list of exactly 3 restaurants that are genuinely active RIGHT NOW — based on recent review volume, sentiment, and rating — not just historically popular.

            OUT OF SCOPE
            - Restaurants with rating < 4.0 or fewer than 50 total reviews
            - Non-English queries (respond: "Currently only supporting English-language queries")
        

            INSTRUCTIONS
            1. Use the Google Maps data for review sentiment and final_score signals.
            2. Use the Yelp data for buzz score, recency (90-day review window), price, and metadata.
            3. Use the Reddit data for community signals: WHY a place is buzzing, quote evidence, mention count, and recency score.
            4. Cross-reference all three sources. Prefer restaurants that appear in multiple sources.
            5. Re-rank by combining: final_score (Google) + buzz_score (Yelp) + community_score (Reddit).
            6. Return EXACTLY 3 restaurant names, one per line, ranked 1 to 3.
            7. If fewer than 3 pass all filters, explain how many qualified and why others were excluded.

            OUTPUT RULES
            - Output ONLY the restaurant names, one per line, numbered 1 to 3
            - No extra text, labels, or explanations
            - Names must match exactly as they appear in the data below

            Example output:
            1. Nopalito
            2. Tartine Manufactory
            3. Garden Creamery

            ---
            GOOGLE MAPS DATA (ratings, sentiment scores, review summaries):
            {google_context}

            ---
            YELP DATA (buzz scores, recency, price, categories):
            {yelp_context}

            ---
            REDDIT COMMUNITY DATA (community quotes, mention counts, recency):
            {reddit_context}
            """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a local SF foodie and real-time restaurant recommendation agent. "
                        "You surface the most currently buzzing restaurants by combining structured "
                        "API signals (Google Maps, Yelp) with community sentiment (Reddit). "
                        "You prioritize recency and genuine current activity over historical popularity."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

        raw_output = response.choices[0].message.content.strip()
        print("OpenAI Response:\n", raw_output)

        # Parse ranked names from "1. Name" format
        ranked_names = []
        for line in raw_output.splitlines():
            line = line.strip()
            if not line:
                continue
            # Strip leading rank number if present (e.g. "1. ", "1) ")
            cleaned = line.lstrip("0123456789").lstrip(". )").strip()
            if cleaned:
                ranked_names.append(cleaned)

        # Build lookup by name (case-insensitive) from Google Maps data
        name_to_place = {
            v.get("name", "").lower(): v
            for v in google_places_data
            if v.get("name")
        }

        # Build per-restaurant Yelp/Reddit snippets (simple name match)
        def extract_snippet(context: str, name: str, lines_after: int = 8) -> str:
            """Pull the block of lines around a restaurant name mention."""
            if not context or not name:
                return ""
            ctx_lines = context.splitlines()
            for i, line in enumerate(ctx_lines):
                if name.lower() in line.lower():
                    return "\n".join(ctx_lines[i: i + lines_after]).strip()
            return ""

        result = []
        for rank, name in enumerate(ranked_names[:3], start=1):
            place = name_to_place.get(name.lower(), {})

            # Fallback: fuzzy-ish match (first word of name)
            if not place:
                first_word = name.split()[0].lower() if name.split() else ""
                for key, val in name_to_place.items():
                    if first_word and first_word in key:
                        place = val
                        break

            unified = {
                **place,
                "rank":           rank,
                "yelp_context":   extract_snippet(yelp_llm_context, name),
                "reddit_context": extract_snippet(reddit_llm_context, name),
            }

            # Ensure name is always present even if no Google match
            if not unified.get("name"):
                unified["name"] = name

            result.append(unified)

        return result
    
    
    
