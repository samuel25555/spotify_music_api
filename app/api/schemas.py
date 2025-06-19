from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

# 请求模型
class DownloadRequest(BaseModel):
    url: str
    format: str = "mp3"
    quality: str = "320k"
    callback_url: Optional[str] = None
    metadata: Optional[dict] = None

class PlaylistDownloadRequest(BaseModel):
    url: str
    format: str = "mp3"
    quality: str = "320k"
    callback_url: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

# 响应模型
class SongResponse(BaseModel):
    id: int
    title: str
    artist: str
    album: Optional[str]
    duration: Optional[float]
    year: Optional[int]
    spotify_id: Optional[str]
    spotify_url: Optional[str]
    preview_url: Optional[str]  # 添加缺失的字段
    album_art_url: Optional[str]  # 添加缺失的字段
    youtube_id: Optional[str]
    youtube_url: Optional[str]
    file_path: Optional[str]
    file_size: Optional[int]
    file_format: Optional[str]
    genre: Optional[str]  # 添加缺失的字段
    track_number: Optional[int]  # 添加缺失的字段
    country: Optional[str]  # 添加缺失的字段
    region: Optional[str]  # 添加缺失的字段
    language: Optional[str]  # 添加缺失的字段
    mood: Optional[str]  # 添加缺失的字段
    tags: Optional[str]  # 添加缺失的字段
    download_status: str
    is_downloaded: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]  # 添加缺失的字段
    downloaded_at: Optional[datetime]

class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner: Optional[str]
    spotify_id: Optional[str]
    spotify_url: Optional[str]
    total_tracks: int
    downloaded_tracks: int
    cover_art_url: Optional[str]
    download_status: str
    created_at: Optional[datetime]
    songs: List[SongResponse] = []

class DownloadTaskResponse(BaseModel):
    id: int
    task_id: str
    task_type: str
    url: str
    format: str
    quality: str
    status: str
    progress: int
    total_songs: int
    completed_songs: int
    failed_songs: int
    error_message: Optional[str]
    created_at: Optional[datetime]
    completed_at: Optional[datetime]

class DownloadStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    total_songs: int
    completed_songs: int
    failed_songs: int
    download_paths: Optional[List[str]]
    error_message: Optional[str]
    created_at: Optional[datetime]
    completed_at: Optional[datetime]

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    per_page: int
    pages: int

class YouTubeSearchResult(BaseModel):
    id: str
    title: str
    uploader: str
    duration: Optional[int]
    view_count: Optional[int]
    url: str
    thumbnail: Optional[str]