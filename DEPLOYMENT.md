# 🚀 项目部署配置指南

## 1. 核心配置修改

### 1.1 修改环境配置文件

**重要：**将 `.env.production` 复制为 `.env` 并修改域名：

```bash
# 应用配置
DEBUG=false
SECRET_KEY=your-super-secret-production-key-2024

# 核心：修改为您的实际域名
DOMAIN=https://yourdomain.com
# 如果使用IP: DOMAIN=http://your-server-ip:8000

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=music_user
DB_PASSWORD=your_secure_password
DB_NAME=music_downloader_prod

# 文件路径 (根据宝塔实际路径修改)
DOWNLOAD_DIR=/www/wwwroot/yourdomain.com/downloads
LOG_FILE=/www/wwwroot/yourdomain.com/logs/app.log
```

### 1.2 Nginx配置 (添加到站点配置)

在宝塔面板 -> 网站 -> 您的域名 -> 配置文件中添加：

```nginx
# 下载文件静态服务 - 关键配置！
location /downloads/ {
    alias /www/wwwroot/yourdomain.com/downloads/;
    expires 7d;
    add_header Cache-Control "public, no-transform";
    add_header Access-Control-Allow-Origin "*";
    
    # 音频文件MIME类型
    location ~* \.(mp3|webm|ogg|m4a)$ {
        add_header Content-Type "audio/mpeg";
        add_header Accept-Ranges bytes;
    }
}

# 前端静态文件
location /static/ {
    alias /www/wwwroot/yourdomain.com/frontend/;
    expires 30d;
}

# API代理
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 100M;
}
```

## 2. 宝塔Python项目配置

### 2.1 Python项目管理器设置

在宝塔面板 -> Python项目管理器：

- **项目路径**: `/www/wwwroot/yourdomain.com`
- **启动方式**: Gunicorn
- **启动文件**: `app.main:app`
- **端口**: 8000
- **进程数**: 4 (根据CPU核心调整)

### 2.2 环境变量设置

在项目设置 -> 环境变量中添加：
```
ENV_FILE=/www/wwwroot/yourdomain.com/.env
PYTHONPATH=/www/wwwroot/yourdomain.com
```

### 2.3 启动参数

```bash
# Gunicorn启动命令
gunicorn -c gunicorn.conf.py app.main:app
```

## 3. 目录权限设置

```bash
cd /www/wwwroot/yourdomain.com

# 设置基本权限
chown -R www:www .
chmod -R 755 .

# 重要：下载目录需要写权限
chmod -R 777 downloads/
chmod -R 777 logs/

# 创建必要目录
mkdir -p downloads logs
```

## 4. Celery后台任务配置

### 4.1 修改Celery脚本

编辑 `deploy_scripts/celery_production.py` 第11行：
```python
PROJECT_ROOT = "/www/wwwroot/yourdomain.com"  # 修改为实际路径
```

### 4.2 启动Celery

```bash
cd /www/wwwroot/yourdomain.com
python deploy_scripts/celery_production.py start
```

## 5. 播放链接自动生成验证

### 5.1 测试配置

1. 启动项目后访问：`https://yourdomain.com/health`
2. 测试API：`https://yourdomain.com/api/playlists/1`
3. 检查返回的 `file_url` 字段格式：

**正确格式示例：**
```json
{
  "data": {
    "songs": [
      {
        "title": "测试歌曲",
        "file_url": "https://yourdomain.com/downloads/abc123.webm",
        "is_downloaded": true
      }
    ]
  }
}
```

### 5.2 验证播放链接

```bash
# 测试文件访问
curl -I https://yourdomain.com/downloads/文件名.webm

# 应该返回 200 OK 和正确的Content-Type
```

## 6. 关键文件修改清单

已自动修改的文件：
- ✅ `app/core/config.py` - 添加了DOMAIN配置
- ✅ `app/utils/url_helper.py` - 新增URL生成工具
- ✅ `app/api/playlists.py` - 修改了播放链接生成逻辑
- ✅ `requirements.txt` - 添加了gunicorn依赖

需要手动配置：
- 🔧 `.env` - 修改DOMAIN为实际域名
- 🔧 `gunicorn.conf.py` - 修改路径配置
- 🔧 Nginx配置 - 添加静态文件服务

## 7. 启动顺序

```bash
# 1. 启动Python项目 (宝塔面板操作)
# 2. 启动Celery
python deploy_scripts/celery_production.py start
# 3. 重启Nginx
sudo systemctl restart nginx
```

## 8. 故障排查

### 8.1 播放链接404
- 检查Nginx `/downloads/` 配置
- 确认文件实际存在
- 检查文件权限 (应该是777)

### 8.2 域名不正确
- 确认 `.env` 中 `DOMAIN` 配置
- 重启Python项目使配置生效

### 8.3 文件无法访问
```bash
# 检查文件权限
ls -la downloads/
# 检查Nginx错误日志
tail -f /www/server/nginx/logs/error.log
```

---

🎯 **核心要点：只需修改 `.env` 中的 `DOMAIN` 配置为您的实际域名，项目就会自动生成正确的播放链接！**