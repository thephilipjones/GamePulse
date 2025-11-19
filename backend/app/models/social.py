"""
Social media data models for GamePulse (Epic 4).

Contains models for:
- Raw social media posts: RawBlueskyPost
- Unified transform layer: StgSocialPost (Story 4-4)
- Sentiment fact table: FactSocialSentiment (Story 4-5)

Each model uses dual storage strategy:
1. Parsed columns for efficient querying and game matching
2. raw_json JSONB for complete data preservation and future ML

All tables are TimescaleDB hypertables for time-series optimization.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, SQLModel


class RawBlueskyPost(SQLModel, table=True):
    """
    Raw Bluesky post storage with dual storage strategy:
    1. Parsed columns for efficient querying (post_uri, text, author, etc.)
    2. raw_json JSONB for complete preservation and future ML experimentation

    TimescaleDB hypertable partitioned on created_at (1-day chunks).
    Retention: 90 days, compression after 7 days.

    Note: Composite PK (post_uri, created_at) required by TimescaleDB hypertable partitioning.
    Format: "at://did:plc:abc123.../app.bsky.feed.post/xyz456..."
    """

    __tablename__ = "raw_bluesky_posts"
    __table_args__ = (
        PrimaryKeyConstraint("post_uri", "created_at", name="raw_bluesky_posts_pkey"),
    )

    # Composite primary key columns
    post_uri: str = Field(
        max_length=300,
        index=True,
        description="atproto URI (e.g., at://did:plc:abc/app.bsky.feed.post/xyz)",
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
        description="Post creation time from Bluesky (partitioning column)",
    )

    # Content identifier (immutable hash of post content)
    post_cid: str = Field(
        max_length=100,
        description="Content ID (CID) - immutable hash of post record",
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
        description="When this record was fetched from Bluesky API",
    )

    # Author information
    author_did: str = Field(
        max_length=100,
        nullable=False,
        description="Decentralized identifier (DID) of post author",
    )
    author_handle: str | None = Field(
        default=None,
        max_length=100,
        description="Human-readable handle (e.g., user.bsky.social)",
    )

    # Post content
    post_text: str | None = Field(
        default=None,
        description="Post text content (TEXT type for unlimited length)",
    )

    # Raw JSON storage (complete Bluesky API response)
    raw_json: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
        description="Complete Bluesky post JSON for future analysis and ML",
    )

    # Game matching fields (for Story 4-4 transform layer)
    matched_to_game: bool = Field(
        default=False,
        index=True,  # Partial index created in migration for unmatched posts
        description="Whether this post has been matched to a specific game",
    )
    match_confidence: float | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=3, scale=2)),  # 0.00-1.00
        description="Confidence score for game match (0-1 scale)",
    )
    processed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When this post was processed by transform layer",
    )

    class Config:
        arbitrary_types_allowed = True  # Allow JSONB type


class StgSocialPost(SQLModel, table=True):
    """
    Unified staging table for Reddit and Bluesky posts (Story 4-4).

    Transform layer that:
    - Normalizes Reddit and Bluesky posts into common schema
    - Calculates engagement scores for prioritization
    - Maintains game matching metadata
    - Partitioned by created_at for time-series queries (TimescaleDB hypertable)

    Business Logic:
    - Engagement score = platform-specific calculation (Reddit: score + comments, Bluesky: likes + replies)
    - Posts processed incrementally: SELECT WHERE processed_at IS NULL
    - Deduplication by composite PK (platform, post_id)

    Note: Composite PK (platform, post_id) required for cross-platform deduplication.
    """

    __tablename__ = "stg_social_posts"
    __table_args__ = (
        # Composite PK must include created_at for TimescaleDB hypertable partitioning
        PrimaryKeyConstraint(
            "platform", "post_id", "created_at", name="stg_social_posts_pkey"
        ),
    )

    # Surrogate key for foreign key relationships (Story 4-5)
    social_post_key: int | None = Field(
        default=None,
        index=True,
        description="Auto-increment surrogate key for FK relationships with fact_social_sentiment",
    )

    # Composite primary key columns
    platform: str = Field(
        max_length=20,
        description="Source platform: reddit or bluesky",
    )
    post_id: str = Field(
        max_length=300,
        description="Platform-specific post ID (Reddit: t3_abc, Bluesky: URI)",
    )

    # Temporal columns
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
        description="When user created post (partitioning column for TimescaleDB)",
    )
    fetched_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="When we extracted this post",
    )

    # Normalized post content
    author_handle: str | None = Field(
        default=None,
        max_length=100,
        description="Platform-specific author handle",
    )
    post_text: str | None = Field(
        default=None,
        description="Post text content (Reddit: title + selftext, Bluesky: post_text)",
    )

    # Engagement metrics for prioritization
    engagement_score: float = Field(
        description="Platform-normalized engagement (Reddit: score + comments, Bluesky: likes + replies)"
    )

    # Game matching metadata
    matched_to_game: bool = Field(
        default=False,
        index=True,
        description="Has this been matched to a game?",
    )
    match_confidence: float | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=3, scale=2)),  # 0.00-1.00
        description="Game matching confidence (0.00-1.00)",
    )
    matched_teams: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String(50))),
        description="Team IDs matched in post text (e.g., ['ncaam_duke', 'ncaam_unc']) for game_key resolution (Story 4-5)",
    )
    processed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When transform layer processed this (partial index created in migration)",
    )

    # Complete raw data for debugging and ML
    raw_json: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
        description="Original platform JSON for debugging and future ML",
    )

    class Config:
        arbitrary_types_allowed = True  # Allow JSONB type


class FactSocialSentiment(SQLModel, table=True):
    """
    Sentiment-enriched social posts linked to games for Epic 5 (Story 4-5).

    Fact table combining:
    - VADER sentiment analysis scores (compound, positive, negative, neutral)
    - Game key FK resolution for Epic 5 excitement scoring
    - Date key for time-series queries
    - Denormalized post_text and engagement_score for analytics

    TimescaleDB hypertable partitioned on created_at (1-day chunks).
    Retention: 90 days, compression after 7 days.

    Business Logic:
    - Compound >= 0.05: Positive sentiment (excitement, enthusiasm)
    - Compound <= -0.05: Negative sentiment (frustration, disappointment)
    - -0.05 to 0.05: Neutral sentiment (informational)
    - Unique constraint on social_post_key: one sentiment record per post
    """

    __tablename__ = "fact_social_sentiment"

    # Primary key
    sentiment_key: int | None = Field(default=None, primary_key=True)

    # Foreign keys
    game_key: int = Field(foreign_key="fact_game.game_key", index=True)
    date_key: int = Field(foreign_key="dim_date.date_key", index=True)

    # References stg_social_posts.social_post_key (no FK due to TimescaleDB hypertable limitation)
    social_post_key: int = Field(
        index=True,
        description="References stg_social_posts.social_post_key (enforced by app, not FK)",
    )

    # VADER sentiment scores
    sentiment_compound: float = Field(
        sa_column=Column(Numeric(precision=5, scale=4)),
        description="Overall sentiment (-1 to +1): >= 0.05 positive, <= -0.05 negative",
    )
    sentiment_positive: float | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=5, scale=4)),
        description="Positive component (0-1)",
    )
    sentiment_negative: float | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=5, scale=4)),
        description="Negative component (0-1)",
    )
    sentiment_neutral: float | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=5, scale=4)),
        description="Neutral component (0-1)",
    )

    # Denormalized fields for Epic 5 queries
    platform: str = Field(
        max_length=20,
        description="Source platform: reddit or bluesky",
    )
    post_text: str = Field(description="Post text content (denormalized for Epic 5)")
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
        description="When user created post (partitioning column for TimescaleDB)",
    )
    engagement_score: float | None = Field(
        default=None,
        description="Platform-normalized engagement (denormalized for Epic 5)",
    )

    # Metadata
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="When sentiment analysis was performed",
    )

    class Config:
        arbitrary_types_allowed = True  # Allow JSONB type


# ----- API Response Schemas (Story 4-10) -----


class SocialPostPublic(SQLModel):
    """
    Public API response schema for social posts (Story 4-10).

    Used by GET /api/v1/games/{game_id}/social-posts endpoint.
    Contains denormalized data plus derived fields (sentiment_label, source_url).
    """

    social_post_key: int
    platform: str  # "reddit" or "bluesky"
    post_text: str
    created_at: datetime
    engagement_score: int
    sentiment_compound: float  # -1.0 to +1.0
    sentiment_label: str  # Derived: "positive", "neutral", "negative"
    source_url: str  # Constructed from platform-specific fields


class SocialPostListResponse(SQLModel):
    """Response schema for social posts list endpoint (Story 4-10)."""

    posts: list[SocialPostPublic]
    total_count: int
    game_id: str
