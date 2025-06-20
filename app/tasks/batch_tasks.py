"""
批量任务处理
包含批量导入收藏库、批量下载等功能
"""
from celery import current_task
from app.celery_app import app
from app.database.connection import get_db_session
from app.services.spotify_service import SpotifyService
from app.database.models import MusicLibrary, Song
from app.services.language_detector import language_detector
import time
import logging

logger = logging.getLogger(__name__)

@app.task(bind=True)
def batch_import_to_library(self, items_data, settings, search_type):
    """
    批量导入到收藏库的异步任务
    
    Args:
        items_data: 要导入的项目数据列表
        settings: 导入设置（分类、国家、语言等）
        search_type: 搜索类型（track, playlist, album）
    """
    try:
        spotify_service = SpotifyService()
        total = len(items_data)
        completed = 0
        failed = 0
        failed_items = []  # 记录失败的项目和原因
        
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'completed': completed, 'total': total, 'failed': failed}
        )
        
        with get_db_session() as db:
            for i, item_id in enumerate(items_data):
                try:
                    if search_type == 'track':
                        # 直接添加歌曲
                        add_track_to_library_sync(db, spotify_service, item_id, settings, user_id=1)
                        completed += 1
                        
                    elif search_type == 'playlist':
                        # 添加歌单中的所有歌曲
                        playlist_url = f"https://open.spotify.com/playlist/{item_id}"
                        tracks_added = add_playlist_to_library_sync(db, spotify_service, playlist_url, settings, user_id=1)
                        completed += tracks_added
                        
                    elif search_type == 'album':
                        # 添加专辑中的所有歌曲
                        album_url = f"https://open.spotify.com/album/{item_id}"
                        tracks_added = add_album_to_library_sync(db, spotify_service, album_url, settings, user_id=1)
                        completed += tracks_added
                        
                except Exception as e:
                    logger.error(f"处理项目 {item_id} 失败: {e}")
                    failed += 1
                    failed_items.append({
                        'item_id': item_id,
                        'error': str(e)
                    })
                
                # 更新进度（每处理5个或最后一个时更新）
                if (i + 1) % 5 == 0 or i == total - 1:
                    self.update_state(
                        state='PROGRESS',
                        meta={'completed': completed, 'total': total, 'failed': failed}
                    )
                
                # 避免请求过快
                time.sleep(0.2)
        
        return {
            'completed': completed,
            'failed': failed,
            'total': total,
            'status': 'completed',
            'failed_items': failed_items  # 返回失败的详细信息
        }
        
    except Exception as e:
        logger.error(f"批量导入任务失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e), 
                'completed': completed, 
                'failed': failed,
                'failed_items': failed_items if 'failed_items' in locals() else []
            }
        )
        raise

