from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import Song, Playlist, DownloadTask
from app.api.schemas import SongResponse, PlaylistResponse, PaginatedResponse, ApiResponse
from typing import List, Optional
import math
import os
import mimetypes

router = APIRouter(prefix="/api", tags=["songs"])

@router.get("/songs", response_model=PaginatedResponse)
async def get_songs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取歌曲列表"""
    query = db.query(Song)
    
    # 筛选条件
    if status:
        query = query.filter(Song.download_status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Song.title.ilike(search_term)) |
            (Song.artist.ilike(search_term)) |
            (Song.album.ilike(search_term))
        )
    
    # 总数
    total = query.count()
    
    # 分页
    songs = query.order_by(desc(Song.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    return PaginatedResponse(
        items=[song.to_dict() for song in songs],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page)
    )

@router.get("/songs/{song_id}", response_model=SongResponse)
async def get_song(song_id: int, db: Session = Depends(get_db)):
    """获取单个歌曲信息"""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    return SongResponse(**song.to_dict())

@router.delete("/songs/{song_id}", response_model=ApiResponse)
async def delete_song(song_id: int, db: Session = Depends(get_db)):
    """删除歌曲"""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    # 删除文件
    if song.file_path and os.path.exists(song.file_path):
        try:
            os.remove(song.file_path)
        except:
            pass
    
    # 删除数据库记录
    db.delete(song)
    db.commit()
    
    return ApiResponse(success=True, message="Song deleted successfully")

@router.get("/playlists", response_model=PaginatedResponse)
async def get_playlists(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取播放列表"""
    query = db.query(Playlist)
    total = query.count()
    
    playlists = query.order_by(desc(Playlist.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    return PaginatedResponse(
        items=[playlist.to_dict() for playlist in playlists],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page)
    )

@router.get("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(playlist_id: int, db: Session = Depends(get_db)):
    """获取播放列表详情"""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    return PlaylistResponse(**playlist.to_dict())

@router.get("/tasks", response_model=PaginatedResponse)
async def get_download_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取下载任务列表"""
    query = db.query(DownloadTask)
    
    if status:
        query = query.filter(DownloadTask.status == status)
    
    total = query.count()
    tasks = query.order_by(desc(DownloadTask.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    return PaginatedResponse(
        items=[task.to_dict() for task in tasks],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page)
    )

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """获取统计信息"""
    total_songs = db.query(Song).count()
    downloaded_songs = db.query(Song).filter(Song.is_downloaded == True).count()
    total_playlists = db.query(Playlist).count()
    pending_tasks = db.query(DownloadTask).filter(DownloadTask.status == "pending").count()
    processing_tasks = db.query(DownloadTask).filter(DownloadTask.status == "processing").count()
    
    return {
        "total_songs": total_songs,
        "downloaded_songs": downloaded_songs,
        "total_playlists": total_playlists,
        "pending_tasks": pending_tasks,
        "processing_tasks": processing_tasks,
        "download_rate": round((downloaded_songs / total_songs * 100) if total_songs > 0 else 0, 2)
    }

@router.get("/stream/{song_id}")
async def stream_song(song_id: int, db: Session = Depends(get_db)):
    """流媒体播放歌曲"""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if not song.file_path or not os.path.exists(song.file_path):
        raise HTTPException(status_code=404, detail="Song file not found")
    
    # 获取文件的 MIME 类型
    mime_type, _ = mimetypes.guess_type(song.file_path)
    if not mime_type:
        mime_type = "audio/mpeg"  # 默认为 MP3
    
    # 获取文件大小
    file_size = os.path.getsize(song.file_path)
    
    # 返回文件流
    return FileResponse(
        song.file_path,
        media_type=mime_type,
        headers={
            "Content-Disposition": f"inline; filename={os.path.basename(song.file_path)}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size)
        }
    )

@router.get("/download/{song_id}")
async def download_song_file(song_id: int, db: Session = Depends(get_db)):
    """下载歌曲文件"""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if not song.file_path or not os.path.exists(song.file_path):
        raise HTTPException(status_code=404, detail="Song file not found")
    
    # 获取文件的 MIME 类型
    mime_type, _ = mimetypes.guess_type(song.file_path)
    if not mime_type:
        mime_type = "audio/mpeg"  # 默认为 MP3
    
    # 生成文件名
    filename = f"{song.artist} - {song.title}.{song.format or 'mp3'}"
    filename = filename.replace("/", "-").replace("\\", "-")  # 移除路径分隔符
    
    # 返回文件下载
    return FileResponse(
        song.file_path,
        media_type=mime_type,
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\""
        }
    )