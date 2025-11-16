"""
Sentiment analysis service using VADER (Valence Aware Dictionary and sEntiment Reasoner).

VADER is a lexicon and rule-based sentiment analysis tool specifically attuned to
sentiments expressed in social media. It provides sentiment scores for positive,
negative, and neutral affect, plus a compound score.

Story 4-5: Sentiment Analysis & Fact Table
"""

import structlog
from vaderSentiment.vaderSentiment import (  # type: ignore[import-untyped]
    SentimentIntensityAnalyzer,
)

logger = structlog.get_logger()

# Initialize VADER analyzer once at module level (singleton pattern)
_analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str | None) -> dict[str, float]:
    """
    Analyze sentiment of text using VADER.

    Args:
        text: Post text to analyze. Can be None or empty string.

    Returns:
        Dictionary with sentiment scores:
        - compound: Overall sentiment score from -1 (negative) to +1 (positive)
          - >= 0.05: positive
          - <= -0.05: negative
          - between -0.05 and 0.05: neutral
        - positive: Proportion of positive affect (0 to 1)
        - negative: Proportion of negative affect (0 to 1)
        - neutral: Proportion of neutral affect (0 to 1)

    Examples:
        >>> analyze_sentiment("Duke crushed UNC! Amazing game!")
        {'compound': 0.8519, 'positive': 0.661, 'negative': 0.0, 'neutral': 0.339}

        >>> analyze_sentiment("Terrible performance, total disaster")
        {'compound': -0.8074, 'positive': 0.0, 'negative': 0.608, 'neutral': 0.392}

        >>> analyze_sentiment(None)
        {'compound': 0.0, 'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
    """
    # Handle None or empty text
    if not text or not text.strip():
        logger.debug("sentiment_analysis_empty_text")
        return {
            "compound": 0.0,
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,  # Empty text is neutral
        }

    # VADER returns: {'neg': 0.0, 'neu': 0.339, 'pos': 0.661, 'compound': 0.8519}
    scores = _analyzer.polarity_scores(text)

    # Normalize keys to match our database schema
    return {
        "compound": scores["compound"],
        "positive": scores["pos"],
        "negative": scores["neg"],
        "neutral": scores["neu"],
    }


def classify_sentiment(compound_score: float) -> str:
    """
    Classify sentiment based on VADER compound score.

    Args:
        compound_score: Compound sentiment score from -1 to +1

    Returns:
        Sentiment classification: "positive", "negative", or "neutral"

    Examples:
        >>> classify_sentiment(0.8)
        'positive'

        >>> classify_sentiment(-0.6)
        'negative'

        >>> classify_sentiment(0.02)
        'neutral'
    """
    if compound_score >= 0.05:
        return "positive"
    elif compound_score <= -0.05:
        return "negative"
    else:
        return "neutral"
