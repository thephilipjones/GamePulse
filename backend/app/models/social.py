"""
Social media data models for GamePulse (Epic 4).

Contains raw social media post storage models for:
- Bluesky (atproto): RawBlueskyPost

Each model uses dual storage strategy:
1. Parsed columns for efficient querying and game matching
2. raw_json JSONB for complete data preservation and future ML

All tables are TimescaleDB hypertables for time-series optimization.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Numeric, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB
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
