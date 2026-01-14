"""Image service for fetching images from various sources."""

import asyncio
from typing import List, Dict, Any, Optional
import httpx
import structlog
from enum import Enum

from app.core.config import settings

logger = structlog.get_logger()


class ImageSource(str, Enum):
    UNSPLASH = "unsplash"
    PEXELS = "pexels"
    WIKIMEDIA = "wikimedia"
    AUTO = "auto"


class ImageService:
    """Service for fetching images from multiple sources."""

    def __init__(self):
        self.timeout = httpx.Timeout(30.0)
        self._cache: Dict[str, Any] = {}

        # API endpoints
        self.unsplash_api = "https://api.unsplash.com"
        self.pexels_api = "https://api.pexels.com/v1"
        self.wikimedia_api = "https://commons.wikimedia.org/w/api.php"

    async def find_image(
        self,
        query: str,
        source: ImageSource = ImageSource.AUTO,
        orientation: str = "landscape",
    ) -> Optional[Dict[str, Any]]:
        """
        Find a single best image for the query.

        Returns: {url, source, attribution, alt, thumbnail}
        """
        if source == ImageSource.AUTO:
            # Try sources in order of preference
            for src in [ImageSource.UNSPLASH, ImageSource.PEXELS, ImageSource.WIKIMEDIA]:
                result = await self._search_source(query, src, limit=1, orientation=orientation)
                if result:
                    return result[0]
            return None
        else:
            result = await self._search_source(query, source, limit=1, orientation=orientation)
            return result[0] if result else None

    async def search_images(
        self,
        query: str,
        source: ImageSource = ImageSource.AUTO,
        limit: int = 5,
        orientation: str = "landscape",
    ) -> List[Dict[str, Any]]:
        """
        Search for images from specified source.

        Returns list of: {url, source, attribution, alt, thumbnail}
        """
        if source == ImageSource.AUTO:
            # Gather from all sources
            results = await asyncio.gather(
                self._search_source(query, ImageSource.UNSPLASH, limit=limit, orientation=orientation),
                self._search_source(query, ImageSource.PEXELS, limit=limit, orientation=orientation),
                self._search_source(query, ImageSource.WIKIMEDIA, limit=limit, orientation=orientation),
                return_exceptions=True,
            )

            all_images = []
            for result in results:
                if isinstance(result, list):
                    all_images.extend(result)

            return all_images[:limit * 2]  # Return more variety
        else:
            return await self._search_source(query, source, limit=limit, orientation=orientation)

    async def _search_source(
        self,
        query: str,
        source: ImageSource,
        limit: int = 5,
        orientation: str = "landscape",
    ) -> List[Dict[str, Any]]:
        """Route to the appropriate source handler."""
        if source == ImageSource.UNSPLASH:
            return await self._search_unsplash(query, limit, orientation)
        elif source == ImageSource.PEXELS:
            return await self._search_pexels(query, limit, orientation)
        elif source == ImageSource.WIKIMEDIA:
            return await self._search_wikimedia(query, limit)
        return []

    async def _search_unsplash(
        self,
        query: str,
        limit: int = 5,
        orientation: str = "landscape",
    ) -> List[Dict[str, Any]]:
        """Search Unsplash for images."""
        api_key = getattr(settings, 'UNSPLASH_ACCESS_KEY', None)
        if not api_key:
            logger.debug("Unsplash API key not configured")
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Client-ID {api_key}"}
                params = {
                    "query": query,
                    "per_page": limit,
                    "orientation": orientation,
                }

                response = await client.get(
                    f"{self.unsplash_api}/search/photos",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for photo in data.get("results", []):
                    user = photo.get("user", {})
                    results.append({
                        "url": photo["urls"]["regular"],
                        "thumbnail": photo["urls"]["thumb"],
                        "source": "unsplash",
                        "source_url": photo["links"]["html"],
                        "attribution": f"Photo by {user.get('name', 'Unknown')} on Unsplash",
                        "alt": photo.get("alt_description", query),
                        "width": photo.get("width"),
                        "height": photo.get("height"),
                    })

                return results

        except Exception as e:
            logger.error("Unsplash search failed", query=query, error=str(e))
            return []

    async def _search_pexels(
        self,
        query: str,
        limit: int = 5,
        orientation: str = "landscape",
    ) -> List[Dict[str, Any]]:
        """Search Pexels for images."""
        api_key = getattr(settings, 'PEXELS_API_KEY', None)
        if not api_key:
            logger.debug("Pexels API key not configured")
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": api_key}
                params = {
                    "query": query,
                    "per_page": limit,
                    "orientation": orientation,
                }

                response = await client.get(
                    f"{self.pexels_api}/search",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for photo in data.get("photos", []):
                    results.append({
                        "url": photo["src"]["large"],
                        "thumbnail": photo["src"]["tiny"],
                        "source": "pexels",
                        "source_url": photo["url"],
                        "attribution": f"Photo by {photo.get('photographer', 'Unknown')} on Pexels",
                        "alt": photo.get("alt", query),
                        "width": photo.get("width"),
                        "height": photo.get("height"),
                    })

                return results

        except Exception as e:
            logger.error("Pexels search failed", query=query, error=str(e))
            return []

    async def _search_wikimedia(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search Wikimedia Commons for images (no API key required)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "action": "query",
                    "format": "json",
                    "generator": "search",
                    "gsrnamespace": 6,  # File namespace
                    "gsrsearch": f"{query} filetype:bitmap",
                    "gsrlimit": limit,
                    "prop": "imageinfo",
                    "iiprop": "url|extmetadata|size",
                    "iiurlwidth": 800,  # Get resized version
                }

                response = await client.get(self.wikimedia_api, params=params)
                response.raise_for_status()
                data = response.json()

                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    return []

                results = []
                for page_id, page in pages.items():
                    if int(page_id) < 0:  # Missing page
                        continue

                    imageinfo = page.get("imageinfo", [{}])[0]
                    metadata = imageinfo.get("extmetadata", {})

                    # Get attribution
                    artist = metadata.get("Artist", {}).get("value", "Unknown")
                    license_short = metadata.get("LicenseShortName", {}).get("value", "")

                    # Clean HTML from artist name
                    import re
                    artist = re.sub(r'<[^>]+>', '', artist)

                    results.append({
                        "url": imageinfo.get("thumburl", imageinfo.get("url")),
                        "thumbnail": imageinfo.get("thumburl", imageinfo.get("url")),
                        "source": "wikimedia",
                        "source_url": imageinfo.get("descriptionurl", ""),
                        "attribution": f"{artist} via Wikimedia Commons ({license_short})",
                        "alt": page.get("title", query).replace("File:", ""),
                        "width": imageinfo.get("thumbwidth", imageinfo.get("width")),
                        "height": imageinfo.get("thumbheight", imageinfo.get("height")),
                    })

                return results

        except Exception as e:
            logger.error("Wikimedia search failed", query=query, error=str(e))
            return []

    async def find_cybersecurity_image(
        self,
        topic: str,
        fallback_queries: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find an image suitable for cybersecurity content.
        Uses fallback queries if the main topic returns no results.
        """
        # Build query list
        queries = [
            f"{topic} cybersecurity",
            f"{topic} hacking",
            f"{topic} computer security",
            topic,
        ]

        if fallback_queries:
            queries.extend(fallback_queries)

        # Add generic fallbacks
        queries.extend([
            "cybersecurity",
            "computer security",
            "hacking code",
            "digital security",
        ])

        for query in queries:
            image = await self.find_image(query)
            if image:
                logger.info("Found image", query=query, source=image["source"])
                return image

        return None

    async def get_topic_images(
        self,
        topics: List[str],
        images_per_topic: int = 1,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get images for multiple topics concurrently.

        Returns: {topic: [images]}
        """
        async def fetch_for_topic(topic: str):
            images = await self.search_images(
                topic,
                limit=images_per_topic,
            )
            return topic, images

        results = await asyncio.gather(
            *[fetch_for_topic(topic) for topic in topics],
            return_exceptions=True,
        )

        topic_images = {}
        for result in results:
            if isinstance(result, tuple):
                topic, images = result
                topic_images[topic] = images
            elif isinstance(result, Exception):
                logger.error("Failed to fetch topic images", error=str(result))

        return topic_images


# Singleton instance
image_service = ImageService()
