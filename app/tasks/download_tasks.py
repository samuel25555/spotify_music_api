"""
下载任务处理
包含单个歌曲下载、批量下载等功能
"""
from celery import current_task
from app.celery_app import app
import time
import logging
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database.connection import get_db

logger = logging.getLogger(__name__)

@app.task(bind=True)
def download_single_track(self, task_id):
    """
    下载单个歌曲的异步任务
    
    Args:
        task_id: 下载任务ID
    """
    try:
        # 获取数据库连接
        db = next(get_db())
        
        # 获取任务信息
        from app.database.models import DownloadTask, Song, MusicLibrary
        task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
        
        if not task:
            raise Exception(f"下载任务 {task_id} 不存在")
        
        # 更新任务状态
        task.status = "downloading" 
        task.progress = 10
        db.commit()
        
        self.update_state(
            state='PROGRESS',
            meta={'progress': 10, 'status': '开始下载', 'task_id': task_id}
        )
        
        # 使用真正的下载服务
        from app.services.download_service import DownloadService
        download_service = DownloadService()
        
        # 准备歌曲信息
        song_info = {
            'name': task.song.title,
            'artist': task.song.artist,
            'album': task.song.album,
            'album_art': task.song.album_art_url,
            'year': task.song.year,
            'spotify_id': task.song.spotify_id
        }
        
        # 更新进度
        task.progress = 20
        db.commit()
        
        self.update_state(
            state='PROGRESS',
            meta={'progress': 20, 'status': f'搜索: {song_info["artist"]} - {song_info["name"]}', 'task_id': task_id}
        )
        
        # 执行下载 (需要在新的事件循环中运行异步函数)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            download_service.download_song(song_info, format=task.format, quality=task.quality)
        )
        loop.close()
        
        if result['success']:
            # 下载成功
            actual_file_path = result.get('file_path')
            
            if actual_file_path:
                # 更新任务状态
                task.status = "completed"
                task.progress = 100
                task.file_path = actual_file_path
                db.commit()
                
                # 更新收藏库下载状态
                library_entry = db.query(MusicLibrary).filter(
                    and_(
                        MusicLibrary.user_id == task.user_id,
                        MusicLibrary.song_id == task.song_id
                    )
                ).first()
                
                if library_entry:
                    library_entry.is_downloaded = True
                    library_entry.download_task_id = task.id
                    db.commit()
                
                self.update_state(
                    state='SUCCESS',
                    meta={'progress': 100, 'status': '下载完成', 'task_id': task_id, 'file_path': actual_file_path}
                )
                
                return {
                    'task_id': task_id,
                    'file_path': actual_file_path,
                    'status': 'completed',
                    'message': '下载完成'
                }
            else:
                raise Exception("下载的文件不存在")
        else:
            # 下载失败
            raise Exception(result.get('error', '未知错误'))
            
    except Exception as e:
        logger.error(f"下载任务 {task_id} 失败: {e}")
        
        # 更新数据库中的失败状态
        try:
            db = next(get_db())
            from app.database.models import DownloadTask
            task = db.query(DownloadTask).filter(DownloadTask.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = str(e)
                db.commit()
        except:
            pass
        
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'task_id': task_id}
        )
        raise

@app.task(bind=True)
def download_batch_tracks(self, task_ids, batch_id=None):
    """
    批量下载歌曲的异步任务
    
    Args:
        task_ids: 下载任务ID列表
        batch_id: 批次ID（可选）
    """
    try:
        total_tracks = len(task_ids)
        completed = 0
        failed = 0
        
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 0, 
                'status': f'开始批量下载 {total_tracks} 首歌曲',
                'total': total_tracks,
                'completed': 0,
                'failed': 0
            }
        )
        
        # 逐个处理下载任务
        for i, task_id in enumerate(task_ids):
            try:
                # 调用单个下载任务
                result = download_single_track.apply(args=[task_id])
                
                if result.successful():
                    completed += 1
                else:
                    failed += 1
                    
                # 更新进度
                progress = int((i + 1) / total_tracks * 100)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': progress,
                        'status': f'已完成 {i+1}/{total_tracks} 首歌曲',
                        'total': total_tracks,
                        'completed': completed,
                        'failed': failed,
                        'current_task': i + 1
                    }
                )
                
            except Exception as e:
                failed += 1
                logger.error(f"批量下载任务 {task_id} 失败: {e}")
                continue
        
        return {
            'batch_id': batch_id,
            'total_tracks': total_tracks,
            'completed': completed,
            'failed': failed,
            'status': 'completed',
            'message': f'批量下载完成：成功 {completed} 首，失败 {failed} 首'
        }
        
    except Exception as e:
        logger.error(f"批量下载失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@app.task(bind=True)
def download_playlist_task(self, playlist_id, user_id, format='mp3', quality='high'):
    """
    下载整个歌单的异步任务
    
    Args:
        playlist_id: 歌单ID
        user_id: 用户ID
        format: 音频格式
        quality: 音频质量
    """
    try:
        # 获取数据库连接
        db = next(get_db())
        
        # 获取歌单信息
        from app.database.models import Playlist, PlaylistSong, Song, DownloadTask
        playlist = db.query(Playlist).filter(
            and_(Playlist.id == playlist_id, Playlist.user_id == user_id)
        ).first()
        
        if not playlist:
            raise Exception(f"歌单 {playlist_id} 不存在")
        
        # 获取歌单中的所有歌曲
        playlist_songs = db.query(PlaylistSong).join(Song).filter(
            PlaylistSong.playlist_id == playlist_id
        ).order_by(PlaylistSong.position).all()
        
        if not playlist_songs:
            raise Exception("歌单为空")
        
        total_tracks = len(playlist_songs)
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 0,
                'status': f'开始下载歌单 "{playlist.name}" ({total_tracks} 首)',
                'total': total_tracks,
                'completed': 0,
                'failed': 0
            }
        )
        
        # 为每首歌创建下载任务
        import uuid
        batch_id = str(uuid.uuid4())
        task_ids = []
        
        for ps in playlist_songs:
            # 检查是否已有进行中的下载任务
            existing_task = db.query(DownloadTask).filter(
                and_(
                    DownloadTask.user_id == user_id,
                    DownloadTask.song_id == ps.song_id,
                    DownloadTask.status.in_(["pending", "downloading"])
                )
            ).first()
            
            if not existing_task:
                download_task = DownloadTask(
                    user_id=user_id,
                    song_id=ps.song_id,
                    playlist_id=playlist_id,
                    url=ps.song.spotify_url,
                    format=format,
                    quality=quality,
                    task_type="playlist",
                    batch_id=batch_id
                )
                
                db.add(download_task)
                db.flush()
                task_ids.append(download_task.id)
        
        db.commit()
        
        if not task_ids:
            return {
                'playlist_id': playlist_id,
                'message': '歌单中的歌曲正在下载中或已下载完成',
                'total': 0,
                'completed': 0,
                'failed': 0
            }
        
        # 调用批量下载任务
        result = download_batch_tracks.apply(args=[task_ids, batch_id])
        
        return {
            'playlist_id': playlist_id,
            'playlist_name': playlist.name,
            'batch_id': batch_id,
            'total_tracks': len(task_ids),
            'status': 'completed',
            'message': f'歌单 "{playlist.name}" 下载任务已完成'
        }
        
    except Exception as e:
        logger.error(f"下载歌单 {playlist_id} 失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise