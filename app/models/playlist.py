from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# 播放列表和歌曲的多对多关系表
playlist_songs = Table(
    'playlist_songs',
    Base.metadata,
    Column('playlist_id', Integer, ForeignKey('playlists.id'), primary_key=True),
    Column('song_id', Integer, ForeignKey('songs.id'), primary_key=True),
    Column('position', Integer, nullable=True)  # 歌曲在播放列表中的位置
)

class Playlist(Base):
    __tablename__ = "playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 基本信息
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner = Column(String(200), nullable=True)
    
    # Spotify信息
    spotify_id = Column(String(100), nullable=True, index=True)  # 允许为空，支持用户自定义歌单
    spotify_url = Column(String(500), nullable=True)
    
    # 统计信息
    total_tracks = Column(Integer, default=0)
    downloaded_tracks = Column(Integer, default=0)
    
    # 元数据
    cover_art_url = Column(String(1000), nullable=True)
    is_public = Column(Boolean, default=True)
    
    # 分类信息
    category = Column(String(100), nullable=True)  # 分类：如"韩国流行"、"日本动漫"等
    tags = Column(String(500), nullable=True)      # 标签，逗号分隔
    country = Column(String(100), nullable=True)   # 主要国家
    language = Column(String(100), nullable=True)  # 主要语言
    mood = Column(String(100), nullable=True)      # 情绪标签
    
    # 类型
    playlist_type = Column(String(20), default="user")  # user, spotify, system
    
    # 状态
    download_status = Column(String(20), default="pending")  # pending, downloading, completed, failed
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    songs = relationship("Song", secondary=playlist_songs, backref="playlists")
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "spotify_id": self.spotify_id,
            "spotify_url": self.spotify_url,
            "total_tracks": self.total_tracks,
            "downloaded_tracks": self.downloaded_tracks,
            "cover_art_url": self.cover_art_url,
            "is_public": self.is_public,
            "category": self.category,
            "tags": self.tags,
            "country": self.country,
            "language": self.language,
            "mood": self.mood,
            "playlist_type": self.playlist_type,
            "download_status": self.download_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "songs": [song.to_dict() for song in self.songs] if hasattr(self, 'songs') else []
        }