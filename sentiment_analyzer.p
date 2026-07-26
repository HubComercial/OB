cat > modules/sentiment_analyzer.py << 'EOF'
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta

class SentimentAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.analyzer = SentimentIntensityAnalyzer()
        self.cache = {}

    def get_news_sentiment(self, query="EURUSD", days_back=2):
        cache_key = f"{query}_{days_back}"
        if cache_key in self.cache:
            cache_time, cached_score = self.cache[cache_key]
            if (datetime.now() - cache_time).seconds < 300:
                return cached_score

        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": 50,
            "apiKey": self.api_key
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get("status") != "ok":
                print(f"⚠️ Erro NewsAPI: {data.get('message', 'Erro')}")
                return 0.0

            articles = data.get("articles", [])
            if not articles:
                return 0.0

            scores = []
            for article in articles[:30]:
                text = (article.get("title") or "") + " " + (article.get("description") or "")
                if len(text) < 10:
                    continue
                vs = self.analyzer.polarity_scores(text)
                scores.append(vs['compound'])

            if not scores:
                return 0.0

            avg_score = sum(scores) / len(scores)
            self.cache[cache_key] = (datetime.now(), avg_score)
            return avg_score

        except Exception as e:
            print(f"❌ Erro nas notícias: {e}")
            return 0.0
EOF
