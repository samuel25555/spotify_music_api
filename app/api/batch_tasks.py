"""
批量任务管理API
处理异步任务的创建、查询、取消等操作
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from celery.result import AsyncResult
from app.celery_app import app as celery_app
# 尝试导入批量任务，如果失败则禁用相关功能
try:
    from app.tasks.batch_tasks import batch_import_to_library, batch_download_tracks
    BATCH_TASKS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 批量任务模块导入失败: {e}")
    BATCH_TASKS_AVAILABLE = False
    batch_import_to_library = None
    batch_download_tracks = None

router = APIRouter(prefix="/api/batch", tags=["Batch Tasks"])

class BatchImportRequest(BaseModel):
    items: List[str]  # 要导入的项目ID列表
    search_type: str  # track, playlist, album
    settings: Dict[str, Any]  # 导入设置

class BatchDownloadRequest(BaseModel):
    track_ids: List[str]
    download_settings: Dict[str, Any] = {}

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/import-library", response_model=TaskResponse)
async def start_batch_import(request: BatchImportRequest):
    """启动批量导入到收藏库的任务"""
    if not BATCH_TASKS_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量任务功能不可用，请启动Celery Worker")
        
    try:
        # 验证搜索类型
        if request.search_type not in ['track', 'playlist', 'album']:
            raise HTTPException(status_code=400, detail="不支持的搜索类型")
        
        # 启动异步任务
        task = batch_import_to_library.delay(
            request.items,
            request.settings,
            request.search_type
        )
        
        return TaskResponse(
            task_id=task.id,
            status="started",
            message=f"已启动批量导入任务，共 {len(request.items)} 项"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")

@router.post("/download-tracks", response_model=TaskResponse)
async def start_batch_download(request: BatchDownloadRequest):
    """启动批量下载任务"""
    if not BATCH_TASKS_AVAILABLE:
        raise HTTPException(status_code=503, detail="批量任务功能不可用，请启动Celery Worker")
        
    try:
        # 启动异步任务
        task = batch_download_tracks.delay(
            request.track_ids,
            request.download_settings
        )
        
        return TaskResponse(
            task_id=task.id,
            status="started",
            message=f"已启动批量下载任务，共 {len(request.track_ids)} 首歌曲"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动下载任务失败: {str(e)}")

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态和进度"""
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        response = TaskStatusResponse(
            task_id=task_id,
            status=result.status.lower()
        )
        
        if result.status == 'PENDING':
            response.progress = {'completed': 0, 'total': 0, 'message': '任务等待中'}
        elif result.status == 'PROGRESS':
            response.progress = result.result
        elif result.status == 'SUCCESS':
            response.result = result.result
            response.progress = {
                'completed': result.result.get('completed', 0),
                'total': result.result.get('total', 0),
                'message': '任务完成'
            }
        elif result.status == 'FAILURE':
            response.error = str(result.result)
            response.progress = {'completed': 0, 'total': 0, 'message': '任务失败'}
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        
        return {"message": f"任务 {task_id} 已取消"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@router.get("/active-tasks")
async def get_active_tasks():
    """获取所有活动任务"""
    try:
        # 获取活动任务
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        if not active_tasks:
            return {"active_tasks": []}
        
        # 格式化任务信息
        tasks = []
        for worker, task_list in active_tasks.items():
            for task in task_list:
                tasks.append({
                    "task_id": task["id"],
                    "name": task["name"],
                    "worker": worker,
                    "args": task.get("args", []),
                    "kwargs": task.get("kwargs", {})
                })
        
        return {"active_tasks": tasks}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取活动任务失败: {str(e)}")

@router.get("/task-history")
async def get_task_history(limit: int = 50):
    """获取任务历史记录"""
    try:
        # TODO: 实现任务历史记录存储和查询
        # 可以使用数据库存储任务历史，或者从Celery后端查询
        
        return {
            "message": "任务历史记录功能待实现",
            "tasks": []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务历史失败: {str(e)}")

@router.get("/worker-status")
async def get_worker_status():
    """获取Celery工作进程状态"""
    try:
        inspect = celery_app.control.inspect()
        
        # 获取工作进程统计信息
        stats = inspect.stats()
        active = inspect.active()
        reserved = inspect.reserved()
        
        return {
            "workers": stats,
            "active_tasks": active,
            "reserved_tasks": reserved
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作进程状态失败: {str(e)}")