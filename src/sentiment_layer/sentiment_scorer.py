"""
Sentiment scoring engine using FinBERT or alternative sentiment models.
Converts news articles into sentiment scores for confidence boosting.
"""
from typing import List, Dict, Any, Optional
import re


class SentimentScorer:
    """
    Sentiment scorer that can use multiple backends:
    1. FinBERT (via transformers) - Best for financial news
    2. TextBlob - Simple, fast, no dependencies
    3. Pre-scored (from Alpha Vantage API)
    """

    def __init__(self, method: str = "textblob"):
        """
        Initialize sentiment scorer.

        Args:
            method: Scoring method ("finbert", "textblob", "prescored")
        """
        self.method = method
        self.model = None
        self.tokenizer = None

        if method == "finbert":
            self._init_finbert()
        elif method == "textblob":
            self._init_textblob()

    def _init_finbert(self):
        """Initialize FinBERT model (requires transformers + torch)."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch

            model_name = "ProsusAI/finbert"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()

            print(f"✓ FinBERT model loaded: {model_name}")

        except ImportError:
            print("⚠ FinBERT requires: pip install transformers torch")
            print("  Falling back to TextBlob")
            self.method = "textblob"
            self._init_textblob()
        except Exception as e:
            print(f"⚠ Error loading FinBERT: {e}")
            print("  Falling back to TextBlob")
            self.method = "textblob"
            self._init_textblob()

    def _init_textblob(self):
        """Initialize TextBlob (lightweight, no ML models needed)."""
        try:
            from textblob import TextBlob
            self.textblob = TextBlob
            print("✓ TextBlob sentiment analyzer ready")
        except ImportError:
            print("⚠ TextBlob not available: pip install textblob")
            print("  Using basic keyword-based scoring")
            self.method = "keywords"

    def score_text(self, text: str) -> float:
        """
        Score a single piece of text.

        Args:
            text: Text to analyze (title, description, or content)

        Returns:
            Sentiment score from -1.0 (very negative) to +1.0 (very positive)
        """
        if not text or len(text.strip()) == 0:
            return 0.0

        if self.method == "finbert":
            return self._score_finbert(text)
        elif self.method == "textblob":
            return self._score_textblob(text)
        elif self.method == "keywords":
            return self._score_keywords(text)
        else:
            return 0.0

    def _score_finbert(self, text: str) -> float:
        """Score using FinBERT model."""
        import torch

        # Tokenize
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

        # Get prediction
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

        # FinBERT outputs: [positive, negative, neutral]
        # Convert to single score: positive_prob - negative_prob
        pos_prob = predictions[0][0].item()
        neg_prob = predictions[0][1].item()

        score = pos_prob - neg_prob  # Range: -1 to +1

        return score

    def _score_textblob(self, text: str) -> float:
        """Score using TextBlob polarity."""
        blob = self.textblob(text)
        # TextBlob polarity is already -1 to +1
        return blob.sentiment.polarity

    def _score_keywords(self, text: str) -> float:
        """
        Simple keyword-based scoring (fallback).
        Counts positive vs negative financial keywords.
        """
        text_lower = text.lower()

        positive_keywords = [
            'surge', 'jump', 'rise', 'gain', 'increase', 'growth', 'expansion',
            'boom', 'rally', 'soar', 'climb', 'advance', 'bullish', 'optimistic',
            'beat expectations', 'exceed', 'strong', 'robust', 'positive'
        ]

        negative_keywords = [
            'fall', 'drop', 'decline', 'decrease', 'plunge', 'crash', 'slump',
            'weak', 'recession', 'downturn', 'bearish', 'pessimistic', 'concern',
            'miss expectations', 'disappoint', 'worse', 'negative', 'poor'
        ]

        pos_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        neg_count = sum(1 for keyword in negative_keywords if keyword in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        # Normalize to -1 to +1
        score = (pos_count - neg_count) / total
        return score

    def score_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Score multiple articles and return aggregate sentiment.

        Args:
            articles: List of article dicts with 'title', 'description', 'content'

        Returns:
            Dict with:
                - average_sentiment: Mean score across all articles
                - sentiment_scores: List of individual scores
                - confidence: How confident we are (based on agreement)
                - article_count: Number of articles analyzed
        """
        if not articles:
            return {
                'average_sentiment': 0.0,
                'sentiment_scores': [],
                'confidence': 0.0,
                'article_count': 0
            }

        scores = []

        for article in articles:
            # Check if already scored (from Alpha Vantage)
            if 'sentiment_score' in article and article['sentiment_score'] is not None:
                scores.append(float(article['sentiment_score']))
                continue

            # Otherwise, score the text
            # Combine title + description for best signal
            text = f"{article.get('title', '')} {article.get('description', '')}"

            # If still empty, try content
            if len(text.strip()) < 10 and 'content' in article:
                text = article['content']

            if len(text.strip()) > 0:
                score = self.score_text(text)
                scores.append(score)

        if not scores:
            return {
                'average_sentiment': 0.0,
                'sentiment_scores': [],
                'confidence': 0.0,
                'article_count': 0
            }

        # Calculate statistics
        avg_sentiment = sum(scores) / len(scores)

        # Confidence based on agreement (low variance = high confidence)
        import statistics
        if len(scores) > 1:
            std_dev = statistics.stdev(scores)
            # High std dev (0.5+) = low confidence
            # Low std dev (0.1-) = high confidence
            confidence = max(0.0, 1.0 - std_dev)
        else:
            confidence = 0.5  # Moderate confidence with single article

        return {
            'average_sentiment': avg_sentiment,
            'sentiment_scores': scores,
            'confidence': confidence,
            'article_count': len(scores)
        }

    def calculate_confidence_boost(
        self,
        base_probability: float,
        sentiment_score: float,
        sentiment_confidence: float,
        max_boost: float = 0.20
    ) -> float:
        """
        Calculate confidence-boosted probability.

        Formula: boosted = base × (1 + sentiment × confidence × max_boost)

        Args:
            base_probability: Base probability from Polymarket (0-1)
            sentiment_score: Sentiment score (-1 to +1)
            sentiment_confidence: Confidence in sentiment (0-1)
            max_boost: Maximum boost multiplier (default: 20%)

        Returns:
            Confidence-boosted probability (capped at 0-1)

        Example:
            base_probability = 0.48
            sentiment_score = 0.5 (moderately positive)
            sentiment_confidence = 0.8 (high confidence)
            max_boost = 0.20

            boost_factor = 0.5 × 0.8 × 0.20 = 0.08
            boosted = 0.48 × (1 + 0.08) = 0.5184 (51.84%)
        """
        boost_factor = sentiment_score * sentiment_confidence * max_boost
        boosted_prob = base_probability * (1 + boost_factor)

        # Cap at valid probability range
        return max(0.0, min(1.0, boosted_prob))


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("SENTIMENT SCORING DEMO")
    print("=" * 70)
    print()

    # Initialize scorer (will try FinBERT, fall back to TextBlob)
    scorer = SentimentScorer(method="textblob")

    # Example articles about CPI
    articles = [
        {
            'title': 'CPI Surges Above Expectations, Inflation Concerns Rise',
            'description': 'Consumer price index jumped 0.5% in latest report, exceeding forecasts.',
            'source': 'Reuters'
        },
        {
            'title': 'Fed Officials Express Concern Over Persistent Inflation',
            'description': 'Central bank signals potential rate hikes if CPI remains elevated.',
            'source': 'Bloomberg'
        },
        {
            'title': 'Economists Worried About Rising Food and Energy Costs',
            'description': 'Core inflation metrics show continued upward pressure on prices.',
            'source': 'WSJ'
        }
    ]

    # Score the articles
    print("Analyzing articles...")
    print()

    for i, article in enumerate(articles, 1):
        score = scorer.score_text(f"{article['title']} {article['description']}")
        print(f"{i}. {article['title'][:60]}...")
        print(f"   Sentiment: {score:+.3f} ({'Positive' if score > 0 else 'Negative' if score < 0 else 'Neutral'})")
        print()

    # Aggregate scoring
    result = scorer.score_articles(articles)

    print("=" * 70)
    print("AGGREGATE SENTIMENT")
    print("=" * 70)
    print(f"Average Sentiment: {result['average_sentiment']:+.3f}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Articles Analyzed: {result['article_count']}")
    print()

    # Calculate confidence boost
    print("=" * 70)
    print("CONFIDENCE BOOST EXAMPLE")
    print("=" * 70)

    base_prob = 0.48
    boosted_prob = scorer.calculate_confidence_boost(
        base_probability=base_prob,
        sentiment_score=result['average_sentiment'],
        sentiment_confidence=result['confidence'],
        max_boost=0.20
    )

    print(f"Base Probability (Polymarket): {base_prob:.1%}")
    print(f"Sentiment Score: {result['average_sentiment']:+.3f}")
    print(f"Sentiment Confidence: {result['confidence']:.1%}")
    print(f"Boosted Probability: {boosted_prob:.1%}")
    print(f"Boost Amount: {(boosted_prob - base_prob):.1%}")
    print()

    if boosted_prob > base_prob:
        print(f"✓ Sentiment supports bullish position (+{(boosted_prob - base_prob):.1%})")
    elif boosted_prob < base_prob:
        print(f"⚠ Sentiment suggests bearish position ({(boosted_prob - base_prob):.1%})")
    else:
        print("→ Neutral sentiment, no adjustment")
