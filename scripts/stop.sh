#!/bin/bash

# 音乐下载器项目停止脚本

echo "🛑 停止音乐下载器项目..."

# 停止FastAPI服务器
echo "⏹️  停止FastAPI服务器..."
pkill -f "uvicorn app.main:app"

# 停止Docker容器
echo "🐳 停止Docker容器..."
docker-compose down

echo "✅ 项目已停止"
echo ""
echo "💡 如需完全清理项目数据，使用："
echo "   docker-compose down -v  # 删除数据卷"
echo "   docker system prune     # 清理未使用的镜像"