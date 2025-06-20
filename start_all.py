#!/usr/bin/env python3
"""
音乐下载器 - 一键启动所有服务
类似宝塔面板的进程管理，自动启动和管理所有必要的服务
"""
import os
import sys
import time
import signal
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.process_manager import process_manager
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/start_all.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """检查依赖服务是否可用"""
    logger.info("🔍 检查依赖服务...")
    
    # 检查Redis
    try:
        import redis
        r = redis.Redis(
            host=settings.REDIS_HOST, 
            port=settings.REDIS_PORT, 
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None
        )
        r.ping()
        logger.info("✅ Redis服务正常")
    except Exception as e:
        logger.error(f"❌ Redis服务不可用: {e}")
        logger.info("请先启动Redis服务:")
        logger.info("  Ubuntu/Debian: sudo systemctl start redis-server")
        logger.info("  CentOS/RHEL: sudo systemctl start redis")
        logger.info("  Docker: docker run -d -p 6379:6379 redis:alpine")
        return False
    
    # 检查MySQL (可选)
    try:
        import pymysql
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        connection.close()
        logger.info("✅ MySQL数据库连接正常")
    except Exception as e:
        logger.warning(f"⚠️ MySQL数据库连接失败: {e}")
        logger.info("如果使用SQLite，可以忽略此警告")
    
    return True

def setup_directories():
    """创建必要的目录"""
    directories = [
        'logs',
        'pids', 
        'downloads',
        'configs',
        'configs/processes'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    logger.info("📁 目录结构已创建")

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"收到信号 {signum}，正在关闭所有服务...")
    process_manager.stop_all()
    sys.exit(0)

def main():
    """主函数"""
    logger.info("🎵 Music Downloader - 启动所有服务")
    logger.info("=" * 50)
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建目录结构
    setup_directories()
    
    # 检查依赖
    if not check_dependencies():
        logger.error("❌ 依赖检查失败，无法启动服务")
        sys.exit(1)
    
    # 加载配置
    try:
        process_manager.load_config()
        logger.info("📋 进程配置已加载")
    except Exception as e:
        logger.warning(f"加载配置失败，使用默认配置: {e}")
    
    # 启动所有服务
    logger.info("🚀 启动所有服务...")
    process_manager.start_all()
    
    # 显示服务状态
    time.sleep(3)  # 等待服务启动
    status = process_manager.get_status()
    
    logger.info("📊 服务状态:")
    logger.info("-" * 50)
    for name, info in status.items():
        status_emoji = "✅" if info['status'] == 'running' else "❌"
        pid_info = f"(PID: {info['pid']})" if info['pid'] else ""
        logger.info(f"{status_emoji} {name}: {info['status']} {pid_info}")
    
    logger.info("-" * 50)
    logger.info("🌐 服务访问地址:")
    logger.info(f"  主应用: http://localhost:8000")
    logger.info(f"  API文档: http://localhost:8000/docs")
    logger.info(f"  进程管理: http://localhost:8000/api/processes/status")
    logger.info(f"  Celery监控: http://localhost:5555 (如果启用)")
    logger.info("-" * 50)
    
    # 保持运行状态
    try:
        logger.info("🔄 服务监控中... (按 Ctrl+C 停止所有服务)")
        while True:
            time.sleep(10)
            
            # 定期检查服务状态
            running_count = 0
            total_count = 0
            
            for name, info in process_manager.get_status().items():
                config = process_manager.processes.get(name, {})
                if getattr(config, 'enabled', True):
                    total_count += 1
                    if info['status'] == 'running':
                        running_count += 1
            
            if running_count < total_count:
                logger.warning(f"⚠️ 有服务停止运行: {running_count}/{total_count}")
            
    except KeyboardInterrupt:
        logger.info("👋 用户请求停止服务")
    except Exception as e:
        logger.error(f"❌ 运行时错误: {e}")
    finally:
        logger.info("🛑 正在停止所有服务...")
        process_manager.stop_all()
        logger.info("✅ 所有服务已停止")

if __name__ == "__main__":
    main()