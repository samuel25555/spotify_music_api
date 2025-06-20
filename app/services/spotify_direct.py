import requests
import base64
import os
from typing import Dict, List, Optional

class SpotifyDirectAPI:
    """直接使用HTTP请求访问Spotify API，用于获取preview_url"""
    
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID", "5f573c9620494bae87890c0f08a60293")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "212476d9b0f3472eaa762d90b19b0ba8")
        self.access_token = None
        self.token_type = None
        
    def get_access_token(self):
        """获取访问令牌"""
        auth_url = "https://accounts.spotify.com/api/token"
        
        # 创建认证头
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(auth_url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_type = token_data['token_type']
            return True
        except Exception as e:
            print(f"获取访问令牌失败: {e}")
            return False
    
    def search_tracks_direct(self, query: str, market: str = "JP", limit: int = 10) -> List[Dict]:
        """直接搜索歌曲"""
        if not self.access_token:
            if not self.get_access_token():
                return []
        
        search_url = "https://api.spotify.com/v1/search"
        headers = {
            'Authorization': f'{self.token_type} {self.access_token}'
        }
        
        params = {
            'q': query,
            'type': 'track',
            'market': market,
            'limit': limit
        }
        
        try:
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('tracks', {}).get('items', [])
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def get_track_by_id(self, track_id: str, market: str = "JP") -> Optional[Dict]:
        """通过ID获取歌曲信息"""
        if not self.access_token:
            if not self.get_access_token():
                return None
        
        track_url = f"https://api.spotify.com/v1/tracks/{track_id}"
        headers = {
            'Authorization': f'{self.token_type} {self.access_token}'
        }
        
        params = {
            'market': market
        }
        
        try:
            response = requests.get(track_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取歌曲信息失败: {e}")
            return None