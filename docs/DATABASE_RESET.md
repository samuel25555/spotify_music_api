# 数据库重置指南

## 快速重置

### 1. 完全重置（清理所有数据）
```bash
# 进入项目目录
cd /www/wwwroot/api.music171.com

# 使用脚本清理所有数据
uv run python scripts/reset_database.py --all

# 或者跳过确认提示
uv run python scripts/reset_database.py --all --yes
```

### 2. 仅重置数据库
```bash
uv run python scripts/reset_database.py --database
```

### 3. 手动重置（不使用脚本）

#### SQLite数据库
```bash
# 停止服务
systemctl stop music-api

# 删除数据库文件
rm -f data/music_downloader.db

# 清理下载文件
rm -rf downloads/*

# 清理日志
rm -f logs/*.log

# 重启服务（会自动创建新数据库）
systemctl start music-api
```

#### MySQL/PostgreSQL数据库
```sql
-- 连接到数据库
mysql -u root -p music_downloader

-- 删除所有表
DROP DATABASE music_downloader;
CREATE DATABASE music_downloader;

-- 或者清空表数据
TRUNCATE TABLE songs;
TRUNCATE TABLE playlists;
TRUNCATE TABLE playlist_songs;
TRUNCATE TABLE download_tasks;
TRUNCATE TABLE music_library;
```

## 选择性清理

### 只清理下载文件
```bash
uv run python scripts/reset_database.py --downloads
```

### 只清理日志
```bash
uv run python scripts/reset_database.py --logs
```

### 只清理缓存
```bash
uv run python scripts/reset_database.py --cache
```

## 重置后的操作

1. **验证服务状态**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **检查数据库连接**
   ```bash
   uv run python -c "from app.database.connection import test_connection; test_connection()"
   ```

3. **访问Web界面**
   - 打开浏览器访问你的域名
   - 确认所有功能正常

## 注意事项

- ⚠️ **数据无法恢复**：重置操作会永久删除所有数据
- 💾 **备份重要数据**：重置前请确保已备份重要数据
- 🔒 **权限问题**：确保运行用户有权限删除文件
- 🚀 **自动重建**：重启服务后会自动创建新的数据库表

## 定期维护建议

1. **定期清理下载文件**（每周）
   ```bash
   uv run python scripts/reset_database.py --downloads --yes
   ```

2. **定期清理日志**（每月）
   ```bash
   uv run python scripts/clean_logs.py --days 30
   ```

3. **完整重置**（按需）
   - 测试环境：经常重置
   - 生产环境：谨慎操作