from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_tables
from app.api.download import router as download_router
from app.api.songs import router as songs_router
from app.api.spotify import router as spotify_router
from app.api.playlist_manager import router as playlist_router
import uvicorn
import os

# 创建FastAPI应用
app = FastAPI(
    title="Music Downloader API",
    description="专为Laravel后端设计的音乐下载微服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置JSON响应不过滤null值
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

class CustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return JSONResponse.render(self, jsonable_encoder(content, exclude_none=False))

# 设置默认响应类
app.default_response_class = CustomJSONResponse

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(download_router)
app.include_router(songs_router)
app.include_router(spotify_router)
app.include_router(playlist_router)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 配置 Jinja2 使用不同的分隔符以避免与 Vue.js 冲突
templates.env.variable_start_string = '[['
templates.env.variable_end_string = ']]'

@app.on_event("startup")
async def startup_event():
    """应用启动时创建数据库表"""
    print("🚀 正在启动 Music Downloader API...")
    create_tables()
    print("✅ Music Downloader API 启动完成")
    print("🌐 Web Interface: http://0.0.0.0:8000")
    print("📖 API Documentation: http://0.0.0.0:8000/docs")

@app.get("/", response_class=HTMLResponse)
async def web_interface(request: Request):
    """Web管理界面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "Music Downloader API",
        "version": "1.0.0"
    }

@app.get("/api/system-info")
async def get_system_info():
    """获取系统信息"""
    import subprocess
    
    # 检测 FFmpeg 是否可用
    ffmpeg_command = os.getenv("FFMPEG_COMMAND", "ffmpeg")
    has_ffmpeg = False
    
    try:
        if ffmpeg_command.startswith("uv run"):
            # 对于 uv run ffmpeg，需要在项目目录执行
            result = subprocess.run(
                ffmpeg_command.split() + ['-version'], 
                capture_output=True, 
                timeout=5,
                cwd=os.getcwd()
            )
        else:
            result = subprocess.run(
                [ffmpeg_command, '-version'], 
                capture_output=True, 
                timeout=5
            )
        has_ffmpeg = result.returncode == 0
    except:
        # 如果配置的命令失败，检查系统 ffmpeg
        try:
            import shutil
            has_ffmpeg = shutil.which('ffmpeg') is not None
        except:
            has_ffmpeg = False
    
    if has_ffmpeg:
        supported_formats = ["mp3", "webm", "m4a", "flac"]
        preferred_format = "mp3"
        format_note = f"支持 MP3 转换 (使用: {ffmpeg_command})"
    else:
        supported_formats = ["webm", "m4a", "opus", "aac"]
        preferred_format = "webm"
        format_note = "下载原始音频格式（推荐安装 FFmpeg 支持 MP3）"
    
    return {
        "has_ffmpeg": has_ffmpeg,
        "supported_formats": supported_formats,
        "preferred_format": preferred_format,
        "format_note": format_note,
        "download_path": os.getenv("DOWNLOAD_PATH", "./downloads"),
        "ffmpeg_command": ffmpeg_command if has_ffmpeg else None
    }

# Laravel调用示例接口文档
@app.get("/laravel-examples")
async def laravel_examples():
    """Laravel调用示例"""
    return {
        "examples": {
            "download_song": {
                "method": "POST",
                "url": "/api/download",
                "body": {
                    "url": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",
                    "format": "mp3",
                    "quality": "320k",
                    "callback_url": "https://your-laravel-app.com/api/download-complete"
                }
            },
            "download_playlist": {
                "method": "POST", 
                "url": "/api/download-playlist",
                "body": {
                    "url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
                    "format": "mp3",
                    "quality": "320k",
                    "callback_url": "https://your-laravel-app.com/api/playlist-complete"
                }
            },
            "check_status": {
                "method": "GET",
                "url": "/api/status/{task_id}"
            },
            "get_songs": {
                "method": "GET",
                "url": "/api/songs?page=1&per_page=50&status=completed"
            },
            "get_stats": {
                "method": "GET",
                "url": "/api/stats"
            }
        },
        "php_example": '''
        // Laravel Controller Example
        use Illuminate\\Support\\Facades\\Http;
        
        class MusicController extends Controller 
        {
            private $apiBase = 'http://localhost:8000/api';
            
            public function downloadSong($spotifyUrl) 
            {
                $response = Http::post($this->apiBase . '/download', [
                    'url' => $spotifyUrl,
                    'format' => 'mp3',
                    'quality' => '320k',
                    'callback_url' => route('download.complete')
                ]);
                
                return $response->json();
            }
            
            public function checkStatus($taskId) 
            {
                $response = Http::get($this->apiBase . "/status/{$taskId}");
                return $response->json();
            }
            
            public function getSongs($page = 1) 
            {
                $response = Http::get($this->apiBase . '/songs', [
                    'page' => $page,
                    'per_page' => 50
                ]);
                
                return $response->json();
            }
        }
        '''
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )