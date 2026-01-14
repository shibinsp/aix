"""
Multi-source cybersecurity news aggregator.
Fetches from:
- Hacker News API (free, no auth)
- Reddit API (free, no auth for public data)
- NewsAPI.org (optional, 100 req/day free tier)
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import structlog
import hashlib
import re

logger = structlog.get_logger()


class NewsArticle(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    severity: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    date: str
    tags: List[str] = []
    score: int = 0
    comments: int = 0


def generate_article_id(title: str, source: str) -> str:
    """Generate a unique ID for an article."""
    content = f"{title}{source}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def categorize_article(title: str, text: str = "") -> tuple[str, str, List[str]]:
    """Categorize article based on keywords."""
    combined = (title + " " + text).lower()

    categories = {
        "Vulnerabilities": ["cve", "vulnerability", "exploit", "zero-day", "0day", "security flaw", "bug bounty", "pwn"],
        "Ransomware": ["ransomware", "ransom", "lockbit", "blackcat", "alphv", "encrypted files", "extortion"],
        "Data Breach": ["data breach", "leak", "exposed", "stolen data", "compromised", "data dump", "breach"],
        "Malware": ["malware", "trojan", "botnet", "backdoor", "spyware", "worm", "virus", "rat"],
        "APT": ["apt", "nation-state", "chinese hackers", "russian hackers", "lazarus", "cozy bear", "fancy bear", "state-sponsored"],
        "Patches": ["patch", "update", "fix", "security update", "hotfix", "microsoft patch", "cisa"],
        "Policy": ["regulation", "gdpr", "compliance", "policy", "law", "legislation", "sec", "ftc"],
        "Phishing": ["phishing", "social engineering", "spear phishing", "bec", "business email"],
        "Network Security": ["firewall", "ids", "ips", "network security", "ddos", "dos attack"],
        "Cloud Security": ["aws", "azure", "cloud", "s3 bucket", "misconfigured", "cloud security"],
        "Crypto": ["cryptocurrency", "crypto", "bitcoin", "blockchain", "wallet", "defi", "nft hack"],
        "Privacy": ["privacy", "surveillance", "tracking", "gdpr", "data protection"],
    }

    severity_keywords = {
        "Critical": ["critical", "severe", "emergency", "actively exploited", "zero-day", "rce", "remote code execution"],
        "High": ["high", "important", "urgent", "ransomware", "breach", "attack"],
        "Medium": ["medium", "moderate", "warning"],
        "Low": ["low", "minor", "informational"],
    }

    # Determine category
    detected_category = "Threats"  # Default
    for cat, keywords in categories.items():
        if any(kw in combined for kw in keywords):
            detected_category = cat
            break

    # Determine severity
    detected_severity = "Info"
    for sev, keywords in severity_keywords.items():
        if any(kw in combined for kw in keywords):
            detected_severity = sev
            break

    # Extract tags
    tags = []
    tag_patterns = [
        r'\bCVE-\d{4}-\d+\b',  # CVE IDs
        r'\b[A-Z]{2,5}\b(?=\s|$)',  # Acronyms
    ]
    for pattern in tag_patterns:
        matches = re.findall(pattern, title + " " + text, re.IGNORECASE)
        tags.extend(matches[:3])

    # Add category as tag
    if detected_category not in tags:
        tags.insert(0, detected_category)

    return detected_category, detected_severity, tags[:5]


class HackerNewsFetcher:
    """Fetch cybersecurity news from Hacker News."""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    SECURITY_KEYWORDS = [
        # Core security terms
        "security", "secure", "hack", "hacker", "hacking", "breach", "breached",
        "vulnerability", "vulnerable", "cve", "malware", "ransomware", "phishing",
        "exploit", "exploited", "cyber", "infosec", "privacy", "encryption",
        "backdoor", "zero-day", "0day", "apt", "ddos", "botnet", "trojan",
        # Attack types
        "attack", "pwn", "pwned", "compromised", "leak", "leaked", "exposed",
        "injection", "xss", "csrf", "sqli", "rce", "lfi", "ssrf",
        # Security tools & concepts
        "firewall", "antivirus", "password", "auth", "authentication", "oauth",
        "ssl", "tls", "https", "vpn", "tor", "proxy", "sandbox",
        # Threat actors
        "nation-state", "chinese", "russian", "north korea", "iran", "lazarus",
        "apt28", "apt29", "cozy bear", "fancy bear", "threat actor",
        # Industry terms
        "cisa", "nsa", "fbi", "europol", "mitre", "owasp", "nist",
        "pentest", "pentesting", "red team", "blue team", "soc", "siem",
        # Tech security
        "cryptography", "crypto", "bitcoin", "blockchain", "wallet", "keys",
        "data protection", "gdpr", "compliance", "audit", "forensics"
    ]

    async def fetch(self, limit: int = 30) -> List[NewsArticle]:
        """Fetch top stories and filter for security-related content."""
        articles = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get top stories
                response = await client.get(f"{self.BASE_URL}/topstories.json")
                story_ids = response.json()[:200]  # Get top 200

                # Also get best stories
                best_response = await client.get(f"{self.BASE_URL}/beststories.json")
                best_story_ids = best_response.json()[:100]

                # Also get new stories for more recent content
                new_response = await client.get(f"{self.BASE_URL}/newstories.json")
                new_story_ids = new_response.json()[:100]

                # Combine and dedupe
                all_ids = list(dict.fromkeys(story_ids + best_story_ids + new_story_ids))

                # Fetch story details concurrently (in batches to avoid overwhelming)
                tasks = [self._fetch_story(client, sid) for sid in all_ids[:300]]
                stories = await asyncio.gather(*tasks, return_exceptions=True)

                for story in stories:
                    if isinstance(story, Exception) or story is None:
                        continue

                    title = story.get("title", "").lower()

                    # Filter for security-related content
                    if any(kw in title for kw in self.SECURITY_KEYWORDS):
                        category, severity, tags = categorize_article(
                            story.get("title", ""),
                            story.get("text", "")
                        )

                        # Format date
                        timestamp = story.get("time", 0)
                        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

                        articles.append(NewsArticle(
                            id=generate_article_id(story.get("title", ""), "HackerNews"),
                            title=story.get("title", "Untitled"),
                            summary=story.get("text", "")[:300] if story.get("text") else f"Discussion on Hacker News about {story.get('title', '')}",
                            category=category,
                            severity=severity,
                            source="Hacker News",
                            source_url=story.get("url") or f"https://news.ycombinator.com/item?id={story.get('id')}",
                            date=date_str,
                            tags=tags,
                            score=story.get("score", 0),
                            comments=story.get("descendants", 0)
                        ))

                logger.info(f"Fetched {len(articles)} security articles from Hacker News")

        except Exception as e:
            logger.error("Failed to fetch from Hacker News", error=str(e))

        return articles[:limit]

    async def _fetch_story(self, client: httpx.AsyncClient, story_id: int) -> Optional[Dict]:
        """Fetch a single story's details."""
        try:
            response = await client.get(f"{self.BASE_URL}/item/{story_id}.json")
            return response.json()
        except:
            return None


