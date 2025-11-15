"""
Reddit API client with token bucket rate limiting for GamePulse (Epic 4).

Implements unauthenticated Reddit JSON endpoint access with 10 QPM rate limit.
Uses token bucket algorithm for burst capacity and accurate rate limiting.

WARNING: This client uses unauthorized scraping which violates Reddit's ToS.
For educational/portfolio purposes only - see README for legal disclaimer.
"""

import asyncio
import time
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger()


class TokenBucket:
    """
    Token bucket rate limiter implementing 10 queries per minute (QPM).

    Features:
    - Burst capacity: Up to 10 immediate requests when idle
    - Accurate QPM enforcement: Tokens refill at 10/minute rate
    - Async-friendly: Uses asyncio.sleep when tokens depleted
    """

    def __init__(self, rate: int = 10, capacity: int = 10):
        """
        Initialize token bucket rate limiter.

        Args:
            rate: Tokens added per minute (default: 10 QPM)
            capacity: Maximum burst capacity (default: 10 tokens)
        """
        self.rate = rate  # Tokens per minute
        self.capacity = capacity  # Max tokens
        self.tokens = float(capacity)  # Current available tokens
        self.last_update = time.time()  # Last refill timestamp

    async def acquire(self) -> None:
        """
        Acquire a token from the bucket, waiting if necessary.

        Refills tokens based on elapsed time since last update.
        Blocks asynchronously if tokens depleted (wait = time to refill 1 token).
        """
        # Refill tokens based on elapsed time
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * (self.rate / 60.0))
        self.last_update = now

        # Wait if no tokens available
        if self.tokens < 1.0:
            wait_time = (1.0 - self.tokens) * (60.0 / self.rate)
            logger.debug(
                "rate_limit_wait",
                wait_seconds=round(wait_time, 2),
                tokens_available=round(self.tokens, 2),
                rate_qpm=self.rate,
            )
            await asyncio.sleep(wait_time)
            self.tokens = 0.0
            self.last_update = time.time()
        else:
            self.tokens -= 1.0


class RedditClient:
    """
    Async Reddit API client with token bucket rate limiting (10 QPM).

    Features:
    - Unauthenticated JSON endpoint access (/r/subreddit/new.json)
    - Token bucket rate limiting (10 queries per minute)
    - Retry logic (3 attempts, exponential backoff)
    - Structured logging (fetch_started, fetch_completed, fetch_failed)
    - Respectful User-Agent header

    Usage:
        async with RedditClient() as client:
            posts = await client.fetch_posts("CollegeBasketball", limit=100)
    """

    BASE_URL = "https://www.reddit.com"
    DEFAULT_TIMEOUT = 30.0  # Reddit can be slow

    def __init__(self):
        """Initialize Reddit client with httpx AsyncClient and token bucket."""
        self.client: httpx.AsyncClient | None = None
        self.rate_limiter = TokenBucket(
            rate=settings.REDDIT_RATE_LIMIT_QPM,
            capacity=settings.REDDIT_RATE_LIMIT_QPM,
        )
        logger.info(
            "reddit_client_initialized",
            base_url=self.BASE_URL,
            rate_limit_qpm=settings.REDDIT_RATE_LIMIT_QPM,
            user_agent=settings.REDDIT_USER_AGENT,
        )

    async def __aenter__(self) -> "RedditClient":
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=self.DEFAULT_TIMEOUT,
            headers={"User-Agent": settings.REDDIT_USER_AGENT},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self.client:
            await self.client.aclose()
            logger.info("reddit_client_closed")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def fetch_posts(
        self,
        subreddit: str,
        limit: int = 100,
        after: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch posts from a subreddit using unauthenticated JSON endpoint.

        Args:
            subreddit: Subreddit name without /r/ prefix (e.g., "CollegeBasketball")
            limit: Number of posts to fetch (default: 100, max: 100)
            after: Reddit pagination cursor (post fullname like "t3_abc123")

        Returns:
            Reddit API JSON response dict with structure:
            {
                "kind": "Listing",
                "data": {
                    "children": [{"kind": "t3", "data": {...post...}}, ...],
                    "after": "t3_next_cursor",
                    "before": null
                }
            }

        Raises:
            httpx.HTTPStatusError: On HTTP error responses (429, 503, etc.)
            httpx.RequestError: On network/timeout errors
        """
        if not self.client:
            raise RuntimeError(
                "RedditClient not initialized. Use async with context manager."
            )

        # Enforce rate limit before making request
        await self.rate_limiter.acquire()

        # Build request URL
        url = f"{self.BASE_URL}/r/{subreddit}/new.json"
        params: dict[str, Any] = {"limit": min(limit, 100)}  # Reddit max is 100
        if after:
            params["after"] = after

        logger.info(
            "reddit_fetch_started",
            subreddit=subreddit,
            limit=limit,
            after=after,
            url=url,
        )

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx

            data = response.json()

            # Extract post count from response
            posts_count = len(data.get("data", {}).get("children", []))
            logger.info(
                "reddit_fetch_completed",
                subreddit=subreddit,
                posts_count=posts_count,
                has_more=data.get("data", {}).get("after") is not None,
            )

            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "reddit_http_error",
                subreddit=subreddit,
                status_code=e.response.status_code,
                url=url,
                error=str(e),
            )
            raise

        except httpx.RequestError as e:
            logger.error(
                "reddit_fetch_failed",
                subreddit=subreddit,
                url=url,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise
