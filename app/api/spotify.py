from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from app.services.spotify_service import SpotifyService
import re

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
                
                # 始终检测国家和语言信息
                from app.services.language_detector import language_detector
                detected_country, detected_language = language_detector.detect_country_and_language(
                    title, artist_names, album
                )
                
                # 应用国家和语言筛选
                if country_filter or language_filter:
                    # 国家筛选
                    if country_filter:
                        country_match = False
                        filter_countries = [c.strip().lower() for c in country_filter.split(',')]
                        for filter_country in filter_countries:
                            if (detected_country and filter_country in detected_country.lower()) or \
                               (filter_country in ['china', 'chinese', '中国'] and detected_country in ['中国', '台湾', '香港']) or \
                               (filter_country in ['korea', 'korean', '韩国'] and detected_country == '韩国') or \
                               (filter_country in ['japan', 'japanese', '日本'] and detected_country == '日本'):
                                country_match = True
                                break
                        if not country_match:
                            continue
                    
                    # 语言筛选  
                    if language_filter:
                        language_match = False
                        filter_languages = [l.strip().lower() for l in language_filter.split(',')]
                        for filter_language in filter_languages:
                            if (detected_language and filter_language in detected_language.lower()) or \
                               (filter_language in ['chinese', '中文'] and detected_language in ['中文', '国语', '粤语']) or \
                               (filter_language in ['korean', '韩语'] and detected_language == '韩语') or \
                               (filter_language in ['japanese', '日语'] and detected_language == '日语'):
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
            playlist_info = spotify_service.get_playlist_info(playlist_id)
            
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
                "tracks": tracks[:50]  # 限制返回前50首歌
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