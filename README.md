# Belly Button

Belly Button is a SF restaurant recommendation app with a FastAPI backend and a React/Vite frontend. The backend combines Google Maps, Yelp, Reddit, OpenAI, and Anthropic services to generate restaurant recommendations from a keyword query, and the frontend presents those results in a chat-style interface.

## What it does

- Accepts restaurant search requests through a chat UI.
- Calls the backend recommendation API for keyword-based restaurant discovery.
- Enriches results with restaurant details, ratings, prices, locations, and map links.
- Displays the response in a conversational layout with restaurant cards.

## Project Structure

```text
.
├── main.py                  # FastAPI app entrypoint
├── config.py                # Environment variable configuration
├── services/                # Google, Yelp, and Reddit data services and OpenAI/Anthropic integration
├── website/                 # React + Vite frontend
└── start_*.sh               # Convenience scripts for local development
```

## Requirements

- Python 3.10+
- Node.js 18+
- API credentials for Google Maps, OpenAI, Yelp, Reddit, and Anthropic

## Backend Setup

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pydantic-settings python-dotenv requests nltk anthropic praw sentence-transformers numpy
```

Run the API server from the repository root:

```bash
uvicorn main:app --reload --env-file .env
```

You can also use the helper script:

```bash
./start_dev_server.sh
```

## Frontend Setup

Install frontend dependencies and start the Vite dev server:

```bash
cd website
npm install
npm run dev
```

Or run the helper script from the repository root:

```bash
./start_dev_front.sh
```

## Environment Variables

Create a `.env` file in the repository root with the backend credentials:

```bash
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
OPENAI_API_KEY=your_openai_api_key
YELP_API_KEY=your_yelp_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_REDIRECT_URI=http://localhost:8000/api/reddit/auth/callback
```

For the frontend, set the API host if you are not using the default backend URL:

```bash
VITE_API_HOST=http://localhost:8000
```

## API Endpoints

### `GET /api/health`

Returns a simple health check response.

Example:

```bash
curl http://localhost:8000/api/health
```

### `GET /api/recommendation?keyword=...`

Returns restaurant recommendations for a keyword query.

Example:

```bash
curl "http://localhost:8000/api/recommendation?keyword=best%20ramen%20in%20san%20francisco"
```

Response shape:

```json
{
	"result": [
		{
			"name": "...",
			"place_id": "...",
			"rating": 4.7,
			"formattedAddress": "...",
			"priceLevel": "$$",
			"typeLabel": "Restaurant",
			"location": {
				"latitude": 0,
				"longitude": 0
			}
		}
	]
}
```

## Notes

- The frontend defaults to `http://localhost:8000` if `VITE_API_HOST` is not set.
- The app currently exposes a keyword-based recommendation endpoint from the backend.
- If you rotate or replace any API keys, update your local `.env` file before starting the server.

## Development Tips

- Start the backend before the frontend so the chat UI can reach the API.
- If the frontend cannot reach the backend, check CORS settings and confirm the backend is running on port `8000`.
- The backend prints loaded settings at startup, so avoid exposing real secrets in shared logs.