"""
身份验证和授权模块
"""
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# JWT配置
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24小时

# HTTP Bearer认证
security = HTTPBearer()

class AuthManager:
    """身份验证管理器"""
    
    def __init__(self):
        # 默认管理员账户
        self.default_users = {
            "admin": {
                "username": "admin",
                "password_hash": self.hash_password("admin123"),
                "role": "admin",
                "created_at": datetime.now().isoformat()
            }
        }
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256((password + settings.SECRET_KEY).encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self.hash_password(password) == password_hash
    
    def create_access_token(self, username: str, role: str = "user") -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": username,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> dict:
        """验证令牌"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="无效的令牌")
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="令牌已过期")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="无效的令牌")
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """验证用户"""
        user = self.default_users.get(username)
        if not user:
            return None
        if not self.verify_password(password, user["password_hash"]):
            return None
        return user
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """根据用户名获取用户"""
        return self.default_users.get(username)

# 全局认证管理器实例
auth_manager = AuthManager()

# 依赖注入函数
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """获取当前用户（需要登录）"""
    try:
        payload = auth_manager.verify_token(credentials.credentials)
        username = payload.get("sub")
        user = auth_manager.get_user_by_username(username)
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="身份验证失败")

async def get_current_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """获取当前管理员用户"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user

# 可选的身份验证（不强制要求登录）
async def get_current_user_optional(request: Request) -> Optional[dict]:
    """可选的用户身份验证"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = auth_manager.verify_token(token)
        username = payload.get("sub")
        return auth_manager.get_user_by_username(username)
    except:
        return None

# 权限检查装饰器
def require_auth(func):
    """需要身份验证的装饰器"""
    async def wrapper(*args, **kwargs):
        # 这里可以添加额外的权限检查逻辑
        return await func(*args, **kwargs)
    return wrapper