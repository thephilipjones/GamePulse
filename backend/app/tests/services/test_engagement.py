"""
Unit tests for engagement score calculations (Story 4-4).

Tests platform-specific engagement formulas:
- Reddit: score + num_comments
- Bluesky: likeCount + replyCount
"""

import pytest

from app.services.engagement import (
    calculate_bluesky_engagement,
    calculate_reddit_engagement,
)


class TestRedditEngagement:
    """Test suite for Reddit engagement score calculation."""

    def test_normal_engagement(self) -> None:
        """Test normal case with both score and comments."""
        score = calculate_reddit_engagement(score=100, num_comments=25)
        assert score == 125.0

    def test_high_score_low_comments(self) -> None:
        """Test highly upvoted post with few comments."""
        score = calculate_reddit_engagement(score=5000, num_comments=10)
        assert score == 5010.0

    def test_low_score_high_comments(self) -> None:
        """Test controversial post with many comments."""
        score = calculate_reddit_engagement(score=5, num_comments=500)
        assert score == 505.0

    def test_negative_score(self) -> None:
        """Test downvoted post (negative score)."""
        score = calculate_reddit_engagement(score=-10, num_comments=15)
        assert score == 5.0

    def test_zero_score(self) -> None:
        """Test post with zero score."""
        score = calculate_reddit_engagement(score=0, num_comments=10)
        assert score == 10.0

    def test_zero_comments(self) -> None:
        """Test post with no comments."""
        score = calculate_reddit_engagement(score=100, num_comments=0)
        assert score == 100.0

    def test_none_score(self) -> None:
        """Test missing score (defaults to 0)."""
        score = calculate_reddit_engagement(score=None, num_comments=25)
        assert score == 25.0

    def test_none_comments(self) -> None:
        """Test missing comments (defaults to 0)."""
        score = calculate_reddit_engagement(score=50, num_comments=None)
        assert score == 50.0

    def test_both_none(self) -> None:
        """Test both score and comments missing (defaults to 0)."""
        score = calculate_reddit_engagement(score=None, num_comments=None)
        assert score == 0.0

    def test_both_zero(self) -> None:
        """Test post with zero engagement."""
        score = calculate_reddit_engagement(score=0, num_comments=0)
        assert score == 0.0


class TestBlueskyEngagement:
    """Test suite for Bluesky engagement score calculation."""

    def test_normal_engagement(self) -> None:
        """Test normal case with likes and replies."""
        raw_json: dict[str, int] = {"likeCount": 42, "replyCount": 8}
        score = calculate_bluesky_engagement(raw_json)
        assert score == 50.0

    def test_high_likes_low_replies(self) -> None:
        """Test viral post with many likes, few replies."""
        raw_json: dict[str, int] = {"likeCount": 1000, "replyCount": 5}
        score = calculate_bluesky_engagement(raw_json)
        assert score == 1005.0

    def test_low_likes_high_replies(self) -> None:
        """Test discussion post with few likes, many replies."""
        raw_json: dict[str, int] = {"likeCount": 10, "replyCount": 100}
        score = calculate_bluesky_engagement(raw_json)
        assert score == 110.0

    def test_only_likes(self) -> None:
        """Test post with likes but no replies."""
        raw_json: dict[str, int] = {"likeCount": 50}
        score = calculate_bluesky_engagement(raw_json)
        assert score == 50.0

    def test_only_replies(self) -> None:
        """Test post with replies but no likes."""
        raw_json: dict[str, int] = {"replyCount": 30}
        score = calculate_bluesky_engagement(raw_json)
        assert score == 30.0

    def test_zero_engagement(self) -> None:
        """Test post with zero likes and replies."""
        raw_json: dict[str, int] = {"likeCount": 0, "replyCount": 0}
        score = calculate_bluesky_engagement(raw_json)
        assert score == 0.0

    def test_empty_json(self) -> None:
        """Test post with missing engagement metrics."""
        raw_json: dict[str, int] = {}
        score = calculate_bluesky_engagement(raw_json)
        assert score == 0.0

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields in raw_json are ignored."""
        raw_json: dict[str, int] = {
            "likeCount": 25,
            "replyCount": 10,
            "repostCount": 5,  # Extra field (not used in formula)
            "quoteCount": 2,  # Extra field (not used in formula)
        }
        score = calculate_bluesky_engagement(raw_json)
        assert score == 35.0  # Only likes + replies

    def test_returns_float(self) -> None:
        """Test that function always returns float type."""
        raw_json: dict[str, int] = {"likeCount": 10, "replyCount": 5}
        score = calculate_bluesky_engagement(raw_json)
        assert isinstance(score, float)


class TestEngagementEdgeCases:
    """Test suite for edge cases across both platforms."""

    def test_reddit_very_large_numbers(self) -> None:
        """Test Reddit with very large engagement numbers."""
        score = calculate_reddit_engagement(score=1000000, num_comments=50000)
        assert score == 1050000.0

    def test_bluesky_very_large_numbers(self) -> None:
        """Test Bluesky with very large engagement numbers."""
        raw_json: dict[str, int] = {"likeCount": 500000, "replyCount": 25000}
        score = calculate_bluesky_engagement(raw_json)
        assert score == 525000.0

    def test_reddit_negative_comments_invalid(self) -> None:
        """Test Reddit with negative comments (invalid data)."""
        # In practice, this shouldn't happen, but function should handle it
        score = calculate_reddit_engagement(score=100, num_comments=-5)
        assert score == 95.0

    @pytest.mark.parametrize(
        "reddit_score,num_comments,expected",
        [
            (100, 25, 125.0),
            (0, 0, 0.0),
            (None, None, 0.0),
            (-10, 10, 0.0),
            (1000, 0, 1000.0),
        ],
    )
    def test_reddit_parameterized(
        self, reddit_score: int | None, num_comments: int | None, expected: float
    ) -> None:
        """Parameterized tests for Reddit engagement."""
        score = calculate_reddit_engagement(reddit_score, num_comments)
        assert score == expected

    @pytest.mark.parametrize(
        "raw_json,expected",
        [
            ({"likeCount": 10, "replyCount": 5}, 15.0),
            ({"likeCount": 0, "replyCount": 0}, 0.0),
            ({}, 0.0),
            ({"likeCount": 100}, 100.0),
            ({"replyCount": 50}, 50.0),
        ],
    )
    def test_bluesky_parameterized(
        self, raw_json: dict[str, int], expected: float
    ) -> None:
        """Parameterized tests for Bluesky engagement."""
        score = calculate_bluesky_engagement(raw_json)
        assert score == expected
