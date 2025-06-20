# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个专为Laravel后端设计的音乐下载微服务，基于FastAPI构建。支持Spotify和YouTube音乐下载，提供RESTful API和Web管理界面。

## 核心技术栈

- **FastAPI**: 现代异步Web框架
- **SQLAlchemy**: ORM数据库操作
- **spotipy**: Spotify Web API客户端
- **yt-dlp**: YouTube下载工具
- **Vue.js 3**: 前端Web界面（位于templates/index.html）

## 开发命令

### 环境管理
```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run python start.py

# 或者直接使用uvicorn
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 代码质量
```bash
# 代码格式化
uv run black app/
uv run isort app/

# 代码检查
uv run flake8 app/

# 运行测试
uv run pytest

# 运行单个测试
uv run pytest tests/test_specific.py::test_function
```

### 数据库操作
```bash
# 数据库表会在应用启动时自动创建
# 查看数据库状态可以通过访问 /api/songs 端点
```

## 架构设计

### API结构
- `app/api/download.py`: 下载相关API（单曲、播放列表下载）
- `app/api/songs.py`: 歌曲管理API（CRUD操作、搜索）
- `app/api/spotify.py`: Spotify集成API（搜索、解析URL、获取元数据）
- `app/api/playlist_manager.py`: 播放列表管理API（创建、管理用户歌单）

### 数据模型
- `Song`: 歌曲信息，包含Spotify和YouTube元数据、本地文件信息、试听链接
- `Playlist`: 播放列表，支持用户自定义歌单和Spotify导入
- `DownloadTask`: 下载任务，异步处理大批量下载

### 服务层
- `SpotifyService`: Spotify API集成，处理认证和数据获取
- `DownloadService`: 下载管理，协调yt-dlp和文件操作
- `LanguageDetector`: 智能语言和地区检测

### 关键特性

#### 双重JSON响应处理
系统实现了`CustomJSONResponse`类来确保API返回完整的歌曲元数据（特别是preview_url和album_art_url字段），绕过FastAPI默认的null值过滤。

#### Spotify API集成策略
- 使用Client Credentials认证，无需用户登录
- 支持多市场搜索以获取更多preview_url
- 实现了智能去重和语言检测
- 处理API限制和错误重试

#### 前端架构
单页面Vue.js应用（templates/index.html），包含：
- 响应式搜索界面，支持防抖和缓存
- 播放列表管理，支持批量操作
- 音乐试听功能，支持30秒预览
- 下载进度追踪和历史记录

## 环境配置

创建`.env`文件：
```env
DATABASE_URL=sqlite:///./music_downloader.db
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
DOWNLOAD_PATH=/path/to/downloads
SECRET_KEY=your_secret_key
HOST=0.0.0.0
PORT=8000
```

## API端点概览

### 核心功能
- `POST /api/download`: 下载单首歌曲
- `POST /api/download-playlist`: 下载播放列表
- `GET /api/songs`: 获取歌曲列表（支持分页、搜索）
- `GET /api/spotify/search`: Spotify歌曲搜索
- `POST /api/playlists/create`: 创建用户歌单

### 管理接口
- `GET /health`: 健康检查
- `GET /api/system-info`: 系统信息（FFmpeg状态等）
- `GET /docs`: OpenAPI文档

## 数据库设计要点

### 歌曲表设计
Song表支持多平台元数据：
- Spotify信息：spotify_id, preview_url, album_art_url
- YouTube信息：youtube_id, youtube_url
- 本地文件：file_path, file_size, file_format
- 分类信息：country, language, mood, genre

### 关系设计
- Playlist和Song之间使用多对多关系（playlist_songs表）
- 支持歌单内歌曲排序（position字段）
- 软删除和状态追踪

## 常见问题解决

### Preview URL问题
如果Spotify歌曲没有preview_url，检查：
1. API响应中SongResponse模型是否包含preview_url字段
2. 是否使用了正确的市场参数
3. 歌曲是否在特定地区可用

### 下载失败
检查FFmpeg安装和yt-dlp版本更新。系统会在启动时检查FFmpeg可用性。

### 数据库问题
数据库表在应用启动时自动创建。如需重置，删除.db文件重启应用。

## Laravel集成注意事项

设计为Laravel后端的微服务，支持：
- 回调URL通知下载完成
- RESTful API设计，便于HTTP客户端调用
- 标准化错误响应格式
- CORS支持跨域请求