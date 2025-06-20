"""
进程管理API - 类似宝塔面板的进程管理接口
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging

from app.core.process_manager import process_manager, ProcessConfig, ProcessStatus

router = APIRouter(prefix="/api/processes", tags=["Process Manager"])
logger = logging.getLogger(__name__)

class ProcessConfigRequest(BaseModel):
    name: str
    command: str
    directory: str
    environment: Optional[Dict[str, str]] = None
    auto_restart: bool = True
    max_restarts: int = 3
    restart_delay: int = 5
    log_file: Optional[str] = None
    pid_file: Optional[str] = None
    user: Optional[str] = None
    priority: int = 999
    enabled: bool = True

class ProcessActionRequest(BaseModel):
    names: List[str]
    force: bool = False

@router.get("/status")
async def get_processes_status():
    """获取所有进程状态"""
    try:
        status = process_manager.get_status()
        return {
            "status": "success",
            "data": status,
            "total": len(status)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程状态失败: {str(e)}")

@router.get("/status/{process_name}")
async def get_process_status(process_name: str):
    """获取单个进程状态"""
    try:
        if process_name not in process_manager.process_info:
            raise HTTPException(status_code=404, detail=f"进程不存在: {process_name}")
        
        status = process_manager.get_status()
        return {
            "status": "success",
            "data": status[process_name]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程状态失败: {str(e)}")

@router.post("/start")
async def start_processes(request: ProcessActionRequest, background_tasks: BackgroundTasks):
    """启动进程"""
    try:
        results = {}
        
        if not request.names:
            # 启动所有进程
            background_tasks.add_task(process_manager.start_all)
            return {
                "status": "success",
                "message": "已开始启动所有进程",
                "data": results
            }
        
        # 启动指定进程
        for name in request.names:
            if name not in process_manager.processes:
                results[name] = {"success": False, "message": f"进程配置不存在: {name}"}
                continue
            
            success = process_manager.start_process(name)
            results[name] = {
                "success": success,
                "message": "启动成功" if success else "启动失败"
            }
        
        return {
            "status": "success",
            "message": "进程启动操作完成",
            "data": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动进程失败: {str(e)}")

@router.post("/stop")
async def stop_processes(request: ProcessActionRequest):
    """停止进程"""
    try:
        results = {}
        
        if not request.names:
            # 停止所有进程
            process_manager.stop_all(request.force)
            return {
                "status": "success",
                "message": "已停止所有进程",
                "data": results
            }
        
        # 停止指定进程
        for name in request.names:
            if name not in process_manager.process_info:
                results[name] = {"success": False, "message": f"进程不存在: {name}"}
                continue
            
            success = process_manager.stop_process(name, request.force)
            results[name] = {
                "success": success,
                "message": "停止成功" if success else "停止失败"
            }
        
        return {
            "status": "success", 
            "message": "进程停止操作完成",
            "data": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止进程失败: {str(e)}")

@router.post("/restart")
async def restart_processes(request: ProcessActionRequest):
    """重启进程"""
    try:
        results = {}
        
        # 重启指定进程
        for name in request.names:
            if name not in process_manager.process_info:
                results[name] = {"success": False, "message": f"进程不存在: {name}"}
                continue
            
            success = process_manager.restart_process(name)
            results[name] = {
                "success": success,
                "message": "重启成功" if success else "重启失败"
            }
        
        return {
            "status": "success",
            "message": "进程重启操作完成",
            "data": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启进程失败: {str(e)}")

@router.put("/enable/{process_name}")
async def enable_process(process_name: str):
    """启用进程"""
    try:
        if process_name not in process_manager.processes:
            raise HTTPException(status_code=404, detail=f"进程不存在: {process_name}")
        
        process_manager.enable_process(process_name)
        
        return {
            "status": "success",
            "message": f"进程 {process_name} 已启用"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启用进程失败: {str(e)}")

@router.put("/disable/{process_name}")
async def disable_process(process_name: str):
    """禁用进程"""
    try:
        if process_name not in process_manager.processes:
            raise HTTPException(status_code=404, detail=f"进程不存在: {process_name}")
        
        process_manager.disable_process(process_name)
        
        return {
            "status": "success",
            "message": f"进程 {process_name} 已禁用"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"禁用进程失败: {str(e)}")

@router.post("/config")
async def add_process_config(config: ProcessConfigRequest):
    """添加进程配置"""
    try:
        process_config = ProcessConfig(
            name=config.name,
            command=config.command,
            directory=config.directory,
            environment=config.environment,
            auto_restart=config.auto_restart,
            max_restarts=config.max_restarts,
            restart_delay=config.restart_delay,
            log_file=config.log_file,
            pid_file=config.pid_file,
            user=config.user,
            priority=config.priority,
            enabled=config.enabled
        )
        
        process_manager.add_process(process_config)
        process_manager.save_config()
        
        return {
            "status": "success",
            "message": f"进程配置已添加: {config.name}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加进程配置失败: {str(e)}")

@router.get("/config")
async def get_processes_config():
    """获取所有进程配置"""
    try:
        configs = {}
        for name, config in process_manager.processes.items():
            configs[name] = {
                "name": config.name,
                "command": config.command,
                "directory": config.directory,
                "environment": config.environment,
                "auto_restart": config.auto_restart,
                "max_restarts": config.max_restarts,
                "restart_delay": config.restart_delay,
                "log_file": config.log_file,
                "pid_file": config.pid_file,
                "user": config.user,
                "priority": config.priority,
                "enabled": config.enabled
            }
        
        return {
            "status": "success",
            "data": configs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程配置失败: {str(e)}")

@router.delete("/config/{process_name}")
async def delete_process_config(process_name: str):
    """删除进程配置"""
    try:
        if process_name not in process_manager.processes:
            raise HTTPException(status_code=404, detail=f"进程不存在: {process_name}")
        
        # 先停止进程
        process_manager.stop_process(process_name)
        
        # 删除配置
        del process_manager.processes[process_name]
        del process_manager.process_info[process_name]
        
        process_manager.save_config()
        
        return {
            "status": "success",
            "message": f"进程配置已删除: {process_name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除进程配置失败: {str(e)}")

@router.get("/logs/{process_name}")
async def get_process_logs(process_name: str, lines: int = 100):
    """获取进程日志"""
    try:
        if process_name not in process_manager.processes:
            raise HTTPException(status_code=404, detail=f"进程不存在: {process_name}")
        
        config = process_manager.processes[process_name]
        if not config.log_file:
            raise HTTPException(status_code=404, detail=f"进程 {process_name} 未配置日志文件")
        
        import os
        if not os.path.exists(config.log_file):
            return {
                "status": "success",
                "data": {
                    "logs": [],
                    "total_lines": 0
                }
            }
        
        # 读取日志文件的最后N行
        with open(config.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            log_lines = f.readlines()
        
        # 获取最后指定行数
        recent_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
        
        return {
            "status": "success",
            "data": {
                "logs": [line.rstrip() for line in recent_lines],
                "total_lines": len(log_lines),
                "showing_lines": len(recent_lines)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程日志失败: {str(e)}")

@router.post("/save-config")
async def save_config():
    """保存进程配置到文件"""
    try:
        process_manager.save_config()
        return {
            "status": "success",
            "message": "进程配置已保存"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")

@router.post("/load-config")
async def load_config():
    """从文件加载进程配置"""
    try:
        process_manager.load_config()
        return {
            "status": "success",
            "message": "进程配置已加载"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载配置失败: {str(e)}")