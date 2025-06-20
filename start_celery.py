#!/usr/bin/env python3
"""
Celery工作进程启动脚本
"""
import os
import sys
from app.celery_app import app

if __name__ == '__main__':
    # 添加项目根目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 启动Celery worker
    app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=4',
        '--queues=batch,download,default',
        '--pool=prefork',
        '--without-gossip',
        '--without-mingle',
        '--without-heartbeat'
    ])