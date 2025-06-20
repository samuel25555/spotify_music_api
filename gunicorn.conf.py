"""
Gunicorn 生产环境配置文件
适用于宝塔面板Python项目部署
"""
import multiprocessing
import os

# 服务器套接字
bind = "0.0.0.0:8000"
backlog = 2048

# 工作进程
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# 超时设置
timeout = 30
keepalive = 2

# 日志配置
accesslog = "/www/wwwroot/yourdomain.com/logs/access.log"
errorlog = "/www/wwwroot/yourdomain.com/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程名称
proc_name = "music-downloader-api"

# 安全设置
user = "www"
group = "www"

# 预加载应用
preload_app = True

# 工作目录
chdir = "/www/wwwroot/yourdomain.com"

# 守护进程模式
daemon = False

# PID文件
pidfile = "/www/wwwroot/yourdomain.com/logs/gunicorn.pid"

# 临时目录
tmp_upload_dir = None

# SSL配置 (如果需要HTTPS)
# keyfile = "/path/to/private.key"
# certfile = "/path/to/certificate.crt"

def post_fork(server, worker):
    """工作进程启动后的回调"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    """工作进程启动前的回调"""
    pass

def worker_int(worker):
    """工作进程收到SIGINT信号时的回调"""
    worker.log.info("worker received INT or QUIT signal")

def on_exit(server):
    """主进程退出时的回调"""
    server.log.info("Master process exiting")