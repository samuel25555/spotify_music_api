from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.sql import func
from app.database import Base

class Song(Base):
    __tablename__ = "songs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 基本信息
    title = Column(String(500), nullable=False, index=True)
    artist = Column(String(500), nullable=False, index=True)
    album = Column(String(500), nullable=True)
    duration = Column(Float, nullable=True)  # 秒
    year = Column(Integer, nullable=True)
    
    # Spotify信息
    spotify_id = Column(String(100), unique=True, index=True)
    spotify_url = Column(String(500), nullable=True)
    preview_url = Column(String(500), nullable=True)  # Spotify试听链接
    
    # YouTube信息
    youtube_id = Column(String(100), nullable=True)
    youtube_url = Column(String(500), nullable=True)
    
    # 文件信息
    file_path = Column(String(1000), nullable=True)
    file_size = Column(Integer, nullable=True)  # 字节
    file_format = Column(String(10), nullable=True)  # mp3, flac等
    
    # 元数据
    genre = Column(String(100), nullable=True)
    track_number = Column(Integer, nullable=True)
    album_art_url = Column(String(1000), nullable=True)
    lyrics = Column(Text, nullable=True)
    
    # 分类信息
    country = Column(String(100), nullable=True)  # 国家/地区
    region = Column(String(100), nullable=True)   # 地区
    language = Column(String(100), nullable=True) # 语言
    mood = Column(String(100), nullable=True)     # 情绪 (happy, sad, energetic, etc.)
    tags = Column(String(500), nullable=True)     # 标签，逗号分隔
    
    # 状态
    download_status = Column(String(20), default="pending")  # pending, downloading, completed, failed
    is_downloaded = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    downloaded_at = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration,
            "year": self.year,
            "spotify_id": self.spotify_id,
            "spotify_url": self.spotify_url,
            "preview_url": self.preview_url,
            "youtube_id": self.youtube_id,
            "youtube_url": self.youtube_url,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_format": self.file_format,
            "genre": self.genre,
            "track_number": self.track_number,
            "album_art_url": self.album_art_url,
            "country": self.country,
            "region": self.region,
            "language": self.language,
            "mood": self.mood,
            "tags": self.tags,
            "download_status": self.download_status,
            "is_downloaded": self.is_downloaded,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "downloaded_at": self.downloaded_at.isoformat() if self.downloaded_at else None,
        }