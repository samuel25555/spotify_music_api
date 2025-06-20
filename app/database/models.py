"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    spotify_token = Column(Text)
    preferences = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")
    download_tasks = relationship("DownloadTask", back_populates="user", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    music_library = relationship("MusicLibrary", back_populates="user", cascade="all, delete-orphan")

class Song(Base):
    __tablename__ = "songs"
    
    id = Column(Integer, primary_key=True, index=True)
    spotify_id = Column(String(100), unique=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    artist = Column(String(255), nullable=False, index=True)
    album = Column(String(255), index=True)
    album_art_url = Column(Text)
    preview_url = Column(Text)
    spotify_url = Column(Text)
    duration = Column(Integer)  # 秒
    year = Column(Integer, index=True)
    country = Column(String(50), index=True)
    region = Column(String(50))
    language = Column(String(50), index=True)
    genre = Column(String(100), index=True)
    mood = Column(String(50), index=True)
    tags = Column(Text)
    popularity = Column(Integer, default=0, index=True)
    track_number = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    playlist_songs = relationship("PlaylistSong", back_populates="song", cascade="all, delete-orphan")
    download_tasks = relationship("DownloadTask", back_populates="song", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="song", cascade="all, delete-orphan")
    library_entries = relationship("MusicLibrary", back_populates="song", cascade="all, delete-orphan")

class Playlist(Base):
    __tablename__ = "playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    image_url = Column(Text)
    category = Column(String(100), index=True)
    country = Column(String(50), index=True)
    language = Column(String(50), index=True)
    mood = Column(String(50), index=True)
    tags = Column(Text)
    is_public = Column(Boolean, default=True, index=True)
    total_tracks = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="playlists")
    playlist_songs = relationship("PlaylistSong", back_populates="playlist", cascade="all, delete-orphan")

class PlaylistSong(Base):
    __tablename__ = "playlist_songs"
    
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    position = Column(Integer, default=0)
    added_at = Column(DateTime, default=func.now())
    
    # 关系
    playlist = relationship("Playlist", back_populates="playlist_songs")
    song = relationship("Song", back_populates="playlist_songs")

class DownloadTask(Base):
    __tablename__ = "download_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), index=True)  # 批量下载关联歌单
    
    url = Column(String(500), nullable=False)
    status = Column(String(20), default="pending", index=True)  # pending, downloading, completed, failed
    progress = Column(Integer, default=0)
    file_path = Column(Text)
    error_message = Column(Text)
    format = Column(String(20), default="mp3")
    quality = Column(String(20), default="high")
    
    # 任务类型
    task_type = Column(String(20), default="single", index=True)  # single, playlist, library_batch
    batch_id = Column(String(50), index=True)  # 批量任务ID，用于关联同一批次的多个任务
    
    task_metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="download_tasks")
    song = relationship("Song", back_populates="download_tasks")
    playlist = relationship("Playlist")

class SearchHistory(Base):
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    query = Column(String(255), nullable=False, index=True)
    search_type = Column(String(50))
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # 关系
    user = relationship("User", back_populates="search_history")

class UserFavorite(Base):
    __tablename__ = "user_favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    user = relationship("User", back_populates="favorites")
    song = relationship("Song", back_populates="favorites")

class MusicLibrary(Base):
    """音乐收藏库 - 保存搜索结果供后续筛选和管理"""
    __tablename__ = "music_library"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    
    # 收藏时的分类标签
    category = Column(String(100), index=True)  # 用户自定义分类
    tags = Column(Text)  # 用户自定义标签，逗号分隔
    notes = Column(Text)  # 用户备注
    
    # 用户自定义的地区信息（与歌曲原有country字段分离）
    custom_country = Column(String(50), index=True)  # 用户自定义国家
    custom_region = Column(String(50), index=True)   # 用户自定义地区
    custom_language = Column(String(50), index=True) # 用户自定义语言
    
    # 状态管理
    is_downloaded = Column(Boolean, default=False, index=True)  # 是否已下载
    download_task_id = Column(Integer, ForeignKey("download_tasks.id"), index=True)  # 关联下载任务
    
    # 时间戳
    added_at = Column(DateTime, default=func.now(), index=True)
    last_accessed = Column(DateTime, default=func.now())
    
    # 关系
    user = relationship("User", back_populates="music_library")
    song = relationship("Song", back_populates="library_entries")
    download_task = relationship("DownloadTask")
    
    # 索引优化
    __table_args__ = (
        Index('idx_user_song', 'user_id', 'song_id'),  # 联合索引，防重复
        Index('idx_user_category', 'user_id', 'category'),
        Index('idx_user_downloaded', 'user_id', 'is_downloaded'),
    )