import requests
from newspaper import Article
from googletrans import Translator

translator = Translator()

def fetch_articles(params):
    """Fetch articles using Google News-compatible API (like NewsAPI)."""
    try:
        response = requests.get("https://newsapi.org/v2/everything", params=params)
        response.raise_for_status()
        return response.json().get("articles", [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch articles: {e}")
        return []

def get_full_article_text(url):
    """Extract full article text from the URL using newspaper3k."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"[ERROR] Failed to extract article from {url}: {e}")
        return "Article could not be retrieved."

def translate_text(text, dest_lang="tr"):
    """Translate text into Turkish using googletrans."""
    try:
        if not text.strip():
            return "No content available to translate."
        translation = translator.translate(text, dest=dest_lang)
        return translation.text
    except Exception as e:
        print(f"[ERROR] Translation failed: {e}")
        return "Translation unavailable."
