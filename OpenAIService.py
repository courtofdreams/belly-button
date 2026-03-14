import os
from openai import OpenAI


class OpenAIService:
    def __init__(self, api_key, model="gpt-4"):
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
    def parse_google_places_data(self, google_places_data: list[dict]) -> str:
        summary = ""
        for place in google_places_data:
            summary += f"Restaurant Id: {place.get('place_id', 'N/A')} | Rating: {place.get('rating', 'N/A')} | User Ratings: {place.get('userRatingCount', 0)}\n"
            summary += f"Restaurant Type: {place.get('typeLabel', 'N/A')}\n"
            summary += f"Price Level: {place.get('priceLevel', 'N/A')}\n"
            
            # reviews = place.get('reviews', [])
            # if reviews:
            #     summary += f"Top Review: {reviews[0].get('text', '')}\n"
            # summary += "\n"
            summary += f"Reviews: {place.get('reviewSummary', '')}\n"
        return summary    

    def recommend_restaurants(self, google_places_data: dict) -> list[dict]:
        context = self.parse_google_places_data(list(google_places_data.values()))
        prompt = f"""
            Based on the following context, recommend restaurants that would be suitable for the user to visit. Consider factors such as reviews, ratings (pioritize restaurants with ratings above 4.0), and the number of user ratings (prioritize restaurants with more than 100 ratings):
                {context}   
            Return EXACTLY top 4 restaurant IDs that meet the criteria.
            OUTPUT RULES:
            - Output ONLY the IDs
            - Separate IDs using " | "
            - No numbering
            - No labels
            - No extra text
            - No explanations
            - Do not include spaces except around "|"

            Example:
            123455 | 1234456789 | 987654321 | 555666777
            """
            
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that recommends restaurants."},
                {"role": "user", "content": prompt}
            ]
        )
        
        print("OpenAI Response:", response.choices[0].message.content)
        result = []
        list_of_recommended_restaurants = response.choices[0].message.content.strip().split("|")
        for restaurant_id in list_of_recommended_restaurants:
            result.append(google_places_data.get(restaurant_id.strip(), {}))
        return result