def add_track_to_library_sync(db, spotify_service, track_id, settings, user_id=1):
    """添加单个歌曲到收藏库"""
    # 检查歌曲是否存在
    song = db.query(Song).filter(Song.spotify_id == track_id).first()
    
    if not song:
        # 从Spotify获取歌曲信息
        track_info = spotify_service.get_track_info(track_id)
        if not track_info:
            raise Exception(f"未找到歌曲信息: {track_id}")
        
        # 创建歌曲记录
        artist_names = ', '.join([artist['name'] for artist in track_info['artists']])
        country, language = language_detector.detect_country_and_language(
            track_info['name'], artist_names, track_info.get('album', {}).get('name')
        )
        
        song = Song(
            spotify_id=track_id,
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
    
    # 检查是否已在收藏库中
    existing = db.query(MusicLibrary).filter(
        MusicLibrary.user_id == user_id,
        MusicLibrary.song_id == song.id
    ).first()
    
    if not existing:
        # 创建收藏库记录
        library_entry = MusicLibrary(
            user_id=user_id,
            song_id=song.id,
            category=settings.get('category'),
            tags=settings.get('tags'),
            notes=settings.get('notes'),
            custom_country=settings.get('custom_country'),
            custom_region=settings.get('custom_region'),
            custom_language=settings.get('custom_language')
        )
        db.add(library_entry)
    else:
        # 如果已存在，更新设置（如果提供了新设置）
        updated = False
        if settings.get('category') and existing.category != settings.get('category'):
            existing.category = settings.get('category')
            updated = True
        if settings.get('tags') and existing.tags != settings.get('tags'):
            existing.tags = settings.get('tags')
            updated = True
        if settings.get('notes') and existing.notes != settings.get('notes'):
            existing.notes = settings.get('notes')
            updated = True
        if settings.get('custom_country') and existing.custom_country != settings.get('custom_country'):
            existing.custom_country = settings.get('custom_country')
            updated = True
        if settings.get('custom_region') and existing.custom_region != settings.get('custom_region'):
            existing.custom_region = settings.get('custom_region')
            updated = True
        if settings.get('custom_language') and existing.custom_language != settings.get('custom_language'):
            existing.custom_language = settings.get('custom_language')
            updated = True
            
        if updated:
            logger.info(f"歌曲 {song.title} 的收藏设置已更新")
        else:
            logger.info(f"歌曲 {song.title} 已在收藏库中，跳过")
    
    db.commit()

def add_playlist_to_library_sync(db, spotify_service, playlist_url, settings, user_id=1):
    """添加歌单中的所有歌曲到收藏库"""
    try:
        # 解析歌单URL获取歌曲
        playlist_id = playlist_url.split('/')[-1]
        playlist_info = spotify_service.get_playlist_info(playlist_id)
        
        if not playlist_info:
            raise Exception("歌单信息获取失败")
        
        tracks_added = 0
        for item in playlist_info.get('tracks', {}).get('items', []):
            if item.get('track') and item['track'].get('type') == 'track':
                track = item['track']
                
                # 更新设置中的备注信息
                track_settings = settings.copy()
                if not track_settings.get('category'):
                    track_settings['category'] = 'Spotify歌单'
                if not track_settings.get('notes'):
                    track_settings['notes'] = f"来自歌单: {playlist_info['name']}"
                
                add_track_to_library_sync(db, spotify_service, track['id'], track_settings, user_id)
                tracks_added += 1
        
        return tracks_added
        
    except Exception as e:
        logger.error(f"添加歌单失败: {e}")
        raise

def add_album_to_library_sync(db, spotify_service, album_url, settings, user_id=1):
    """添加专辑中的所有歌曲到收藏库"""
    try:
        # 解析专辑URL获取歌曲
        album_id = album_url.split('/')[-1]
        album_info = spotify_service.get_album_info(album_id)
        
        if not album_info:
            raise Exception("专辑信息获取失败")
        
        tracks_added = 0
        for track in album_info.get('tracks', {}).get('items', []):
            # 更新设置中的备注信息
            track_settings = settings.copy()
            if not track_settings.get('category'):
                track_settings['category'] = 'Spotify专辑'
            if not track_settings.get('notes'):
                track_settings['notes'] = f"来自专辑: {album_info['name']}"
            
            add_track_to_library_sync(db, spotify_service, track['id'], track_settings, user_id)
            tracks_added += 1
        
        return tracks_added
        
    except Exception as e:
        logger.error(f"添加专辑失败: {e}")
        raise

@app.task(bind=True)
def add_single_track_to_library(self, track_id, settings, user_id=1):
    """
    添加单个歌曲到收藏库的异步任务
    
    Args:
        track_id: Spotify歌曲ID
        settings: 收藏库设置（分类、标签等）
        user_id: 用户ID
    """
    try:
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0, 'status': f'开始添加歌曲: {track_id}'}
        )
        
        spotify_service = SpotifyService()
        
        with get_db_session() as db:
            add_track_to_library_sync(db, spotify_service, track_id, settings, user_id)
            
        self.update_state(
            state='SUCCESS',
            meta={'progress': 100, 'status': '歌曲添加完成'}
        )
        
        return {
            'track_id': track_id,
            'status': 'completed',
            'message': '歌曲已添加到收藏库'
        }
        
    except Exception as e:
        logger.error(f"添加歌曲 {track_id} 失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@app.task(bind=True)
def add_single_playlist_to_library(self, playlist_id, settings, user_id=1):
    """
    添加单个歌单到收藏库的异步任务
    
    Args:
        playlist_id: Spotify歌单ID
        settings: 收藏库设置
        user_id: 用户ID
    """
    try:
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0, 'status': f'开始解析歌单: {playlist_id}'}
        )
        
        spotify_service = SpotifyService()
        
        with get_db_session() as db:
            playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
            tracks_added = add_playlist_to_library_sync(db, spotify_service, playlist_url, settings, user_id)
            
        self.update_state(
            state='SUCCESS',
            meta={'progress': 100, 'status': f'歌单导入完成，共添加 {tracks_added} 首歌曲'}
        )
        
        return {
            'playlist_id': playlist_id,
            'tracks_added': tracks_added,
            'status': 'completed',
            'message': f'歌单已添加到收藏库，共 {tracks_added} 首歌曲'
        }
        
    except Exception as e:
        logger.error(f"添加歌单 {playlist_id} 失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@app.task(bind=True)
def add_single_album_to_library(self, album_id, settings, user_id=1):
    """
    添加单个专辑到收藏库的异步任务
    
    Args:
        album_id: Spotify专辑ID
        settings: 收藏库设置
        user_id: 用户ID
    """
    try:
        self.update_state(
            state='PROGRESS',
            meta={'progress': 0, 'status': f'开始解析专辑: {album_id}'}
        )
        
        spotify_service = SpotifyService()
        
        with get_db_session() as db:
            album_url = f"https://open.spotify.com/album/{album_id}"
            tracks_added = add_album_to_library_sync(db, spotify_service, album_url, settings, user_id)
            
        self.update_state(
            state='SUCCESS',
            meta={'progress': 100, 'status': f'专辑导入完成，共添加 {tracks_added} 首歌曲'}
        )
        
        return {
            'album_id': album_id,
            'tracks_added': tracks_added,
            'status': 'completed',
            'message': f'专辑已添加到收藏库，共 {tracks_added} 首歌曲'
        }
        
    except Exception as e:
        logger.error(f"添加专辑 {album_id} 失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@app.task(bind=True)
def batch_add_multiple_playlists(self, playlist_ids, settings, user_id=1):
    """
    批量添加多个歌单到收藏库的异步任务
    
    Args:
        playlist_ids: Spotify歌单ID列表
        settings: 收藏库设置
        user_id: 用户ID
    """
    try:
        total = len(playlist_ids)
        completed = 0
        failed = 0
        total_tracks_added = 0
        failed_items = []
        
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 0,
                'status': f'开始批量导入 {total} 个歌单',
                'completed': 0,
                'total': total,
                'failed': 0,
                'tracks_added': 0
            }
        )
        
        spotify_service = SpotifyService()
        
        with get_db_session() as db:
            for i, playlist_id in enumerate(playlist_ids):
                try:
                    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
                    tracks_added = add_playlist_to_library_sync(db, spotify_service, playlist_url, settings, user_id)
                    total_tracks_added += tracks_added
                    completed += 1
                    
                    progress = int((i + 1) / total * 100)
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress,
                            'status': f'已完成 {completed}/{total} 个歌单，共添加 {total_tracks_added} 首歌曲',
                            'completed': completed,
                            'total': total,
                            'failed': failed,
                            'tracks_added': total_tracks_added
                        }
                    )
                    
                except Exception as e:
                    failed += 1
                    failed_items.append({
                        'playlist_id': playlist_id,
                        'error': str(e)
                    })
                    logger.error(f"添加歌单 {playlist_id} 失败: {e}")
                
                # 避免请求过快
                time.sleep(0.5)
        
        return {
            'completed': completed,
            'failed': failed,
            'total': total,
            'tracks_added': total_tracks_added,
            'status': 'completed',
            'failed_items': failed_items,
            'message': f'批量导入完成：成功 {completed} 个歌单，失败 {failed} 个，共添加 {total_tracks_added} 首歌曲'
        }
        
    except Exception as e:
        logger.error(f"批量导入歌单失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@app.task(bind=True)
def batch_add_multiple_albums(self, album_ids, settings, user_id=1):
    """
    批量添加多个专辑到收藏库的异步任务
    
    Args:
        album_ids: Spotify专辑ID列表
        settings: 收藏库设置
        user_id: 用户ID
    """
    try:
        total = len(album_ids)
        completed = 0
        failed = 0
        total_tracks_added = 0
        failed_items = []
        
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 0,
                'status': f'开始批量导入 {total} 个专辑',
                'completed': 0,
                'total': total,
                'failed': 0,
                'tracks_added': 0
            }
        )
        
        spotify_service = SpotifyService()
        
        with get_db_session() as db:
            for i, album_id in enumerate(album_ids):
                try:
                    album_url = f"https://open.spotify.com/album/{album_id}"
                    tracks_added = add_album_to_library_sync(db, spotify_service, album_url, settings, user_id)
                    total_tracks_added += tracks_added
                    completed += 1
                    
                    progress = int((i + 1) / total * 100)
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress,
                            'status': f'已完成 {completed}/{total} 个专辑，共添加 {total_tracks_added} 首歌曲',
                            'completed': completed,
                            'total': total,
                            'failed': failed,
                            'tracks_added': total_tracks_added
                        }
                    )
                    
                except Exception as e:
                    failed += 1
                    failed_items.append({
                        'album_id': album_id,
                        'error': str(e)
                    })
                    logger.error(f"添加专辑 {album_id} 失败: {e}")
                
                # 避免请求过快
                time.sleep(0.5)
        
        return {
            'completed': completed,
            'failed': failed,
            'total': total,
            'tracks_added': total_tracks_added,
            'status': 'completed',
            'failed_items': failed_items,
            'message': f'批量导入完成：成功 {completed} 个专辑，失败 {failed} 个，共添加 {total_tracks_added} 首歌曲'
        }
        
    except Exception as e:
        logger.error(f"批量导入专辑失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise