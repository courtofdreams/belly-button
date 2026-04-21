import json
import math
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

import anthropic
import numpy as np
import praw
from sentence_transformers import SentenceTransformer


class RedditService:

    # ── Default configuration ──────────────────────────────────────────────────
    SUBREDDITS       = ["AskSF", "SFFood"]
    POST_LIMIT       = 100
    MAX_AGE_DAYS     = 365
    TOP_COMMENTS     = 25
    DB_PATH          = "master_database_v2.json"

    SKIP_WORDS = {
        "best", "good", "great", "san", "francisco", "sf",
        "restaurant", "place", "spot", "where", "what", "any",
        "near", "want", "find", "some", "with", "from", "have",
        "that", "this", "they", "their", "there", "been", "will",
        "also", "just", "really", "very",
    }

    # Scoring weights (recency × sum, log-upvotes, subreddit diversity)
    W_RECENCY   = 1.0
    W_UPVOTES   = 0.3
    W_DIVERSITY = 0.5

    # LLM extraction settings
    TOP_COMMENTS_RETRIEVE      = 10
    TOP_RESTAURANTS_OUTPUT     = 5
    MAX_COMMENT_CHARS_FOR_LLM  = 500
    SAMPLE_COMMENT_CHARS       = 250
    EMBEDDING_MODEL            = "all-MiniLM-L6-v2"

    def __init__(
        self,
        reddit_client_id: str,
        reddit_client_secret: str,
        reddit_username: str,
        reddit_password: str,
        anthropic_api_key: str,
        db_path: str = DB_PATH,
    ):
        self.reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            username=reddit_username,
            password=reddit_password,
            user_agent="restaurant_recommender by u/Effective-Street7281",
        )
        self.claude  = anthropic.Anthropic(api_key=anthropic_api_key)
        self.db_path = db_path

        # Embedding model + index (lazy-loaded on first query)
        self._embed_model: SentenceTransformer | None = None
        self._embeddings_normed: np.ndarray | None    = None
        self._indexed_comments: list[dict]            = []

    # ── 0. Utilities ───────────────────────────────────────────────────────────

    def _get_age_days(self, utc_timestamp: float) -> int:
        """Return how many days ago a UTC timestamp was."""
        post_time = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
        return (datetime.now(tz=timezone.utc) - post_time).days

    def _format_timestamp(self, utc_timestamp: float) -> str:
        """Convert UTC timestamp to YYYY-MM-DD string."""
        return datetime.fromtimestamp(utc_timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

    def _compute_recency_score(self, age_days: int) -> float:
        """
        Linear recency score: 1.0 = today, 0.0 = MAX_AGE_DAYS ago.
        Applied to comment date, not post date.
        """
        if age_days <= 0:
            return 1.0
        if age_days >= self.MAX_AGE_DAYS:
            return 0.0
        return round(1.0 - (age_days / self.MAX_AGE_DAYS), 3)

    def _extract_location(self, query: str) -> str:
        """Parse 'in <Location>' from a query string."""
        match = re.search(r"\bin\s+(.+)$", query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return query.strip().split()[-1]

    # ── 1. LLM Classifier ─────────────────────────────────────────────────────

    def _llm_classifier(
        self, post_title: str, post_body: str, comments_preview: str, max_retries: int = 3
    ) -> bool:
        """
        Claude Haiku classifier — determines whether a post is a food/drink
        recommendation thread. Retries on transient API errors.
        """
        prompt = (
            "Is this Reddit post asking for or giving recommendations for any food or drink "
            "establishment in San Francisco? This includes restaurants, cafes, bars, ice cream "
            "shops, bakeries, dessert spots, food trucks, coffee shops, and similar places.\n\n"
            f"Title: {post_title}\n"
            f"Body: {post_body[:200]}\n"
            f"Top comments preview: {comments_preview[:300]}\n\n"
            "Answer yes or no only."
        )
        for attempt in range(max_retries):
            try:
                response = self.claude.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=5,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text.strip().lower() == "yes"
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"Classifier failed after {max_retries} retries: {e}")
                    return False
        return False

    # ── 2. Build / Refresh Database ────────────────────────────────────────────

    def update_database(self) -> list[dict]:
        """
        Build or refresh the comment database.

        Steps:
            1. Load existing DB (or start fresh)
            2. Scrape new posts from each subreddit (new / hot / top-month feeds)
            3. LLM classifier filters posts to food/drink threads only
            4. Flatten approved posts into individual comment rows
            5. Remove comments older than MAX_AGE_DAYS
            6. Save updated DB to self.db_path

        Returns:
            list[dict] of all current comment rows
        """
        try:
            with open(self.db_path, "r") as f:
                existing = json.load(f)
            existing_comments = {c["comment_id"]: c for c in existing["comments"]}
            seen_post_ids     = set(existing.get("processed_post_ids", []))
            print(f"Loaded existing DB: {len(existing_comments)} comments")
        except FileNotFoundError:
            existing_comments = {}
            seen_post_ids     = set()
            print("No existing DB — building fresh")

        new_comments       = 0
        rejected_llm       = 0
        new_posts_processed = 0
        start_time         = time.time()

        for sub_name in self.SUBREDDITS:
            print(f"\nScraping r/{sub_name}...")
            subreddit = self.reddit.subreddit(sub_name)

            feeds = [
                subreddit.new(limit=self.POST_LIMIT),
                subreddit.hot(limit=self.POST_LIMIT),
                subreddit.top(limit=self.POST_LIMIT, time_filter="month"),
            ]

            seen_in_this_run: set[str] = set()

            for feed in feeds:
                for post in feed:
                    if post.id in seen_post_ids or post.id in seen_in_this_run:
                        continue
                    seen_in_this_run.add(post.id)

                    if self._get_age_days(post.created_utc) > self.MAX_AGE_DAYS:
                        continue

                    try:
                        post.comments.replace_more(limit=0)
                    except Exception as e:
                        print(f"  Skipping post {post.id} (comment fetch failed: {e})")
                        continue

                    comments_preview = " ".join([
                        c.body[:100] for c in post.comments[:3]
                        if c.body not in ["[removed]", "[deleted]"]
                    ])

                    if not self._llm_classifier(post.title, post.selftext, comments_preview):
                        rejected_llm += 1
                        seen_post_ids.add(post.id)
                        continue

                    for comment in post.comments[: self.TOP_COMMENTS]:
                        age_days = self._get_age_days(comment.created_utc)
                        if age_days > self.MAX_AGE_DAYS:
                            continue
                        if not comment.body or comment.body in ["[removed]", "[deleted]"]:
                            continue
                        if comment.id not in existing_comments:
                            existing_comments[comment.id] = {
                                "comment_id":       comment.id,
                                "comment_body":     comment.body,
                                "comment_date":     self._format_timestamp(comment.created_utc),
                                "comment_age_days": age_days,
                                "recency_score":    self._compute_recency_score(age_days),
                                "comment_upvotes":  comment.score,
                                "post_title":       post.title,
                                "post_url":         f"https://reddit.com{post.permalink}",
                                "subreddit":        sub_name,
                            }
                            new_comments += 1

                    seen_post_ids.add(post.id)
                    new_posts_processed += 1

                    if new_posts_processed % 25 == 0:
                        elapsed = time.time() - start_time
                        print(
                            f"  Processed {new_posts_processed} posts "
                            f"({new_comments} comments, {elapsed:.0f}s elapsed)"
                        )

        # Prune expired comments
        existing_comments = {
            cid: c for cid, c in existing_comments.items()
            if c["comment_age_days"] <= self.MAX_AGE_DAYS
        }

        output = {
            "version":              "v2",
            "last_updated":         datetime.now(tz=timezone.utc).isoformat(),
            "total_comments":       len(existing_comments),
            "subreddits":           self.SUBREDDITS,
            "max_age_days":         self.MAX_AGE_DAYS,
            "top_comments_per_post": self.TOP_COMMENTS,
            "processed_post_ids":   list(seen_post_ids),
            "comments":             list(existing_comments.values()),
        }

        with open(self.db_path, "w") as f:
            json.dump(output, f, indent=2)

        total_elapsed = time.time() - start_time
        print(f"\n=== DB Update Complete ===")
        print(f"Runtime: {total_elapsed / 60:.1f} minutes")
        print(f"New posts processed : {new_posts_processed}")
        print(f"New comments added  : {new_comments}")
        print(f"Rejected by Haiku   : {rejected_llm}")
        print(f"Total in DB         : {len(existing_comments)}")

        # Invalidate embedding index since DB changed
        self._embeddings_normed = None
        self._indexed_comments  = []

        return list(existing_comments.values())

    def load_database(self) -> list[dict]:
        """Load and return all comments from the current DB file."""
        with open(self.db_path, "r") as f:
            db = json.load(f)
        return db["comments"]

    # ── 3. Embedding Index ─────────────────────────────────────────────────────

    def _ensure_index(self) -> None:
        """Lazy-build the sentence-transformer embedding index."""
        if self._embeddings_normed is not None:
            return

        if self._embed_model is None:
            print(f"Loading embedding model ({self.EMBEDDING_MODEL})...")
            self._embed_model = SentenceTransformer(self.EMBEDDING_MODEL)

        self._indexed_comments = self.load_database()
        texts = [
            c["comment_body"] + " " + c["post_title"]
            for c in self._indexed_comments
        ]
        print(f"Embedding {len(texts)} comments...")
        emb = self._embed_model.encode(texts, show_progress_bar=False, batch_size=64)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        self._embeddings_normed = emb / (norms + 1e-8)
        print("Index ready.")

    # ── 4. Search ──────────────────────────────────────────────────────────────

    def keyword_search(self, query: str, top_n: int = 15) -> list[dict]:
        """
        Sparse keyword search over the comment DB.
        Strips stop-words, matches against comment body + post title,
        ranks by recency score.

        Args:
            query:  User query string.
            top_n:  Max results to return.

        Returns:
            list[dict] of matching comment rows sorted by recency_score desc.
        """
        comments = self.load_database()
        terms = [
            t.lower() for t in query.split()
            if len(t) > 2 and t.lower() not in self.SKIP_WORDS
        ]
        results = [
            c for c in comments
            if any(t in (c["comment_body"] + " " + c["post_title"]).lower() for t in terms)
        ]
        results.sort(key=lambda x: x["recency_score"], reverse=True)
        return results[:top_n]

    def semantic_search(self, query: str, top_n: int = 15) -> list[dict]:
        """
        Hybrid semantic search: cosine similarity over sentence embeddings,
        boosted by exact phrase / word matches.

        Args:
            query:  User query string.
            top_n:  Max results to return.

        Returns:
            list[dict] of comment rows sorted by boosted similarity score desc.
        """
        self._ensure_index()

        q_emb  = self._embed_model.encode([query])
        q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-8)
        scores = (self._embeddings_normed @ q_norm.T).flatten().copy()

        # Phrase-match boost
        q_clean = query.lower()
        for stop in [
            "in san francisco", "san francisco", " sf ", "best ",
            "good ", "great ", "top ", "shop", "shops", "place", "places",
        ]:
            q_clean = q_clean.replace(stop, " ")
        q_clean = " ".join(q_clean.split())

        match_phrases    = [q_clean] if len(q_clean) > 2 else []
        individual_words = [w for w in q_clean.split() if len(w) > 3]

        if match_phrases or individual_words:
            for i, c in enumerate(self._indexed_comments):
                searchable = (c["comment_body"] + " " + c["post_title"]).lower()
                if any(p in searchable for p in match_phrases):
                    scores[i] *= 2.0
                elif any(w in searchable.split() for w in individual_words):
                    scores[i] *= 1.3

        top_idx = np.argsort(scores)[::-1][:top_n]
        return [self._indexed_comments[i] for i in top_idx]

    # ── 5. Restaurant Extraction & Ranking ────────────────────────────────────

    def _extract_restaurants_from_comment(self, comment_body: str) -> list[str]:
        """
        Claude Haiku reads a comment and returns a list of restaurant names.

        Args:
            comment_body: Raw comment text.

        Returns:
            list[str] of restaurant/establishment names (may be empty).
        """
        prompt = (
            "Extract all restaurant, cafe, bar, or food establishment names mentioned "
            "in this Reddit comment.\n"
            "Return ONLY a JSON array of names — no commentary, no explanation.\n"
            "If no specific places are named, return [].\n\n"
            f"Comment: {comment_body[:self.MAX_COMMENT_CHARS_FOR_LLM]}\n\n"
            'Examples:\n'
            '"Try Nopalito and Tartine" -> ["Nopalito", "Tartine"]\n'
            '"I love the burritos there" -> []\n'
            '"Bi-Rite is overrated, Garden Creamery is better" -> ["Bi-Rite", "Garden Creamery"]'
        )
        try:
            response = self.claude.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
            names = json.loads(text)
            if isinstance(names, list):
                return [str(n).strip() for n in names if n and isinstance(n, (str, int, float))]
        except Exception:
            pass
        return []

    def _normalize_key(self, name: str) -> str:
        """Dedup key: 'Bi-Rite Creamery' / 'Bi-Rite' / 'bi rite' → same key."""
        key = re.sub(r"[\-'\s\.,&]", "", name.lower().strip())
        for suffix in ["restaurant", "cafe", "bar", "creamery", "bakery", "sf", "thesf"]:
            if key.endswith(suffix) and len(key) > len(suffix) + 2:
                key = key[: -len(suffix)]
        return key or name.lower()

    def _aggregate_and_rank(self, comments: list[dict], top_k: int) -> list[dict]:
        """
        Extract restaurant names from comments via Haiku, then aggregate and
        rank by (recency × sum) + log-upvotes + subreddit diversity.

        Args:
            comments: list[dict] from semantic_search() or keyword_search().
            top_k:    Number of top restaurants to return.

        Returns:
            list[dict] of ranked restaurant dicts.
        """
        restaurants: dict = defaultdict(lambda: {"display_name": None, "mentions": []})

        print(f"Extracting restaurants from {len(comments)} comments...")
        for comment in comments:
            names = self._extract_restaurants_from_comment(comment["comment_body"])
            for name in names:
                key = self._normalize_key(name)
                if not key:
                    continue
                current = restaurants[key]["display_name"]
                if current is None or len(name) > len(current):
                    restaurants[key]["display_name"] = name
                restaurants[key]["mentions"].append({
                    "comment_id":    comment["comment_id"],
                    "body":          comment["comment_body"],
                    "recency_score": comment["recency_score"],
                    "upvotes":       comment.get("comment_upvotes", 0),
                    "subreddit":     comment["subreddit"],
                    "date":          comment["comment_date"],
                    "age_days":      comment["comment_age_days"],
                    "post_title":    comment["post_title"],
                    "url":           comment["post_url"],
                })

        ranked = []
        for key, data in restaurants.items():
            mentions        = data["mentions"]
            recency_sum     = sum(m["recency_score"] for m in mentions)
            upvote_boost    = sum(math.log1p(max(m["upvotes"], 0)) for m in mentions)
            sub_diversity   = len(set(m["subreddit"] for m in mentions))
            score = (
                self.W_RECENCY   * recency_sum
                + self.W_UPVOTES * upvote_boost
                + self.W_DIVERSITY * sub_diversity
            )
            ranked.append({
                "display_name":  data["display_name"],
                "key":           key,
                "mentions":      mentions,
                "mention_count": len(mentions),
                "score":         round(score, 3),
                "avg_recency":   round(recency_sum / len(mentions), 3),
                "max_upvotes":   max((m["upvotes"] for m in mentions), default=0),
                "subreddits":    sorted(set(m["subreddit"] for m in mentions)),
                "latest_date":   max(m["date"] for m in mentions),
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]

    # ── 6. LLM Context Formatter ──────────────────────────────────────────────

    def format_as_llm_context(self, query: str, ranked: list[dict], n_retrieved: int) -> str:
        """
        Format aggregated Reddit results as a clean context string for the
        orchestration layer. Mirrors Yelp/Google Maps formatter shape.

        Args:
            query:       Original user query string.
            ranked:      list[dict] from _aggregate_and_rank().
            n_retrieved: Number of comments retrieved before ranking.

        Returns:
            Formatted context string.
        """
        subs_display = " + ".join(f"r/{s}" for s in self.SUBREDDITS)

        lines = [
            f'Reddit restaurant recommendations for: "{query}"',
            f"Retrieved {len(ranked)} restaurants (sorted by community score)",
            f"Retrieval: semantic search ({self.EMBEDDING_MODEL}) over {n_retrieved} top-matched comments",
            f"Corpus: {subs_display}, {self.MAX_AGE_DAYS}-day window, up to {self.TOP_COMMENTS} comments per post",
            f"Scoring: {self.W_RECENCY}×recency_sum + {self.W_UPVOTES}×log_upvotes + {self.W_DIVERSITY}×subreddit_diversity",
            "=" * 60,
            "",
        ]

        if not ranked:
            lines.append("No restaurants extracted from the retrieved comments.")
            lines.append(
                "(Query may be under-represented in the Reddit corpus. "
                "Orchestrator should rely on Yelp/Google for this category.)"
            )
            return "\n".join(lines)

        for i, r in enumerate(ranked, 1):
            top_mention = max(r["mentions"], key=lambda m: (m["upvotes"], m["recency_score"]))
            sample = top_mention["body"][: self.SAMPLE_COMMENT_CHARS]
            if len(top_mention["body"]) > self.SAMPLE_COMMENT_CHARS:
                sample += "..."

            subs_str       = ", ".join(f"r/{s}" for s in r["subreddits"])
            unique_comments = len(set(m["comment_id"] for m in r["mentions"]))

            lines += [
                f"RESTAURANT {i}",
                f"  Name: {r['display_name']}",
                f"  Community Score: {r['score']} (higher = more buzz)",
                f"  Mention Count: {r['mention_count']} (across {unique_comments} comments)",
                f"  Avg Recency Score: {r['avg_recency']} (1.0=today, 0.0={self.MAX_AGE_DAYS} days ago)",
                f"  Top Upvoted Mention: {r['max_upvotes']} upvotes",
                f"  Subreddits: {subs_str}",
                f"  Latest Mention: {r['latest_date']}",
                f"  Community Quote:",
                f'    "{sample}"',
                f"    — r/{top_mention['subreddit']}, {top_mention['date']}, {top_mention['upvotes']} upvotes",
                f"  Source: Reddit | {top_mention['url']}",
                "",
            ]

        return "\n".join(lines)

    # ── 7. Full Pipeline ──────────────────────────────────────────────────────

    def run_pipeline(self, query: str) -> str:
        """
        Run the full Reddit pipeline end-to-end from a natural-language query.

        Steps:
            1. semantic_search()        — retrieve top matching comments
            2. _aggregate_and_rank()    — LLM extract + score restaurants
            3. format_as_llm_context()  — format for orchestration layer

        Args:
            query: Full user query (e.g. "Best Taco Shop in San Francisco").

        Returns:
            Formatted LLM context string.
        """
        print(f"── Semantic search: {query} ──")
        comments = self.semantic_search(query, top_n=self.TOP_COMMENTS_RETRIEVE)

        print(f"\n── Extracting & ranking restaurants from {len(comments)} comments ──")
        ranked = self._aggregate_and_rank(comments, top_k=self.TOP_RESTAURANTS_OUTPUT)

        print("\n── Formatting for LLM ──")
        return self.format_as_llm_context(query, ranked, len(comments))