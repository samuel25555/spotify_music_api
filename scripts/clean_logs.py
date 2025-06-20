#!/usr/bin/env python3
"""
日志清理脚本
可以配置到cron中定期运行
"""
import os
import sys
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.logger import clean_old_logs
from app.core.config import settings


def main():
    parser = argparse.ArgumentParser(description='清理旧日志文件')
    parser.add_argument(
        '--days', 
        type=int, 
        default=7, 
        help='保留最近多少天的日志 (默认: 7)'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default=None,
        help='日志目录路径 (默认: 使用配置文件中的路径)'
    )
    
    args = parser.parse_args()
    
    # 确定日志目录
    log_dir = args.log_dir
    if not log_dir:
        log_dir = os.path.dirname(settings.LOG_FILE)
    
    if not log_dir or not os.path.exists(log_dir):
        print(f"日志目录不存在: {log_dir}")
        return
    
    print(f"开始清理日志目录: {log_dir}")
    print(f"保留最近 {args.days} 天的日志")
    print(f"当前时间: {datetime.now()}")
    
    # 执行清理
    clean_old_logs(log_dir, days_to_keep=args.days)
    
    print("日志清理完成")


if __name__ == "__main__":
    main()