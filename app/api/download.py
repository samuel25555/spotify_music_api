"""
下载管理 API
支持单曲下载、歌单批量下载、防重复下载等功能
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from pydantic import BaseModel
import uuid
import os
from datetime import datetime

from app.database.connection import get_db
from app.database.models import DownloadTask, Song, MusicLibrary, Playlist, PlaylistSong

router = APIRouter(prefix="/api", tags=["Download"])

def generate_file_hash(song, format_ext="mp3"):
    """生成基于歌曲信息的唯一文件名hash"""
    import hashlib
    hash_source = f"{song.spotify_id}_{song.title}_{song.artist}"
    file_hash = hashlib.md5(hash_source.encode('utf-8')).hexdigest()
    return f"{file_hash}.{format_ext}"

def get_file_path(song, format_ext="mp3"):
    """获取歌曲的完整文件路径"""
    downloads_dir = "downloads"
    file_name = generate_file_hash(song, format_ext)
    return os.path.join(downloads_dir, file_name)

def check_file_exists(song, format_ext="mp3"):
    """检查歌曲文件是否实际存在"""
    # 检查请求的格式
    file_path = get_file_path(song, format_ext)
    if os.path.exists(file_path):
        return True
    
    # 如果是mp3格式，也检查webm格式（因为实际下载的是webm）
    if format_ext == "mp3":
        webm_path = file_path.replace('.mp3', '.webm')
        if os.path.exists(webm_path):
            return True
    
    return False

# Pydantic 模型
class DownloadRequest(BaseModel):
    spotify_id: str
    format: str = "mp3"
    quality: str = "high"

class LibraryDownloadRequest(BaseModel):
    library_ids: List[int]  # 收藏库记录ID列表
    format: str = "mp3"
    quality: str = "high"

class PlaylistDownloadRequest(BaseModel):
    playlist_id: int
    format: str = "mp3" 
    quality: str = "high"
    
class DownloadResponse(BaseModel):
    task_id: int
    message: str
    batch_id: Optional[str] = None
    total_songs: int = 1
    
class TaskStatus(BaseModel):
    id: int
    song_title: str
    artist: str
    status: str
    progress: int
    file_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# 临时用户ID (实际应用中从认证中获取)
def get_current_user_id() -> int:
    return 1

# 删除这个函数，现在使用Celery任务代替

@router.post("/download", response_model=DownloadResponse)
async def create_download_task(
    request: DownloadRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """创建单曲下载任务"""
    try:
        # 检查歌曲是否存在
        song = db.query(Song).filter(Song.spotify_id == request.spotify_id).first()
        
        if not song:
            # 从Spotify获取歌曲信息
            from app.api.spotify import spotify_service
            track_info = spotify_service.get_track_info(request.spotify_id)
            
            if not track_info:
                raise HTTPException(status_code=404, detail="歌曲信息未找到")
            
            # 创建歌曲记录
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
            db.flush()
        
        # 检查是否已有进行中或完成的下载任务
        existing_task = db.query(DownloadTask).filter(
            and_(
                DownloadTask.user_id == user_id,
                DownloadTask.song_id == song.id,
                DownloadTask.status.in_(["pending", "downloading", "completed"])
            )
        ).first()
        
        if existing_task:
            if existing_task.status == "completed":
                raise HTTPException(status_code=409, detail="该歌曲已下载完成")
            else:
                raise HTTPException(status_code=409, detail="该歌曲正在下载中")
        
        # 创建下载任务
        download_task = DownloadTask(
            user_id=user_id,
            song_id=song.id,
            url=song.spotify_url,
            format=request.format,
            quality=request.quality,
            task_type="single"
        )
        
        db.add(download_task)
        db.commit()
        
        # 使用Celery异步任务
        from app.tasks.download_tasks import download_single_track
        celery_task = download_single_track.delay(download_task.id)
        
        return DownloadResponse(
            task_id=download_task.id,
            message="下载任务已创建",
            total_songs=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建下载任务失败: {str(e)}")

@router.post("/download/library", response_model=DownloadResponse)
async def download_from_library(
    request: LibraryDownloadRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """从收藏库批量下载"""
    try:
        # 验证收藏库记录
        library_entries = db.query(MusicLibrary).filter(
            and_(
                MusicLibrary.user_id == user_id,
                MusicLibrary.id.in_(request.library_ids)
            )
        ).all()
        
        if len(library_entries) != len(request.library_ids):
            raise HTTPException(status_code=400, detail="部分歌曲不在您的收藏库中")
        
        # 过滤已下载的歌曲
        to_download = [entry for entry in library_entries if not entry.is_downloaded]
        
        if not to_download:
            raise HTTPException(status_code=409, detail="所选歌曲均已下载")
        
        # 生成批次ID
        batch_id = str(uuid.uuid4())
        tasks_created = []
        
        # 为每首歌创建下载任务
        for entry in to_download:
            # 检查是否已有进行中的任务
            existing_task = db.query(DownloadTask).filter(
                and_(
                    DownloadTask.user_id == user_id,
                    DownloadTask.song_id == entry.song_id,
                    DownloadTask.status.in_(["pending", "downloading"])
                )
            ).first()
            
            if existing_task:
                continue  # 跳过已有任务的歌曲
            
            download_task = DownloadTask(
                user_id=user_id,
                song_id=entry.song_id,
                url=entry.song.spotify_url,
                format=request.format,
                quality=request.quality,
                task_type="library_batch",
                batch_id=batch_id
            )
            
            db.add(download_task)
            tasks_created.append(download_task)
        
        db.commit()
        
        # 使用Celery批量下载任务
        if tasks_created:
            task_ids = [task.id for task in tasks_created]
            from app.tasks.download_tasks import download_batch_tracks
            celery_task = download_batch_tracks.delay(task_ids, batch_id)
        
        return DownloadResponse(
            task_id=tasks_created[0].id if tasks_created else 0,
            message=f"已创建 {len(tasks_created)} 个下载任务",
            batch_id=batch_id,
            total_songs=len(tasks_created)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量下载失败: {str(e)}")

@router.post("/download/playlist", response_model=DownloadResponse)
async def download_playlist(
    request: PlaylistDownloadRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """下载整个歌单"""
    try:
        # 验证歌单所有权
        playlist = db.query(Playlist).filter(
            and_(Playlist.id == request.playlist_id, Playlist.user_id == user_id)
        ).first()
        
        if not playlist:
            raise HTTPException(status_code=404, detail="歌单未找到")
        
        # 获取歌单中的所有歌曲
        playlist_songs = db.query(PlaylistSong).join(Song).filter(
            PlaylistSong.playlist_id == request.playlist_id
        ).order_by(PlaylistSong.position).all()
        
        if not playlist_songs:
            raise HTTPException(status_code=400, detail="歌单为空")
        
        # 过滤有正在进行下载任务的歌曲
        to_download = []
        for ps in playlist_songs:
            # 检查是否有正在进行的下载任务
            existing_task = db.query(DownloadTask).filter(
                and_(
                    DownloadTask.user_id == user_id,
                    DownloadTask.song_id == ps.song_id,
                    DownloadTask.status.in_(["pending", "downloading"])
                )
            ).first()
            
            if not existing_task:
                to_download.append(ps)
        
        if not to_download:
            raise HTTPException(status_code=409, detail="歌单中的歌曲正在下载中，请稍后再试")
        
        # 生成批次ID
        batch_id = str(uuid.uuid4())
        tasks_created = []
        
        # 为每首歌创建下载任务
        for ps in to_download:
            # 检查是否已有进行中的任务
            existing_task = db.query(DownloadTask).filter(
                and_(
                    DownloadTask.user_id == user_id,
                    DownloadTask.song_id == ps.song_id,
                    DownloadTask.status.in_(["pending", "downloading"])
                )
            ).first()
            
            if existing_task:
                continue
            
            download_task = DownloadTask(
                user_id=user_id,
                song_id=ps.song_id,
                playlist_id=request.playlist_id,
                url=ps.song.spotify_url,
                format=request.format,
                quality=request.quality,
                task_type="playlist",
                batch_id=batch_id
            )
            
            db.add(download_task)
            tasks_created.append(download_task)
        
        db.commit()
        
        # 使用Celery歌单下载任务
        from app.tasks.download_tasks import download_playlist_task
        celery_task = download_playlist_task.delay(
            request.playlist_id, 
            user_id, 
            request.format, 
            request.quality
        )
        
        return DownloadResponse(
            task_id=tasks_created[0].id if tasks_created else 0,
            message=f"歌单下载已启动，共 {len(tasks_created)} 首歌曲",
            batch_id=batch_id,
            total_songs=len(tasks_created)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"歌单下载失败: {str(e)}")

@router.get("/tasks")
async def get_download_tasks(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取下载任务列表"""
    try:
        query = db.query(DownloadTask).join(Song).filter(DownloadTask.user_id == user_id)
        
        if status:
            query = query.filter(DownloadTask.status == status)
        
        if batch_id:
            query = query.filter(DownloadTask.batch_id == batch_id)
        
        # 按创建时间倒序
        query = query.order_by(DownloadTask.created_at.desc())
        
        total = query.count()
        offset = (page - 1) * per_page
        tasks = query.offset(offset).limit(per_page).all()
        
        task_list = []
        for task in tasks:
            task_list.append(TaskStatus(
                id=task.id,
                song_title=task.song.title,
                artist=task.song.artist,
                status=task.status,
                progress=task.progress,
                file_path=task.file_path,
                error_message=task.error_message,
                created_at=task.created_at
            ))
        
        return {
            "tasks": task_list,
            "total": total,
            "page": page,
            "per_page": per_page
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@router.delete("/tasks/clear-all")
async def clear_download_tasks(
    status: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """清除下载任务记录"""
    try:
        # 首先清除music_library中的download_task_id引用
        if status:
            # 获取要删除的任务ID
            task_ids = db.query(DownloadTask.id).filter(
                and_(DownloadTask.user_id == user_id, DownloadTask.status == status)
            ).all()
            task_ids = [t[0] for t in task_ids]
            
            if task_ids:
                # 清除引用
                db.query(MusicLibrary).filter(
                    MusicLibrary.download_task_id.in_(task_ids)
                ).update({MusicLibrary.download_task_id: None}, synchronize_session=False)
                
                # 删除特定状态的任务
                deleted_count = db.query(DownloadTask).filter(
                    and_(DownloadTask.user_id == user_id, DownloadTask.status == status)
                ).delete()
        else:
            # 获取所有任务ID
            task_ids = db.query(DownloadTask.id).filter(DownloadTask.user_id == user_id).all()
            task_ids = [t[0] for t in task_ids]
            
            if task_ids:
                # 清除所有引用
                db.query(MusicLibrary).filter(
                    MusicLibrary.download_task_id.in_(task_ids)
                ).update({MusicLibrary.download_task_id: None}, synchronize_session=False)
                
                # 删除所有任务
                deleted_count = db.query(DownloadTask).filter(DownloadTask.user_id == user_id).delete()
            else:
                deleted_count = 0
        
        db.commit()
        
        return {
            "message": f"已清除 {deleted_count} 条下载记录",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"清除记录失败: {str(e)}")

@router.delete("/tasks/{task_id}")
async def cancel_download_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """取消下载任务"""
    try:
        task = db.query(DownloadTask).filter(
            and_(DownloadTask.id == task_id, DownloadTask.user_id == user_id)
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务未找到")
        
        if task.status == "completed":
            raise HTTPException(status_code=400, detail="已完成的任务无法取消")
        
        if task.status in ["pending", "downloading"]:
            task.status = "cancelled"
            db.commit()
            return {"message": "任务已取消"}
        else:
            raise HTTPException(status_code=400, detail="任务状态不允许取消")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@router.get("/download/stats")
async def get_download_stats(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取下载统计信息"""
    try:
        total_tasks = db.query(DownloadTask).filter(DownloadTask.user_id == user_id).count()
        completed_tasks = db.query(DownloadTask).filter(
            and_(DownloadTask.user_id == user_id, DownloadTask.status == "completed")
        ).count()
        failed_tasks = db.query(DownloadTask).filter(
            and_(DownloadTask.user_id == user_id, DownloadTask.status == "failed")
        ).count()
        pending_tasks = db.query(DownloadTask).filter(
            and_(DownloadTask.user_id == user_id, DownloadTask.status.in_(["pending", "downloading"]))
        ).count()
        
        return {
            "total_tasks": total_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks,
            "pending": pending_tasks,
            "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")