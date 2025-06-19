
# Music Downloader API

专为Laravel后端设计的音乐下载微服务，支持Spotify和YouTube音乐下载。

## 🎯 核心功能

- **Laravel集成**: 专为Laravel后端调用设计的RESTful API
- **链接下载**: 支持Spotify歌曲/播放列表链接直接下载
- **数据库存储**: 自动存储歌曲信息和下载历史
- **Web管理**: 简单的Web界面管理下载任务
- **异步处理**: 支持大批量下载任务

## 🚀 快速开始

### 安装依赖
```bash
uv sync
```

### 启动服务
```bash
# 开发模式
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式  
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### API文档
访问 `http://localhost:8000/docs` 查看交互式API文档

## 📋 Laravel调用示例

```php
// 下载单首歌曲
$response = Http::post('http://localhost:8000/api/download', [
    'url' => 'https://open.spotify.com/track/...',
    'format' => 'mp3',
    'quality' => '320k'
]);

// 下载播放列表
$response = Http::post('http://localhost:8000/api/download-playlist', [
    'url' => 'https://open.spotify.com/playlist/...',
    'callback_url' => 'https://your-site.com/api/download-complete'
]);

// 获取下载状态
$response = Http::get('http://localhost:8000/api/status/{task_id}');

// 获取所有歌曲
$response = Http::get('http://localhost:8000/api/songs?page=1&limit=50');
```

## 🔧 配置

创建 `.env` 文件：
```env
DATABASE_URL=sqlite:///./music_downloader.db
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
DOWNLOAD_PATH=/path/to/downloads
SECRET_KEY=your_secret_key
```

## 📊 数据库结构

- **songs**: 歌曲信息表
- **playlists**: 播放列表表
- **downloads**: 下载记录表
- **download_tasks**: 下载任务表

## 🌐 Web界面

访问 `http://localhost:8000` 打开Web管理界面
=======


