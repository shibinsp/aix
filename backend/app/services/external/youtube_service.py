"""YouTube service for finding educational videos."""

import asyncio
from typing import List, Dict, Any, Optional
import httpx
import structlog
import re
from datetime import datetime

from app.core.config import settings

logger = structlog.get_logger()


class YouTubeService:
    """Service for finding educational YouTube videos."""

    def __init__(self):
        self.timeout = httpx.Timeout(30.0)
        self.api_url = "https://www.googleapis.com/youtube/v3"
        self._cache: Dict[str, Any] = {}

        # Curated cybersecurity channels (fallback when API not available)
        self.trusted_channels = [
            "NetworkChuck",
            "John Hammond",
            "LiveOverflow",
            "HackerSploit",
            "David Bombal",
            "The Cyber Mentor",
            "IppSec",
            "Computerphile",
            "Professor Messer",
        ]

    async def search_educational_videos(
        self,
        topic: str,
        difficulty: str = "beginner",
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for educational videos on a topic.

        Returns list of: {video_id, title, channel, duration, thumbnail, description, url}
        """
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)

        if api_key:
            return await self._search_with_api(topic, difficulty, max_results, api_key)
        else:
            # Fallback to providing curated video suggestions
            return await self._get_curated_suggestions(topic, difficulty)

    async def _search_with_api(
        self,
        topic: str,
        difficulty: str,
        max_results: int,
        api_key: str,
    ) -> List[Dict[str, Any]]:
        """Search YouTube using the official API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Build search query with educational context
                search_query = f"{topic} tutorial {difficulty}"

                params = {
                    "part": "snippet",
                    "q": search_query,
                    "type": "video",
                    "maxResults": max_results,
                    "videoDuration": "medium",  # 4-20 minutes
                    "relevanceLanguage": "en",
                    "safeSearch": "strict",
                    "key": api_key,
                }

                response = await client.get(
                    f"{self.api_url}/search",
                    params=params,
                )
                response.raise_for_status()
                search_data = response.json()

                # Get video IDs for duration info
                video_ids = [item["id"]["videoId"] for item in search_data.get("items", [])]

                if not video_ids:
                    return []

                # Get video details (for duration)
                video_params = {
                    "part": "contentDetails,statistics",
                    "id": ",".join(video_ids),
                    "key": api_key,
                }

                video_response = await client.get(
                    f"{self.api_url}/videos",
                    params=video_params,
                )
                video_response.raise_for_status()
                video_data = video_response.json()

                # Create lookup for durations
                durations = {}
                for item in video_data.get("items", []):
                    duration = self._parse_duration(item["contentDetails"]["duration"])
                    durations[item["id"]] = duration

                results = []
                for item in search_data.get("items", []):
                    snippet = item["snippet"]
                    video_id = item["id"]["videoId"]

                    results.append({
                        "video_id": video_id,
                        "title": snippet["title"],
                        "channel": snippet["channelTitle"],
                        "description": snippet["description"][:200] + "..." if len(snippet["description"]) > 200 else snippet["description"],
                        "thumbnail": snippet["thumbnails"]["high"]["url"],
                        "duration": durations.get(video_id, "Unknown"),
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "embed_url": f"https://www.youtube.com/embed/{video_id}",
                        "published_at": snippet["publishedAt"],
                    })

                return results

        except Exception as e:
            logger.error("YouTube API search failed", topic=topic, error=str(e))
            return await self._get_curated_suggestions(topic, difficulty)

    def _parse_duration(self, duration_str: str) -> str:
        """Parse ISO 8601 duration to human readable format."""
        # Format: PT#H#M#S
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return "Unknown"

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    async def _get_curated_suggestions(
        self,
        topic: str,
        difficulty: str,
    ) -> List[Dict[str, Any]]:
        """
        Provide curated video suggestions when API is not available.
        These are based on well-known cybersecurity education channels.
        """
        # This is a fallback - returns suggestions to search manually
        suggestions = []

        # Map topics to likely video titles/searches
        cybersecurity_topics = {
            "sql injection": [
                {"channel": "Computerphile", "search": "SQL Injection"},
                {"channel": "LiveOverflow", "search": "SQL Injection Tutorial"},
            ],
            "xss": [
                {"channel": "LiveOverflow", "search": "Cross Site Scripting"},
                {"channel": "HackerSploit", "search": "XSS Tutorial"},
            ],
            "penetration testing": [
                {"channel": "The Cyber Mentor", "search": "Penetration Testing"},
                {"channel": "NetworkChuck", "search": "Ethical Hacking"},
            ],
            "nmap": [
                {"channel": "NetworkChuck", "search": "Nmap Tutorial"},
                {"channel": "HackerSploit", "search": "Nmap Scanning"},
            ],
            "burp suite": [
                {"channel": "The Cyber Mentor", "search": "Burp Suite Tutorial"},
                {"channel": "John Hammond", "search": "Burp Suite"},
            ],
            "linux": [
                {"channel": "NetworkChuck", "search": "Linux for Hackers"},
                {"channel": "David Bombal", "search": "Linux Tutorial"},
            ],
            "networking": [
                {"channel": "NetworkChuck", "search": "Networking Fundamentals"},
                {"channel": "Professor Messer", "search": "Network+ Training"},
            ],
            "cryptography": [
                {"channel": "Computerphile", "search": "Cryptography Explained"},
            ],
            "reverse engineering": [
                {"channel": "LiveOverflow", "search": "Reverse Engineering"},
                {"channel": "John Hammond", "search": "Malware Analysis"},
            ],
        }

        # Find matching suggestions
        topic_lower = topic.lower()
        matched_suggestions = []

        for key, videos in cybersecurity_topics.items():
            if key in topic_lower or topic_lower in key:
                matched_suggestions.extend(videos)

        # If no specific match, suggest general channels
        if not matched_suggestions:
            matched_suggestions = [
                {"channel": "NetworkChuck", "search": f"{topic} Tutorial"},
                {"channel": "The Cyber Mentor", "search": topic},
                {"channel": "HackerSploit", "search": f"{topic} Tutorial"},
            ]

        # Format as video suggestions
        for i, suggestion in enumerate(matched_suggestions[:5]):
            suggestions.append({
                "video_id": None,  # Not available without API
                "title": f"Search: {suggestion['search']}",
                "channel": suggestion["channel"],
                "description": f"Search on {suggestion['channel']}'s channel for tutorials on this topic.",
                "thumbnail": None,
                "duration": "Varies",
                "url": f"https://www.youtube.com/results?search_query={suggestion['search'].replace(' ', '+')}+{suggestion['channel'].replace(' ', '+')}",
                "embed_url": None,
                "is_suggestion": True,
            })

        return suggestions

    async def get_video_details(
        self,
        video_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific video."""
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)

        if not api_key:
            return {
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "part": "snippet,contentDetails,statistics",
                    "id": video_id,
                    "key": api_key,
                }

                response = await client.get(
                    f"{self.api_url}/videos",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                items = data.get("items", [])
                if not items:
                    return None

                item = items[0]
                snippet = item["snippet"]
                stats = item.get("statistics", {})

                return {
                    "video_id": video_id,
                    "title": snippet["title"],
                    "channel": snippet["channelTitle"],
                    "description": snippet["description"],
                    "thumbnail": snippet["thumbnails"]["high"]["url"],
                    "duration": self._parse_duration(item["contentDetails"]["duration"]),
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "embed_url": f"https://www.youtube.com/embed/{video_id}",
                    "published_at": snippet["publishedAt"],
                }

        except Exception as e:
            logger.error("Failed to get video details", video_id=video_id, error=str(e))
            return None

    async def find_videos_for_topics(
        self,
        topics: List[str],
        difficulty: str = "beginner",
        videos_per_topic: int = 2,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find videos for multiple topics concurrently.

        Returns: {topic: [videos]}
        """
        async def fetch_for_topic(topic: str):
            videos = await self.search_educational_videos(
                topic,
                difficulty=difficulty,
                max_results=videos_per_topic,
            )
            return topic, videos

        results = await asyncio.gather(
            *[fetch_for_topic(topic) for topic in topics],
            return_exceptions=True,
        )

        topic_videos = {}
        for result in results:
            if isinstance(result, tuple):
                topic, videos = result
                topic_videos[topic] = videos
            elif isinstance(result, Exception):
                logger.error("Failed to fetch topic videos", error=str(result))

        return topic_videos

    def get_embed_html(
        self,
        video_id: str,
        width: int = 560,
        height: int = 315,
        autoplay: bool = False,
    ) -> str:
        """Generate HTML embed code for a video."""
        autoplay_param = "1" if autoplay else "0"
        return f'''<iframe
            width="{width}"
            height="{height}"
            src="https://www.youtube.com/embed/{video_id}?autoplay={autoplay_param}"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen>
        </iframe>'''


# Singleton instance
youtube_service = YouTubeService()
