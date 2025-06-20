#!/usr/bin/env python3
"""
Celery 生产环境启动脚本
适用于宝塔面板部署
"""
import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# 项目配置
PROJECT_ROOT = "/www/wwwroot/yourdomain.com"  # 修改为实际项目路径
LOG_DIR = f"{PROJECT_ROOT}/logs"
PID_DIR = f"{PROJECT_ROOT}/logs"

def ensure_directories():
    """确保必要的目录存在"""
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(PID_DIR, exist_ok=True)

def start_celery_worker():
    """启动Celery Worker"""
    print("🚀 启动 Celery Worker...")
    
    cmd = [
        "celery", 
        "-A", "app.celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--pool=prefork",
        "--max-tasks-per-child=1000",
        "--queues=batch,download,default",
        f"--logfile={LOG_DIR}/celery_worker.log",
        f"--pidfile={PID_DIR}/celery_worker.pid",
        "--detach"  # 守护进程模式
    ]
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        print("✅ Celery Worker 已启动")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动Celery Worker失败: {e}")
        return False

def start_celery_beat():
    """启动Celery Beat"""
    print("⏰ 启动 Celery Beat...")
    
    cmd = [
        "celery",
        "-A", "app.celery_app", 
        "beat",
        "--loglevel=info",
        f"--logfile={LOG_DIR}/celery_beat.log",
        f"--pidfile={PID_DIR}/celery_beat.pid",
        "--detach"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        print("✅ Celery Beat 已启动")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动Celery Beat失败: {e}")
        return False

def stop_celery_services():
    """停止Celery服务"""
    print("🛑 停止 Celery 服务...")
    
    # 停止Worker
    worker_pid_file = f"{PID_DIR}/celery_worker.pid"
    if os.path.exists(worker_pid_file):
        try:
            with open(worker_pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            print("✅ Celery Worker 已停止")
        except (FileNotFoundError, ProcessLookupError, ValueError):
            print("⚠️ Celery Worker PID文件不存在或进程已停止")
    
    # 停止Beat
    beat_pid_file = f"{PID_DIR}/celery_beat.pid"
    if os.path.exists(beat_pid_file):
        try:
            with open(beat_pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            print("✅ Celery Beat 已停止")
        except (FileNotFoundError, ProcessLookupError, ValueError):
            print("⚠️ Celery Beat PID文件不存在或进程已停止")

def status_celery_services():
    """检查Celery服务状态"""
    print("📊 检查 Celery 服务状态...")
    
    # 检查Worker
    worker_pid_file = f"{PID_DIR}/celery_worker.pid"
    if os.path.exists(worker_pid_file):
        try:
            with open(worker_pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # 检查进程是否存在
            print(f"✅ Celery Worker 运行中 (PID: {pid})")
        except (FileNotFoundError, ProcessLookupError, ValueError):
            print("❌ Celery Worker 未运行")
    else:
        print("❌ Celery Worker 未运行")
    
    # 检查Beat
    beat_pid_file = f"{PID_DIR}/celery_beat.pid"
    if os.path.exists(beat_pid_file):
        try:
            with open(beat_pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"✅ Celery Beat 运行中 (PID: {pid})")
        except (FileNotFoundError, ProcessLookupError, ValueError):
            print("❌ Celery Beat 未运行")
    else:
        print("❌ Celery Beat 未运行")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Celery 生产环境服务管理")
    parser.add_argument("command", choices=["start", "stop", "restart", "status"], help="操作命令")
    parser.add_argument("--service", choices=["worker", "beat", "all"], default="all", help="服务类型")
    
    args = parser.parse_args()
    
    # 确保目录存在
    ensure_directories()
    
    # 切换到项目目录
    os.chdir(PROJECT_ROOT)
    
    if args.command == "start":
        if args.service in ["worker", "all"]:
            start_celery_worker()
        if args.service in ["beat", "all"]:
            start_celery_beat()
    
    elif args.command == "stop":
        stop_celery_services()
    
    elif args.command == "restart":
        stop_celery_services()
        time.sleep(2)
        if args.service in ["worker", "all"]:
            start_celery_worker()
        if args.service in ["beat", "all"]:
            start_celery_beat()
    
    elif args.command == "status":
        status_celery_services()