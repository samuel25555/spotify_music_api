#!/bin/bash
# Celery Worker启动脚本

cd "$(dirname "$0")/.."

echo "🚀 启动Celery Worker..."

# 检查Redis是否运行
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Redis未运行，请先启动Redis服务"
    echo "   Ubuntu/Debian: sudo systemctl start redis-server"
    echo "   CentOS/RHEL: sudo systemctl start redis"
    echo "   Docker: docker run -d -p 6379:6379 redis:alpine"
    exit 1
fi

echo "✅ Redis连接正常"

# 启动Celery Worker
celery -A app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=batch,download,default \
    --pool=prefork \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --logfile=logs/celery_worker.log \
    --pidfile=logs/celery_worker.pid

echo "👋 Celery Worker已停止"