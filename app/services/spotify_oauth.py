"""
基于OAuth用户认证的Spotify服务，用于获取preview_url
参考spotify-downloader项目的实现
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import os
from typing import Dict, List, Optional

class SpotifyOAuthService:
    """
    使用OAuth用户认证的Spotify服务
    可以获取更完整的track信息，包括preview_url
    """
    
    def __init__(self, use_oauth: bool = False):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID", "5f573c9620494bae87890c0f08a60293")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "212476d9b0f3472eaa762d90b19b0ba8")
        self.use_oauth = use_oauth
        self.sp = None
        
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化Spotify客户端"""
        try:
            if self.use_oauth:
                # 使用OAuth用户认证 - 可以获取preview_url
                auth_manager = SpotifyOAuth(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    redirect_uri="http://127.0.0.1:9900/",
                    scope="user-library-read,user-follow-read,playlist-read-private",
                    open_browser=False,  # 在服务器环境中不打开浏览器
                )
                self.sp = spotipy.Spotify(auth_manager=auth_manager)
                print("✅ Spotify OAuth 服务初始化完成")
            else:
                # 使用客户端认证 - 无法获取preview_url
                auth_manager = SpotifyClientCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                self.sp = spotipy.Spotify(auth_manager=auth_manager)
                print("✅ Spotify Client Credentials 服务初始化完成")
                
        except Exception as e:
            print(f"❌ Spotify API初始化失败: {e}")
            self.sp = None
    
    def search_with_preview(self, query: str, limit: int = 10, market: str = "US") -> List[Dict]:
        """
        搜索歌曲并尝试获取preview_url
        使用OAuth认证时，更容易获取preview_url
        """
        if not self.sp:
            raise Exception("Spotify API not available")
        
        try:
            results = self.sp.search(q=query, type="track", limit=limit, market=market)
            tracks = results["tracks"]["items"]
            
            # 统计有preview_url的歌曲
            tracks_with_preview = [t for t in tracks if t.get('preview_url')]
            print(f"搜索 '{query}': 找到 {len(tracks)} 首歌曲, {len(tracks_with_preview)} 首有预览")
            
            return tracks
            
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def get_track_with_preview(self, track_id: str, market: str = "US") -> Optional[Dict]:
        """
        获取歌曲信息，包括preview_url
        """
        if not self.sp:
            raise Exception("Spotify API not available")
        
        try:
            track = self.sp.track(track_id, market=market)
            return track
        except Exception as e:
            print(f"获取歌曲失败: {e}")
            return None
    
    def test_preview_capability(self) -> Dict[str, any]:
        """
        测试当前认证方式是否能获取preview_url
        """
        if not self.sp:
            return {"error": "Spotify API not available"}
        
        # 测试一个已知的歌曲ID
        test_track_id = "4iV5W9uYEdYUVa79Axb7Rh"  # "Shape of You" by Ed Sheeran
        
        try:
            track = self.sp.track(test_track_id, market="US")
            has_preview = track.get('preview_url') is not None
            
            return {
                "auth_type": "OAuth" if self.use_oauth else "Client Credentials",
                "test_track": track.get('name', 'Unknown'),
                "test_artist": track.get('artists', [{}])[0].get('name', 'Unknown'),
                "has_preview": has_preview,
                "preview_url": track.get('preview_url'),
                "available_markets": len(track.get('available_markets', [])),
                "track_id": test_track_id
            }
        except Exception as e:
            return {"error": str(e)}

# 创建两个实例用于比较
spotify_oauth = SpotifyOAuthService(use_oauth=True)  # OAuth认证
spotify_client = SpotifyOAuthService(use_oauth=False)  # 客户端认证