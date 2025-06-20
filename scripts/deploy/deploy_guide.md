# 🚀 宝塔面板生产环境部署指南

## 1. 服务器环境准备

### 1.1 安装宝塔面板
```bash
# CentOS/RHEL
yum install -y wget && wget -O install.sh http://download.bt.cn/install/install_6.0.sh && sh install.sh

# Ubuntu/Debian  
wget -O install.sh http://download.bt.cn/install/install-ubuntu_6.0.sh && sudo bash install.sh
```

### 1.2 安装必要软件
在宝塔面板软件商店安装：
- **Python 项目管理器** (必须)
- **MySQL 5.7+** 或 **MySQL 8.0**
- **Redis** 
- **Nginx**
- **Python 3.9+**

## 2. 项目部署步骤

### 2.1 上传项目文件
1. 将整个项目文件夹上传到服务器：`/www/wwwroot/yourdomain.com/`
2. 确保项目结构如下：
```
/www/wwwroot/yourdomain.com/
├── app/                    # 主应用代码
├── frontend/              # 前端文件
├── downloads/             # 下载文件目录
├── logs/                  # 日志目录
├── requirements.txt       # Python依赖
├── .env.production       # 生产环境配置
├── gunicorn.conf.py      # Gunicorn配置
└── deploy_scripts/       # 部署脚本
```

### 2.2 配置域名和SSL
1. 在宝塔面板 -> 网站 -> 添加站点
2. 域名：填入你的实际域名 (如: music.yourdomain.com)
3. 根目录：`/www/wwwroot/yourdomain.com`
4. 申请SSL证书 (推荐Let's Encrypt免费证书)

### 2.3 修改配置文件

#### 修改 `.env.production`
```bash
# 重要：修改为实际域名！！！
DOMAIN=https://music.yourdomain.com

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=music_user
DB_PASSWORD=your_secure_password
DB_NAME=music_downloader_prod

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Spotify API (申请你自己的)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# 文件路径配置
DOWNLOAD_DIR=/www/wwwroot/yourdomain.com/downloads
LOG_FILE=/www/wwwroot/yourdomain.com/logs/app.log
```

#### 修改 `gunicorn.conf.py`
```python
# 修改所有路径中的 yourdomain.com 为实际域名
chdir = "/www/wwwroot/music.yourdomain.com"
accesslog = "/www/wwwroot/music.yourdomain.com/logs/access.log"
errorlog = "/www/wwwroot/music.yourdomain.com/logs/error.log"
pidfile = "/www/wwwroot/music.yourdomain.com/logs/gunicorn.pid"
```

### 2.4 创建数据库
在宝塔面板 -> 数据库 -> 添加数据库：
- 数据库名：`music_downloader_prod`
- 用户名：`music_user`  
- 密码：设置强密码

### 2.5 配置Python项目管理器

1. 进入宝塔面板 -> 软件商店 -> Python项目管理器
2. 添加项目：
   - **项目名称**：Music Downloader API
   - **项目路径**：`/www/wwwroot/yourdomain.com`
   - **Python版本**：选择 Python 3.9+
   - **启动方式**：Gunicorn
   - **启动文件**：`app.main:app`
   - **端口**：8000
   - **项目域名**：yourdomain.com

3. 配置启动参数：
   - **进程数**：4 (根据服务器CPU核心数调整)
   - **配置文件**：`gunicorn.conf.py`

### 2.6 安装Python依赖
在Python项目管理器中点击"模块"，然后：
```bash
# 方式1：通过requirements.txt安装
pip install -r requirements.txt

# 方式2：手动安装关键依赖
pip install fastapi uvicorn sqlalchemy pymysql redis celery spotipy yt-dlp
```

### 2.7 设置环境变量
在Python项目管理器 -> 项目设置 -> 环境变量：
```
ENV_FILE=/www/wwwroot/yourdomain.com/.env.production
PYTHONPATH=/www/wwwroot/yourdomain.com
```

## 3. Nginx反向代理配置

### 3.1 配置Nginx
在宝塔面板 -> 网站 -> 你的域名 -> 配置文件，添加：

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL配置 (宝塔会自动添加)
    
    # 静态文件直接服务
    location /downloads/ {
        alias /www/wwwroot/yourdomain.com/downloads/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
        
        # 音频文件MIME类型
        location ~* \.(mp3|webm|ogg|m4a)$ {
            add_header Content-Type "audio/mpeg";
            add_header Accept-Ranges bytes;
        }
    }
    
    location /static/ {
        alias /www/wwwroot/yourdomain.com/frontend/;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    # API代理到FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 大文件上传支持
        client_max_body_size 100M;
        proxy_read_timeout 300;
        proxy_send_timeout 300;
    }
    
    # 错误页面
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
}
```

## 4. 启动Celery后台任务

### 4.1 修改Celery脚本路径
编辑 `deploy_scripts/celery_production.py`：
```python
PROJECT_ROOT = "/www/wwwroot/yourdomain.com"  # 修改为实际路径
```

### 4.2 启动Celery服务
```bash
cd /www/wwwroot/yourdomain.com
python deploy_scripts/celery_production.py start
```

### 4.3 设置开机自启 (可选)
创建systemd服务文件：
```bash
# 创建服务文件
sudo nano /etc/systemd/system/music-celery.service
```

添加内容：
```ini
[Unit]
Description=Music Downloader Celery Service
After=network.target

