"""Wikipedia service for fetching and processing Wikipedia content."""

import asyncio
import re
from typing import List, Dict, Any, Optional
import httpx
import structlog
from functools import lru_cache

logger = structlog.get_logger()

WIKIPEDIA_API_URL = "https://en.wikipedia.org/api/rest_v1"
WIKIPEDIA_ACTION_API = "https://en.wikipedia.org/w/api.php"


class WikipediaService:
    """Service for fetching Wikipedia content for educational materials."""

    def __init__(self):
        self.timeout = httpx.Timeout(30.0)
        self._cache: Dict[str, Any] = {}

    async def search_articles(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search Wikipedia for articles matching the query.

        Returns list of: {title, description, url, pageid}
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": limit,
                    "srprop": "snippet|titlesnippet",
                }

                response = await client.get(WIKIPEDIA_ACTION_API, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("query", {}).get("search", []):
                    # Clean HTML from snippet
                    snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                    results.append({
                        "title": item["title"],
                        "description": snippet,
                        "url": f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                        "pageid": item["pageid"],
                    })

                return results

        except Exception as e:
            logger.error("Wikipedia search failed", query=query, error=str(e))
            return []

    async def get_article_summary(
        self,
        title: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a summary of a Wikipedia article.

        Returns: {title, extract, url, thumbnail, description}
        """
        cache_key = f"summary:{title}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use REST API for cleaner summaries
                encoded_title = title.replace(" ", "_")
                url = f"{WIKIPEDIA_API_URL}/page/summary/{encoded_title}"

                response = await client.get(url)

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                data = response.json()

                result = {
                    "title": data.get("title", title),
                    "extract": data.get("extract", ""),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "thumbnail": data.get("thumbnail", {}).get("source"),
                    "description": data.get("description", ""),
                }

                self._cache[cache_key] = result
                return result

        except Exception as e:
            logger.error("Failed to get Wikipedia summary", title=title, error=str(e))
            return None

    async def get_article_content(
        self,
        title: str,
        sections: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get full article content, optionally filtered by sections.

        Returns: {title, content, sections, url}
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": title,
                    "prop": "extracts|sections",
                    "explaintext": True,
                    "exsectionformat": "plain",
                }

                response = await client.get(WIKIPEDIA_ACTION_API, params=params)
                response.raise_for_status()
                data = response.json()

                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    return None

                page = list(pages.values())[0]
                if "missing" in page:
                    return None

                content = page.get("extract", "")

                # If specific sections requested, filter content
                if sections:
                    filtered_content = []
                    for section in sections:
                        section_content = await self._get_section_content(title, section)
                        if section_content:
                            filtered_content.append(f"## {section}\n\n{section_content}")
                    content = "\n\n".join(filtered_content) if filtered_content else content

                return {
                    "title": page.get("title", title),
                    "content": content,
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                }

        except Exception as e:
            logger.error("Failed to get Wikipedia content", title=title, error=str(e))
            return None

    async def _get_section_content(
        self,
        title: str,
        section_name: str,
    ) -> Optional[str]:
        """Get content for a specific section of an article."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # First get section index
                params = {
                    "action": "parse",
                    "format": "json",
                    "page": title,
                    "prop": "sections",
                }

                response = await client.get(WIKIPEDIA_ACTION_API, params=params)
                response.raise_for_status()
                data = response.json()

                sections = data.get("parse", {}).get("sections", [])
                section_index = None

                for section in sections:
                    if section.get("line", "").lower() == section_name.lower():
                        section_index = section.get("index")
                        break

                if section_index is None:
                    return None

                # Get section content
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": title,
                    "prop": "extracts",
                    "explaintext": True,
                    "exsectionformat": "plain",
                    "section": section_index,
                }

                response = await client.get(WIKIPEDIA_ACTION_API, params=params)
                response.raise_for_status()
                data = response.json()

                pages = data.get("query", {}).get("pages", {})
                if pages:
                    page = list(pages.values())[0]
                    return page.get("extract", "")

                return None

        except Exception as e:
            logger.error("Failed to get section content", title=title, section=section_name, error=str(e))
            return None

    async def get_related_articles(
        self,
        title: str,
        limit: int = 5,
    ) -> List[Dict[str, str]]:
        """Get articles related to the given title."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": title,
                    "prop": "links",
                    "pllimit": limit * 3,  # Get more to filter
                    "plnamespace": 0,  # Main namespace only
                }

                response = await client.get(WIKIPEDIA_ACTION_API, params=params)
                response.raise_for_status()
                data = response.json()

                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    return []

                page = list(pages.values())[0]
                links = page.get("links", [])

                results = []
                for link in links[:limit]:
                    link_title = link.get("title", "")
                    results.append({
                        "title": link_title,
                        "url": f"https://en.wikipedia.org/wiki/{link_title.replace(' ', '_')}",
                    })

                return results

        except Exception as e:
            logger.error("Failed to get related articles", title=title, error=str(e))
            return []

    async def summarize_for_lesson(
        self,
        topic: str,
        context: Optional[str] = None,
        max_length: int = 500,
    ) -> Dict[str, Any]:
        """
        Search Wikipedia and create a lesson-ready summary.

        Returns: {title, summary, url, sections_used, thumbnail}
        """
        # Search for the topic
        search_results = await self.search_articles(topic, limit=3)

        if not search_results:
            return {
                "title": topic,
                "summary": f"No Wikipedia article found for '{topic}'.",
                "url": None,
                "sections_used": [],
                "thumbnail": None,
            }

        # Get the best match (first result)
        best_match = search_results[0]

        # Get full summary
        article = await self.get_article_summary(best_match["title"])

        if not article:
            return {
                "title": best_match["title"],
                "summary": best_match["description"],
                "url": best_match["url"],
                "sections_used": [],
                "thumbnail": None,
            }

        # Trim summary to max length
        summary = article["extract"]
        if len(summary) > max_length:
            # Cut at last sentence before max_length
            summary = summary[:max_length]
            last_period = summary.rfind(".")
            if last_period > max_length // 2:
                summary = summary[:last_period + 1]
            else:
                summary = summary + "..."

        return {
            "title": article["title"],
            "summary": summary,
            "url": article["url"],
            "sections_used": ["Introduction"],
            "thumbnail": article.get("thumbnail"),
        }

    async def get_cybersecurity_context(
        self,
        topic: str,
    ) -> Dict[str, Any]:
        """
        Get cybersecurity-specific Wikipedia content.
        Searches with cybersecurity context and related terms.
        """
        # Try cybersecurity-specific search first
        search_queries = [
            f"{topic} cybersecurity",
            f"{topic} computer security",
            f"{topic} hacking",
            topic,
        ]

        for query in search_queries:
            results = await self.search_articles(query, limit=1)
            if results:
                article = await self.get_article_summary(results[0]["title"])
                if article and article.get("extract"):
                    return {
                        "found": True,
                        "title": article["title"],
                        "content": article["extract"],
                        "url": article["url"],
                        "thumbnail": article.get("thumbnail"),
                        "query_used": query,
                    }

        return {
            "found": False,
            "title": topic,
            "content": None,
            "url": None,
            "thumbnail": None,
            "query_used": None,
        }


# Singleton instance
wikipedia_service = WikipediaService()
