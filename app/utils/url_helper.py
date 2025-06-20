"""
URL生成辅助工具
用于生成完整的文件访问URL
"""
from app.core.config import settings


def generate_file_url(file_path: str) -> str:
    """生成完整的文件访问URL
    
    Args:
        file_path: 本地文件路径，如 "downloads/abc123.webm"
        
    Returns:
        完整的HTTP访问URL，如 "https://yourdomain.com/downloads/abc123.webm"
    """
    if not file_path:
        return None
        
    # 提取文件名
    file_name = file_path.split('/')[-1]
    
    # 确保域名不以斜杠结尾
    domain = settings.DOMAIN.rstrip('/')
    
    # 生成完整URL
    return f"{domain}/downloads/{file_name}"


def generate_static_url(static_path: str) -> str:
    """生成静态文件访问URL
    
    Args:
        static_path: 静态文件路径，如 "js/app.js"
        
    Returns:
        完整的静态文件URL
    """
    if not static_path:
        return None
        
    domain = settings.DOMAIN.rstrip('/')
    return f"{domain}/{static_path}"


def is_production() -> bool:
    """判断是否为生产环境"""
    return not settings.DEBUG


def get_base_url() -> str:
    """获取基础URL"""
    return settings.DOMAIN.rstrip('/')