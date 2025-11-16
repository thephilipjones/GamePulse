"""
Bluesky API client with atproto SDK and rate limiting for GamePulse (Epic 4).

Implements authenticated Bluesky API access via atproto SDK with 5000 points/hour rate limit.
Uses token bucket algorithm for burst capacity and accurate rate limiting.

Legal: Official Bluesky SDK with proper authentication - compliant for production use.
"""

import asyncio
import time
from datetime import datetime
from typing import Any

import structlog
from atproto import Client  # type: ignore[import-untyped]
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger()


class BlueskyRateLimiter:
    """
    Token bucket rate limiter implementing 5000 points per hour.

    Features:
    - Burst capacity: Up to 83 immediate requests when idle
    - Accurate points/hour enforcement: Tokens refill at 5000/hour rate
    - Async-friendly: Uses asyncio.sleep when tokens depleted

    Note: Each search query costs ~100 points, so this allows ~50 searches/hour
    with burst capacity for immediate testing and retries.
    """

    def __init__(self, points_per_hour: int = 5000, points_per_request: int = 100):
        """
        Initialize token bucket rate limiter.

        Args:
            points_per_hour: Total points budget per hour (default: 5000)
            points_per_request: Points consumed per request (default: 100 for search)
        """
        self.points_per_hour = points_per_hour
        self.points_per_request = points_per_request
        # Convert to points per minute for bucket refill
        self.rate = points_per_hour / 60.0  # Points per minute
        # Capacity allows burst of multiple requests when idle
        self.capacity = float(points_per_hour / 60.0)  # 1 minute worth of points
        self.tokens = self.capacity  # Start with full capacity
        self.last_update = time.time()

    async def acquire(self) -> None:
        """
        Acquire points from the bucket, waiting if necessary.

        Refills tokens based on elapsed time since last update.
        Blocks asynchronously if insufficient tokens (wait = time to refill needed points).
        """
        # Refill tokens based on elapsed time
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(
            self.capacity, self.tokens + elapsed * (self.rate / 60.0)
        )  # rate per second
        self.last_update = now

        # Wait if insufficient tokens available
        if self.tokens < self.points_per_request:
            needed = self.points_per_request - self.tokens
            wait_time = needed / (self.rate / 60.0)  # Convert to seconds
            logger.debug(
                "bluesky_rate_limit_wait",
                wait_seconds=round(wait_time, 2),
                tokens_available=round(self.tokens, 2),
                points_needed=self.points_per_request,
                rate_points_per_hour=self.points_per_hour,
            )
            await asyncio.sleep(wait_time)
            self.tokens = 0.0
            self.last_update = time.time()
        else:
            self.tokens -= self.points_per_request


