"""
系统相关API接口
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/api/system")

@router.get("/info")
async def get_system_info():
    """获取系统信息"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG
    }