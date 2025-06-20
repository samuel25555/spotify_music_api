"""
歌单管理API
支持创建、管理和操作用户歌单
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os

from app.database.connection import get_db
from app.database.models import Playlist, PlaylistSong, Song, User, MusicLibrary, DownloadTask

router = APIRouter(prefix="/api/playlists", tags=["Playlists"])

# Pydantic 模型
class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    category: Optional[str] = None

class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None

class AddSongsRequest(BaseModel):
    song_ids: List[int]

class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    song_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PlaylistDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    song_count: int
    songs: List[dict]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 临时用户ID (实际应用中从认证中获取)
def get_current_user_id() -> int:
    return 1

@router.get("/", response_model=dict)
async def get_playlists(
    page: int = 1,
    per_page: int = 20,
    category: Optional[str] = None,
    search: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    获取用户歌单列表
    
    返回用户创建的所有歌单，包含统计信息和封面。
    
    **查询参数：**
    - page: 页码（默认1）
    - per_page: 每页数量（默认20）
    - category: 按分类筛选
    - search: 按名称搜索
    
    **返回数据包含：**
    - 歌单基本信息
    - 歌曲统计（总数、已下载数、可试听数）
    - 歌单封面（第一首歌的专辑封面）
    - API访问链接
    
    **Laravel使用示例：**
    ```php
    $response = Http::get('http://your-domain/api/playlists');
    foreach ($response->json()['data']['playlists'] as $playlist) {
        echo $playlist['name'] . ' (' . $playlist['song_count'] . '首)';
        echo 'API: ' . $playlist['api_url'];
    }
    ```
    """
    try:
        query = db.query(Playlist).filter(Playlist.user_id == user_id)
        
        if category:
            query = query.filter(Playlist.category == category)
        
        if search:
            query = query.filter(Playlist.name.contains(search))
        
        # 按更新时间倒序
        query = query.order_by(Playlist.updated_at.desc())
        
        total = query.count()
        offset = (page - 1) * per_page
        playlists = query.offset(offset).limit(per_page).all()
        
        # 计算每个歌单的详细信息
        playlist_list = []
        for playlist in playlists:
            # 歌曲总数
            song_count = db.query(PlaylistSong).filter(
                PlaylistSong.playlist_id == playlist.id
            ).count()
            
            # 已下载歌曲数
            downloaded_count = db.query(PlaylistSong).join(Song).join(MusicLibrary).filter(
                and_(
                    PlaylistSong.playlist_id == playlist.id,
                    MusicLibrary.user_id == user_id,
                    MusicLibrary.is_downloaded == True
                )
            ).count()
            
            # 有试听的歌曲数
            preview_count = db.query(PlaylistSong).join(Song).filter(
                and_(
                    PlaylistSong.playlist_id == playlist.id,
                    Song.preview_url.isnot(None)
                )
            ).count()
            
            # 获取歌单封面（使用第一首歌的封面）
            first_song = db.query(PlaylistSong).join(Song).filter(
                PlaylistSong.playlist_id == playlist.id
            ).order_by(PlaylistSong.position).first()
            
            cover_art = first_song.song.album_art_url if first_song else None
            
            playlist_data = {
                "id": playlist.id,
                "name": playlist.name,
                "description": playlist.description,
                "category": playlist.category,
                "song_count": song_count,
                "downloaded_count": downloaded_count,
                "preview_count": preview_count,
                "cover_art_url": cover_art,
                "created_at": playlist.created_at.isoformat(),
                "updated_at": playlist.updated_at.isoformat(),
                "api_url": f"/api/playlists/{playlist.id}"
            }
            
            playlist_list.append(playlist_data)
        
        return {
            "data": {
                "playlists": playlist_list,
                "total": total,
                "page": page,
                "per_page": per_page
            },
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取歌单列表失败: {str(e)}")

@router.get("/{playlist_id}", response_model=dict)
async def get_playlist_detail(
    playlist_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    获取歌单详情
    
    返回完整的歌单信息，包括所有歌曲的详细元数据，适用于Laravel等外部系统集成。
    
    **返回数据包含：**
    - 歌单基本信息（名称、描述、分类等）
    - 歌曲完整元数据（标题、歌手、专辑、封面、时长等）
    - Spotify信息（ID、链接、试听地址等）
    - 下载状态（是否已下载、文件路径、可访问URL等）
    - 收藏库信息（分类、标签、备注等）
    
    **重要说明：**
    - 文件名使用MD5 hash命名，避免特殊字符问题
    - is_downloaded基于实际文件存在性检查，确保准确性
    - file_url可直接用于播放器，无需额外处理
    
    **使用示例（Laravel）：**
    ```php
    use Illuminate\\Support\\Facades\\Http;
    
    $response = Http::get('http://your-domain/api/playlists/{playlist_id}');
    $playlist = $response->json();
    
    foreach ($playlist['data']['songs'] as $song) {
        echo $song['title'] . ' - ' . $song['artist'];
        
        // 播放链接
        if ($song['is_downloaded'] && $song['file_url']) {
            echo ' [下载版本: ' . $song['file_url'] . ']';
        } elseif ($song['preview_url']) {
            echo ' [试听版本: ' . $song['preview_url'] . ']';
        }
        
        // 文件信息
        if ($song['is_downloaded']) {
            echo ' [本地文件: ' . $song['file_path'] . ']';
        }
    }
    ```
    
    **注意：**
    - 支持跨域请求（CORS）
    - 数据实时更新
    - 包含完整的歌曲元数据
    """
    try:
        # 验证歌单所有权
        playlist = db.query(Playlist).filter(
            and_(Playlist.id == playlist_id, Playlist.user_id == user_id)
        ).first()
        
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单未找到")
        
        # 获取歌单中的歌曲
        playlist_songs = db.query(PlaylistSong).join(Song).filter(
            PlaylistSong.playlist_id == playlist_id
        ).order_by(PlaylistSong.position).all()
        
        songs_data = []
        for ps in playlist_songs:
            # 检查歌曲下载状态 - 基于实际文件存在性
            from app.api.download import check_file_exists, get_file_path
            
            library_entry = db.query(MusicLibrary).filter(
                and_(MusicLibrary.user_id == user_id, MusicLibrary.song_id == ps.song.id)
            ).first()
            
            # 检查文件是否实际存在
            is_downloaded = check_file_exists(ps.song)
            file_path = None
            file_url = None
            
            if is_downloaded:
                # 获取实际存在的文件路径和可访问的URL
                file_path = get_file_path(ps.song, "mp3")
                
                # 检查实际文件格式（优先检查webm，因为实际下载的是webm）
                if os.path.exists(file_path.replace('.mp3', '.webm')):
                    file_path = file_path.replace('.mp3', '.webm')
                
                # 生成可通过HTTP访问的URL路径
                from app.utils.url_helper import generate_file_url
                file_url = generate_file_url(file_path)
                
                # 同步更新收藏库状态
                if library_entry and not library_entry.is_downloaded:
                    library_entry.is_downloaded = True
                    db.commit()
            
            songs_data.append({
                # 基础歌曲信息
                "id": ps.song.id,
                "spotify_id": ps.song.spotify_id,
                "title": ps.song.title,
                "artist": ps.song.artist,
                "album": ps.song.album,
                
                # 媒体资源
                "album_art_url": ps.song.album_art_url,
                "preview_url": ps.song.preview_url,
                "spotify_url": ps.song.spotify_url,
                
                # 歌曲属性
                "duration": ps.song.duration,
                "year": ps.song.year,
                "popularity": ps.song.popularity,
                "country": ps.song.country,
                "language": ps.song.language,
                
                # 歌单相关
                "position": ps.position,
                "added_at": ps.added_at.isoformat() if ps.added_at else None,
                
                # 下载状态
                "is_downloaded": is_downloaded,
                "file_path": file_path,  # 服务器本地路径
                "file_url": file_url,    # 可直接访问的HTTP URL
                
                # 收藏库信息
                "library_info": {
                    "library_id": library_entry.id if library_entry else None,
                    "category": library_entry.category if library_entry else None,
                    "tags": library_entry.tags if library_entry else None,
                    "notes": library_entry.notes if library_entry else None,
                    "added_to_library_at": library_entry.added_at.isoformat() if library_entry and library_entry.added_at else None,
                    "last_accessed": library_entry.last_accessed.isoformat() if library_entry and library_entry.last_accessed else None
                }
            })
        
        return {
            "data": PlaylistDetailResponse(
                id=playlist.id,
                name=playlist.name,
                description=playlist.description,
                category=playlist.category,
                song_count=len(songs_data),
                songs=songs_data,
                created_at=playlist.created_at,
                updated_at=playlist.updated_at
            ),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取歌单详情失败: {str(e)}")

@router.post("/", response_model=dict)
async def create_playlist(
    request: PlaylistCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """创建新歌单"""
    try:
        # 检查歌单名称是否已存在
        existing = db.query(Playlist).filter(
            and_(Playlist.user_id == user_id, Playlist.name == request.name)
        ).first()
        
        if existing:
            raise HTTPException(status_code=409, detail="歌单名称已存在")
        
        # 创建歌单
        playlist = Playlist(
            user_id=user_id,
            name=request.name,
            description=request.description,
            category=request.category
        )
        
        db.add(playlist)
        db.commit()
        db.refresh(playlist)
        
        return {
            "data": PlaylistResponse(
                id=playlist.id,
                name=playlist.name,
                description=playlist.description,
                category=playlist.category,
                song_count=0,
                created_at=playlist.created_at,
                updated_at=playlist.updated_at
            ),
            "status": "success",
            "message": "歌单创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建歌单失败: {str(e)}")

@router.put("/{playlist_id}", response_model=dict)
async def update_playlist(
    playlist_id: int,
    request: PlaylistUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """更新歌单信息"""
    try:
        # 验证歌单所有权
        playlist = db.query(Playlist).filter(
            and_(Playlist.id == playlist_id, Playlist.user_id == user_id)
        ).first()
        
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单未找到")
        
        # 更新歌单信息
        if request.name is not None:
            # 检查名称是否与其他歌单冲突
            existing = db.query(Playlist).filter(
                and_(
                    Playlist.user_id == user_id,
                    Playlist.name == request.name,
                    Playlist.id != playlist_id
                )
            ).first()
            
            if existing:
                raise HTTPException(status_code=409, detail="歌单名称已存在")
            
            playlist.name = request.name
        
        if request.description is not None:
            playlist.description = request.description
        
        if request.category is not None:
            playlist.category = request.category
        
        playlist.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "data": {"message": "歌单更新成功"},
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新歌单失败: {str(e)}")

@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """删除歌单"""
    try:
        # 验证歌单所有权
        playlist = db.query(Playlist).filter(
            and_(Playlist.id == playlist_id, Playlist.user_id == user_id)
        ).first()
        
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单未找到")
        
        # 删除歌单中的歌曲关联
        db.query(PlaylistSong).filter(PlaylistSong.playlist_id == playlist_id).delete()
        
        # 处理与此歌单相关的下载任务
        from app.database.models import DownloadTask, MusicLibrary
        
        # 获取与此歌单相关的下载任务ID
        playlist_download_tasks = db.query(DownloadTask.id).filter(
            DownloadTask.playlist_id == playlist_id
        ).all()
        
        if playlist_download_tasks:
            task_ids = [task.id for task in playlist_download_tasks]
            
            # 将music_library中引用这些任务的download_task_id设置为NULL
            db.query(MusicLibrary).filter(
                MusicLibrary.download_task_id.in_(task_ids)
            ).update({MusicLibrary.download_task_id: None}, synchronize_session=False)
            
            # 删除下载任务
            db.query(DownloadTask).filter(DownloadTask.playlist_id == playlist_id).delete()
        
        # 删除歌单
        db.delete(playlist)
        db.commit()
        
        return {"message": "歌单删除成功", "status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除歌单失败: {str(e)}")

@router.post("/{playlist_id}/songs", response_model=dict)
async def add_songs_to_playlist(
    playlist_id: int,
    request: AddSongsRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """添加歌曲到歌单"""
    try:
        # 验证歌单所有权
        playlist = db.query(Playlist).filter(
            and_(Playlist.id == playlist_id, Playlist.user_id == user_id)
        ).first()
        
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单未找到")
        
        # 获取当前歌单的最大位置
        max_position = db.query(PlaylistSong.position).filter(
            PlaylistSong.playlist_id == playlist_id
        ).order_by(PlaylistSong.position.desc()).first()
        
        next_position = (max_position[0] if max_position else 0) + 1
        
        added_count = 0
        for song_id in request.song_ids:
            # 检查歌曲是否存在
            song = db.query(Song).filter(Song.id == song_id).first()
            if not song:
                continue
            
            # 检查歌曲是否已在歌单中
            existing = db.query(PlaylistSong).filter(
                and_(
                    PlaylistSong.playlist_id == playlist_id,
                    PlaylistSong.song_id == song_id
                )
            ).first()
            
            if existing:
                continue
            
            # 添加歌曲到歌单
            playlist_song = PlaylistSong(
                playlist_id=playlist_id,
                song_id=song_id,
                position=next_position
            )
            
            db.add(playlist_song)
            next_position += 1
            added_count += 1
        
        # 更新歌单的修改时间
        playlist.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "data": {"added_count": added_count},
            "status": "success",
            "message": f"成功添加 {added_count} 首歌曲到歌单"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加歌曲失败: {str(e)}")

@router.delete("/{playlist_id}/songs/{song_id}")
async def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """从歌单移除歌曲"""
    try:
        # 验证歌单所有权
        playlist = db.query(Playlist).filter(
            and_(Playlist.id == playlist_id, Playlist.user_id == user_id)
        ).first()
        
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单未找到")
        
        # 删除歌曲关联
        deleted = db.query(PlaylistSong).filter(
            and_(
                PlaylistSong.playlist_id == playlist_id,
                PlaylistSong.song_id == song_id
            )
        ).delete()
        
        if deleted == 0:
            raise HTTPException(status_code=404, detail="歌曲不在此歌单中")
        
        # 更新歌单的修改时间
        playlist.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "歌曲已从歌单移除", "status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"移除歌曲失败: {str(e)}")

@router.get("/categories/list")
async def get_playlist_categories(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取用户的歌单分类列表"""
    try:
        categories = db.query(Playlist.category).filter(
            and_(Playlist.user_id == user_id, Playlist.category.isnot(None))
        ).distinct().all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        
        return {
            "data": {"categories": category_list},
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")