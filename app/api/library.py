"""
音乐收藏库 API
提供搜索结果收藏、筛选、管理功能
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.database.connection import get_db
from app.database.models import MusicLibrary, Song, User, DownloadTask, Playlist, PlaylistSong
from app.api.spotify import SpotifyTrack

router = APIRouter(prefix="/api/library", tags=["Music Library"])

# Pydantic 模型
class LibraryAddRequest(BaseModel):
    spotify_id: str
    category: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    custom_country: Optional[str] = None  # 用户自定义国家
    custom_region: Optional[str] = None   # 用户自定义地区
    custom_language: Optional[str] = None # 用户自定义语言

class LibraryFilter(BaseModel):
    region_group: Optional[str] = None  # 地区分组
    country: Optional[str] = None
    language: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    has_preview: Optional[bool] = None
    is_downloaded: Optional[bool] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None

class LibraryCreatePlaylistRequest(BaseModel):
    name: str
    description: Optional[str] = None
    song_ids: List[int]  # 从收藏库选择的歌曲ID
    category: Optional[str] = None

class LibraryEntry(BaseModel):
    id: int
    song: SpotifyTrack
    category: Optional[str]
    tags: Optional[str]
    notes: Optional[str]
    custom_country: Optional[str]  # 用户自定义国家
    custom_region: Optional[str]   # 用户自定义地区
    custom_language: Optional[str] # 用户自定义语言
    is_downloaded: bool
    download_task_id: Optional[int]
    added_at: datetime
    
    class Config:
        from_attributes = True

class LibraryResponse(BaseModel):
    entries: List[LibraryEntry]
    total: int
    page: int
    per_page: int
    filters_applied: Dict[str, Any]

# 临时用户ID (实际应用中从认证中获取)
def get_current_user_id() -> int:
    return 1  # 临时固定用户ID

@router.post("/add")
async def add_to_library(
    request: LibraryAddRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """添加歌曲到收藏库"""
    try:
        # 检查歌曲是否存在，不存在则从Spotify获取并保存
        song = db.query(Song).filter(Song.spotify_id == request.spotify_id).first()
        
        if not song:
            # 从Spotify API获取歌曲信息
            from app.api.spotify import spotify_service
            track_info = spotify_service.get_track_info(request.spotify_id)
            
            if not track_info:
                raise HTTPException(status_code=404, detail="歌曲信息未找到")
            
            # 创建新歌曲记录
            from app.services.language_detector import language_detector
            artist_names = ', '.join([artist['name'] for artist in track_info['artists']])
            country, language = language_detector.detect_country_and_language(
                track_info['name'], artist_names, track_info.get('album', {}).get('name')
            )
            
            song = Song(
                spotify_id=request.spotify_id,
                title=track_info['name'],
                artist=artist_names,
                album=track_info.get('album', {}).get('name'),
                album_art_url=track_info.get('album', {}).get('images', [{}])[0].get('url') if track_info.get('album', {}).get('images') else None,
                preview_url=track_info.get('preview_url'),
                spotify_url=track_info['external_urls']['spotify'],
                duration=track_info.get('duration_ms', 0) // 1000,
                year=int(track_info.get('album', {}).get('release_date', '')[:4]) if track_info.get('album', {}).get('release_date') else None,
                country=country,
                language=language,
                popularity=track_info.get('popularity', 0)
            )
            db.add(song)
            db.flush()  # 获取song.id
        
        # 检查是否已经在收藏库中
        existing = db.query(MusicLibrary).filter(
            and_(MusicLibrary.user_id == user_id, MusicLibrary.song_id == song.id)
        ).first()
        
        if existing:
            # 更新现有记录
            if request.category:
                existing.category = request.category
            if request.tags:
                existing.tags = request.tags
            if request.notes:
                existing.notes = request.notes
            if request.custom_country:
                existing.custom_country = request.custom_country
            if request.custom_region:
                existing.custom_region = request.custom_region
            if request.custom_language:
                existing.custom_language = request.custom_language
            existing.last_accessed = datetime.now()
            
            # 更新歌曲的国家和语言信息（如果提供）
            if request.country and not song.country:
                song.country = request.country
            if request.language and not song.language:
                song.language = request.language
            
            db.commit()
            return {"message": "收藏库记录已更新", "library_id": existing.id}
        
        # 更新歌曲的国家和语言信息（如果提供）
        if request.country and not song.country:
            song.country = request.country
        if request.language and not song.language:
            song.language = request.language
        
        # 创建新的收藏库记录
        library_entry = MusicLibrary(
            user_id=user_id,
            song_id=song.id,
            category=request.category,
            tags=request.tags,
            notes=request.notes,
            custom_country=request.custom_country,
            custom_region=request.custom_region,
            custom_language=request.custom_language
        )
        
        db.add(library_entry)
        db.commit()
        
        return {"message": "已添加到收藏库", "library_id": library_entry.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")

@router.get("/", response_model=dict)
async def get_library(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=10000),
    # 筛选参数
    region_group: Optional[str] = Query(""),  # 地区分组
    country: Optional[str] = Query(""),
    language: Optional[str] = Query(""),
    category: Optional[str] = Query(""),
    tags: Optional[str] = Query(""),
    has_preview: Optional[str] = Query(""),
    is_downloaded: Optional[str] = Query(""),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    search: Optional[str] = Query(""),
    sort_by: str = Query("added_at"),
    sort_order: str = Query("desc"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取用户的音乐收藏库，支持筛选和分页"""
    try:
        # 构建查询
        query = db.query(MusicLibrary).join(Song).filter(MusicLibrary.user_id == user_id)
        
        # 应用筛选条件
        filters_applied = {}
        
        # 处理空字符串，转换为None
        region_group = region_group if region_group and region_group.strip() else None
        country = country if country and country.strip() else None
        language = language if language and language.strip() else None
        category = category if category and category.strip() else None
        tags = tags if tags and tags.strip() else None
        search = search if search and search.strip() else None
        
        # 处理布尔字符串
        if has_preview and has_preview.strip():
            has_preview = has_preview.lower() in ('true', '1', 'yes')
        else:
            has_preview = None
            
        if is_downloaded and is_downloaded.strip():
            is_downloaded = is_downloaded.lower() in ('true', '1', 'yes')
        else:
            is_downloaded = None
        
        # 地区分组筛选
        if region_group:
            # 定义地区分组映射
            region_group_mapping = {
                'asia': ['中国', '韩国', '日本', '台湾', '泰国', '越南', '新加坡', '马来西亚', '印度尼西亚', '菲律宾', '印度'],
                'eastasia': ['中国', '韩国', '日本', '台湾'],
                'japankorea': ['韩国', '日本'],
                'southeast': ['泰国', '越南', '新加坡', '马来西亚', '印度尼西亚', '菲律宾'],
                'southasia': ['印度'],
                'europe': ['英国', '法国', '德国', '西班牙', '意大利', '俄罗斯'],
                'westerneurope': ['英国', '法国', '德国', '西班牙', '意大利'],
                'easterneurope': ['俄罗斯'],
                'northamerica': ['美国', '加拿大'],
                'southamerica': ['巴西', '墨西哥', '阿根廷'],
                'oceania': ['澳大利亚'],
                'middleeast': ['土耳其'],
                'africa': []
            }
            
            if region_group in region_group_mapping:
                countries_in_group = region_group_mapping[region_group]
                if countries_in_group:
                    # 支持同时筛选歌曲原始国家和用户自定义国家
                    query = query.filter(
                        or_(
                            Song.country.in_(countries_in_group),
                            MusicLibrary.custom_country.in_(countries_in_group)
                        )
                    )
                    filters_applied["region_group"] = region_group
        
        if country:
            # 支持同时筛选歌曲原始国家和用户自定义国家
            query = query.filter(
                or_(
                    Song.country == country,
                    MusicLibrary.custom_country == country
                )
            )
            filters_applied["country"] = country
            
        if language:
            # 支持同时筛选歌曲原始语言和用户自定义语言
            query = query.filter(
                or_(
                    Song.language == language,
                    MusicLibrary.custom_language == language
                )
            )
            filters_applied["language"] = language
            
        if category:
            query = query.filter(MusicLibrary.category == category)
            filters_applied["category"] = category
            
        if tags:
            query = query.filter(MusicLibrary.tags.contains(tags))
            filters_applied["tags"] = tags
            
        if has_preview is not None:
            if has_preview:
                query = query.filter(Song.preview_url.isnot(None))
            else:
                query = query.filter(Song.preview_url.is_(None))
            filters_applied["has_preview"] = has_preview
            
        if is_downloaded is not None:
            query = query.filter(MusicLibrary.is_downloaded == is_downloaded)
            filters_applied["is_downloaded"] = is_downloaded
            
        if year_from:
            query = query.filter(Song.year >= year_from)
            filters_applied["year_from"] = year_from
            
        if year_to:
            query = query.filter(Song.year <= year_to)
            filters_applied["year_to"] = year_to
            
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Song.title.like(search_term),
                    Song.artist.like(search_term),
                    Song.album.like(search_term),
                    MusicLibrary.tags.like(search_term),
                    MusicLibrary.notes.like(search_term)
                )
            )
            filters_applied["search"] = search
        
        # 排序
        if sort_by == "added_at":
            sort_column = MusicLibrary.added_at
        elif sort_by == "title":
            sort_column = Song.title
        elif sort_by == "artist":
            sort_column = Song.artist
        elif sort_by == "year":
            sort_column = Song.year
        elif sort_by == "popularity":
            sort_column = Song.popularity
        else:
            sort_column = MusicLibrary.added_at
            
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * per_page
        entries = query.offset(offset).limit(per_page).all()
        
        # 格式化响应
        library_entries = []
        for entry in entries:
            song_data = SpotifyTrack(
                id=entry.song.spotify_id,
                title=entry.song.title,
                artist=entry.song.artist,
                album=entry.song.album,
                album_art=entry.song.album_art_url,
                duration=entry.song.duration,
                preview_url=entry.song.preview_url,
                spotify_url=entry.song.spotify_url,
                year=entry.song.year,
                country=entry.song.country,
                language=entry.song.language
            )
            # 添加数据库ID作为额外属性
            song_data.database_id = entry.song.id
            
            library_entries.append(LibraryEntry(
                id=entry.id,
                song=song_data,
                category=entry.category,
                tags=entry.tags,
                notes=entry.notes,
                custom_country=entry.custom_country,
                custom_region=entry.custom_region,
                custom_language=entry.custom_language,
                is_downloaded=entry.is_downloaded,
                download_task_id=entry.download_task_id,
                added_at=entry.added_at
            ))
        
        return {
            "data": LibraryResponse(
                entries=library_entries,
                total=total,
                page=page,
                per_page=per_page,
                filters_applied=filters_applied
            ),
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取收藏库失败: {str(e)}")

@router.delete("/{library_id}")
async def remove_from_library(
    library_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """从收藏库删除歌曲"""
    try:
        entry = db.query(MusicLibrary).filter(
            and_(MusicLibrary.id == library_id, MusicLibrary.user_id == user_id)
        ).first()
        
        if not entry:
            raise HTTPException(status_code=404, detail="收藏记录未找到")
        
        db.delete(entry)
        db.commit()
        
        return {"message": "已从收藏库删除"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post("/create-playlist")
async def create_playlist_from_library(
    request: LibraryCreatePlaylistRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """从收藏库创建歌单"""
    try:
        # 验证选择的歌曲都属于当前用户的收藏库
        library_entries = db.query(MusicLibrary).filter(
            and_(
                MusicLibrary.user_id == user_id,
                MusicLibrary.id.in_(request.song_ids)
            )
        ).all()
        
        if len(library_entries) != len(request.song_ids):
            raise HTTPException(status_code=400, detail="部分歌曲不在您的收藏库中")
        
        # 创建歌单
        playlist = Playlist(
            user_id=user_id,
            name=request.name,
            description=request.description,
            category=request.category,
            total_tracks=len(library_entries)
        )
        
        db.add(playlist)
        db.flush()  # 获取playlist.id
        
        # 添加歌曲到歌单
        for position, entry in enumerate(library_entries):
            playlist_song = PlaylistSong(
                playlist_id=playlist.id,
                song_id=entry.song_id,
                position=position
            )
            db.add(playlist_song)
        
        db.commit()
        
        return {
            "message": "歌单创建成功",
            "playlist_id": playlist.id,
            "playlist_name": playlist.name,
            "songs_added": len(library_entries)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建歌单失败: {str(e)}")

@router.get("/categories")
async def get_categories(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取用户收藏库中的所有分类"""
    try:
        categories = db.query(MusicLibrary.category).filter(
            and_(MusicLibrary.user_id == user_id, MusicLibrary.category.isnot(None))
        ).distinct().all()
        
        return {"categories": [cat[0] for cat in categories if cat[0]]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")

@router.get("/stats")
async def get_library_stats(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取收藏库统计信息"""
    try:
        total_songs = db.query(MusicLibrary).filter(MusicLibrary.user_id == user_id).count()
        
        downloaded_songs = db.query(MusicLibrary).filter(
            and_(MusicLibrary.user_id == user_id, MusicLibrary.is_downloaded == True)
        ).count()
        
        # 按国家统计
        from sqlalchemy import func
        country_stats = db.query(Song.country, func.count(MusicLibrary.id)).join(
            MusicLibrary
        ).filter(MusicLibrary.user_id == user_id).group_by(Song.country).all()
        
        # 按语言统计
        language_stats = db.query(Song.language, func.count(MusicLibrary.id)).join(
            MusicLibrary
        ).filter(MusicLibrary.user_id == user_id).group_by(Song.language).all()
        
        # 有预览的歌曲数量
        preview_available = db.query(MusicLibrary).join(Song).filter(
            and_(MusicLibrary.user_id == user_id, Song.preview_url.isnot(None))
        ).count()
        
        return {
            "data": {
                "total_songs": total_songs,
                "downloaded_songs": downloaded_songs,
                "preview_available": preview_available,
                "download_rate": downloaded_songs / total_songs if total_songs > 0 else 0,
                "preview_rate": preview_available / total_songs if total_songs > 0 else 0,
                "country_distribution": [{"country": country, "count": count} for country, count in country_stats],
                "language_distribution": [{"language": language, "count": count} for language, count in language_stats]
            },
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

# ============= 异步任务端点 =============

class AsyncLibraryAddRequest(BaseModel):
    spotify_id: str
    category: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    custom_country: Optional[str] = None
    custom_region: Optional[str] = None
    custom_language: Optional[str] = None

class AsyncPlaylistAddRequest(BaseModel):
    playlist_id: str
    category: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    custom_country: Optional[str] = None
    custom_region: Optional[str] = None
    custom_language: Optional[str] = None

class AsyncAlbumAddRequest(BaseModel):
    album_id: str
    category: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    custom_country: Optional[str] = None
    custom_region: Optional[str] = None
    custom_language: Optional[str] = None

class BatchPlaylistAddRequest(BaseModel):
    playlist_ids: List[str]
    category: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    custom_country: Optional[str] = None
    custom_region: Optional[str] = None
    custom_language: Optional[str] = None

class BatchAlbumAddRequest(BaseModel):
    album_ids: List[str]
    category: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    custom_country: Optional[str] = None
    custom_region: Optional[str] = None
    custom_language: Optional[str] = None

@router.post("/add-async")
async def add_to_library_async(
    request: AsyncLibraryAddRequest,
    user_id: int = Depends(get_current_user_id)
):
    """异步添加歌曲到收藏库"""
    try:
        settings = {
            'category': request.category,
            'country': request.country,
            'language': request.language,
            'tags': request.tags,
            'notes': request.notes,
            'custom_country': request.custom_country,
            'custom_region': request.custom_region,
            'custom_language': request.custom_language
        }
        
        from app.tasks.batch_tasks import add_single_track_to_library
        task = add_single_track_to_library.delay(request.spotify_id, settings, user_id)
        
        return {
            "task_id": task.id,
            "message": "歌曲添加任务已创建",
            "status": "pending"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.post("/add-playlist-async")
async def add_playlist_to_library_async(
    request: AsyncPlaylistAddRequest,
    user_id: int = Depends(get_current_user_id)
):
    """异步添加歌单到收藏库"""
    try:
        settings = {
            'category': request.category,
            'tags': request.tags,
            'notes': request.notes,
            'custom_country': request.custom_country,
            'custom_region': request.custom_region,
            'custom_language': request.custom_language
        }
        
        from app.tasks.batch_tasks import add_single_playlist_to_library
        task = add_single_playlist_to_library.delay(request.playlist_id, settings, user_id)
        
        return {
            "task_id": task.id,
            "message": "歌单添加任务已创建",
            "status": "pending"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.post("/add-album-async")
async def add_album_to_library_async(
    request: AsyncAlbumAddRequest,
    user_id: int = Depends(get_current_user_id)
):
    """异步添加专辑到收藏库"""
    try:
        settings = {
            'category': request.category,
            'tags': request.tags,
            'notes': request.notes,
            'custom_country': request.custom_country,
            'custom_region': request.custom_region,
            'custom_language': request.custom_language
        }
        
        from app.tasks.batch_tasks import add_single_album_to_library
        task = add_single_album_to_library.delay(request.album_id, settings, user_id)
        
        return {
            "task_id": task.id,
            "message": "专辑添加任务已创建",
            "status": "pending"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.post("/add-playlists-batch-async")
async def add_multiple_playlists_async(
    request: BatchPlaylistAddRequest,
    user_id: int = Depends(get_current_user_id)
):
    """异步批量添加多个歌单到收藏库"""
    try:
        settings = {
            'category': request.category,
            'tags': request.tags,
            'notes': request.notes,
            'custom_country': request.custom_country,
            'custom_region': request.custom_region,
            'custom_language': request.custom_language
        }
        
        from app.tasks.batch_tasks import batch_add_multiple_playlists
        task = batch_add_multiple_playlists.delay(request.playlist_ids, settings, user_id)
        
        return {
            "task_id": task.id,
            "message": f"批量歌单添加任务已创建，共 {len(request.playlist_ids)} 个歌单",
            "status": "pending",
            "total_playlists": len(request.playlist_ids)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.post("/add-albums-batch-async")
async def add_multiple_albums_async(
    request: BatchAlbumAddRequest,
    user_id: int = Depends(get_current_user_id)
):
    """异步批量添加多个专辑到收藏库"""
    try:
        settings = {
            'category': request.category,
            'tags': request.tags,
            'notes': request.notes,
            'custom_country': request.custom_country,
            'custom_region': request.custom_region,
            'custom_language': request.custom_language
        }
        
        from app.tasks.batch_tasks import batch_add_multiple_albums
        task = batch_add_multiple_albums.delay(request.album_ids, settings, user_id)
        
        return {
            "task_id": task.id,
            "message": f"批量专辑添加任务已创建，共 {len(request.album_ids)} 个专辑",
            "status": "pending",
            "total_albums": len(request.album_ids)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.get("/task-status/{task_id}")
async def get_library_task_status(task_id: str):
    """获取收藏库任务状态"""
    try:
        from app.celery_app import app as celery_app
        task = celery_app.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'status': '任务等待中',
                'progress': 0
            }
        elif task.state == 'PROGRESS':
            response = {
                'state': task.state,
                'progress': task.info.get('progress', 0),
                'status': task.info.get('status', '处理中'),
                'completed': task.info.get('completed', 0),
                'total': task.info.get('total', 0),
                'failed': task.info.get('failed', 0)
            }
        elif task.state == 'SUCCESS':
            response = {
                'state': task.state,
                'progress': 100,
                'status': '任务完成',
                'result': task.result
            }
        else:  # FAILURE
            response = {
                'state': task.state,
                'status': '任务失败',
                'error': str(task.info)
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")