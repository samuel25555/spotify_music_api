from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from app.services.spotify_service import SpotifyService
import re

def detect_country_from_track(track_info):
    """从歌曲信息智能识别国家"""
    artist_names = ', '.join([artist['name'] for artist in track_info.get('artists', [])])
    title = track_info.get('name', '')
    
    # 中文字符检测
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', f"{title} {artist_names}")
    if len(chinese_chars) > 2:
        return 'china'
    
    # 韩文字符检测
    korean_chars = re.findall(r'[\uac00-\ud7af]', f"{title} {artist_names}")
    if len(korean_chars) > 2:
        return 'korea'
    
    # 日文字符检测（平假名、片假名）
    japanese_chars = re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', f"{title} {artist_names}")
    if len(japanese_chars) > 2:
        return 'japan'
    
    # 通过艺术家名称识别
    if any(keyword in artist_names.lower() for keyword in ['(us)', '(usa)', '(america)']):
        return 'usa'
    elif any(keyword in artist_names.lower() for keyword in ['(uk)', '(british)', '(britain)']):
        return 'uk'
    
    return None

def detect_language_from_track(track_info):
    """从歌曲信息智能识别语言"""
    artist_names = ', '.join([artist['name'] for artist in track_info.get('artists', [])])
    title = track_info.get('name', '')
    
    # 中文检测
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', f"{title} {artist_names}")
    if len(chinese_chars) > 2:
        return 'chinese'
    
    # 韩文检测
    korean_chars = re.findall(r'[\uac00-\ud7af]', f"{title} {artist_names}")
    if len(korean_chars) > 2:
        return 'korean'
    
    # 日文检测
    japanese_chars = re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', f"{title} {artist_names}")
    if len(japanese_chars) > 2:
        return 'japanese'
    
    # 默认英语
    return 'english'

router = APIRouter(prefix="/api/spotify", tags=["Spotify"])

spotify_service = SpotifyService()

class SpotifyParseRequest(BaseModel):
    url: HttpUrl

class SpotifyTrack(BaseModel):
    id: str
    title: str
    artist: str
    album: Optional[str] = None
    album_art: Optional[str] = None
    duration: Optional[int] = None
    preview_url: Optional[str] = None
    spotify_url: str
    year: Optional[int] = None
    country: Optional[str] = None
    language: Optional[str] = None
    database_id: Optional[int] = None  # 数据库中的song.id

class SpotifySearchResponse(BaseModel):
    tracks: List[SpotifyTrack]
    total: int

