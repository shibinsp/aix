"""
Cybersecurity News API Routes.
Aggregates real-time news from:
- Hacker News (free, no auth)
- Reddit (r/netsec, r/cybersecurity, r/hacking)
- NewsAPI.org (optional, 100 req/day free)
"""

from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.saved_article import SavedArticle
from app.services.news_fetcher import news_aggregator, NewsArticle
from app.services.ai.teaching_engine import teaching_engine
import json

logger = structlog.get_logger()

router = APIRouter()


class NewsResponse(BaseModel):
    articles: List[NewsArticle]
    generated_at: str
    cached: bool = False
    sources: List[str] = ["Hacker News", "Reddit", "NewsAPI"]


class NewsCategory(BaseModel):
    name: str
    count: int


@router.get("", response_model=NewsResponse)
async def get_cyber_news(refresh: bool = False):
    """
    Get latest cybersecurity news from multiple sources.

    Sources:
    - Hacker News (security-filtered)
    - Reddit (r/netsec, r/cybersecurity, r/hacking, r/ReverseEngineering, r/Malware)
    - NewsAPI.org (if configured)

    Set refresh=true to bypass cache and fetch fresh news.
    """
    articles = await news_aggregator.fetch_all(force_refresh=refresh)

    # Get unique sources
    sources = list(set(a.source.split(" ")[0] for a in articles))

    return NewsResponse(
        articles=articles,
        generated_at=datetime.now().isoformat(),
        cached=not refresh,
        sources=sources
    )


@router.get("/trending", response_model=List[NewsArticle])
async def get_trending_news(limit: int = 10):
    """Get trending cybersecurity news (highest scored articles)."""
    articles = news_aggregator.get_cached()

    if not articles:
        articles = await news_aggregator.fetch_all()

    # Sort by score (upvotes/likes)
    trending = sorted(articles, key=lambda x: x.score, reverse=True)

    return trending[:limit]


@router.get("/recent", response_model=List[NewsArticle])
async def get_recent_news(limit: int = 20):
    """Get most recent cybersecurity news."""
    articles = news_aggregator.get_cached()

    if not articles:
        articles = await news_aggregator.fetch_all()

    # Sort by date (newest first)
    recent = sorted(articles, key=lambda x: x.date, reverse=True)

    return recent[:limit]


@router.get("/categories", response_model=List[NewsCategory])
async def get_news_categories():
    """Get available news categories with counts."""
    articles = news_aggregator.get_cached()

    if not articles:
        articles = await news_aggregator.fetch_all()

    categories = {}
    for article in articles:
        cat = article.category
        categories[cat] = categories.get(cat, 0) + 1

    return [NewsCategory(name=k, count=v) for k, v in sorted(categories.items(), key=lambda x: x[1], reverse=True)]


@router.get("/by-category/{category}", response_model=List[NewsArticle])
async def get_news_by_category(category: str, limit: int = 20):
    """Get news filtered by category."""
    articles = news_aggregator.get_cached()

    if not articles:
        articles = await news_aggregator.fetch_all()

    filtered = [
        article for article in articles
        if article.category.lower() == category.lower()
    ]

    return filtered[:limit]


@router.get("/by-severity/{severity}", response_model=List[NewsArticle])
async def get_news_by_severity(severity: str, limit: int = 20):
    """Get news filtered by severity."""
    articles = news_aggregator.get_cached()

    if not articles:
        articles = await news_aggregator.fetch_all()

    filtered = [
        article for article in articles
        if article.severity and article.severity.lower() == severity.lower()
    ]

    return filtered[:limit]


@router.get("/by-source/{source}", response_model=List[NewsArticle])
async def get_news_by_source(source: str, limit: int = 20):
    """Get news filtered by source (e.g., 'HackerNews', 'Reddit')."""
    articles = news_aggregator.get_cached()

    if not articles:
        articles = await news_aggregator.fetch_all()

    filtered = [
        article for article in articles
        if source.lower() in article.source.lower()
    ]

    return filtered[:limit]


@router.get("/search", response_model=List[NewsArticle])
async def search_news(q: str, limit: int = 20):
    """Search news articles by keyword."""
    articles = news_aggregator.get_cached()

    if not articles:
        articles = await news_aggregator.fetch_all()

    query = q.lower()
    filtered = [
        article for article in articles
        if query in article.title.lower() or query in article.summary.lower()
    ]

    return filtered[:limit]


# ============================================================================
# Article Detail (with AI Analysis)
# ============================================================================

class ArticleDetail(BaseModel):
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
    # Extended details (AI generated)
    full_analysis: str
    technical_details: str
    impact_assessment: str
    recommendations: List[str]
    related_cves: List[str] = []
    affected_systems: List[str] = []
    iocs: List[str] = []


