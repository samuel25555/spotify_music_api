"""
数据库连接配置
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.database.models import Base
try:
    from app.core.config import settings
except ImportError:
    # 临时配置，当settings不可用时
    class TempSettings:
        DATABASE_URL = None
        DB_USER = "music_user"
        DB_PASSWORD = "music_pass"
        DB_HOST = "localhost"
        DB_PORT = 3306
        DB_NAME = "music_downloader"
        DEBUG = True
    settings = TempSettings()

# 数据库URL
if settings.DATABASE_URL:
    DATABASE_URL = settings.DATABASE_URL
else:
    DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset=utf8mb4"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "connect_timeout": 10,  # 连接超时10秒
        "read_timeout": 30,     # 读取超时30秒
        "write_timeout": 30,    # 写入超时30秒
    },
    echo=settings.DEBUG,  # 在开发模式下显示SQL日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """获取数据库会话 - FastAPI依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Session:
    """获取数据库会话 - 直接返回会话对象"""
    return SessionLocal()

# 测试数据库连接
def test_connection():
    """测试数据库连接"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False