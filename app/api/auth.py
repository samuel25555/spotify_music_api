"""
身份验证API路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.auth import auth_manager, get_current_user, get_current_admin_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    expires_in: int = 24 * 60 * 60  # 24小时，以秒为单位

class UserResponse(BaseModel):
    username: str
    role: str
    created_at: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    user = auth_manager.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    # 创建访问令牌
    access_token = auth_manager.create_access_token(
        username=user["username"],
        role=user["role"]
    )
    
    # 返回用户信息（不包含密码哈希）
    user_info = {
        "username": user["username"],
        "role": user["role"],
        "created_at": user["created_at"]
    }
    
    return LoginResponse(
        access_token=access_token,
        user=user_info
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        username=current_user["username"],
        role=current_user["role"],
        created_at=current_user["created_at"]
    )

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    # 验证当前密码
    if not auth_manager.verify_password(request.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=400, detail="当前密码错误")
    
    # 更新密码
    new_password_hash = auth_manager.hash_password(request.new_password)
    auth_manager.default_users[current_user["username"]]["password_hash"] = new_password_hash
    
    return {"message": "密码修改成功"}

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """用户登出（客户端需要删除token）"""
    return {"message": "登出成功"}

@router.get("/check")
async def check_auth_status(current_user: dict = Depends(get_current_user)):
    """检查身份验证状态"""
    return {
        "authenticated": True,
        "user": {
            "username": current_user["username"],
            "role": current_user["role"]
        }
    }

@router.get("/system-info")
async def get_system_info(current_user: dict = Depends(get_current_admin_user)):
    """获取系统信息（仅管理员）"""
    import os
    import psutil
    from datetime import datetime
    
    return {
        "system": {
            "platform": os.name,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent if os.path.exists('/') else 0
        },
        "app": {
            "version": "1.0.0",
            "startup_time": datetime.now().isoformat(),
            "total_users": len(auth_manager.default_users)
        }
    }