# 🚀 部署指南

## 📋 项目概述

Music Downloader API 是一个专为Laravel后端设计的音乐下载微服务，提供：

- ✅ RESTful API接口
- ✅ Spotify/YouTube音乐下载  
- ✅ 数据库存储歌曲信息
- ✅ Web管理界面
- ✅ 异步任务处理
- ✅ Laravel完美集成

## 🛠️ 快速部署

### 1. 环境准备

```bash
# 克隆项目
cd /your/project/path
# 项目已在 /mnt/d/code/music-downloader-api

# 安装依赖
uv sync

# 复制环境配置
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=sqlite:///./music_downloader.db

# Spotify API配置 (可选)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# 下载路径
DOWNLOAD_PATH=./downloads

# 服务配置
HOST=0.0.0.0
PORT=8000
```

### 3. 启动服务

```bash
# 开发模式
uv run python start.py

# 或直接启动
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 验证部署

```bash
# 运行测试
uv run python test_api.py

# 访问服务
curl http://localhost:8000/health
```

## 🌐 访问地址

- **API文档**: http://localhost:8000/docs
- **Web管理**: http://localhost:8000
- **健康检查**: http://localhost:8000/health

## 🔧 Laravel集成

### 1. 安装服务类

将 `LARAVEL_INTEGRATION.md` 中的 `MusicDownloaderService` 复制到你的Laravel项目：

```bash
# Laravel项目中
php artisan make:service MusicDownloaderService
```

### 2. 添加配置

```php
// config/services.php
'music_downloader' => [
    'url' => env('MUSIC_DOWNLOADER_URL', 'http://localhost:8000/api'),
],
```

### 3. 创建控制器

```bash
php artisan make:controller Api/MusicController
```

### 4. 添加路由

```php
// routes/api.php
Route::prefix('music')->group(function () {
    Route::post('download', [MusicController::class, 'download']);
    Route::get('status/{taskId}', [MusicController::class, 'status']);
    Route::get('songs', [MusicController::class, 'songs']);
});
```

## 📊 API接口文档

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/download` | POST | 下载单曲/播放列表 |
| `/api/status/{task_id}` | GET | 查询下载状态 |
| `/api/songs` | GET | 获取歌曲列表 |
| `/api/stats` | GET | 获取统计信息 |
| `/api/search-youtube` | POST | 搜索YouTube |

### Laravel调用示例

```php
// 下载歌曲
$response = Http::post('http://localhost:8000/api/download', [
    'url' => 'https://open.spotify.com/track/...',
    'format' => 'mp3',
    'quality' => '320k'
]);

// 检查状态
$status = Http::get("http://localhost:8000/api/status/{$taskId}");

// 获取歌曲
$songs = Http::get('http://localhost:8000/api/songs?page=1');
```

## 🔄 生产环境部署

### 使用Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 使用Systemd

```ini
# /etc/systemd/system/music-downloader.service
[Unit]
Description=Music Downloader API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/music-downloader-api
ExecStart=/usr/local/bin/uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📈 监控和维护

### 日志管理

```python
# 在app/main.py中添加日志配置
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("music_downloader.log"),
        logging.StreamHandler()
    ]
)
```

### 性能监控

```bash
# 使用htop监控资源使用
htop

# 查看API性能
curl -w "Time: %{time_total}s\n" http://localhost:8000/api/stats
```

### 数据备份

```bash
# 备份SQLite数据库
cp music_downloader.db music_downloader_backup_$(date +%Y%m%d).db

# 备份下载文件
tar -czf downloads_backup_$(date +%Y%m%d).tar.gz downloads/
```

## 🛡️ 安全考虑

1. **API限流**: 在生产环境中启用限流
2. **认证**: 添加API密钥验证
3. **HTTPS**: 在生产环境中使用HTTPS
4. **文件权限**: 确保下载目录权限正确

## 🚨 故障排除

### 常见问题

1. **端口占用**
```bash
# 检查端口
lsof -i :8000
# 杀死进程
kill -9 <PID>
```

2. **依赖问题**
```bash
# 重新安装依赖
uv sync --reinstall
```

3. **数据库问题**
```bash
# 删除数据库重新创建
rm music_downloader.db
# 重启服务
```

4. **下载失败**
- 检查网络连接
- 验证Spotify URL格式
- 检查磁盘空间

## 📞 技术支持

- **文档**: 查看 `/docs` 接口文档
- **日志**: 检查应用日志文件
- **测试**: 运行 `python test_api.py`

项目已经完全可以投入使用！🎉