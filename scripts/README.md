# Scripts 目录说明

## 目录结构

### 🚀 运行脚本
- `start.py` - 主要启动脚本
- `start.sh` - Shell启动脚本  
- `stop.sh` - 停止服务脚本
- `start_celery_worker.sh` - Celery工作进程
- `start_celery_flower.sh` - Celery监控界面

### 🗄️ 数据库管理
- `reset_database.py` - 完整数据库重置工具
- `reset_database_simple.py` - 简化版重置工具
- `truncate_tables.py` - 清空表数据工具

### 🧹 维护脚本
- `clean_logs.py` - 日志清理工具

### 📦 部署脚本 (deploy/)
- `deploy/deploy_guide.md` - 部署指南
- `deploy/check_config.py` - 配置检查
- `deploy/celery_production.py` - 生产环境Celery配置
- `deploy/setup_log_rotation.sh` - 日志轮转设置

### 🛠️ 安装脚本
- `install.sh` - 系统安装脚本

## 使用说明

### 开发环境
```bash
# 启动开发服务器
./scripts/start.sh

# 停止服务
./scripts/stop.sh

# 清理数据库
uv run python scripts/truncate_tables.py --all
```

### 生产环境
```bash
# 检查配置
python scripts/deploy/check_config.py

# 设置日志轮转
./scripts/deploy/setup_log_rotation.sh

# 启动生产服务
python scripts/start.py
```

### 维护
```bash
# 清理旧日志
python scripts/clean_logs.py --days 7

# 重置数据库
python scripts/reset_database.py --all
```