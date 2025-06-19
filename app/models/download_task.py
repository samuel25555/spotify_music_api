from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid

class DownloadTask(Base):
    __tablename__ = "download_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 任务信息
    task_id = Column(String(100), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(String(20), nullable=False)  # song, playlist, album
    
    # 请求信息
    url = Column(String(1000), nullable=False)
    format = Column(String(10), default="mp3")
    quality = Column(String(10), default="320k")
    
    # 回调信息
    callback_url = Column(String(1000), nullable=True)
    
    # 状态信息
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    
    # 结果信息
    total_songs = Column(Integer, default=0)
    completed_songs = Column(Integer, default=0)
    failed_songs = Column(Integer, default=0)
    
    # 详细信息
    task_metadata = Column(JSON, nullable=True)  # 存储额外的元数据
    error_message = Column(Text, nullable=True)
    download_paths = Column(JSON, nullable=True)  # 存储下载文件路径列表
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "url": self.url,
            "format": self.format,
            "quality": self.quality,
            "callback_url": self.callback_url,
            "status": self.status,
            "progress": self.progress,
            "total_songs": self.total_songs,
            "completed_songs": self.completed_songs,
            "failed_songs": self.failed_songs,
            "metadata": self.task_metadata,
            "error_message": self.error_message,
            "download_paths": self.download_paths,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }