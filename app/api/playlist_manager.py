from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import Song, Playlist, playlist_songs
from app.services.language_detector import language_detector
from app.api.schemas import ApiResponse
from pydantic import BaseModel
from typing import List, Optional
import math
import json

router = APIRouter(prefix="/api/playlists", tags=["playlist_manager"])

class CreatePlaylistRequest(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    mood: Optional[str] = None
    is_public: bool = True

class AddSongsToPlaylistRequest(BaseModel):
    song_ids: List[int]

class SearchResultTrack(BaseModel):
    id: str
    title: str
    artist: str
    album: Optional[str] = None
    album_art: Optional[str] = None
    duration: Optional[int] = None
    preview_url: Optional[str] = None
    spotify_url: str
    country: Optional[str] = None
    language: Optional[str] = None

class AddSearchResultsRequest(BaseModel):
    tracks: List[SearchResultTrack]

class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    total_tracks: int
    category: Optional[str]
    tags: Optional[str]
    country: Optional[str]
    language: Optional[str]
    mood: Optional[str]
    playlist_type: str
    created_at: str
    songs: List[dict] = []

@router.post("/create", response_model=ApiResponse)
async def create_playlist(
    request: CreatePlaylistRequest,
    db: Session = Depends(get_db)
):
    """创建新歌单"""
    try:
        # 检查同名歌单
        existing = db.query(Playlist).filter(
            Playlist.name == request.name,
            Playlist.playlist_type == "user"
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="歌单名称已存在")
        
        # 创建歌单
        playlist = Playlist(
            name=request.name,
            description=request.description,
            category=request.category,
            tags=request.tags,
            country=request.country,
            language=request.language,
            mood=request.mood,
            is_public=request.is_public,
            playlist_type="user",
            owner="用户"  # 可以后续改为实际用户系统
        )
        
        db.add(playlist)
        db.commit()
        db.refresh(playlist)
        
        return ApiResponse(
            success=True,
            message=f"歌单 '{request.name}' 创建成功",
            data={"playlist_id": playlist.id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def get_user_playlists(
    search: Optional[str] = Query(None, description="搜索歌单名称"),
    category: Optional[str] = Query(None, description="按分类筛选"),
    country: Optional[str] = Query(None, description="按国家筛选"),
    language: Optional[str] = Query(None, description="按语言筛选"),
    db: Session = Depends(get_db)
):
    """获取用户歌单列表"""
    try:
        query = db.query(Playlist).filter(Playlist.playlist_type == "user")
        
        # 搜索过滤
        if search:
            search_term = f"%{search}%"
            query = query.filter(Playlist.name.ilike(search_term))
        
        # 分类过滤
        if category:
            query = query.filter(Playlist.category == category)
        
        # 国家过滤
        if country:
            query = query.filter(Playlist.country == country)
        
        # 语言过滤
        if language:
            query = query.filter(Playlist.language == language)
        
        playlists = query.order_by(desc(Playlist.created_at)).all()
        
        # 直接返回dict列表，避免Pydantic过滤
        result = [playlist.to_dict() for playlist in playlists]
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cleanup-empty", response_model=ApiResponse)
async def cleanup_empty_playlists(db: Session = Depends(get_db)):
    """清理空歌单"""
    try:
        # 查找没有歌曲的用户歌单
        empty_playlists = db.query(Playlist).filter(
            Playlist.playlist_type == "user",
            Playlist.total_tracks == 0
        ).all()
        
        count = len(empty_playlists)
        
        # 删除空歌单
        for playlist in empty_playlists:
            db.delete(playlist)
        
        db.commit()
        
        return ApiResponse(
            success=True,
            message=f"已清理 {count} 个空歌单"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{playlist_id}")
async def get_playlist_detail(
    playlist_id: int,
    db: Session = Depends(get_db)
):
    """获取歌单详情"""
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单不存在")
        
        # 直接返回dict，让FastAPI使用更新后的Pydantic模型处理
        result = playlist.to_dict()
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{playlist_id}/songs", response_model=ApiResponse)
async def add_songs_to_playlist(
    playlist_id: int,
    request: AddSongsToPlaylistRequest,
    db: Session = Depends(get_db)
):
    """添加歌曲到歌单"""
    try:
        # 检查歌单是否存在
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单不存在")
        
        added_count = 0
        skipped_count = 0
        
        for song_id in request.song_ids:
            # 检查歌曲是否存在
            song = db.query(Song).filter(Song.id == song_id).first()
            if not song:
                continue
            
            # 检查歌曲是否已在歌单中
            existing = db.query(playlist_songs).filter(
                playlist_songs.c.playlist_id == playlist_id,
                playlist_songs.c.song_id == song_id
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            # 添加歌曲到歌单
            playlist.songs.append(song)
            added_count += 1
        
        # 更新歌单统计
        playlist.total_tracks = len(playlist.songs)
        
        db.commit()
        
        message = f"成功添加 {added_count} 首歌曲"
        if skipped_count > 0:
            message += f"，跳过 {skipped_count} 首重复歌曲"
        
        return ApiResponse(
            success=True,
            message=message,
            data={
                "added": added_count,
                "skipped": skipped_count,
                "total_tracks": playlist.total_tracks
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{playlist_id}/songs/{song_id}", response_model=ApiResponse)
async def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    db: Session = Depends(get_db)
):
    """从歌单中移除歌曲"""
    try:
        # 检查歌单是否存在
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单不存在")
        
        # 检查歌曲是否存在
        song = db.query(Song).filter(Song.id == song_id).first()
        if not song:
            raise HTTPException(status_code=404, detail="歌曲不存在")
        
        # 从歌单中移除歌曲
        if song in playlist.songs:
            playlist.songs.remove(song)
            playlist.total_tracks = len(playlist.songs)
            db.commit()
            
            return ApiResponse(
                success=True,
                message="歌曲已从歌单中移除",
                data={"total_tracks": playlist.total_tracks}
            )
        else:
            raise HTTPException(status_code=404, detail="歌曲不在此歌单中")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{playlist_id}", response_model=ApiResponse)
async def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db)
):
    """删除歌单"""
    try:
        playlist = db.query(Playlist).filter(
            Playlist.id == playlist_id,
            Playlist.playlist_type == "user"  # 只允许删除用户创建的歌单
        ).first()
        
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单不存在或无权删除")
        
        # 删除歌单（关联的歌曲不会被删除，只是解除关联）
        db.delete(playlist)
        db.commit()
        
        return ApiResponse(
            success=True,
            message=f"歌单 '{playlist.name}' 已删除"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/list")
async def get_playlist_categories(db: Session = Depends(get_db)):
    """获取歌单分类列表"""
    try:
        categories = db.query(Playlist.category).filter(
            Playlist.category.isnot(None),
            Playlist.category != ""
        ).distinct().all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        
        # 添加一些预设分类
        default_categories = [
            "韩国流行", "日本动漫", "欧美经典", "中文流行", 
            "电子音乐", "摇滚金属", "民谣轻音乐", "古典音乐"
        ]
        
        # 合并并去重
        all_categories = list(set(category_list + default_categories))
        all_categories.sort()
        
        return {"categories": all_categories}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{playlist_id}/add-search-results", response_model=ApiResponse)
async def add_search_results_to_playlist(
    playlist_id: int,
    request: AddSearchResultsRequest,
    db: Session = Depends(get_db)
):
    """添加搜索结果到歌单（自动创建歌曲记录）"""
    try:
        # 检查歌单是否存在
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单不存在")
        
        added_count = 0
        skipped_count = 0
        
        for track_data in request.tracks:
            # 检查歌曲是否已存在（基于Spotify ID）
            existing_song = db.query(Song).filter(Song.spotify_id == track_data.id).first()
            
            if existing_song:
                # 歌曲已存在，检查是否已在歌单中
                if existing_song in playlist.songs:
                    skipped_count += 1
                    continue
                else:
                    playlist.songs.append(existing_song)
                    added_count += 1
            else:
                # 创建新歌曲记录
                # 智能检测国家和语言
                country, language = language_detector.detect_country_and_language(
                    track_data.title, track_data.artist, track_data.album
                )
                
                # 使用传入的数据或检测的数据
                final_country = track_data.country or country
                final_language = track_data.language or language
                
                new_song = Song(
                    title=track_data.title,
                    artist=track_data.artist,
                    album=track_data.album,
                    duration=track_data.duration,
                    spotify_id=track_data.id,
                    spotify_url=track_data.spotify_url,
                    preview_url=track_data.preview_url,
                    album_art_url=track_data.album_art,
                    country=final_country,
                    language=final_language,
                    download_status="not_downloaded"
                )
                
                db.add(new_song)
                db.flush()  # 获取新歌曲的ID
                
                # 添加到歌单
                playlist.songs.append(new_song)
                added_count += 1
        
        # 更新歌单统计
        playlist.total_tracks = len(playlist.songs)
        
        db.commit()
        
        message = f"成功添加 {added_count} 首歌曲到歌单"
        if skipped_count > 0:
            message += f"，跳过 {skipped_count} 首重复歌曲"
        
        return ApiResponse(
            success=True,
            message=message,
            data={
                "added": added_count,
                "skipped": skipped_count,
                "total_tracks": playlist.total_tracks
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
