# 🔧 故障排查指南

## 📋 常见问题与解决方案

### 1. 启动问题

#### 问题：虚拟环境导入失败
```bash
ImportError: /path/to/.venv/lib/python3.12/site-packages/pydantic_core/_pydantic_core.so: failed to map segment from shared object
```

**原因：** WSL或挂载的文件系统不支持执行权限

**解决方案：**
```bash
# 方案1: 在原生Linux文件系统创建虚拟环境
rm -rf .venv
mkdir -p /tmp/music-venv
uv venv /tmp/music-venv --python 3.12
ln -sf /tmp/music-venv .venv

# 方案2: 修复共享库权限
find .venv -name "*.so" -exec chmod +x {} \;
```

#### 问题：数据库连接超时
```bash
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**原因：** 远程数据库连接慢或配置不当

**解决方案：**
```python
# app/database/connection.py
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30,
    },
    pool_pre_ping=True,
    pool_recycle=300,
)
```

#### 问题：批量任务模块导入失败
```bash
cannot import name 'batch_download_tracks' from 'app.tasks.batch_tasks'
```

**解决方案：**
```python
# 在相关模块添加优雅处理
try:
    from app.tasks.batch_tasks import batch_download_tracks
    BATCH_TASKS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 批量任务模块导入失败: {e}")
    BATCH_TASKS_AVAILABLE = False
```

### 2. Git相关问题

#### 问题：Git目录所有权警告
```bash
fatal: detected dubious ownership in repository at '/path/to/repo'
```

**解决方案：**
```bash
# 添加安全目录
git config --global --add safe.directory /path/to/repo

# 或修复目录所有权
chown -R $USER:$USER /path/to/repo
```

#### 问题：SSH密钥认证失败
```bash
Permission denied (publickey)
```

**解决方案：**
```bash
# 生成SSH密钥
ssh-keygen -t ed25519 -C "your-email@example.com"

# 添加到SSH agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 测试连接
ssh -T git@github.com
```

### 3. 前端问题

#### 问题：API请求超时
```bash
timeout of 30000ms exceeded
```

**原因：** API地址配置错误或网络问题

**解决方案：**
```javascript
// 检查API配置
console.log('API Base URL:', this.baseURL);

// 使用动态域名
this.baseURL = window.location.origin || 'http://localhost:8000';
```

#### 问题：CORS跨域错误
```bash
Access to XMLHttpRequest blocked by CORS policy
```

**解决方案：**
```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. 数据库问题

#### 问题：表不存在
```bash
sqlalchemy.exc.ProgrammingError: (mysql.connector.errors.ProgrammingError) 1146 (42S02): Table 'music_api.songs' doesn't exist
```

**解决方案：**
```python
# 确保在应用启动时创建表
from app.database.connection import create_tables
create_tables()
```

#### 问题：字符编码问题
```bash
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**解决方案：**
```python
# 数据库连接中添加字符集
DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
```

### 5. Celery问题

#### 问题：Worker无法启动
```bash
kombu.exceptions.OperationalError: [Errno 111] Connection refused
```

**原因：** Redis服务未启动

**解决方案：**
```bash
# 启动Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 或检查Redis状态
redis-cli ping
```

#### 问题：任务状态丢失
```bash
Celery task result backend not configured
```

**解决方案：**
```python
# 确保配置了结果后端
CELERY_RESULT_BACKEND = "redis://localhost:6379/6"
```

### 6. Spotify API问题

#### 问题：认证失败
```bash
spotipy.exceptions.SpotifyException: http status: 401
```

**解决方案：**
```bash
# 检查API密钥配置
echo $SPOTIFY_CLIENT_ID
echo $SPOTIFY_CLIENT_SECRET

# 重新申请或更新密钥
```

#### 问题：API限流
```bash
spotipy.exceptions.SpotifyException: http status: 429
```

**解决方案：**
```python
# 添加重试机制
import time
from functools import wraps

def retry_on_rate_limit(retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except SpotifyException as e:
                    if e.http_status == 429 and attempt < retries - 1:
                        time.sleep(delay * (2 ** attempt))
                        continue
                    raise
            return None
        return wrapper
    return decorator
```

### 7. 下载问题

#### 问题：yt-dlp下载失败
```bash
ERROR: Unable to extract video id
```

**解决方案：**
```bash
# 更新yt-dlp到最新版本
pip install --upgrade yt-dlp

# 或使用备用提取器
yt-dlp --extractor-args "youtube:player_client=android"
```

#### 问题：文件权限错误
```bash
PermissionError: [Errno 13] Permission denied
```

**解决方案：**
```bash
# 修复下载目录权限
chmod -R 755 downloads/
chown -R www:www downloads/
```

### 8. 部署问题

#### 问题：端口被占用
```bash
OSError: [Errno 98] Address already in use
```

**解决方案：**
```bash
# 查找占用端口的进程
lsof -i :8000
netstat -tlnp | grep 8000

# 杀死进程
kill -9 <PID>
```

#### 问题：环境变量未加载
```bash
KeyError: 'SPOTIFY_CLIENT_ID'
```

**解决方案：**
```bash
# 检查.env文件位置和内容
ls -la .env
cat .env

# 确保应用正确加载环境变量
python -c "from app.core.config import settings; print(settings.SPOTIFY_CLIENT_ID)"
```

## 🔍 调试工具

### 1. 日志分析
```bash
# 查看应用日志
tail -f logs/app.log

# 查看Celery日志
tail -f celery.log

# 查看系统日志
journalctl -u your-service -f
```

### 2. 数据库调试
```bash
# 连接数据库
mysql -h host -u user -p database

# 查看表结构
DESCRIBE songs;

# 查看数据
SELECT * FROM songs LIMIT 10;
```

### 3. API调试
```bash
# 健康检查
curl -v http://localhost:8000/health

# 测试API
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{"spotify_id": "test"}'
```

### 4. 性能监控
```bash
# 系统资源监控
htop
iostat -x 1

# 网络监控
netstat -i
ss -tuln
```

## 📊 监控告警

### 1. 应用监控
```python
# 添加健康检查端点
@app.get("/health")
async def health_check():
    checks = {
        "database": test_database_connection(),
        "redis": test_redis_connection(),
        "celery": test_celery_workers(),
    }
    
    status = "healthy" if all(checks.values()) else "unhealthy"
    return {"status": status, "checks": checks}
```

### 2. 日志监控
```bash
# 监控错误日志
tail -f logs/app.log | grep ERROR

# 监控API访问
tail -f /var/log/nginx/access.log | grep api
```

## 🚨 紧急恢复

### 1. 服务快速恢复
```bash
# 重启所有服务
systemctl restart nginx
docker restart redis
# 宝塔面板重启Python项目

# 回滚到稳定版本
git reset --hard <stable-commit>
```

### 2. 数据恢复
```bash
# 从备份恢复数据库
mysql -u user -p database < backup.sql

# 检查数据完整性
python scripts/check_data_integrity.py
```

## 📞 支持联系

遇到无法解决的问题时，请：

1. 收集相关日志和错误信息
2. 记录复现步骤
3. 查看相关文档
4. 联系开发团队

---

这份故障排查指南涵盖了开发和部署过程中的常见问题，建议团队成员熟悉这些解决方案以提高问题处理效率。