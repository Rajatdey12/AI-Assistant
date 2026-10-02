"""
Web Search Integration Stub for Chiku (Phase 2)

Placeholder for web search and real-time information. 
Real implementation coming in MVP 2 using DuckDuckGo or similar.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def search(query: str, num_results: int = 3) -> List[Dict]:
    """
    Search the web.
    Currently returns mock results.
    
    Real implementation will use:
    - DuckDuckGo API (free, privacy-focused)
    - Google Custom Search API
    """
    
    # Mock search results
    mock_results = {
        "weather": [
            {"title": "Weather Today", "snippet": "Partly cloudy, 72°F (22°C)"}
        ],
        "time": [
            {"title": "Current Time", "snippet": "2:45 PM EST"}
        ]
    }
    
    # Check if query contains weather/time keywords
    query_lower = query.lower()
    if "weather" in query_lower:
        return mock_results.get("weather", [])
    elif "time" in query_lower:
        return mock_results.get("time", [])
    else:
        return [{"title": "Search Result", "snippet": "Real web search coming in MVP 2"}]


def get_weather(location: str = "current") -> Dict:
    """Mock: Get weather for location"""
    return {
        "location": location,
        "temperature": "72°F",
        "condition": "Partly Cloudy",
        "humidity": "65%"
    }


def get_news(topic: str = "general", num_articles: int = 3) -> List[Dict]:
    """Mock: Get latest news"""
    return [
        {"title": "Sample News Article", "source": "Demo", "summary": "This is a mock news article"}
    ]


if __name__ == "__main__":
    print("Testing Web Search Integration (Stub)...")
    
    results = search("what's the weather?")
    print(f"Search results for weather:")
    for r in results:
        print(f"  - {r['title']}: {r['snippet']}")
    
    weather = get_weather()
    print(f"\nWeather: {weather['condition']}, {weather['temperature']}")