class RedditFetcher:
    """Fetch cybersecurity news from Reddit."""

    SUBREDDITS = ["netsec", "cybersecurity", "hacking", "ReverseEngineering", "Malware"]

    async def fetch(self, limit: int = 30) -> List[NewsArticle]:
        """Fetch top posts from security subreddits."""
        articles = []

        # Reddit requires a proper User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                for subreddit in self.SUBREDDITS:
                    try:
                        # Fetch hot posts
                        response = await client.get(
                            f"https://www.reddit.com/r/{subreddit}/hot.json",
                            params={"limit": 25, "raw_json": 1}
                        )

                        if response.status_code != 200:
                            logger.warning(f"Reddit r/{subreddit} returned status {response.status_code}")
                            continue

                        data = response.json()
                        posts = data.get("data", {}).get("children", [])
                        logger.debug(f"Reddit r/{subreddit}: got {len(posts)} posts")

                        for post in posts:
                            post_data = post.get("data", {})

                            # Skip stickied posts and self posts without content
                            if post_data.get("stickied"):
                                continue

                            title = post_data.get("title", "")
                            selftext = post_data.get("selftext", "")[:500]

                            category, severity, tags = categorize_article(title, selftext)

                            # Format date
                            created = post_data.get("created_utc", 0)
                            date_str = datetime.fromtimestamp(created).strftime("%Y-%m-%d")

                            # Use link URL or Reddit permalink
                            url = post_data.get("url", "")
                            if "reddit.com" in url or not url:
                                url = f"https://reddit.com{post_data.get('permalink', '')}"

                            articles.append(NewsArticle(
                                id=generate_article_id(title, f"Reddit-{subreddit}"),
                                title=title,
                                summary=selftext if selftext else f"Discussion on r/{subreddit}",
                                category=category,
                                severity=severity,
                                source=f"Reddit r/{subreddit}",
                                source_url=url,
                                date=date_str,
                                tags=tags + [subreddit],
                                score=post_data.get("score", 0),
                                comments=post_data.get("num_comments", 0)
                            ))

                        # Small delay between subreddits to be nice to Reddit
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning(f"Failed to fetch from r/{subreddit}", error=str(e))
                        continue

                logger.info(f"Fetched {len(articles)} articles from Reddit")

        except Exception as e:
            logger.error("Failed to fetch from Reddit", error=str(e))

        return articles[:limit]


