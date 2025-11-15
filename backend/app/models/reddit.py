"""
Reddit data models for GamePulse social media integration (Epic 4).

Models:
- DimSport: Sport reference dimension for subreddit-sport mappings
- DimSubreddit: Subreddit configuration dimension
- SubredditSportMapping: Many-to-many junction table
- RawRedditPost: Raw Reddit post storage with complete JSON preservation

TimescaleDB hypertable: raw_reddit_posts partitioned on fetched_at (1-day chunks).
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class DimSport(SQLModel, table=True):
    """
    Sport reference dimension for subreddit-sport many-to-many mappings.

    Used to map subreddits to relevant sports for game matching in Story 4-4.
    """

    __tablename__ = "dim_sport"

    sport_key: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )
    sport_code: str = Field(
        unique=True, index=True, max_length=10
    )  # "ncaam", "nfl", etc.
    sport_name: str = Field(max_length=50)  # "NCAA Men's Basketball", "NFL"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class DimSubreddit(SQLModel, table=True):
    """
    Subreddit configuration dimension.

    Defines which subreddits to poll and their active status.
    Many-to-many relationship with sports via SubredditSportMapping.
    """

    __tablename__ = "dim_subreddit"

    subreddit_key: int = Field(
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    subreddit_name: str = Field(
        unique=True, index=True, max_length=50
    )  # "CollegeBasketball" (no /r/)
    reddit_url: str = Field(
        max_length=200
    )  # "https://www.reddit.com/r/CollegeBasketball"
    is_active: bool = Field(default=True, index=True)  # Enable/disable polling
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class SubredditSportMapping(SQLModel, table=True):
    """
    Many-to-many junction table between subreddits and sports.

    Examples:
    - r/CollegeBasketball → ncaam only
    - r/sports → ncaam, ncaaf, nfl, nba, etc. (multi-sport)
    """

    __tablename__ = "subreddit_sport_mapping"

    subreddit_key: int = Field(
        foreign_key="dim_subreddit.subreddit_key", primary_key=True
    )
    sport_key: int = Field(foreign_key="dim_sport.sport_key", primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class RawRedditPost(SQLModel, table=True):
    """
    Raw Reddit post storage with dual storage strategy:
    1. Parsed columns for efficient querying (post_id, title, score, etc.)
    2. raw_json JSONB for complete preservation and future ML experimentation

    TimescaleDB hypertable partitioned on fetched_at (1-day chunks).
    Retention: 90 days, compression after 7 days.

    Note: Composite PK (post_id, fetched_at) required by TimescaleDB hypertable partitioning.
    """

    __tablename__ = "raw_reddit_posts"
    __table_args__ = (
        PrimaryKeyConstraint("post_id", "fetched_at", name="raw_reddit_posts_pkey"),
    )

    # Composite primary key columns
    post_id: str = Field(max_length=50, index=True)  # Reddit ID like "t3_abc123"
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )

    # Subreddit and post creation time
    subreddit: str = Field(
        foreign_key="dim_subreddit.subreddit_name", index=True, max_length=50
    )
    post_created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), index=True, nullable=False)
    )

    # Parsed metadata columns (for efficient querying)
    author: str | None = Field(default=None, max_length=50)  # null if deleted
    title: str | None = Field(default=None)  # TEXT type (no max_length)
    selftext: str | None = Field(default=None)  # Post body for self posts
    score: int | None = Field(default=None)  # Upvotes - downvotes
    num_comments: int | None = Field(default=None)
    upvote_ratio: float | None = Field(default=None)  # 0.0-1.0
    permalink: str | None = Field(default=None, max_length=500)
    flair_text: str | None = Field(default=None, max_length=100)
    post_type: str | None = Field(
        default=None, max_length=20
    )  # "link", "self", "image", "video"

    # Raw JSON storage (complete Reddit API response)
    raw_json: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
        description="Complete Reddit post JSON for future analysis",
    )

    # Game matching fields (for Story 4-4 transform layer)
    matched_to_game: bool = Field(default=False)
    match_confidence: float | None = Field(
        default=None,
        sa_column=Column(Numeric(precision=3, scale=2)),  # 0.00-1.00
    )
    processed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

    class Config:
        arbitrary_types_allowed = True  # Allow JSONB type
