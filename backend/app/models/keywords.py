"""
Unified keyword models for multi-platform social media extraction (Epic 4).

Models:
- DimKeyword: Unified keyword configuration (replaces DimSubreddit)
- KeywordSportMapping: Many-to-many junction table for keyword-sport relationships

Supports Reddit subreddits and Bluesky hashtags with platform and keyword_type
discrimination for future extensibility (e.g., user searches, custom feeds).

Created in Story 4-4 to consolidate Reddit and Bluesky keyword management.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime
from sqlmodel import Field, SQLModel


class DimKeyword(SQLModel, table=True):
    """
    Unified keyword configuration for Reddit subreddits and Bluesky hashtags.

    Supports multi-platform social media extraction with many-to-many sport mappings.
    Replaces DimSubreddit with added platform and keyword_type for extensibility.

    Platform discrimination allows same keyword on different platforms:
    - Example: "CollegeBasketball" exists as both Reddit subreddit and Bluesky hashtag

    Keyword type enables future expansion:
    - Reddit: subreddit (current), user_search (future), custom_feed (future)
    - Bluesky: hashtag (current), custom_feed (future), user_mentions (future)
    """

    __tablename__ = "dim_keyword"

    keyword_key: int = Field(
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        description="Surrogate key for keyword",
    )
    keyword_value: str = Field(
        max_length=100,
        description="Keyword text (subreddit name or hashtag without prefix)",
    )
    platform: str = Field(max_length=20, description="Platform: reddit or bluesky")
    keyword_type: str = Field(
        max_length=20,
        description="Type: subreddit, hashtag, user_search, or custom_feed",
    )
    url: str | None = Field(
        default=None,
        max_length=300,
        description="Platform URL (required for Reddit subreddits, null for Bluesky hashtags)",
    )
    is_active: bool = Field(
        default=True,
        index=True,
        description="Enable/disable polling for this keyword",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class KeywordSportMapping(SQLModel, table=True):
    """
    Many-to-many junction table between keywords and sports.

    Enables multi-sport keywords (e.g., Reddit /r/sports covers all 8 sports).
    Replaces SubredditSportMapping with unified keyword approach.

    Examples:
    - Bluesky #CollegeBasketball → ncaam only
    - Reddit /r/sports → ncaam, ncaaf, nfl, nba, etc. (multi-sport)
    """

    __tablename__ = "keyword_sport_mapping"

    keyword_key: int = Field(foreign_key="dim_keyword.keyword_key", primary_key=True)
    sport_key: int = Field(foreign_key="dim_sport.sport_key", primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
