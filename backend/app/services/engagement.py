"""
Engagement score calculations for social media posts (Story 4-4).

Platform-specific engagement formulas:
- Reddit: score (upvotes - downvotes) + number of comments
- Bluesky: like_count + reply_count (from raw_json)

These scores are used for prioritizing posts in the transform layer.
"""

from typing import Any


def calculate_reddit_engagement(score: int | None, num_comments: int | None) -> float:
    """
    Calculate engagement score for Reddit posts.

    Formula: score + num_comments
    - score: Upvotes minus downvotes (Reddit's "karma" for the post)
    - num_comments: Total comment count

    Args:
        score: Reddit post score (upvotes - downvotes)
        num_comments: Number of comments on the post

    Returns:
        Engagement score (defaults to 0.0 if both inputs are None)

    Examples:
        >>> calculate_reddit_engagement(100, 25)
        125.0
        >>> calculate_reddit_engagement(50, None)
        50.0
        >>> calculate_reddit_engagement(None, None)
        0.0
    """
    score_val = score if score is not None else 0
    comments_val = num_comments if num_comments is not None else 0
    return float(score_val + comments_val)


def calculate_bluesky_engagement(raw_json: dict[str, Any]) -> float:
    """
    Calculate engagement score for Bluesky posts.

    Formula: like_count + reply_count
    - like_count: Number of likes on the post
    - reply_count: Number of replies to the post

    Args:
        raw_json: Complete Bluesky post JSON from API response

    Returns:
        Engagement score (defaults to 0.0 if metrics are missing)

    Examples:
        >>> raw_json = {"likeCount": 42, "replyCount": 8}
        >>> calculate_bluesky_engagement(raw_json)
        50.0
        >>> raw_json = {"likeCount": 10}  # Missing replyCount
        >>> calculate_bluesky_engagement(raw_json)
        10.0
        >>> raw_json = {}  # No engagement metrics
        >>> calculate_bluesky_engagement(raw_json)
        0.0
    """
    like_count = raw_json.get("likeCount", 0)
    reply_count = raw_json.get("replyCount", 0)
    return float(like_count + reply_count)
