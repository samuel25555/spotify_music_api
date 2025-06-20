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
    
    def get_playlist_tracks_complete(self, playlist_id: str) -> Dict:
        """获取播放列表的完整歌曲信息（支持分页获取所有歌曲）"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        # 获取播放列表基本信息
        playlist = self.sp.playlist(playlist_id, fields="id,name,description,external_urls,images,owner,public,followers,tracks.total")
        
        # 获取所有歌曲（通过分页）
        all_tracks = []
        offset = 0
        limit = 100  # Spotify API最大限制为100
        
        while True:
            # 获取当前页的歌曲
            tracks_response = self.sp.playlist_tracks(
                playlist_id, 
                offset=offset, 
                limit=limit,
                fields="items(track(id,name,artists,album,duration_ms,preview_url,external_urls)),next,total"
            )
            
            # 添加当前页的歌曲
            all_tracks.extend(tracks_response['items'])
            
            # 检查是否还有更多歌曲
            if not tracks_response.get('next'):
                break
                
            offset += limit
        
        # 更新播放列表信息，包含完整的歌曲列表
        playlist['tracks'] = {
            'items': all_tracks,
            'total': len(all_tracks)
        }
        
        return playlist
    
    def get_album_info(self, album_id: str) -> Dict:
        """获取专辑信息"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        return self.sp.album(album_id)
    
    def search_track(self, query: str, limit: int = 10, market: str = "US") -> List[Dict]:
        """搜索歌曲"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        # Spotify API最大限制为50
        actual_limit = min(limit, 50)
        results = self.sp.search(q=query, type="track", limit=actual_limit, market=market)
        return results["tracks"]["items"]
    
    def search_track_with_preview(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索歌曲并尝试获取preview_url"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        # 尝试少数几个最有可能有preview_url的市场
        markets_to_try = ["JP", "US", "GB"]
        all_tracks = []
        seen_ids = set()
        
        for market in markets_to_try:
            try:
                results = self.sp.search(q=query, type="track", limit=limit, market=market)
                tracks = results["tracks"]["items"]
                
                for track in tracks:
                    if track["id"] not in seen_ids:
                        # 如果这个市场的版本有preview_url，使用它
                        if track.get("preview_url"):
                            seen_ids.add(track["id"])
                            all_tracks.append(track)
                        elif track["id"] not in seen_ids:
                            # 即使没有preview_url，也保存第一次看到的版本
                            seen_ids.add(track["id"])
                            all_tracks.append(track)
                
                # 如果已经找到足够的带preview的歌曲，提前结束
                tracks_with_preview = [t for t in all_tracks if t.get("preview_url")]
                if len(tracks_with_preview) >= limit:
                    return tracks_with_preview[:limit]
                    
            except Exception as e:
                print(f"市场 {market} 搜索失败: {e}")
                continue
        
        # 返回找到的所有歌曲（优先返回有preview的）
        tracks_with_preview = [t for t in all_tracks if t.get("preview_url")]
        tracks_without_preview = [t for t in all_tracks if not t.get("preview_url")]
        
        return (tracks_with_preview + tracks_without_preview)[:limit]
    
    def search_multi_type(self, query: str, search_types: List[str] = None, limit: int = 10, market: str = "US") -> Dict:
        """多类型搜索：歌曲、专辑、艺人、歌单
        
        Args:
            query: 搜索查询
            search_types: 搜索类型列表 ["track", "album", "artist", "playlist"] 
            limit: 每个类型的结果数量限制
            market: 市场代码
            
        Returns:
            Dict包含各类型的搜索结果
        """
        if not self.sp:
            raise Exception("Spotify API not available")
        
        # 默认搜索所有类型
        if search_types is None:
            search_types = ["track", "album", "artist", "playlist"]
        
        # Spotify API支持的类型
        valid_types = ["track", "album", "artist", "playlist"]
        search_types = [t for t in search_types if t in valid_types]
        
        if not search_types:
            raise ValueError("No valid search types provided")
        
        # 构建搜索类型字符串
        type_string = ",".join(search_types)
        
        try:
            # 执行多类型搜索
            results = self.sp.search(q=query, type=type_string, limit=limit, market=market)
            
            # 格式化返回结果
            formatted_results = {}
            
            if "track" in search_types and "tracks" in results:
                formatted_results["tracks"] = results["tracks"]["items"]
            
            if "album" in search_types and "albums" in results:
                formatted_results["albums"] = results["albums"]["items"]
            
            if "artist" in search_types and "artists" in results:
                formatted_results["artists"] = results["artists"]["items"]
            
            if "playlist" in search_types and "playlists" in results:
                formatted_results["playlists"] = results["playlists"]["items"]
            
            return formatted_results
            
        except Exception as e:
            print(f"多类型搜索失败: {e}")
            raise
    
    def search_playlists_advanced(self, query: str, limit: int = 20, market: str = "US") -> List[Dict]:
        """高级歌单搜索，支持分类和主题
        
        Args:
            query: 搜索查询
            limit: 结果数量限制
            market: 市场代码
            
        Returns:
            歌单列表，按相关性排序
        """
        if not self.sp:
            raise Exception("Spotify API not available")
        
        # 构建歌单专用的搜索查询 - 参考spotify-downloader的查询构建策略
        playlist_queries = []
        
        # 智能查询构建
        if any(keyword in query.lower() for keyword in ['韩国', '韩语', 'korean', 'k-pop', 'kpop']):
            playlist_queries.extend([
                f"k-pop {query}",
                f"korean {query}",
                f"kpop {query}",
                f"best korean {query}",
                f"top k-pop {query}"
            ])
        elif any(keyword in query.lower() for keyword in ['日本', '日语', 'japanese', 'j-pop', 'jpop', 'anime']):
            playlist_queries.extend([
                f"j-pop {query}",
                f"japanese {query}",
                f"jpop {query}",
                f"anime {query}",
                f"best japanese {query}"
            ])
        elif any(keyword in query.lower() for keyword in ['中国', '中文', '华语', 'chinese', 'mandarin']):
            playlist_queries.extend([
                f"chinese {query}",
                f"mandarin {query}",
                f"c-pop {query}",
                f"taiwanese {query}",
                f"best chinese {query}"
            ])
        else:
            # 通用查询构建
            playlist_queries.extend([
                query,
                f"{query} playlist",
                f"{query} music",
                f"best {query}",
                f"top {query}",
                f"{query} hits",
                f"popular {query}"
            ])
        
        all_playlists = []
        seen_ids = set()
        
        for search_query in playlist_queries:
            try:
                results = self.sp.search(q=search_query, type="playlist", limit=20, market=market)
                playlists = results["playlists"]["items"]
                
                for playlist in playlists:
                    if playlist["id"] not in seen_ids:
                        seen_ids.add(playlist["id"])
                        # 过滤质量检查 - 参考spotify-downloader的过滤逻辑
                        if self._is_quality_playlist(playlist):
                            all_playlists.append(playlist)
                
                if len(all_playlists) >= limit:
                    break
                    
            except Exception as e:
                print(f"歌单搜索查询失败 '{search_query}': {e}")
                continue
        
        return all_playlists[:limit]
    
    def _is_quality_playlist(self, playlist: Dict) -> bool:
        """判断歌单质量 - 参考spotify-downloader的过滤机制"""
        # 基本检查
        if not playlist.get("public", True):
            return False
        
        # 必须有封面图片
        if not playlist.get("images") or len(playlist.get("images", [])) == 0:
            return False
        
        # 必须有足够的歌曲数量
        tracks_total = playlist.get("tracks", {}).get("total", 0)
        if tracks_total < 5:  # 至少5首歌
            return False
        
        # 检查歌单名称质量（避免垃圾歌单）
        name = playlist.get("name", "").lower()
        forbidden_words = ["test", "temp", "private", "untitled", "new playlist"]
        if any(word in name for word in forbidden_words):
            return False
        
        # 检查描述质量
        description = playlist.get("description", "").lower()
        if len(description) < 10 and tracks_total < 20:  # 歌曲少且描述简陋的可能是低质量歌单
            return False
        
        return True
    
    def get_featured_playlists_by_category(self, category: str, limit: int = 20, market: str = "US") -> List[Dict]:
        """根据分类获取特色歌单 - 参考spotify-downloader的分类系统"""
        if not self.sp:
            raise Exception("Spotify API not available")
        
        # 定义分类关键词映射 - 基于spotify-downloader的分类优化
        category_keywords = {
            "korean": ["k-pop", "korean pop", "kpop", "korea music", "korean hits", "korean indie"],
            "japanese": ["j-pop", "japanese pop", "jpop", "japan music", "anime music", "japanese indie", "city pop"],
            "chinese": ["chinese pop", "mandarin", "c-pop", "taiwan music", "hong kong music", "chinese indie"],
            "pop": ["pop hits", "top pop", "mainstream pop", "popular music", "chart toppers"],
            "rock": ["rock classics", "alternative rock", "indie rock", "metal", "hard rock"],
            "electronic": ["electronic music", "edm", "techno", "house music", "dance music", "dubstep"],
            "classical": ["classical music", "orchestra", "symphony", "piano classics", "chamber music"],
            "jazz": ["jazz classics", "smooth jazz", "blues", "contemporary jazz", "jazz fusion"],
            "country": ["country music", "country hits", "folk music", "americana", "bluegrass"],
            "hip-hop": ["hip hop", "rap music", "r&b", "urban music", "trap music"],
            "latin": ["latin music", "reggaeton", "salsa", "spanish music", "latin pop"],
            "indie": ["indie music", "alternative", "underground", "independent artists", "indie pop"],
            "mood-chill": ["chill music", "relaxing", "ambient", "study music", "focus music", "lofi"],
            "mood-party": ["party music", "dance hits", "energetic", "workout music", "upbeat"],
            "mood-sad": ["sad songs", "melancholy", "emotional music", "heartbreak", "indie folk"],
            "mood-happy": ["happy music", "uplifting", "positive vibes", "feel good", "sunny day"],
            "decades-2020s": ["2020s hits", "recent hits", "new music", "current"],
            "decades-2010s": ["2010s hits", "2010s pop", "decade 2010s"],
            "decades-2000s": ["2000s hits", "2000s pop", "y2k", "millennium"],
            "decades-90s": ["90s hits", "90s pop", "90s rock", "nineties"],
            "decades-80s": ["80s hits", "80s pop", "80s rock", "eighties", "retro"],
        }
        
        keywords = category_keywords.get(category.lower(), [category])
        all_playlists = []
        seen_ids = set()
        
        for keyword in keywords:
            try:
                # 搜索歌单
                results = self.sp.search(q=keyword, type="playlist", limit=15, market=market)
                playlists = results["playlists"]["items"]
                
                for playlist in playlists:
                    if (playlist["id"] not in seen_ids and self._is_quality_playlist(playlist)):
                        seen_ids.add(playlist["id"])
                        all_playlists.append(playlist)
                
                if len(all_playlists) >= limit:
                    break
                    
            except Exception as e:
                print(f"分类歌单搜索失败 '{keyword}': {e}")
                continue
        
        return all_playlists[:limit]