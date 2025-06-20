"""
日志系统工具模块
自动创建目录、处理权限、实现日志轮转
"""
import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime


def ensure_log_directory(log_path: str) -> None:
    """确保日志目录存在"""
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, mode=0o755, exist_ok=True)
        except PermissionError:
            # 如果没有权限创建目录，尝试使用临时目录
            import tempfile
            fallback_dir = os.path.join(tempfile.gettempdir(), 'music-downloader-logs')
            os.makedirs(fallback_dir, mode=0o755, exist_ok=True)
            print(f"无法创建日志目录 {log_dir}，使用备用目录: {fallback_dir}")
            return fallback_dir
    return log_dir


def setup_logger(
    name: str = None,
    log_file: str = None,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    format_string: str = None,
    use_time_rotation: bool = False,
    when: str = 'midnight',
    interval: int = 1,
    encoding: str = 'utf-8'
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
        level: 日志级别
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的历史日志文件数量
        format_string: 日志格式字符串
        use_time_rotation: 是否使用基于时间的轮转
        when: 时间轮转间隔类型 ('S', 'M', 'H', 'D', 'midnight')
        interval: 轮转间隔
        encoding: 文件编码
        
    Returns:
        配置好的日志记录器
    """
    
    # 创建或获取logger
    logger = logging.getLogger(name or __name__)
    logger.setLevel(level)
    
    # 清除现有的处理器
    logger.handlers.clear()
    
    # 默认格式
    if not format_string:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        try:
            # 确保日志目录存在
            log_dir = ensure_log_directory(log_file)
            if log_dir != os.path.dirname(log_file):
                # 使用备用目录
                log_file = os.path.join(log_dir, os.path.basename(log_file))
            
            # 尝试创建日志文件
            Path(log_file).touch(exist_ok=True)
            
            if use_time_rotation:
                # 基于时间的日志轮转
                file_handler = TimedRotatingFileHandler(
                    log_file,
                    when=when,
                    interval=interval,
                    backupCount=backup_count,
                    encoding=encoding
                )
                # 设置轮转后的文件命名格式
                file_handler.suffix = "%Y%m%d"
            else:
                # 基于大小的日志轮转
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding=encoding
                )
            
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except (PermissionError, IOError) as e:
            logger.warning(f"无法创建日志文件 {log_file}: {e}")
            logger.warning("将只使用控制台输出")
    
    return logger


def clean_old_logs(log_dir: str, days_to_keep: int = 7) -> None:
    """
    清理旧日志文件
    
    Args:
        log_dir: 日志目录
        days_to_keep: 保留最近多少天的日志
    """
    import time
    
    if not os.path.exists(log_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
    
    for filename in os.listdir(log_dir):
        if filename.endswith('.log'):
            file_path = os.path.join(log_dir, filename)
            try:
                file_modified = os.path.getmtime(file_path)
                if file_modified < cutoff_time:
                    os.remove(file_path)
                    print(f"已删除旧日志文件: {filename}")
            except Exception as e:
                print(f"删除日志文件失败 {filename}: {e}")


# 导出便捷函数
def get_logger(name: str, log_file: str = None) -> logging.Logger:
    """获取配置好的日志记录器"""
    from app.core.config import settings
    
    if not log_file:
        log_file = settings.LOG_FILE
    
    return setup_logger(
        name=name,
        log_file=log_file,
        level=getattr(logging, settings.LOG_LEVEL),
        use_time_rotation=True,  # 使用基于时间的轮转
        when='midnight',  # 每天午夜轮转
        backup_count=7,  # 保留7天的日志
    )