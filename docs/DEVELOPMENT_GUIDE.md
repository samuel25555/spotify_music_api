# 🚀 开发流程与最佳实践指南

## 📋 开发环境配置

### 1. 本地开发环境搭建
```bash
# 克隆项目
git clone git@github.com:samuel25555/spotify_music_api.git
cd spotify_music_api

# 创建虚拟环境
uv venv --python 3.12
source .venv/bin/activate

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要配置
```

### 2. Docker开发环境
```bash
# 启动完整开发环境
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api
```

## 🔄 开发工作流

### 1. 功能开发流程
```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 进行开发
# 编写代码...

# 3. 运行测试
uv run pytest tests/

# 4. 代码检查
uv run black app/
uv run isort app/
uv run flake8 app/

# 5. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 6. 推送分支
git push origin feature/new-feature

# 7. 创建Pull Request
```

### 2. 热重载开发
```bash
# 启动开发服务器（自动重载）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动Celery Worker（开发模式）
uv run celery -A app.celery_app worker --loglevel=debug
```

### 3. API测试
```bash
# 健康检查
curl http://localhost:8000/health

# API文档
open http://localhost:8000/docs

# 测试搜索
curl "http://localhost:8000/api/spotify/search?q=test"
```

## 📂 项目结构说明

```
music-downloader-api/
├── app/                    # 主应用目录
│   ├── api/               # API路由模块
│   │   ├── spotify.py     # Spotify相关API
│   │   ├── download.py    # 下载功能API
│   │   ├── playlists.py   # 歌单管理API
│   │   └── ...
│   ├── core/              # 核心配置
│   ├── database/          # 数据库相关
│   ├── services/          # 业务逻辑服务
│   ├── tasks/             # Celery异步任务
│   └── utils/             # 工具函数
├── frontend/              # 前端文件
│   ├── js/               # JavaScript文件
│   ├── css/              # 样式文件
│   └── index.html        # 主页面
├── docs/                  # 项目文档
├── tests/                 # 测试文件
├── deploy_scripts/        # 部署脚本
└── docker-compose.yml     # Docker配置
```

## 🎯 核心模块开发指南

### 1. API路由开发
```python
# app/api/example.py
from fastapi import APIRouter, HTTPException, Depends
from app.database.connection import get_db

router = APIRouter(prefix="/api/example", tags=["Example"])

@router.get("/")
async def get_examples(db: Session = Depends(get_db)):
    """获取示例列表"""
    try:
        # 业务逻辑
        return {"data": examples}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. 服务层开发
```python
# app/services/example_service.py
class ExampleService:
    def __init__(self):
        self.cache = {}
    
    async def process_data(self, data: dict) -> dict:
        """处理数据的业务逻辑"""
        # 实现具体逻辑
        return processed_data
```

### 3. 异步任务开发
```python
# app/tasks/example_tasks.py
from app.celery_app import app

@app.task(bind=True)
def example_task(self, data):
    """示例异步任务"""
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'progress': 50, 'status': '处理中...'}
        )
        
        # 执行任务逻辑
        result = process_data(data)
        
        return {'status': 'completed', 'result': result}
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise
```

### 4. 数据模型开发
```python
# app/database/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ExampleModel(Base):
    __tablename__ = "examples"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 🧪 测试指南

### 1. 单元测试
```python
# tests/test_example.py
import pytest
from app.services.example_service import ExampleService

@pytest.fixture
def example_service():
    return ExampleService()

def test_process_data(example_service):
    """测试数据处理功能"""
    data = {"key": "value"}
    result = example_service.process_data(data)
    assert result["status"] == "success"
```

### 2. API测试
```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### 3. 运行测试
```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_api.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=app tests/
```

## 🔧 调试技巧

### 1. 日志配置
```python
import logging

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug("调试信息")
```

### 2. 断点调试
```python
# 使用pdb调试
import pdb; pdb.set_trace()

# 或者使用ipdb（更友好）
import ipdb; ipdb.set_trace()
```

### 3. 性能分析
```python
import time
import functools

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} 执行时间: {end - start:.2f}秒")
        return result
    return wrapper

@timer
def slow_function():
    # 耗时操作
    pass
```

## 📦 依赖管理

### 1. 添加新依赖
```bash
# 添加运行时依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 添加可选依赖
uv add --optional package-name
```

### 2. 锁定依赖版本
```bash
# 生成锁文件
uv lock

# 从锁文件安装
uv sync --locked
```

## 🚀 部署流程

### 1. 本地测试部署
```bash
# 构建Docker镜像
docker build -t music-api .

# 运行容器
docker run -p 8000:8000 music-api
```

### 2. 生产部署
```bash
# 推送代码
git push origin main

# 服务器部署
ssh root@api.music171.com
cd /www/wwwroot/api.music171.com
git pull origin main

# 重启服务
# 在宝塔面板重启Python项目
```

## 🛡️ 代码质量保证

### 1. 代码格式化
```bash
# 自动格式化
uv run black app/
uv run isort app/

# 检查格式
uv run black --check app/
uv run flake8 app/
```

### 2. 类型检查
```bash
# 使用mypy进行类型检查
uv run mypy app/
```

### 3. 安全检查
```bash
# 检查安全漏洞
uv run bandit -r app/

# 检查依赖安全性
uv run safety check
```

## 📊 监控和日志

### 1. 应用监控
```python
# 添加性能监控
from time import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    process_time = time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### 2. 错误追踪
```python
# 配置错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

## 🎯 性能优化建议

### 1. 数据库优化
- 添加适当的索引
- 使用连接池
- 实现查询缓存

### 2. API优化
- 实现响应缓存
- 使用异步处理
- 添加请求限流

### 3. 前端优化
- 启用Gzip压缩
- 使用CDN加速
- 实现懒加载

---

这份开发指南涵盖了项目开发的各个方面，遵循这些最佳实践可以确保代码质量和开发效率。