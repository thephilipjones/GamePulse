"""
Unit tests for sentiment analysis service (Story 4-5).

Tests VADER sentiment analysis wrapper with various inputs.
"""

from app.services.sentiment_analyzer import analyze_sentiment, classify_sentiment


class TestAnalyzeSentiment:
    """Test analyze_sentiment function."""

    def test_positive_sentiment(self) -> None:
        """Test positive sentiment text."""
        text = "Duke crushed UNC! Amazing game! Best performance ever!"
        result = analyze_sentiment(text)

        assert "compound" in result
        assert "positive" in result
        assert "negative" in result
        assert "neutral" in result

        # Positive text should have positive compound score
        assert result["compound"] > 0.05
        # Positive score should be higher than negative
        assert result["positive"] > result["negative"]

    def test_negative_sentiment(self) -> None:
        """Test negative sentiment text."""
        text = "Terrible performance, total disaster, awful game"
        result = analyze_sentiment(text)

        assert "compound" in result
        assert "positive" in result
        assert "negative" in result
        assert "neutral" in result

        # Negative text should have negative compound score
        assert result["compound"] < -0.05
        # Negative score should be higher than positive
        assert result["negative"] > result["positive"]

    def test_neutral_sentiment(self) -> None:
        """Test neutral sentiment text."""
        text = "The game happened on Saturday at the arena."
        result = analyze_sentiment(text)

        assert "compound" in result
        # Neutral text should have compound score near zero
        assert -0.05 <= result["compound"] <= 0.05

    def test_mixed_sentiment(self) -> None:
        """Test text with mixed sentiment."""
        text = "Great offense but terrible defense, mixed feelings"
        result = analyze_sentiment(text)

        assert "compound" in result
        assert "positive" in result
        assert "negative" in result

        # Mixed sentiment should have both positive and negative scores
        assert result["positive"] > 0
        assert result["negative"] > 0

    def test_empty_string(self) -> None:
        """Test empty string returns neutral scores."""
        result = analyze_sentiment("")

        assert result == {
            "compound": 0.0,
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
        }

    def test_whitespace_only(self) -> None:
        """Test whitespace-only string returns neutral scores."""
        result = analyze_sentiment("   \n\t  ")

        assert result == {
            "compound": 0.0,
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
        }

    def test_none_value(self) -> None:
        """Test None value returns neutral scores."""
        result = analyze_sentiment(None)

        assert result == {
            "compound": 0.0,
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
        }

    def test_score_ranges(self) -> None:
        """Test that all scores are within valid ranges."""
        text = "This is a test sentence with some words."
        result = analyze_sentiment(text)

        # Compound score should be between -1 and 1
        assert -1.0 <= result["compound"] <= 1.0

        # Individual scores should be between 0 and 1
        assert 0.0 <= result["positive"] <= 1.0
        assert 0.0 <= result["negative"] <= 1.0
        assert 0.0 <= result["neutral"] <= 1.0

        # Individual scores should sum to approximately 1 (within rounding error)
        total = result["positive"] + result["negative"] + result["neutral"]
        assert 0.99 <= total <= 1.01

    def test_emojis_and_special_chars(self) -> None:
        """Test sentiment analysis with emojis and special characters."""
        text = "Great win! 🏀🔥 #MarchMadness"
        result = analyze_sentiment(text)

        # Should still return valid scores
        assert "compound" in result
        assert -1.0 <= result["compound"] <= 1.0


class TestClassifySentiment:
    """Test classify_sentiment function."""

    def test_positive_classification(self) -> None:
        """Test positive score classification."""
        assert classify_sentiment(0.8) == "positive"
        assert classify_sentiment(0.05) == "positive"
        assert classify_sentiment(1.0) == "positive"

    def test_negative_classification(self) -> None:
        """Test negative score classification."""
        assert classify_sentiment(-0.8) == "negative"
        assert classify_sentiment(-0.05) == "negative"
        assert classify_sentiment(-1.0) == "negative"

    def test_neutral_classification(self) -> None:
        """Test neutral score classification."""
        assert classify_sentiment(0.0) == "neutral"
        assert classify_sentiment(0.04) == "neutral"
        assert classify_sentiment(-0.04) == "neutral"

    def test_boundary_values(self) -> None:
        """Test exact boundary values."""
        # Just above neutral threshold
        assert classify_sentiment(0.050001) == "positive"

        # Just below neutral threshold
        assert classify_sentiment(-0.050001) == "negative"

        # Exactly at neutral boundaries
        assert classify_sentiment(0.049999) == "neutral"
        assert classify_sentiment(-0.049999) == "neutral"