@router.get("/search", response_model=SpotifySearchResponse)
async def search_spotify(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=500, description="返回数量，最多500首"),
    country_filter: Optional[str] = Query(None, description="国家筛选：china, korea, japan, usa 等"),
    language_filter: Optional[str] = Query(None, description="语言筛选：chinese, korean, japanese, english 等"),
    deduplicate: bool = Query(True, description="去除重复歌曲"),
    preview_only: bool = Query(False, description="只返回有预览的歌曲")
):
    """搜索 Spotify 歌曲（支持智能筛选和去重）"""
    try:
        # 智能查询优化：如果搜索中文相关词汇，优化搜索策略
        enhanced_queries = []
        if any(word in q.lower() for word in ['华语', '中文', '中国', '台湾', '香港']):
            enhanced_queries = [
                f"{q} chinese",
                f"{q} mandarin", 
                f"{q} taiwan",
                f"{q} hong kong",
                q  # 原始查询
            ]
        elif any(word in q.lower() for word in ['韩语', '韩国', 'korean', 'korea']):
            enhanced_queries = [
                f"{q} korean",
                f"{q} kpop",
                f"{q} korea",
                q
            ]
        elif any(word in q.lower() for word in ['日语', '日本', 'japanese', 'japan']):
            enhanced_queries = [
                f"{q} japanese",
                f"{q} jpop", 
                f"{q} japan",
                q
            ]
        else:
            enhanced_queries = [q]
        
        all_tracks = []
        unique_tracks = set()
        
        # 对每个增强查询执行搜索
        for query in enhanced_queries:
            remaining = limit - len(all_tracks)
            if remaining <= 0:
                break
                
            offset = 0
            query_tracks = []
            
            while remaining > 0 and offset < 1000:  # Spotify API最大offset限制
                batch_size = min(remaining, 50)
                
                # 简化搜索策略避免rate limit
                try:
                    results = spotify_service.sp.search(q=query, type="track", limit=batch_size, offset=offset)
                    batch_tracks = results["tracks"]["items"]
                except Exception as e:
                    print(f"搜索失败: {e}")
                    batch_tracks = []
                
                if not batch_tracks:  # 没有更多结果
                    break
                    
                query_tracks.extend(batch_tracks)
                remaining -= len(batch_tracks)
                offset += batch_size
            
            # 去重和筛选
            for track_info in query_tracks:
                track_id = track_info['id']
                
                # 去重检查
                if deduplicate and track_id in unique_tracks:
                    continue
                    
                # 获取发行年份
                release_year = None
                if track_info.get('album', {}).get('release_date'):
                    try:
                        release_year = int(track_info['album']['release_date'][:4])
                    except (ValueError, TypeError):
                        pass
                
                # 创建track对象进行筛选
                artist_names = ', '.join([artist['name'] for artist in track_info['artists']])
                title = track_info['name']
                album = track_info['album']['name'] if 'album' in track_info else None
                
                # 使用智能识别函数检测国家和语言信息
                detected_country = detect_country_from_track(track_info)
                detected_language = detect_language_from_track(track_info)
                
                # 应用国家和语言筛选（宽松模式：没有检测到的不过滤）
                if country_filter and detected_country:
                    country_match = False
                    filter_countries = [c.strip().lower() for c in country_filter.split(',')]
                    for filter_country in filter_countries:
                        if filter_country == detected_country.lower():
                            country_match = True
                            break
                        elif filter_country in ['china', 'chinese'] and detected_country == 'china':
                            country_match = True
                            break
                        elif filter_country in ['korea', 'korean'] and detected_country == 'korea':
                            country_match = True
                            break
                        elif filter_country in ['japan', 'japanese'] and detected_country == 'japan':
                            country_match = True
                            break
                        elif filter_country in ['usa', 'america', 'english'] and detected_country in ['usa', 'uk']:
                            country_match = True
                            break
                    if not country_match:
                        continue
                
                # 语言筛选（宽松模式：没有检测到的不过滤）  
                if language_filter and detected_language:
                    language_match = False
                    filter_languages = [l.strip().lower() for l in language_filter.split(',')]
                    for filter_language in filter_languages:
                        if filter_language == detected_language.lower():
                            language_match = True
                            break
                        elif filter_language in ['chinese', '中文'] and detected_language == 'chinese':
                            language_match = True
                            break
                        elif filter_language in ['korean', '韩语'] and detected_language == 'korean':
                            language_match = True
                            break
                        elif filter_language in ['japanese', '日语'] and detected_language == 'japanese':
                            language_match = True
                            break
                        elif filter_language in ['english', '英语'] and detected_language == 'english':
                            language_match = True
                            break
                    if not language_match:
                        continue
                
                # 预览筛选
                if preview_only and not track_info.get('preview_url'):
                    continue
                
                if deduplicate:
                    unique_tracks.add(track_id)
                
                track = SpotifyTrack(
                    id=track_id,
                    title=title,
                    artist=artist_names,
                    album=album,
                    album_art=track_info['album']['images'][0]['url'] if track_info.get('album', {}).get('images') else None,
                    duration=track_info.get('duration_ms', 0) // 1000,
                    preview_url=track_info.get('preview_url'),
                    spotify_url=track_info['external_urls']['spotify'],
                    year=release_year,
                    country=detected_country,
                    language=detected_language
                )
                all_tracks.append(track)
                
                if len(all_tracks) >= limit:
                    break
            
            if len(all_tracks) >= limit:
                break
        
        return SpotifySearchResponse(
            tracks=all_tracks[:limit],
            total=len(all_tracks[:limit])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.post("/parse")
async def parse_spotify_url(request: SpotifyParseRequest):
    """解析 Spotify URL 获取歌曲信息"""
    try:
        url = str(request.url)
        
        # 检查 URL 类型
        if 'track/' in url:
            # 单曲
            track_id_match = re.search(r'track/([a-zA-Z0-9]+)', url)
            if not track_id_match:
                raise HTTPException(status_code=400, detail="无效的 Spotify track URL")
            
            track_id = track_id_match.group(1)
            track_info = spotify_service.get_track_info(track_id)
            
            if not track_info:
                raise HTTPException(status_code=404, detail="未找到歌曲信息")
            
            return {
                "type": "track",
                "data": SpotifyTrack(
                    id=track_info['id'],
                    title=track_info['name'],
                    artist=', '.join([artist['name'] for artist in track_info['artists']]),
                    album=track_info['album']['name'] if 'album' in track_info else None,
                    album_art=track_info['album']['images'][0]['url'] if track_info.get('album', {}).get('images') else None,
                    duration=track_info.get('duration_ms', 0) // 1000,
                    preview_url=track_info.get('preview_url'),
                    spotify_url=track_info['external_urls']['spotify']
                )
            }
            
        elif 'playlist/' in url:
            # 播放列表
            playlist_id_match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
            if not playlist_id_match:
                raise HTTPException(status_code=400, detail="无效的 Spotify playlist URL")
            
            playlist_id = playlist_id_match.group(1)
            playlist_info = spotify_service.get_playlist_tracks_complete(playlist_id)
            
            if not playlist_info:
                raise HTTPException(status_code=404, detail="未找到播放列表信息")
            
            # 获取播放列表中的歌曲
            tracks = []
            for item in playlist_info.get('tracks', {}).get('items', []):
                if item.get('track') and item['track'].get('type') == 'track':
                    track = item['track']
                    tracks.append(SpotifyTrack(
                        id=track['id'],
                        title=track['name'],
                        artist=', '.join([artist['name'] for artist in track['artists']]),
                        album=track['album']['name'] if 'album' in track else None,
                        album_art=track['album']['images'][0]['url'] if track.get('album', {}).get('images') else None,
                        duration=track.get('duration_ms', 0) // 1000,
                        preview_url=track.get('preview_url'),
                        spotify_url=track['external_urls']['spotify']
                    ))
            
            return {
                "type": "playlist",
                "name": playlist_info['name'],
                "description": playlist_info.get('description', ''),
                "total_tracks": len(tracks),
                "tracks": tracks  # 返回所有歌曲
            }
            
        elif 'album/' in url:
            # 专辑
            album_id_match = re.search(r'album/([a-zA-Z0-9]+)', url)
            if not album_id_match:
                raise HTTPException(status_code=400, detail="无效的 Spotify album URL")
            
            album_id = album_id_match.group(1)
            album_info = spotify_service.get_album_info(album_id)
            
            if not album_info:
                raise HTTPException(status_code=404, detail="未找到专辑信息")
            
            # 获取专辑中的歌曲
            tracks = []
            for track in album_info.get('tracks', {}).get('items', []):
                tracks.append(SpotifyTrack(
                    id=track['id'],
                    title=track['name'],
                    artist=', '.join([artist['name'] for artist in track['artists']]),
                    album=album_info['name'],
                    album_art=album_info['images'][0]['url'] if album_info.get('images') else None,
                    duration=track.get('duration_ms', 0) // 1000,
                    preview_url=track.get('preview_url'),
                    spotify_url=track['external_urls']['spotify']
                ))
            
            return {
                "type": "album",
                "name": album_info['name'],
                "artist": ', '.join([artist['name'] for artist in album_info['artists']]),
                "total_tracks": len(tracks),
                "tracks": tracks
            }
            
        else:
            raise HTTPException(status_code=400, detail="不支持的 Spotify URL 类型。支持的类型：track、playlist、album")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析 URL 失败: {str(e)}")

@router.get("/search-with-preview", response_model=SpotifySearchResponse)
async def search_with_preview(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="返回数量")
):
    """搜索歌曲（优化版，尝试获取preview_url）"""
    try:
        tracks_data = spotify_service.search_track_with_preview(q, limit)
        
        tracks = []
        for track_info in tracks_data:
            # 获取艺术家名称
            artist_names = ', '.join([artist['name'] for artist in track_info['artists']])
            title = track_info['name']
            album = track_info['album']['name'] if 'album' in track_info else None
            
            # 检测语言和国家
            from app.services.language_detector import language_detector
            detected_country, detected_language = language_detector.detect_country_and_language(
                title, artist_names, album
            )
            
            track = SpotifyTrack(
                id=track_info['id'],
                title=title,
                artist=artist_names,
                album=album,
                album_art=track_info['album']['images'][0]['url'] if track_info.get('album', {}).get('images') else None,
                duration=track_info.get('duration_ms', 0) // 1000,
                preview_url=track_info.get('preview_url'),
                spotify_url=track_info['external_urls']['spotify'],
                year=None,
                country=detected_country,
                language=detected_language
            )
            tracks.append(track)
        
        # 统计有preview的歌曲数量
        tracks_with_preview = [t for t in tracks if t.preview_url]
        print(f"搜索 '{q}': 总共 {len(tracks)} 首, 有preview {len(tracks_with_preview)} 首")
        
        return SpotifySearchResponse(
            tracks=tracks,
            total=len(tracks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.get("/track/{track_id}")
async def get_track_details(track_id: str):
    """获取单个歌曲的详细信息"""
    try:
        track_info = spotify_service.get_track_info(track_id)
        
        if not track_info:
            raise HTTPException(status_code=404, detail="未找到歌曲信息")
        
        return {
            "id": track_info['id'],
            "name": track_info['name'],
            "artists": [{"name": artist['name'], "id": artist['id']} for artist in track_info['artists']],
            "album": {
                "name": track_info['album']['name'],
                "id": track_info['album']['id'],
                "images": track_info['album']['images']
            } if 'album' in track_info else None,
            "duration_ms": track_info.get('duration_ms', 0),
            "preview_url": track_info.get('preview_url'),
            "popularity": track_info.get('popularity', 0),
            "external_urls": track_info.get('external_urls', {})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取歌曲详情失败: {str(e)}")

@router.get("/country-top", response_model=SpotifySearchResponse)
async def get_country_top_tracks(
    country: str = Query(..., description="国家名称或代码：korea, japan, turkey, usa, uk, china 等"),
    limit: int = Query(100, ge=1, le=500, description="返回数量，最多500首")
):
    """获取指定国家的热门音乐"""
    try:
        # 国家映射
        country_map = {
            "korea": "韩国",
            "korean": "韩国",
            "韩国": "korean",
            "japan": "日本",
            "japanese": "日本",
            "日本": "japanese",
            "turkey": "土耳其",
            "turkish": "土耳其",
            "土耳其": "turkish",
            "usa": "美国",
            "us": "美国",
            "america": "美国",
            "美国": "american",
            "uk": "英国",
            "britain": "英国",
            "英国": "british",
            "china": "中国",
            "chinese": "中国",
            "中国": "chinese",
            "taiwan": "台湾",
            "taiwanese": "台湾",
            "台湾": "taiwanese",
            "europe": "欧洲",
            "european": "欧洲",
            "欧洲": "european"
        }
        
        # 获取搜索关键词
        search_term = country_map.get(country.lower(), country)
        
        # 构建搜索查询：热门 + 国家
        queries = [
            f"top 50 {search_term}",
            f"hot {search_term} songs",
            f"{search_term} hits 2024",
            f"popular {search_term} music"
        ]
        
        all_tracks = []
        unique_tracks = set()
        
        # 尝试多个搜索查询
        for query in queries:
            try:
                # 每个查询最多获取50首，避免超过API限制
                batch_limit = min(50, limit - len(all_tracks))
                tracks_data = spotify_service.search_track(query, limit=batch_limit)
                for track_info in tracks_data:
                    track_id = track_info['id']
                    if track_id not in unique_tracks:
                        unique_tracks.add(track_id)
                        track = SpotifyTrack(
                            id=track_id,
                            title=track_info['name'],
                            artist=', '.join([artist['name'] for artist in track_info['artists']]),
                            album=track_info['album']['name'] if 'album' in track_info else None,
                            album_art=track_info['album']['images'][0]['url'] if track_info.get('album', {}).get('images') else None,
                            duration=track_info.get('duration_ms', 0) // 1000,
                            preview_url=track_info.get('preview_url'),
                            spotify_url=track_info['external_urls']['spotify']
                        )
                        all_tracks.append(track)
                        
                        if len(all_tracks) >= limit:
                            break
            except Exception as e:
                print(f"搜索查询失败: {query}, 错误: {e}")
                continue
            
            if len(all_tracks) >= limit:
                break
        
        # 按照流行度排序（如果可能的话）
        return SpotifySearchResponse(
            tracks=all_tracks[:limit],
            total=len(all_tracks[:limit])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取国家热门音乐失败: {str(e)}")

# 新增数据模型
class SpotifyPlaylist(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None
    total_tracks: int
    image_url: Optional[str] = None
    spotify_url: str
    is_public: bool

class SpotifyAlbum(BaseModel):
    id: str
    name: str
    artist: str
    total_tracks: int
    release_date: Optional[str] = None
    image_url: Optional[str] = None
    spotify_url: str

class SpotifyArtist(BaseModel):
    id: str
    name: str
    genres: List[str]
    followers: int
    image_url: Optional[str] = None
    spotify_url: str
    popularity: int

class MultiSearchResponse(BaseModel):
    tracks: Optional[List[SpotifyTrack]] = None
    playlists: Optional[List[SpotifyPlaylist]] = None
    albums: Optional[List[SpotifyAlbum]] = None
    artists: Optional[List[SpotifyArtist]] = None
    total: int

@router.get("/search-multi", response_model=MultiSearchResponse)
async def search_multi_type(
    q: str = Query(..., description="搜索查询"),
    types: str = Query("track,playlist,album,artist", description="搜索类型，逗号分隔: track,playlist,album,artist"),
    limit: int = Query(10, ge=1, le=50, description="每种类型的返回数量"),
    market: str = Query("US", description="市场代码")
):
    """多类型搜索 - 模仿Spotify Web界面的搜索功能"""
    try:
        search_types = [t.strip() for t in types.split(",")]
        results = spotify_service.search_multi_type(q, search_types, limit, market)
        
        # 格式化响应
        response_data = {"total": 0}
        
        # 处理歌曲结果
        if "tracks" in results:
            tracks = []
            for track in results["tracks"]:
                tracks.append(SpotifyTrack(
                    id=track["id"],
                    title=track["name"],
                    artist=', '.join([artist['name'] for artist in track['artists']]),
                    album=track['album']['name'] if 'album' in track else None,
                    album_art=track['album']['images'][0]['url'] if track.get('album', {}).get('images') else None,
                    duration=track.get('duration_ms', 0) // 1000,
                    preview_url=track.get('preview_url'),
                    spotify_url=track['external_urls']['spotify'],
                    year=track.get('album', {}).get('release_date', '')[:4] if track.get('album', {}).get('release_date') else None,
                    country=detect_country_from_track(track),
                    language=detect_language_from_track(track)
                ))
            response_data["tracks"] = tracks
            response_data["total"] += len(tracks)
        
        # 处理歌单结果
        if "playlists" in results:
            playlists = []
            for playlist in results["playlists"]:
                playlists.append(SpotifyPlaylist(
                    id=playlist["id"],
                    name=playlist["name"],
                    description=playlist.get("description"),
                    owner=playlist["owner"]["display_name"] if playlist.get("owner") else None,
                    total_tracks=playlist["tracks"]["total"],
                    image_url=playlist["images"][0]["url"] if playlist.get("images") else None,
                    spotify_url=playlist["external_urls"]["spotify"],
                    is_public=playlist.get("public", True)
                ))
            response_data["playlists"] = playlists
            response_data["total"] += len(playlists)
        
        # 处理专辑结果
        if "albums" in results:
            albums = []
            for album in results["albums"]:
                albums.append(SpotifyAlbum(
                    id=album["id"],
                    name=album["name"],
                    artist=', '.join([artist['name'] for artist in album['artists']]),
                    total_tracks=album["total_tracks"],
                    release_date=album.get("release_date"),
                    image_url=album["images"][0]["url"] if album.get("images") else None,
                    spotify_url=album["external_urls"]["spotify"]
                ))
            response_data["albums"] = albums
            response_data["total"] += len(albums)
        
        # 处理艺人结果
        if "artists" in results:
            artists = []
            for artist in results["artists"]:
                artists.append(SpotifyArtist(
                    id=artist["id"],
                    name=artist["name"],
                    genres=artist.get("genres", []),
                    followers=artist["followers"]["total"],
                    image_url=artist["images"][0]["url"] if artist.get("images") else None,
                    spotify_url=artist["external_urls"]["spotify"],
                    popularity=artist.get("popularity", 0)
                ))
            response_data["artists"] = artists
            response_data["total"] += len(artists)
        
        return MultiSearchResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"多类型搜索失败: {str(e)}")

@router.get("/search-playlists", response_model=List[SpotifyPlaylist])
async def search_playlists_advanced(
    q: str = Query(..., description="搜索查询"),
    limit: int = Query(20, ge=1, le=50, description="返回数量"),
    market: str = Query("US", description="市场代码")
):
    """高级歌单搜索 - 专门优化歌单搜索结果质量"""
    try:
        playlists = spotify_service.search_playlists_advanced(q, limit, market)
        
        result = []
        for playlist in playlists:
            result.append(SpotifyPlaylist(
                id=playlist["id"],
                name=playlist["name"],
                description=playlist.get("description"),
                owner=playlist["owner"]["display_name"] if playlist.get("owner") else None,
                total_tracks=playlist["tracks"]["total"],
                image_url=playlist["images"][0]["url"] if playlist.get("images") else None,
                spotify_url=playlist["external_urls"]["spotify"],
                is_public=playlist.get("public", True)
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"歌单搜索失败: {str(e)}")

@router.get("/playlists-by-category", response_model=List[SpotifyPlaylist])
async def get_playlists_by_category(
    category: str = Query(..., description="分类: korean, japanese, chinese, pop, rock, electronic, etc."),
    limit: int = Query(20, ge=1, le=50, description="返回数量"),
    market: str = Query("US", description="市场代码")
):
    """按分类获取精选歌单"""
    try:
        playlists = spotify_service.get_featured_playlists_by_category(category, limit, market)
        
        result = []
        for playlist in playlists:
            result.append(SpotifyPlaylist(
                id=playlist["id"],
                name=playlist["name"],
                description=playlist.get("description"),
                owner=playlist["owner"]["display_name"] if playlist.get("owner") else None,
                total_tracks=playlist["tracks"]["total"],
                image_url=playlist["images"][0]["url"] if playlist.get("images") else None,
                spotify_url=playlist["external_urls"]["spotify"],
                is_public=playlist.get("public", True)
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类歌单失败: {str(e)}")