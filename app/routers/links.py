from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import random
import string
from typing import Optional
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
import logging
import urllib.parse 
from ..database import get_db
from ..models import Link, User
from ..schemas import LinkCreate, LinkResponse, LinkUpdate, LinkStats
from ..routers.auth import get_current_user
from ..tasks import increment_click_count

router = APIRouter(prefix="/links", tags=["links"])
logger = logging.getLogger(__name__)

def generate_short_code(length: int = 6) -> str:
    """Генерация уникального короткого кода"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@router.get("/search", response_model=list[LinkResponse])
async def search_by_original_url(
    original_url: str = Query(..., description="Original URL to search"),
    db: Session = Depends(get_db)
):
    """Поиск ссылок по оригинальному URL"""
    decoded_url = urllib.parse.unquote(original_url)
    
    logger.info(f"Searching for URL: {original_url}")
    logger.info(f"Decoded URL: {decoded_url}")
    
    links = db.query(Link).filter(
        (Link.original_url == original_url) | 
        (Link.original_url.contains(decoded_url)) |
        (Link.original_url == decoded_url),
        Link.is_active == True
    ).all()
    
    logger.info(f"Found {len(links)} links")
    
    if not links:
        all_links = db.query(Link).filter(Link.is_active == True).all()
        logger.info(f"All active links in DB: {[l.original_url for l in all_links]}")
    
    return links

@router.post("/shorten", response_model=LinkResponse)
async def create_short_link(
    link_data: LinkCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Создание короткой ссылки"""
    if link_data.custom_alias:
        existing = db.query(Link).filter(
            or_(
                Link.short_code == link_data.custom_alias,
                Link.custom_alias == link_data.custom_alias
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom alias already exists"
            )
        short_code = link_data.custom_alias
    else:
        while True:
            short_code = generate_short_code()
            existing = db.query(Link).filter(Link.short_code == short_code).first()
            if not existing:
                break
    
    db_link = Link(
        original_url=str(link_data.original_url),
        short_code=short_code,
        custom_alias=link_data.custom_alias,
        expires_at=link_data.expires_at,
        owner_id=current_user.id if current_user else None
    )
    
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    
    try:
        await FastAPICache.clear()
        logger.info(f"Cache cleared after creating link {short_code}")
    except Exception as e:
        logger.warning(f"Cache clear error (non-critical): {e}")
    
    return db_link

@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    db: Session = Depends(get_db)
):
    """Перенаправление на оригинальный URL"""
    link = db.query(Link).filter(
        or_(Link.short_code == short_code, Link.custom_alias == short_code),
        Link.is_active == True
    ).first()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found or expired"
        )
    
    if link.expires_at and link.expires_at < datetime.utcnow():
        link.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Link has expired"
        )
    
    try:
        increment_click_count.delay(link.id)
    except Exception as e:
        logger.error(f"Error incrementing click count: {e}")
    
    logger.info(f"Redirecting {short_code} -> {link.original_url}")
    return RedirectResponse(url=link.original_url)

@router.delete("/{short_code}")
async def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаление ссылки (только для авторизованных пользователей)"""
    link = db.query(Link).filter(
        or_(Link.short_code == short_code, Link.custom_alias == short_code)
    ).first()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )
    
    if link.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db.delete(link)
    db.commit()
    
    try:
        await FastAPICache.clear()
        logger.info(f"Cache cleared after deleting link {short_code}")
    except Exception as e:
        logger.warning(f"Cache clear error (non-critical): {e}")
    
    return {"message": "Link deleted successfully"}

@router.put("/{short_code}", response_model=LinkResponse)
async def update_link(
    short_code: str,
    link_data: LinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновление URL для короткой ссылки"""
    link = db.query(Link).filter(
        or_(Link.short_code == short_code, Link.custom_alias == short_code)
    ).first()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )

    if link.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    link.original_url = link_data.original_url
    db.commit()
    db.refresh(link)

    try:
        await FastAPICache.clear()
        logger.info(f"Cache cleared after updating link {short_code}")
    except Exception as e:
        logger.warning(f"Cache clear error (non-critical): {e}")
    
    return link

@router.get("/{short_code}/stats", response_model=LinkStats)
@cache(expire=60)
async def get_link_stats(
    short_code: str,
    db: Session = Depends(get_db)
):
    """Статистика по ссылке"""
    link = db.query(Link).filter(
        or_(Link.short_code == short_code, Link.custom_alias == short_code)
    ).first()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )

    base_url = "http://localhost:8000"
    short_url = f"{base_url}/{link.short_code}"

    stats_data = {
        "id": link.id,
        "original_url": link.original_url,
        "short_code": link.short_code,
        "created_at": link.created_at,
        "expires_at": link.expires_at,
        "clicks": link.clicks,
        "owner_id": link.owner_id,
        "custom_alias": link.custom_alias,
        "last_clicked_at": link.last_clicked_at,
        "short_url": short_url
    }
    
    return stats_data
