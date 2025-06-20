"""
Celery配置文件
用于异步任务处理，如批量导入、下载等耗时操作
"""
from celery import Celery
from app.core.config import settings

# 创建Celery实例
app = Celery(
    'music_downloader',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.batch_tasks', 'app.tasks.download_tasks']
)

# Celery配置
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    
    # 任务路由配置
    task_routes={
        'app.tasks.batch_tasks.*': {'queue': 'batch'},
        'app.tasks.download_tasks.*': {'queue': 'download'},
    },
    
    # 任务结果过期时间
    result_expires=3600,
    
    # 工作进程配置
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
)

if __name__ == '__main__':
    app.start()