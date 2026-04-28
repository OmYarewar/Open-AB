import requests
import urllib.parse

def search_web(query: str) -> str:
    """Perform a web search using DuckDuckGo HTML."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text[:2000] # Return first 2000 chars of HTML
    except Exception as e:
        return f"Error during web search: {e}"

def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text[:5000]
    except Exception as e:
        return f"Error fetching URL: {e}"
