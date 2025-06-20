#!/bin/bash
# 音乐下载器一键安装脚本

set -e

echo "🎵 音乐下载器一键安装脚本"
echo "================================"

# 检查系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "✅ 检测到Linux系统"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ 检测到macOS系统"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    exit 1
fi

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 请先安装Python 3.8+版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
echo "✅ Python版本: $PYTHON_VERSION"

# 检查Redis
if ! command -v redis-server &> /dev/null; then
    echo "🔴 Redis未安装，正在安装..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y redis-server
        elif command -v yum &> /dev/null; then
            sudo yum install -y redis
        else
            echo "❌ 无法自动安装Redis，请手动安装"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install redis
        else
            echo "❌ 请先安装Homebrew，然后运行: brew install redis"
            exit 1
        fi
    fi
fi

# 启动Redis
if ! pgrep redis-server > /dev/null; then
    echo "🔴 启动Redis服务..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo systemctl start redis-server || redis-server --daemonize yes
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start redis
    fi
fi

echo "✅ Redis服务正常"

# 安装Python依赖
echo "📦 安装Python依赖..."
if command -v uv &> /dev/null; then
    echo "使用uv安装依赖..."
    uv sync
else
    echo "使用pip安装依赖..."
    python3 -m pip install --upgrade pip
    pip3 install -r requirements.txt
fi

# 创建目录
echo "📁 创建必要目录..."
mkdir -p logs pids downloads configs/processes

# 复制配置文件
if [ ! -f .env ]; then
    echo "📝 创建配置文件..."
    cp .env.example .env
    echo "⚠️ 请编辑 .env 文件配置Spotify API密钥"
fi

# 设置systemd服务 (Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v systemctl &> /dev/null; then
    echo "🔧 配置系统服务..."
    
    # 更新服务文件中的路径
    PWD=$(pwd)
    sed "s|/opt/music-downloader-api|$PWD|g" configs/systemd/music-downloader.service > /tmp/music-downloader.service
    
    sudo cp /tmp/music-downloader.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable music-downloader
    
    echo "✅ 系统服务已配置"
    echo "启动服务: sudo systemctl start music-downloader"
    echo "查看状态: sudo systemctl status music-downloader"
    echo "查看日志: sudo journalctl -u music-downloader -f"
fi

echo "================================"
echo "🎉 安装完成！"
echo ""
echo "🚀 启动方式："
echo "  方式1 - 直接启动: python3 start_all.py"
echo "  方式2 - 系统服务: sudo systemctl start music-downloader"
echo "  方式3 - Docker: docker-compose up -d"
echo ""
echo "🌐 访问地址："
echo "  主页面: http://localhost:8000"
echo "  进程管理: http://localhost:8000/process-manager"
echo "  API文档: http://localhost:8000/docs"
echo ""
echo "📝 配置文件: .env"
echo "📊 日志目录: logs/"
echo "📁 下载目录: downloads/"