# 🚀 环境重启指南

## 📋 问题诊断

### 当前问题
- ❌ 应用卡死 (MySQL连接失败)
- ❌ Docker容器未启动 (权限问题)
- ❌ 重构未完成 (核心功能缺失)

---

## 🎯 重启方案

### 方案A: 快速恢复 (推荐) ⚡
**适用**: 需要立即使用应用

```bash
# 1. 清理当前进程
pkill -f uvicorn
pkill -f python

# 2. 备份当前重构进度
git add . && git commit -m "WIP: 重构进度保存"

# 3. 恢复到功能版本
cp -r backup/20250619_120758/* ./

# 4. 启动原版本
python start.py
```

**预期结果**: 5分钟内恢复完整功能

---

### 方案B: 继续重构 🔧
**适用**: 要完成现代化架构

#### B1. 启动Docker环境
```bash
# 检查Docker状态
docker --version

# 启动Docker (可能需要管理员权限)
sudo systemctl start docker
# 或者
sudo service docker start

# 启动数据库服务
sudo docker compose up -d mysql redis

# 等待服务启动
sleep 30

# 验证服务状态
docker ps
```

#### B2. 测试数据库连接
```bash
# 测试MySQL连接
docker exec -it music_downloader_mysql mysql -umusic_user -pmusic_pass music_downloader

# 测试Redis连接  
docker exec -it music_downloader_redis redis-cli -a musicredis2024
```

#### B3. 启动应用
```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### 方案C: 临时SQLite方案 🗄️
**适用**: Docker问题但想使用新架构

```bash
# 1. 修改数据库配置为SQLite
# 编辑 app/database/connection.py
# 将 DATABASE_URL 改为: "sqlite:///./music_downloader.db"

# 2. 禁用Redis (可选)
# 注释掉 app/main.py 中的Redis连接代码

# 3. 启动应用
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔍 环境检查命令

### 进程检查
```bash
# 查看Python进程
ps aux | grep python

# 查看端口占用
netstat -tlnp | grep :8000
# 或
ss -tlnp | grep :8000

# 强制杀死进程
pkill -f uvicorn
```

### Docker检查
```bash
# 检查Docker服务
systemctl status docker

# 查看容器状态
docker ps -a

# 查看容器日志
docker logs music_downloader_mysql
docker logs music_downloader_redis
```

### 依赖检查
```bash
# Python环境
python --version
which python

# 包管理器
uv --version

# 检查虚拟环境
which python
pip list | grep -E "(fastapi|sqlalchemy|mysql)"
```

---

## 🚨 故障排除

### 常见问题

#### 1. Docker权限错误
```bash
# 错误: permission denied while trying to connect to the Docker daemon
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. 端口被占用
```bash
# 错误: Address already in use
sudo lsof -i :8000
sudo kill -9 <PID>
```

#### 3. MySQL连接失败
```bash
# 错误: Can't connect to MySQL server
# 检查容器状态
docker ps | grep mysql

# 重启容器
docker restart music_downloader_mysql
```

#### 4. 模块导入错误
```bash
# 错误: ModuleNotFoundError
# 重新安装依赖
uv sync --reinstall
```

---

## 📊 服务验证

### 验证应用启动
```bash
# 检查健康状态
curl http://localhost:8000/health

# 检查API文档
curl http://localhost:8000/docs

# 检查前端
curl http://localhost:8000/
```

### 验证数据库
```bash
# 测试数据库连接
python -c "
from app.database.connection import test_connection
print('数据库状态:', test_connection())
"
```

---

## 🎯 推荐操作流程

### 立即恢复 (方案A)
1. 执行快速恢复命令
2. 访问 http://localhost:8000 验证
3. 测试核心功能 (搜索、下载)

### 环境重置 (方案B)
1. 获取管理员权限启动Docker
2. 逐步验证服务启动
3. 解决重构中的功能缺失

### 问题报告
如果遇到其他问题，请提供：
- 错误日志
- 系统环境信息
- 具体操作步骤

---

**总结**: 建议优先使用方案A快速恢复功能，然后再考虑是否继续重构工作。