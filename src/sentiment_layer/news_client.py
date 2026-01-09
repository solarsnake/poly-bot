"""
News API client for fetching financial news related to prediction market events.
Supports NewsAPI and Alpha Vantage.
"""
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os


class NewsClient:
    """
    Client for fetching news from multiple sources.
    Free tier limitations: NewsAPI allows 100 requests/day, 7-day history.
    """

    def __init__(self, newsapi_key: Optional[str] = None, alphavantage_key: Optional[str] = None):
        """
        Initialize news clients.

        Args:
            newsapi_key: NewsAPI key (get free at https://newsapi.org)
            alphavantage_key: Alpha Vantage key (get free at https://www.alphavantage.co)
        """
        self.newsapi_key = newsapi_key or os.getenv('NEWSAPI_KEY')
        self.alphavantage_key = alphavantage_key or os.getenv('ALPHAVANTAGE_KEY')

        self.newsapi_base = "https://newsapi.org/v2"
        self.alphavantage_base = "https://www.alphavantage.co/query"

    def fetch_news_for_event(
        self,
        keywords: List[str],
        from_date: Optional[datetime] = None,
        language: str = "en",
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles related to an event.

        Args:
            keywords: List of keywords to search (e.g., ["CPI", "inflation"])
            from_date: Start date for news (default: 7 days ago)
            language: Language code (default: "en")
            max_results: Maximum number of articles to return

        Returns:
            List of news articles with title, description, source, publishedAt
        """
        if not from_date:
            from_date = datetime.now() - timedelta(days=7)

        articles = []

        # Try NewsAPI first
        if self.newsapi_key:
            try:
                newsapi_articles = self._fetch_from_newsapi(keywords, from_date, language, max_results)
                articles.extend(newsapi_articles)
            except Exception as e:
                print(f"NewsAPI fetch failed: {e}")

        # Fallback to Alpha Vantage news sentiment
        if len(articles) < max_results and self.alphavantage_key:
            try:
                av_articles = self._fetch_from_alphavantage(keywords, max_results - len(articles))
                articles.extend(av_articles)
            except Exception as e:
                print(f"Alpha Vantage fetch failed: {e}")

        return articles[:max_results]

    def _fetch_from_newsapi(
        self,
        keywords: List[str],
        from_date: datetime,
        language: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Fetch from NewsAPI."""
        if not self.newsapi_key:
            return []

        # Build query
        query = " OR ".join(keywords)

        params = {
            'q': query,
            'from': from_date.strftime('%Y-%m-%d'),
            'language': language,
            'sortBy': 'publishedAt',
            'pageSize': min(max_results, 100),
            'apiKey': self.newsapi_key
        }

        response = requests.get(f"{self.newsapi_base}/everything", params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get('status') != 'ok':
            raise Exception(f"NewsAPI error: {data.get('message', 'Unknown error')}")

        articles = []
        for article in data.get('articles', []):
            articles.append({
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'content': article.get('content', ''),
                'source': article.get('source', {}).get('name', 'Unknown'),
                'publishedAt': article.get('publishedAt', ''),
                'url': article.get('url', '')
            })

        return articles

    def _fetch_from_alphavantage(self, keywords: List[str], max_results: int) -> List[Dict[str, Any]]:
        """Fetch from Alpha Vantage news sentiment API."""
        if not self.alphavantage_key:
            return []

        # Alpha Vantage uses tickers or topics
        # For general events, use topics
        topics = ','.join(keywords[:5])  # Limit to 5 topics

        params = {
            'function': 'NEWS_SENTIMENT',
            'topics': topics,
            'apikey': self.alphavantage_key,
            'limit': max_results
        }

        response = requests.get(self.alphavantage_base, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if 'feed' not in data:
            raise Exception(f"Alpha Vantage error: {data.get('Note', 'Unknown error')}")

        articles = []
        for item in data['feed'][:max_results]:
            articles.append({
                'title': item.get('title', ''),
                'description': item.get('summary', ''),
                'content': item.get('summary', ''),
                'source': ', '.join([s['name'] for s in item.get('authors', [])]),
                'publishedAt': item.get('time_published', ''),
                'url': item.get('url', ''),
                'sentiment_score': float(item.get('overall_sentiment_score', 0.0)),  # Already scored!
                'sentiment_label': item.get('overall_sentiment_label', 'Neutral')
            })

        return articles

    def match_event_to_keywords(self, event_description: str) -> List[str]:
        """
        Extract relevant keywords from an event description.

        Args:
            event_description: Human-readable event (e.g., "US CPI YoY above 3.5%")

        Returns:
            List of keywords for news search
        """
        # Common economic indicators
        economic_keywords = {
            'cpi': ['CPI', 'inflation', 'consumer price'],
            'gdp': ['GDP', 'economic growth', 'gross domestic product'],
            'unemployment': ['unemployment', 'jobless', 'employment rate'],
            'fed': ['Federal Reserve', 'Fed rate', 'interest rate', 'FOMC'],
            'jobs': ['jobs report', 'nonfarm payroll', 'employment'],
            'pce': ['PCE', 'personal consumption', 'core inflation'],
            'housing': ['housing', 'home sales', 'real estate'],
            'retail': ['retail sales', 'consumer spending'],
            'manufacturing': ['manufacturing', 'PMI', 'factory orders']
        }

        # Convert to lowercase for matching
        desc_lower = event_description.lower()

        keywords = []

        # Check for economic indicators
        for indicator, terms in economic_keywords.items():
            if indicator in desc_lower:
                keywords.extend(terms)

        # Also add the event description itself (cleaned)
        # Remove common words and special characters
        import re
        cleaned = re.sub(r'[^\w\s]', ' ', event_description)
        words = [w for w in cleaned.split() if len(w) > 3 and w.lower() not in
                 ['will', 'than', 'above', 'below', 'before', 'after', 'this', 'that']]
        keywords.extend(words[:3])  # Add top 3 significant words

        return list(set(keywords))  # Remove duplicates


# Example usage
if __name__ == "__main__":
    import os
    from datetime import datetime, timedelta

    # Set your API keys in environment or .env
    # NEWSAPI_KEY=your_key_here
    # ALPHAVANTAGE_KEY=your_key_here

    client = NewsClient()

    # Example 1: Fetch CPI news
    print("=" * 70)
    print("Example 1: Fetching CPI News")
    print("=" * 70)

    keywords = client.match_event_to_keywords("US CPI YoY above 3.5%")
    print(f"Keywords: {keywords}")
    print()

    articles = client.fetch_news_for_event(
        keywords=['CPI', 'inflation'],
        from_date=datetime.now() - timedelta(days=3),
        max_results=5
    )

    print(f"Found {len(articles)} articles:")
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title']}")
        print(f"   Source: {article['source']}")
        print(f"   Published: {article['publishedAt']}")
        if 'sentiment_score' in article:
            print(f"   Sentiment: {article['sentiment_label']} ({article['sentiment_score']:.3f})")

    # Example 2: Fetch Fed news
    print("\n" + "=" * 70)
    print("Example 2: Fetching Federal Reserve News")
    print("=" * 70)

    articles = client.fetch_news_for_event(
        keywords=['Federal Reserve', 'Fed rate', 'FOMC'],
        max_results=3
    )

    print(f"Found {len(articles)} articles:")
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title'][:80]}...")
        print(f"   Source: {article['source']}")