class NewsAPIFetcher:
    """Fetch cybersecurity news from NewsAPI.org (requires API key)."""

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def fetch(self, limit: int = 20) -> List[NewsArticle]:
        """Fetch cybersecurity news from NewsAPI."""
        if not self.api_key:
            return []

        articles = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Search for cybersecurity news
                queries = [
                    "cybersecurity vulnerability",
                    "ransomware attack",
                    "data breach",
                    "hacking security"
                ]

                for query in queries:
                    try:
                        response = await client.get(
                            f"{self.BASE_URL}/everything",
                            params={
                                "q": query,
                                "language": "en",
                                "sortBy": "publishedAt",
                                "pageSize": 10,
                                "apiKey": self.api_key
                            }
                        )

                        if response.status_code != 200:
                            continue

                        data = response.json()

                        for article in data.get("articles", []):
                            title = article.get("title", "")
                            description = article.get("description", "") or ""

                            category, severity, tags = categorize_article(title, description)

                            # Parse date
                            published = article.get("publishedAt", "")
                            date_str = published[:10] if published else datetime.now().strftime("%Y-%m-%d")

                            articles.append(NewsArticle(
                                id=generate_article_id(title, article.get("source", {}).get("name", "NewsAPI")),
                                title=title,
                                summary=description[:400],
                                category=category,
                                severity=severity,
                                source=article.get("source", {}).get("name", "Unknown"),
                                source_url=article.get("url"),
                                date=date_str,
                                tags=tags,
                                score=0,
                                comments=0
                            ))

                    except Exception as e:
                        logger.warning(f"NewsAPI query failed: {query}", error=str(e))
                        continue

                logger.info(f"Fetched {len(articles)} articles from NewsAPI")

        except Exception as e:
            logger.error("Failed to fetch from NewsAPI", error=str(e))

        # Dedupe by title
        seen_titles = set()
        unique_articles = []
        for article in articles:
            if article.title not in seen_titles:
                seen_titles.add(article.title)
                unique_articles.append(article)

        return unique_articles[:limit]


class CyberNewsAggregator:
    """Aggregates news from multiple sources."""

    def __init__(self, newsapi_key: Optional[str] = None):
        self.hn_fetcher = HackerNewsFetcher()
        self.reddit_fetcher = RedditFetcher()
        self.newsapi_fetcher = NewsAPIFetcher(newsapi_key)

        # Cache
        self._cache: List[NewsArticle] = []
        self._cache_time: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=30)

    async def fetch_all(self, force_refresh: bool = False) -> List[NewsArticle]:
        """Fetch news from all sources and aggregate."""

        # Check cache
        if not force_refresh and self._cache and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_duration:
                logger.info("Returning cached news")
                return self._cache

        logger.info("Fetching fresh news from all sources...")

        # Fetch from all sources concurrently
        results = await asyncio.gather(
            self.hn_fetcher.fetch(limit=25),
            self.reddit_fetcher.fetch(limit=30),
            self.newsapi_fetcher.fetch(limit=20),
            return_exceptions=True
        )

        all_articles = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Source fetch failed", error=str(result))
                continue
            all_articles.extend(result)

        # Dedupe by similar titles
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            # Normalize title for comparison
            normalized = article.title.lower()[:50]
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_articles.append(article)

        # Sort by date and score
        unique_articles.sort(
            key=lambda x: (x.date, x.score),
            reverse=True
        )

        # Update cache
        self._cache = unique_articles
        self._cache_time = datetime.now()

        logger.info(f"Aggregated {len(unique_articles)} unique articles")

        return unique_articles

    def get_cached(self) -> List[NewsArticle]:
        """Get cached articles without fetching."""
        return self._cache


# Global instance
news_aggregator = CyberNewsAggregator()
