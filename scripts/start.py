#!/usr/bin/env python3
"""
Music Downloader API 启动脚本
"""
import uvicorn
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    print("🎵 Starting Music Downloader API...")
    print(f"📡 Server: http://{host}:{port}")
    print(f"📖 API Docs: http://{host}:{port}/docs")
    print(f"🌐 Web Interface: http://{host}:{port}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )