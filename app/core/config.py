"""
应用配置
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用设置
    APP_NAME: str = "Music Downloader API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "music-downloader-secret-key-2024"
    
    # 域名设置 (生产环境重要配置)
    DOMAIN: str = "http://localhost:8000"  # 生产环境需要修改为实际域名
    
    # 数据库设置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "music_user"
    DB_PASSWORD: str = "music_pass"
    DB_NAME: str = "music_downloader"
    DATABASE_URL: Optional[str] = None
    
    # Redis设置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "musicredis2024"
    REDIS_DB: int = 0
    
    # Spotify API设置
    SPOTIFY_CLIENT_ID: str = "5f573c9620494bae87890c0f08a60293"
    SPOTIFY_CLIENT_SECRET: str = "212476d9b0f3472eaa762d90b19b0ba8"
    
    # 缓存设置
    CACHE_EXPIRE_TIME: int = 3600  # 1小时
    SEARCH_CACHE_EXPIRE: int = 1800  # 30分钟
    
    # 下载设置
    DOWNLOAD_DIR: str = "./downloads"
    MAX_DOWNLOAD_CONCURRENT: int = 5
    
    # 分页设置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # 文件处理设置
    MAX_DOWNLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB 最大下载文件大小
    
    # 日志设置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    # Celery设置
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局设置实例
settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)