# Cache for article details
_article_detail_cache: Dict[str, ArticleDetail] = {}


async def generate_article_details(article: NewsArticle) -> ArticleDetail:
    """Generate detailed analysis for a news article using AI."""

    prompt = f"""You are a senior cybersecurity analyst. Provide a detailed analysis of this cybersecurity news:

Title: {article.title}
Summary: {article.summary}
Category: {article.category}
Severity: {article.severity}
Source: {article.source}
Date: {article.date}

Generate a comprehensive analysis in the following JSON format ONLY (no markdown, no explanation):
{{
    "full_analysis": "A detailed 3-4 paragraph analysis of this security incident/vulnerability/threat. Include background context, how it works, who is affected, and the broader implications for the cybersecurity landscape.",
    "technical_details": "Technical explanation including attack vectors, exploitation methods, vulnerability mechanics, or malware capabilities. Be specific and technical.",
    "impact_assessment": "Assessment of the potential impact on organizations, including business impact, data at risk, and potential consequences of exploitation.",
    "recommendations": ["Specific actionable recommendation 1", "Recommendation 2", "Recommendation 3", "Recommendation 4", "Recommendation 5"],
    "related_cves": ["CVE-YYYY-XXXXX", "CVE-YYYY-XXXXX"],
    "affected_systems": ["System/Software 1", "System/Software 2", "System/Software 3"],
    "iocs": ["indicator1.malicious.com", "192.168.x.x", "hash:abc123..."]
}}

Make the analysis realistic, detailed, and technically accurate. If no CVEs are relevant, return empty array. Generate realistic IOCs if applicable."""

    try:
        messages = [{"role": "user", "content": prompt}]

        response = await teaching_engine.generate_response(
            messages=messages,
            teaching_mode="lecture",
            skill_level="advanced",
            temperature=0.7,
            max_tokens=2500,
        )

        # Parse JSON from response
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        start = response.find("{")
        end = response.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        details_data = json.loads(response[start:end])

        return ArticleDetail(
            id=article.id,
            title=article.title,
            summary=article.summary,
            category=article.category,
            severity=article.severity,
            source=article.source,
            source_url=article.source_url,
            date=article.date,
            tags=article.tags,
            score=article.score,
            comments=article.comments,
            full_analysis=details_data.get("full_analysis", "Analysis not available."),
            technical_details=details_data.get("technical_details", "Technical details not available."),
            impact_assessment=details_data.get("impact_assessment", "Impact assessment not available."),
            recommendations=details_data.get("recommendations", []),
            related_cves=details_data.get("related_cves", []),
            affected_systems=details_data.get("affected_systems", []),
            iocs=details_data.get("iocs", [])
        )

    except Exception as e:
        logger.error("Failed to generate article details", error=str(e))
        # Return basic details on error
        return ArticleDetail(
            id=article.id,
            title=article.title,
            summary=article.summary,
            category=article.category,
            severity=article.severity,
            source=article.source,
            source_url=article.source_url,
            date=article.date,
            tags=article.tags,
            score=article.score,
            comments=article.comments,
            full_analysis=f"This {article.category.lower()} news highlights ongoing developments in the cybersecurity landscape. {article.summary}",
            technical_details="Detailed technical analysis is being generated. Please try again.",
            impact_assessment="Organizations should assess their exposure to this threat and take appropriate measures.",
            recommendations=["Monitor security advisories", "Apply available patches", "Review access controls", "Enhance monitoring"],
            related_cves=[],
            affected_systems=[],
            iocs=[]
        )


@router.get("/article/{article_id}", response_model=ArticleDetail)
async def get_article_detail(article_id: str):
    """Get detailed AI analysis for a specific article."""
    global _article_detail_cache

    # Check cache first
    if article_id in _article_detail_cache:
        return _article_detail_cache[article_id]

    # Find the article
    articles = news_aggregator.get_cached()
    if not articles:
        articles = await news_aggregator.fetch_all()

    article = None
    for a in articles:
        if a.id == article_id:
            article = a
            break

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Generate detailed analysis
    detail = await generate_article_details(article)

    # Cache the result
    _article_detail_cache[article_id] = detail

    return detail


class ArticleDetailRequest(BaseModel):
    """Request body for generating article details from provided data."""
    id: str
    title: str
    summary: str
    category: str
    severity: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    date: str
    tags: List[str] = []


@router.post("/article/details", response_model=ArticleDetail)
async def get_article_detail_from_data(request: ArticleDetailRequest):
    """Get detailed AI analysis for an article using provided data."""
    global _article_detail_cache

    # Check cache first
    if request.id in _article_detail_cache:
        return _article_detail_cache[request.id]

    # Create article object from request data
    article = NewsArticle(
        id=request.id,
        title=request.title,
        summary=request.summary,
        category=request.category,
        severity=request.severity,
        source=request.source,
        source_url=request.source_url,
        date=request.date,
        tags=request.tags,
        score=0,
        comments=0
    )

    # Generate detailed analysis
    detail = await generate_article_details(article)

    # Cache the result
    _article_detail_cache[request.id] = detail

    return detail


# ============================================================================
# Saved Articles (User's saved news articles - persisted to database)
# ============================================================================

class SaveArticleRequest(BaseModel):
    """Request body for saving an article."""
    id: str
    title: str
    summary: str
    category: str
    severity: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    date: str
    tags: List[str] = []


class SavedArticleResponse(BaseModel):
    """Response for a saved article."""
    id: str
    title: str
    summary: str
    category: str
    severity: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    date: str
    tags: List[str] = []
    is_favorite: bool = False
    saved_at: Optional[str] = None


class SavedArticlesListResponse(BaseModel):
    """Response for list of saved articles."""
    articles: List[SavedArticleResponse]
    favorite_ids: List[str]
    total: int


@router.get("/saved", response_model=SavedArticlesListResponse)
async def get_saved_articles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all saved articles for the current user."""
    saved = db.query(SavedArticle).filter(
        SavedArticle.user_id == current_user.id
    ).order_by(SavedArticle.saved_at.desc()).all()

    articles = [
        SavedArticleResponse(
            id=s.article_id,
            title=s.title,
            summary=s.summary,
            category=s.category,
            severity=s.severity,
            source=s.source,
            source_url=s.source_url,
            date=s.article_date,
            tags=s.tags or [],
            is_favorite=s.is_favorite,
            saved_at=s.saved_at.isoformat() if s.saved_at else None
        )
        for s in saved
    ]

    favorite_ids = [s.article_id for s in saved if s.is_favorite]

    return SavedArticlesListResponse(
        articles=articles,
        favorite_ids=favorite_ids,
        total=len(articles)
    )


@router.post("/saved", response_model=SavedArticleResponse)
async def save_article(
    request: SaveArticleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save an article to the user's saved articles."""
    # Check if already saved
    existing = db.query(SavedArticle).filter(
        SavedArticle.user_id == current_user.id,
        SavedArticle.article_id == request.id
    ).first()

    if existing:
        # Article already saved, return it
        return SavedArticleResponse(
            id=existing.article_id,
            title=existing.title,
            summary=existing.summary,
            category=existing.category,
            severity=existing.severity,
            source=existing.source,
            source_url=existing.source_url,
            date=existing.article_date,
            tags=existing.tags or [],
            is_favorite=existing.is_favorite,
            saved_at=existing.saved_at.isoformat() if existing.saved_at else None
        )

    # Create new saved article
    saved = SavedArticle(
        user_id=current_user.id,
        article_id=request.id,
        title=request.title,
        summary=request.summary,
        category=request.category,
        severity=request.severity,
        source=request.source,
        source_url=request.source_url,
        article_date=request.date,
        tags=request.tags,
        is_favorite=False
    )

    db.add(saved)
    db.commit()
    db.refresh(saved)

    logger.info("Article saved", user_id=str(current_user.id), article_id=request.id)

    return SavedArticleResponse(
        id=saved.article_id,
        title=saved.title,
        summary=saved.summary,
        category=saved.category,
        severity=saved.severity,
        source=saved.source,
        source_url=saved.source_url,
        date=saved.article_date,
        tags=saved.tags or [],
        is_favorite=saved.is_favorite,
        saved_at=saved.saved_at.isoformat() if saved.saved_at else None
    )


@router.delete("/saved/{article_id}")
async def unsave_article(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove an article from saved articles."""
    saved = db.query(SavedArticle).filter(
        SavedArticle.user_id == current_user.id,
        SavedArticle.article_id == article_id
    ).first()

    if not saved:
        raise HTTPException(status_code=404, detail="Saved article not found")

    db.delete(saved)
    db.commit()

    logger.info("Article unsaved", user_id=str(current_user.id), article_id=article_id)

    return {"success": True, "message": "Article removed from saved"}


@router.post("/saved/{article_id}/favorite")
async def toggle_favorite(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle favorite status for a saved article."""
    saved = db.query(SavedArticle).filter(
        SavedArticle.user_id == current_user.id,
        SavedArticle.article_id == article_id
    ).first()

    if not saved:
        raise HTTPException(status_code=404, detail="Saved article not found")

    saved.is_favorite = not saved.is_favorite
    db.commit()

    logger.info(
        "Article favorite toggled",
        user_id=str(current_user.id),
        article_id=article_id,
        is_favorite=saved.is_favorite
    )

    return {
        "success": True,
        "is_favorite": saved.is_favorite
    }
