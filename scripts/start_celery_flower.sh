#!/bin/bash
# Celery Flower监控界面启动脚本

cd "$(dirname "$0")/.."

echo "🌸 启动Celery Flower监控界面..."

# 检查Redis是否运行
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Redis未运行，请先启动Redis服务"
    exit 1
fi

echo "✅ Redis连接正常"

# 启动Flower
celery -A app.celery_app flower \
    --port=5555 \
    --broker=redis://localhost:6379/0 \
    --basic_auth=admin:admin123 \
    --logfile=logs/celery_flower.log \
    --persistent=True

echo "👋 Celery Flower已停止"