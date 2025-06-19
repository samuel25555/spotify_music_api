import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import os
import re
from typing import Dict, List, Optional

class SpotifyService:
    def __init__(self):
        # 优先使用环境变量中的凭据
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        
        # 如果没有环境变量，使用默认凭据（参考 spotify-downloader 项目）
        if not client_id or not client_secret:
            client_id = "5f573c9620494bae87890c0f08a60293"
            client_secret = "212476d9b0f3472eaa762d90b19b0ba8"
        
        try:
            # 使用客户端凭据认证
            auth_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            print("✅ Spotify 服务初始化完成")
        except Exception as e:
            print(f"❌ Spotify API初始化失败: {e}")
            self.sp = None
    
    def extract_spotify_id(self, url: str) -> tuple[str, str]:
        """从Spotify URL提取ID和类型"""
        patterns = {
            'track': r'track/([a-zA-Z0-9]{22})',
            'playlist': r'playlist/([a-zA-Z0-9]{22})',
            'album': r'album/([a-zA-Z0-9]{22})',
            'artist': r'artist/([a-zA-Z0-9]{22})'
        }
        
        for item_type, pattern in patterns.items():
            match = re.search(pattern, url)
            if match:
                return match.group(1), item_type
        
        raise ValueError("Invalid Spotify URL")
    
    def get_track_info(self, track_id: str) -> Dict:
        """获取歌曲信息"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        track = self.sp.track(track_id)
        
        return track
    
    def get_playlist_info(self, playlist_id: str) -> Dict:
        """获取播放列表信息"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        return self.sp.playlist(playlist_id)
    
    def get_album_info(self, album_id: str) -> Dict:
        """获取专辑信息"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        return self.sp.album(album_id)
    
    def search_track(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索歌曲"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        # Spotify API最大限制为50
        actual_limit = min(limit, 50)
        results = self.sp.search(q=query, type="track", limit=actual_limit)
        return results["tracks"]["items"]