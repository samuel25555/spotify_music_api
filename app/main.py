"""
Music Downloader API - 主应用入口
现代化架构版本
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.database.connection import create_tables, test_connection
from app.database.redis_client import redis_client

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 导入API路由
from app.api import spotify, download, playlists, library, system
# 现在可以启用批量任务了
try:
    from app.api import batch_tasks
    BATCH_TASKS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"批量任务模块导入失败: {e}")
    BATCH_TASKS_AVAILABLE = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 启动 Music Downloader API...")
    
    # 测试数据库连接
    logger.info("📊 测试数据库连接...")
    if test_connection():
        logger.info("✅ 数据库连接成功")
        # 创建数据库表
        create_tables()
        logger.info("📋 数据库表已创建/更新")
    else:
        logger.error("❌ 数据库连接失败")
    
    # 连接Redis
    logger.info("🔴 连接Redis...")
    if await redis_client.connect():
        logger.info("✅ Redis连接成功")
    else:
        logger.error("❌ Redis连接失败")
    
    logger.info("🎵 Music Downloader API 启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("🛑 关闭 Music Downloader API...")
    await redis_client.close()
    logger.info("👋 再见！")

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="现代化的音乐下载和管理API",
    lifespan=lifespan
)

# 添加CORS中间件 - 改进版本
def get_allowed_origins():
    """根据环境获取允许的源"""
    if settings.DEBUG:
        return [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",  # 开发服务器
        ]
    else:
        # 生产环境应该使用具体域名
        return [settings.DOMAIN] if settings.DOMAIN != "http://localhost:8000" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 全局异常处理
from fastapi.responses import JSONResponse

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"请求验证错误: {exc}")
    return JSONResponse(
        status_code=422,
        content={"error": "请求参数验证失败", "details": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误", "message": str(exc)}
    )

# 注册API路由
app.include_router(spotify.router, tags=["Spotify"])
app.include_router(download.router, tags=["下载"])
app.include_router(playlists.router, tags=["歌单"])
app.include_router(library.router, tags=["音乐库"])
app.include_router(system.router, tags=["系统"])

# 条件注册批量任务路由
if BATCH_TASKS_AVAILABLE:
    app.include_router(batch_tasks.router, tags=["批量任务"])
    logger.info("✅ 批量任务路由已启用")
else:
    logger.warning("❌ 批量任务路由未启用")

# 自定义静态文件类，添加缓存控制
class NoCacheStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        # 对于开发环境，禁用缓存
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# 静态文件服务 - 改进版本
if os.path.exists("frontend"):
    # 按类型分别挂载静态资源，避免路径冲突
    app.mount("/js", NoCacheStaticFiles(directory="frontend/js"), name="js")
    app.mount("/css", NoCacheStaticFiles(directory="frontend/css"), name="css")
    app.mount("/assets", NoCacheStaticFiles(directory="frontend/assets"), name="assets")
    # 提供完整的静态文件访问（用于备用）
    app.mount("/static", NoCacheStaticFiles(directory="frontend"), name="static")

# 下载文件服务
downloads_dir = "downloads"
if os.path.exists(downloads_dir):
    app.mount("/downloads", StaticFiles(directory=downloads_dir), name="downloads")
else:
    # 如果下载目录不存在，创建它
    os.makedirs(downloads_dir, exist_ok=True)
    app.mount("/downloads", StaticFiles(directory=downloads_dir), name="downloads")

# 主页路由
@app.get("/")
async def read_root():
    """返回前端页面"""
    frontend_path = "frontend/index.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    else:
        return {
            "message": "🎵 Music Downloader API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "frontend": "前端文件未找到，请检查 frontend/ 目录"
        }

# 进程管理页面
@app.get("/process-manager")
async def process_manager_page():
    """进程管理页面"""
    process_manager_path = "frontend/process-manager.html"
    if os.path.exists(process_manager_path):
        return FileResponse(process_manager_path)
    else:
        return {"error": "进程管理页面未找到"}

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "database": "connected" if test_connection() else "disconnected",
        "redis": "connected" if await redis_client.get_client() else "disconnected"
    }

# API信息
@app.get("/api/info")
async def api_info():
    """API信息接口"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "现代化的音乐下载和管理API",
        "features": [
            "🔍 智能多类型搜索",
            "🎵 Spotify API集成", 
            "📥 多格式音频下载",
            "🎼 歌单管理",
            "⚡ Redis缓存加速",
            "🗄️ MySQL数据持久化"
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "spotify_search": "/api/spotify/search",
            "multi_search": "/api/spotify/search-multi",
            "download": "/api/download",
            "playlists": "/api/playlists"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 直接启动模式")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )