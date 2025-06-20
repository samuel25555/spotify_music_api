#!/bin/bash

# 音乐下载器项目启动脚本

echo "🎵 启动音乐下载器项目..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p downloads logs uploads

# 复制环境配置文件
if [ ! -f .env ]; then
    echo "📋 复制环境配置文件..."
    cp .env.example .env
    echo "✅ 已创建.env文件，请根据需要修改配置"
fi

# 启动Docker容器
echo "🐳 启动Docker容器..."
docker-compose up -d

# 等待MySQL启动
echo "⏳ 等待MySQL启动..."
sleep 30

# 检查MySQL连接
echo "🔍 检查数据库连接..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker exec music_downloader_mysql mysql -u music_user -pmusic_pass -e "SELECT 1;" music_downloader &>/dev/null; then
        echo "✅ MySQL连接成功"
        break
    else
        echo "⏳ 等待MySQL启动... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ MySQL启动失败"
    exit 1
fi

# 检查Redis连接
echo "🔍 检查Redis连接..."
if docker exec music_downloader_redis redis-cli -a musicredis2024 ping &>/dev/null; then
    echo "✅ Redis连接成功"
else
    echo "❌ Redis连接失败"
    exit 1
fi

# 安装Python依赖（如果需要）
if [ -f requirements.txt ]; then
    echo "📦 检查Python依赖..."
    if command -v python3 &> /dev/null; then
        if [ ! -d "venv" ]; then
            echo "🐍 创建Python虚拟环境..."
            python3 -m venv venv
        fi
        
        echo "📦 激活虚拟环境并安装依赖..."
        source venv/bin/activate
        pip install -r requirements.txt
        
        echo "🚀 启动FastAPI服务器..."
        nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > logs/app.log 2>&1 &
        
        echo "✅ FastAPI服务器已启动在端口8000"
    else
        echo "⚠️  Python3未安装，请手动安装依赖并启动服务器"
    fi
fi

echo ""
echo "🎉 项目启动完成！"
echo ""
echo "📊 服务状态："
echo "   MySQL:     http://localhost:3306"
echo "   Redis:     http://localhost:6379"
echo "   API服务:   http://localhost:8000"
echo "   前端页面:  http://localhost:8000"
echo ""
echo "🔧 管理命令："
echo "   查看日志:   docker-compose logs -f"
echo "   停止服务:   docker-compose down"
echo "   重启服务:   docker-compose restart"
echo ""
echo "📝 注意事项："
echo "   - 首次启动可能需要等待数据库初始化"
echo "   - 请确保端口3306、6379、8000未被占用"
echo "   - 如需修改配置，请编辑.env文件后重启"