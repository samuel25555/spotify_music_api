from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Song, Playlist, DownloadTask
from app.services import SpotifyService, DownloadService
from app.services.language_detector import language_detector
from app.api.schemas import (
    DownloadRequest, PlaylistDownloadRequest, DownloadTaskResponse,
    DownloadStatusResponse, ApiResponse, SearchRequest, YouTubeSearchResult
)
from typing import List, Optional
import asyncio
from datetime import datetime
import os

router = APIRouter(prefix="/api", tags=["download"])

# 初始化服务
spotify_service = SpotifyService()
download_service = DownloadService()

async def process_download_task_async(task_id: str):
    """异步后台处理下载任务 - 创建独立的数据库会话"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        print(f"🔄 开始处理下载任务: {task_id}")
        await process_download_task(task_id, db)
        print(f"✅ 下载任务完成: {task_id}")
    except Exception as e:
        print(f"❌ 下载任务失败: {task_id}, 错误: {e}")
        # 确保任务状态被更新为失败
        try:
            task = db.query(DownloadTask).filter(DownloadTask.task_id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                db.commit()
        except Exception as db_error:
            print(f"❌ 更新任务状态失败: {db_error}")
    finally:
        db.close()

async def process_download_task(task_id: str, db: Session):
    """后台处理下载任务"""
    task = db.query(DownloadTask).filter(DownloadTask.task_id == task_id).first()
    if not task:
        return
    
    try:
        # 更新任务状态为处理中
        task.status = "processing"
        task.progress = 10
        db.commit()
        
        # 解析Spotify URL
        spotify_id, item_type = spotify_service.extract_spotify_id(task.url)
        
        if item_type == "track":
            # 单首歌曲下载
            await process_single_song(task, spotify_id, db)
        elif item_type == "playlist":
            # 播放列表下载
            await process_playlist(task, spotify_id, db)
        elif item_type == "album":
            # 专辑下载
            await process_album(task, spotify_id, db)
        else:
            raise ValueError(f"Unsupported item type: {item_type}")
            
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()
        print(f"Download task failed: {e}")

async def process_single_song(task: DownloadTask, track_id: str, db: Session):
    """处理单首歌曲下载"""
    try:
        # 获取Spotify信息
        track_info = spotify_service.get_track_info(track_id)
        task.total_songs = 1
        task.progress = 30
        db.commit()
        
        # 检查歌曲是否已存在
        existing_song = db.query(Song).filter(Song.spotify_id == track_id).first()
        if existing_song and existing_song.is_downloaded:
            task.status = "completed"
            task.completed_songs = 1
            task.progress = 100
            task.download_paths = [existing_song.file_path]
            task.completed_at = datetime.utcnow()
            db.commit()
            return
        
        # 创建或更新歌曲记录
        if not existing_song:
            title = track_info["name"]
            artist = ', '.join([artist['name'] for artist in track_info["artists"]])
            album = track_info["album"]["name"] if "album" in track_info else None
            
            # 智能检测国家和语言
            country, language = language_detector.detect_country_and_language(title, artist, album)
            
            # 根据专辑风格推测情绪
            genres = track_info.get("album", {}).get("genres", [])
            genre_str = ', '.join(genres) if genres else None
            mood = language_detector.suggest_mood_from_genre(genre_str) if genre_str else None
            
            song = Song(
                title=title,
                artist=artist,
                album=album,
                duration=track_info["duration_ms"] / 1000,
                year=int(track_info["album"]["release_date"][:4]) if track_info.get("album", {}).get("release_date") else None,
                spotify_id=track_info["id"],
                spotify_url=track_info["external_urls"]["spotify"],
                preview_url=track_info.get("preview_url"),
                album_art_url=track_info["album"]["images"][0]["url"] if track_info.get("album", {}).get("images") else None,
                track_number=track_info.get("track_number"),
                download_status="downloading",
                # 智能标记的属性
                country=country,
                language=language,
                mood=mood,
                genre=genre_str
            )
            db.add(song)
            db.commit()
            db.refresh(song)
        else:
            song = existing_song
            song.download_status = "downloading"
            db.commit()
        
        task.progress = 50
        db.commit()
        
        # 准备下载服务需要的歌曲信息格式
        song_info_for_download = {
            "name": track_info["name"],
            "artist": ', '.join([artist['name'] for artist in track_info["artists"]]),
            "album": track_info["album"]["name"] if "album" in track_info else None,
            "duration_ms": track_info["duration_ms"],
            "year": int(track_info["album"]["release_date"][:4]) if track_info.get("album", {}).get("release_date") else None,
            "track_number": track_info.get("track_number"),
            "album_art": track_info["album"]["images"][0]["url"] if track_info.get("album", {}).get("images") else None
        }
        
        # 下载歌曲
        download_result = await download_service.download_song(
            song_info_for_download, task.format, task.quality
        )
        
        if download_result["success"]:
            # 更新歌曲信息
            song.file_path = download_result["file_path"]
            song.file_size = download_result["file_size"]
            song.file_format = task.format
            song.youtube_id = download_result.get("youtube_info", {}).get("id")
            song.youtube_url = download_result.get("youtube_info", {}).get("url")
            song.download_status = "completed"
            song.is_downloaded = True
            song.downloaded_at = datetime.utcnow()
            
            # 更新任务状态
            task.status = "completed"
            task.completed_songs = 1
            task.progress = 100
            task.download_paths = [download_result["file_path"]]
            task.completed_at = datetime.utcnow()
        else:
            # 下载失败
            song.download_status = "failed"
            task.status = "failed"
            task.failed_songs = 1
            task.error_message = download_result["error"]
            task.completed_at = datetime.utcnow()
        
        db.commit()
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()

async def process_playlist(task: DownloadTask, playlist_id: str, db: Session):
    """处理播放列表下载"""
    try:
        # 获取播放列表信息
        playlist_info = spotify_service.get_playlist_info(playlist_id)
        tracks = playlist_info["tracks"]["items"]
        task.total_songs = len(tracks)
        task.progress = 20
        db.commit()
        
        # 创建播放列表记录
        playlist = Playlist(
            name=playlist_info["name"],
            description=playlist_info.get("description", ""),
            owner=playlist_info["owner"]["display_name"],
            spotify_id=playlist_info["id"],
            spotify_url=playlist_info["external_urls"]["spotify"],
            total_tracks=playlist_info["tracks"]["total"],
            cover_art_url=playlist_info["images"][0]["url"] if playlist_info.get("images") else None,
            is_public=playlist_info.get("public", True),
            download_status="downloading"
        )
        db.add(playlist)
        db.commit()
        db.refresh(playlist)
        
        # 下载每首歌曲
        completed = 0
        failed = 0
        download_paths = []
        
        for i, item in enumerate(tracks):
            try:
                if not item.get("track") or item["track"]["type"] != "track":
                    continue
                    
                track = item["track"]
                
                # 准备下载服务需要的歌曲信息格式
                song_info_for_download = {
                    "name": track["name"],
                    "artist": ', '.join([artist['name'] for artist in track["artists"]]),
                    "album": track["album"]["name"] if "album" in track else None,
                    "duration_ms": track["duration_ms"],
                    "year": int(track["album"]["release_date"][:4]) if track.get("album", {}).get("release_date") else None,
                    "track_number": track.get("track_number"),
                    "album_art": track["album"]["images"][0]["url"] if track.get("album", {}).get("images") else None
                }
                
                # 下载歌曲
                download_result = await download_service.download_song(
                    song_info_for_download, task.format, task.quality
                )
                
                # 创建歌曲记录
                song = Song(
                    title=track["name"],
                    artist=', '.join([artist['name'] for artist in track["artists"]]),
                    album=track["album"]["name"] if "album" in track else None,
                    duration=track["duration_ms"] / 1000,
                    year=int(track["album"]["release_date"][:4]) if track.get("album", {}).get("release_date") else None,
                    spotify_id=track["id"],
                    spotify_url=track["external_urls"]["spotify"],
                    preview_url=track.get("preview_url"),  # 添加试听链接
                    album_art_url=track["album"]["images"][0]["url"] if track.get("album", {}).get("images") else None,
                    track_number=track.get("track_number")
                )
                
                if download_result["success"]:
                    song.file_path = download_result["file_path"]
                    song.file_size = download_result["file_size"]
                    song.file_format = task.format
                    song.youtube_id = download_result.get("youtube_info", {}).get("id")
                    song.youtube_url = download_result.get("youtube_info", {}).get("url")
                    song.download_status = "completed"
                    song.is_downloaded = True
                    song.downloaded_at = datetime.utcnow()
                    download_paths.append(download_result["file_path"])
                    completed += 1
                else:
                    song.download_status = "failed"
                    failed += 1
                
                db.add(song)
                playlist.songs.append(song)
                
                # 更新进度
                progress = 20 + (80 * (i + 1) / len(tracks))
                task.progress = int(progress)
                task.completed_songs = completed
                task.failed_songs = failed
                db.commit()
                
            except Exception as e:
                failed += 1
                task.failed_songs = failed
                db.commit()
        
        # 更新播放列表状态
        playlist.downloaded_tracks = completed
        playlist.download_status = "completed" if failed == 0 else "partial"
        
        # 更新任务状态
        task.status = "completed"
        task.progress = 100
        task.download_paths = download_paths
        task.completed_at = datetime.utcnow()
        
        db.commit()
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()

async def process_album(task: DownloadTask, album_id: str, db: Session):
    """处理专辑下载 - 类似播放列表处理"""
    try:
        album_info = spotify_service.get_album_info(album_id)
        # 将专辑作为播放列表处理
        playlist_info = {
            "name": album_info["name"],
            "description": f"Album by {album_info['artist']}",
            "owner": album_info["artist"],
            "id": album_info["id"],
            "spotify_url": album_info["spotify_url"],
            "total_tracks": album_info["total_tracks"],
            "cover_art": album_info["cover_art"],
            "public": True,
            "tracks": album_info["tracks"]
        }
        await process_playlist(task, album_id, db)
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()

@router.post("/download", response_model=DownloadTaskResponse)
async def download_song(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """下载单首歌曲或开始下载任务"""
    try:
        # 验证URL
        spotify_id, item_type = spotify_service.extract_spotify_id(request.url)
        
        # 获取歌曲信息以存储元数据
        task_metadata = {}
        if request.metadata:
            task_metadata = {
                "title": request.metadata.get("title", "未知歌曲"),
                "artist": request.metadata.get("artist", "未知艺术家"),
                "album": request.metadata.get("album", "未知专辑"),
                "album_art": request.metadata.get("album_art")
            }
        else:
            # 尝试从 Spotify 获取信息
            try:
                if item_type == "track":
                    print(f"🎵 获取 Spotify 歌曲信息: {spotify_id}")
                    track_info = spotify_service.get_track_info(spotify_id)
                    task_metadata = {
                        "title": track_info["name"],
                        "artist": ', '.join([artist['name'] for artist in track_info["artists"]]),
                        "album": track_info["album"]["name"] if "album" in track_info else None,
                        "album_art": track_info["album"]["images"][0]["url"] if track_info.get("album", {}).get("images") else None
                    }
                    print(f"✅ 获取歌曲信息成功: {task_metadata['title']} - {task_metadata['artist']}")
                elif item_type in ["playlist", "album"]:
                    # 对于播放列表和专辑，先获取基本信息
                    if item_type == "playlist":
                        playlist_info = spotify_service.get_playlist_info(spotify_id)
                        task_metadata = {
                            "title": f"播放列表: {playlist_info['name']}",
                            "artist": f"by {playlist_info['owner']['display_name']}",
                            "album": f"{playlist_info['tracks']['total']} 首歌曲",
                            "album_art": playlist_info["images"][0]["url"] if playlist_info.get("images") else None
                        }
                    else:  # album
                        album_info = spotify_service.get_album_info(spotify_id)
                        task_metadata = {
                            "title": f"专辑: {album_info['name']}",
                            "artist": ', '.join([artist['name'] for artist in album_info["artists"]]),
                            "album": f"{len(album_info['tracks']['items'])} 首歌曲",
                            "album_art": album_info["images"][0]["url"] if album_info.get("images") else None
                        }
            except Exception as e:
                print(f"❌ 获取 Spotify 信息失败: {e}")
                task_metadata = {
                    "title": "未知歌曲",
                    "artist": "未知艺术家",
                    "album": "未知专辑"
                }

        # 创建下载任务
        task = DownloadTask(
            task_type=item_type,
            url=request.url,
            format=request.format,
            quality=request.quality,
            callback_url=request.callback_url,
            status="pending",
            task_metadata=task_metadata
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # 添加后台任务 - 创建新的数据库会话
        background_tasks.add_task(process_download_task_async, task.task_id)
        
        return DownloadTaskResponse(**task.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download-playlist", response_model=DownloadTaskResponse)
async def download_playlist(
    request: PlaylistDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """下载播放列表"""
    return await download_song(
        DownloadRequest(**request.dict()),
        background_tasks,
        db
    )

@router.get("/status/{task_id}", response_model=DownloadStatusResponse)
async def get_download_status(task_id: str, db: Session = Depends(get_db)):
    """获取下载任务状态"""
    task = db.query(DownloadTask).filter(DownloadTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return DownloadStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        total_songs=task.total_songs,
        completed_songs=task.completed_songs,
        failed_songs=task.failed_songs,
        download_paths=task.download_paths,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at
    )

@router.post("/search-youtube", response_model=List[YouTubeSearchResult])
async def search_youtube(request: SearchRequest):
    """搜索YouTube视频"""
    try:
        results = download_service.search_youtube(request.query, request.limit)
        return [YouTubeSearchResult(**result) for result in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/get-stream-url")
async def get_stream_url(request: dict):
    """获取歌曲的直接播放链接"""
    try:
        query = request.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Missing query parameter")
        
        # 先搜索 YouTube
        search_results = download_service.search_youtube(query, limit=1)
        if not search_results:
            raise HTTPException(status_code=404, detail="No YouTube results found")
        
        # 获取第一个结果的播放链接
        youtube_url = search_results[0]['url']
        stream_result = download_service.get_stream_url(youtube_url)
        
        if stream_result['success']:
            return {
                "success": True,
                "stream_url": stream_result['stream_url'],
                "youtube_info": search_results[0],
                "title": stream_result['title'],
                "duration": stream_result['duration'],
                "thumbnail": stream_result['thumbnail']
            }
        else:
            raise HTTPException(status_code=500, detail=stream_result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tasks/clear", response_model=ApiResponse)
async def clear_download_tasks(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """清除下载任务记录"""
    try:
        query = db.query(DownloadTask)
        
        # 可选按状态过滤
        if status:
            query = query.filter(DownloadTask.status == status)
        
        # 获取要删除的任务数量
        count = query.count()
        
        # 删除任务
        query.delete()
        db.commit()
        
        return ApiResponse(
            success=True, 
            message=f"成功清除 {count} 条下载记录"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))