[Service]
Type=forking
User=www
Group=www
WorkingDirectory=/www/wwwroot/yourdomain.com
ExecStart=/usr/bin/python3 deploy_scripts/celery_production.py start
ExecStop=/usr/bin/python3 deploy_scripts/celery_production.py stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable music-celery
sudo systemctl start music-celery
```

## 5. 文件权限设置

### 5.1 设置目录权限
```bash
cd /www/wwwroot/yourdomain.com
sudo chown -R www:www .
sudo chmod -R 755 .
sudo chmod -R 777 downloads/
sudo chmod -R 777 logs/
```

### 5.2 创建必要目录
```bash
mkdir -p downloads logs
```

## 6. 启动和测试

### 6.1 启动应用
在宝塔面板 -> Python项目管理器 -> 你的项目 -> 启动

### 6.2 检查服务状态
```bash
# 检查应用是否运行
curl http://localhost:8000/health

# 检查Celery状态
python deploy_scripts/celery_production.py status

# 查看日志
tail -f logs/app.log
tail -f logs/celery_worker.log
```

### 6.3 测试播放链接
访问：`https://yourdomain.com/api/playlists/1`
检查返回的 `file_url` 字段是否为完整的域名链接。

## 7. 监控和维护

### 7.1 查看日志
- 应用日志：`/www/wwwroot/yourdomain.com/logs/app.log`
- Celery日志：`/www/wwwroot/yourdomain.com/logs/celery_worker.log`
- Nginx日志：宝塔面板 -> 网站 -> 日志

### 7.2 重启服务
```bash
# 重启FastAPI应用
宝塔面板 -> Python项目管理器 -> 重启

# 重启Celery
python deploy_scripts/celery_production.py restart

# 重启Nginx
sudo systemctl restart nginx
```

### 7.3 数据库备份
在宝塔面板 -> 数据库 -> 定时备份 设置自动备份

## 8. 常见问题解决

### 8.1 播放链接404问题
1. 检查Nginx配置中的 `/downloads/` 路径
2. 确认文件实际存在于downloads目录
3. 检查文件权限是否正确

### 8.2 Celery任务不执行
1. 检查Redis连接：`redis-cli ping`
2. 查看Celery日志是否有错误
3. 重启Celery服务

### 8.3 数据库连接失败
1. 检查MySQL服务是否运行
2. 验证数据库用户名密码
3. 确认防火墙设置

## 9. 安全建议

1. **更换默认密码**：数据库、Redis、宝塔面板密码
2. **限制访问**：配置防火墙，只开放必要端口
3. **定期更新**：保持系统和软件包更新
4. **备份策略**：定期备份数据库和重要文件
5. **监控日志**：定期检查错误日志

---

部署完成后，你的音乐下载API将通过域名提供完整的播放链接服务！🎉