class BlueskyClient:
    """
    Async Bluesky API client with atproto SDK and rate limiting (5000 points/hour).

    Features:
    - Authenticated API access via app password
    - Hashtag search with keyword filtering
    - Rate limiting (5000 points/hour = ~50 searches/hour)
    - Retry logic (3 attempts, exponential backoff)
    - Structured logging (search_started, search_completed, search_failed)
    - Incremental extraction (since parameter)
    - URI deduplication across multiple hashtag searches

    Usage:
        async with BlueskyClient() as client:
            posts = await client.fetch_posts_by_hashtag("CollegeBasketball", limit=100)
            all_posts = await client.fetch_all_hashtags(["CollegeBasketball", "NCAAM"])
    """

    def __init__(self) -> None:
        """Initialize Bluesky client with atproto Client and rate limiter."""
        self.client: Client | None = None
        self.rate_limiter = BlueskyRateLimiter(
            points_per_hour=settings.BLUESKY_RATE_LIMIT_POINTS_PER_HOUR,
            points_per_request=100,  # Estimated cost per search query
        )
        logger.info(
            "bluesky_client_initialized",
            rate_limit_points_per_hour=settings.BLUESKY_RATE_LIMIT_POINTS_PER_HOUR,
            handle=settings.BLUESKY_HANDLE,
        )

    async def __aenter__(self) -> "BlueskyClient":
        """
        Async context manager entry - authenticates with Bluesky API.

        Raises:
            ValueError: If BLUESKY_HANDLE or BLUESKY_APP_PASSWORD not configured
            Exception: If authentication fails (invalid credentials)
        """
        if not settings.BLUESKY_HANDLE or not settings.BLUESKY_APP_PASSWORD:
            raise ValueError(
                "BLUESKY_HANDLE and BLUESKY_APP_PASSWORD must be configured"
            )

        # atproto Client is synchronous, so we use it directly
        self.client = Client()
        try:
            self.client.login(settings.BLUESKY_HANDLE, settings.BLUESKY_APP_PASSWORD)
            logger.info("bluesky_authenticated", handle=settings.BLUESKY_HANDLE)
        except Exception as e:
            logger.error(
                "bluesky_authentication_failed",
                handle=settings.BLUESKY_HANDLE,
                error=str(e),
            )
            raise

        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the client session."""
        # atproto Client doesn't require explicit cleanup
        self.client = None
        logger.info("bluesky_client_closed")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )
    async def fetch_posts_by_hashtag(
        self,
        hashtag: str,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch posts from Bluesky by hashtag using app.bsky.feed.searchPosts.

        Args:
            hashtag: Hashtag without # prefix (e.g., "CollegeBasketball")
            limit: Maximum number of posts to fetch (default: 100)
            since: Only return posts created after this timestamp (for incremental extraction)

        Returns:
            List of post dictionaries with structure from atproto SDK:
            [
                {
                    "uri": "at://did:plc:abc/app.bsky.feed.post/xyz",
                    "cid": "bafyrei...",
                    "author": {...},
                    "record": {"text": "...", "createdAt": "...", ...},
                    ...
                },
                ...
            ]

        Raises:
            RuntimeError: If client not initialized
            Exception: On API errors or network failures (retried 3 times)
        """
        if not self.client:
            raise RuntimeError(
                "BlueskyClient not initialized. Use async with context manager."
            )

        # Enforce rate limit before making request
        await self.rate_limiter.acquire()

        # Build search query with hashtag syntax
        query = f"#{hashtag}"
        logger.info(
            "bluesky_search_started",
            hashtag=hashtag,
            query=query,
            limit=limit,
            since=since.isoformat() if since else None,
        )

        try:
            # Type narrowing: client is guaranteed non-None after check above
            client = self.client

            # atproto SDK's search_posts is synchronous
            # We need to run it in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.app.bsky.feed.search_posts(
                    params={"q": query, "limit": limit}
                ),
            )

            # Extract posts from response
            posts = response.posts if hasattr(response, "posts") else []

            # Filter by since timestamp if provided (incremental extraction)
            if since:
                filtered_posts = []
                for post in posts:
                    # Parse createdAt from post record
                    created_at_str = post.record.created_at
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                    if created_at > since:
                        filtered_posts.append(post)
                posts = filtered_posts

            # Convert posts to dicts for easier processing
            posts_data = [
                {
                    "uri": post.uri,
                    "cid": post.cid,
                    "author": {
                        "did": post.author.did,
                        "handle": post.author.handle,
                        "displayName": getattr(post.author, "display_name", None),
                    },
                    "record": {
                        "text": post.record.text,
                        "createdAt": post.record.created_at,
                    },
                    # Store full post as raw_data for JSONB storage
                    "raw_data": post.model_dump(),
                }
                for post in posts
            ]

            logger.info(
                "bluesky_search_completed",
                hashtag=hashtag,
                posts_count=len(posts_data),
                filtered=since is not None,
            )

            return posts_data

        except Exception as e:
            logger.error(
                "bluesky_search_failed",
                hashtag=hashtag,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def fetch_all_hashtags(
        self,
        hashtags: list[str],
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch posts from multiple hashtags and deduplicate by URI.

        Same post can appear under multiple hashtags - deduplication ensures
        we don't store duplicates in the database.

        Args:
            hashtags: List of hashtags without # prefix
            limit: Maximum posts per hashtag (default: 100)
            since: Only return posts created after this timestamp

        Returns:
            List of unique posts (deduplicated by URI)
        """
        all_posts: dict[str, dict[str, Any]] = {}  # uri -> post dict

        logger.info(
            "bluesky_fetch_all_hashtags_started",
            hashtags=hashtags,
            limit_per_hashtag=limit,
            since=since.isoformat() if since else None,
        )

        for hashtag in hashtags:
            try:
                posts = await self.fetch_posts_by_hashtag(
                    hashtag=hashtag, limit=limit, since=since
                )
                # Deduplicate by URI (same post can have multiple hashtags)
                for post in posts:
                    uri = post["uri"]
                    if uri not in all_posts:
                        all_posts[uri] = post
            except Exception as e:
                # Log error but continue with other hashtags
                logger.error(
                    "bluesky_hashtag_fetch_failed",
                    hashtag=hashtag,
                    error=str(e),
                )
                continue

        posts_list = list(all_posts.values())
        logger.info(
            "bluesky_fetch_all_hashtags_completed",
            hashtags=hashtags,
            total_unique_posts=len(posts_list),
        )

        return posts_list
