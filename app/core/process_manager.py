"""
进程管理器 - 类似宝塔面板的进程管理
自动启动和管理所有必要的服务进程
"""
import os
import sys
import time
import signal
import subprocess
import threading
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ProcessStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"

@dataclass
class ProcessConfig:
    name: str
    command: str
    directory: str
    environment: Dict[str, str] = None
    auto_restart: bool = True
    max_restarts: int = 3
    restart_delay: int = 5
    log_file: str = None
    pid_file: str = None
    user: str = None
    priority: int = 999
    enabled: bool = True

@dataclass
class ProcessInfo:
    name: str
    status: ProcessStatus
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    log_file: str = None

class ProcessManager:
    def __init__(self, config_dir: str = "configs/processes"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.processes: Dict[str, ProcessConfig] = {}
        self.process_info: Dict[str, ProcessInfo] = {}
        self.process_handles: Dict[str, subprocess.Popen] = {}
        self.monitor_threads: Dict[str, threading.Thread] = {}
        
        self.running = False
        self.monitor_interval = 5  # 监控间隔（秒）
        
        # 创建日志目录
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 创建PID目录
        self.pid_dir = Path("pids")
        self.pid_dir.mkdir(exist_ok=True)
        
        self.load_default_configs()
    
    def load_default_configs(self):
        """加载默认的进程配置"""
        project_root = Path(__file__).parent.parent.parent
        
        # 主API服务
        self.add_process(ProcessConfig(
            name="api_server",
            command="python -m uvicorn app.main:app --host 0.0.0.0 --port 8000",
            directory=str(project_root),
            environment={"PYTHONPATH": str(project_root)},
            auto_restart=True,
            log_file=str(self.log_dir / "api_server.log"),
            pid_file=str(self.pid_dir / "api_server.pid"),
            priority=1
        ))
        
        # Celery Worker
        self.add_process(ProcessConfig(
            name="celery_worker",
            command="python -m celery -A app.celery_app worker --loglevel=info --concurrency=4 --queues=batch,download,default",
            directory=str(project_root),
            environment={"PYTHONPATH": str(project_root)},
            auto_restart=True,
            log_file=str(self.log_dir / "celery_worker.log"),
            pid_file=str(self.pid_dir / "celery_worker.pid"),
            priority=2
        ))
        
        # Celery Beat (定时任务调度器)
        self.add_process(ProcessConfig(
            name="celery_beat",
            command="python -m celery -A app.celery_app beat --loglevel=info",
            directory=str(project_root),
            environment={"PYTHONPATH": str(project_root)},
            auto_restart=True,
            log_file=str(self.log_dir / "celery_beat.log"),
            pid_file=str(self.pid_dir / "celery_beat.pid"),
            priority=3
        ))
        
        # Celery Flower (可选的监控界面)
        self.add_process(ProcessConfig(
            name="celery_flower",
            command="python -m celery -A app.celery_app flower --port=5555 --basic_auth=admin:admin123",
            directory=str(project_root),
            environment={"PYTHONPATH": str(project_root)},
            auto_restart=True,
            log_file=str(self.log_dir / "celery_flower.log"),
            pid_file=str(self.pid_dir / "celery_flower.pid"),
            priority=4,
            enabled=False  # 默认不启用，可通过配置开启
        ))
    
    def add_process(self, config: ProcessConfig):
        """添加进程配置"""
        self.processes[config.name] = config
        self.process_info[config.name] = ProcessInfo(
            name=config.name,
            status=ProcessStatus.STOPPED,
            log_file=config.log_file
        )
    
    def start_process(self, name: str) -> bool:
        """启动单个进程"""
        if name not in self.processes:
            logger.error(f"进程配置不存在: {name}")
            return False
        
        config = self.processes[name]
        info = self.process_info[name]
        
        if not config.enabled:
            logger.info(f"进程已禁用: {name}")
            return False
        
        if info.status == ProcessStatus.RUNNING:
            logger.warning(f"进程已在运行: {name}")
            return True
        
        try:
            info.status = ProcessStatus.STARTING
            logger.info(f"启动进程: {name}")
            
            # 准备环境变量
            env = os.environ.copy()
            if config.environment:
                env.update(config.environment)
            
            # 准备日志文件
            log_file = None
            if config.log_file:
                log_file = open(config.log_file, 'a', encoding='utf-8')
            
            # 启动进程
            process = subprocess.Popen(
                config.command.split(),
                cwd=config.directory,
                env=env,
                stdout=log_file or subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            self.process_handles[name] = process
            info.pid = process.pid
            info.status = ProcessStatus.RUNNING
            info.start_time = datetime.now()
            
            # 写入PID文件
            if config.pid_file:
                with open(config.pid_file, 'w') as f:
                    f.write(str(process.pid))
            
            # 启动监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_process,
                args=(name,),
                daemon=True
            )
            monitor_thread.start()
            self.monitor_threads[name] = monitor_thread
            
            logger.info(f"进程启动成功: {name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"启动进程失败: {name}, 错误: {e}")
            info.status = ProcessStatus.FAILED
            return False
    
    def stop_process(self, name: str, force: bool = False) -> bool:
        """停止单个进程"""
        if name not in self.process_info:
            logger.error(f"进程不存在: {name}")
            return False
        
        info = self.process_info[name]
        
        if info.status != ProcessStatus.RUNNING:
            logger.warning(f"进程未运行: {name}")
            return True
        
        try:
            info.status = ProcessStatus.STOPPING
            logger.info(f"停止进程: {name}")
            
            process = self.process_handles.get(name)
            if process:
                if force:
                    # 强制终止
                    if os.name == 'nt':
                        process.terminate()
                    else:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    # 优雅关闭
                    if os.name == 'nt':
                        process.terminate()
                    else:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    
                    # 等待进程结束
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"进程 {name} 未在10秒内结束，强制终止")
                        if os.name == 'nt':
                            process.kill()
                        else:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                
                del self.process_handles[name]
            
            info.status = ProcessStatus.STOPPED
            info.pid = None
            
            # 删除PID文件
            config = self.processes[name]
            if config.pid_file and os.path.exists(config.pid_file):
                os.remove(config.pid_file)
            
            logger.info(f"进程停止成功: {name}")
            return True
            
        except Exception as e:
            logger.error(f"停止进程失败: {name}, 错误: {e}")
            return False
    
    def restart_process(self, name: str) -> bool:
        """重启进程"""
        logger.info(f"重启进程: {name}")
        self.stop_process(name)
        time.sleep(2)  # 等待进程完全停止
        return self.start_process(name)
    
    def _monitor_process(self, name: str):
        """监控单个进程"""
        config = self.processes[name]
        info = self.process_info[name]
        
        while self.running and name in self.process_handles:
            try:
                process = self.process_handles[name]
                
                # 检查进程是否还在运行
                if process.poll() is not None:
                    # 进程已退出
                    info.status = ProcessStatus.FAILED
                    info.pid = None
                    
                    logger.warning(f"进程意外退出: {name} (退出码: {process.returncode})")
                    
                    # 自动重启
                    if config.auto_restart and info.restart_count < config.max_restarts:
                        info.restart_count += 1
                        info.last_restart = datetime.now()
                        
                        logger.info(f"自动重启进程: {name} (第{info.restart_count}次)")
                        time.sleep(config.restart_delay)
                        
                        if self.start_process(name):
                            continue
                    else:
                        logger.error(f"进程重启次数超限或禁用自动重启: {name}")
                        break
                
                # 更新进程资源使用情况
                try:
                    import psutil
                    ps_process = psutil.Process(process.pid)
                    info.cpu_percent = ps_process.cpu_percent()
                    info.memory_mb = ps_process.memory_info().rss / 1024 / 1024
                except (ImportError, psutil.NoSuchProcess):
                    pass
                
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"监控进程出错: {name}, 错误: {e}")
                time.sleep(self.monitor_interval)
    
    def start_all(self):
        """启动所有进程"""
        logger.info("启动所有进程...")
        self.running = True
        
        # 按优先级排序启动
        sorted_processes = sorted(
            self.processes.items(),
            key=lambda x: x[1].priority
        )
        
        for name, config in sorted_processes:
            if config.enabled:
                self.start_process(name)
                time.sleep(2)  # 间隔启动，避免资源竞争
    
    def stop_all(self, force: bool = False):
        """停止所有进程"""
        logger.info("停止所有进程...")
        self.running = False
        
        # 按优先级逆序停止
        sorted_processes = sorted(
            self.processes.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )
        
        for name, _ in sorted_processes:
            self.stop_process(name, force)
    
    def get_status(self) -> Dict[str, dict]:
        """获取所有进程状态"""
        status = {}
        for name, info in self.process_info.items():
            status[name] = asdict(info)
            status[name]['status'] = info.status.value
            # 转换datetime为字符串
            if info.start_time:
                status[name]['start_time'] = info.start_time.isoformat()
            if info.last_restart:
                status[name]['last_restart'] = info.last_restart.isoformat()
        
        return status
    
    def save_config(self, filename: str = "processes.json"):
        """保存进程配置到文件"""
        config_file = self.config_dir / filename
        config_data = {}
        
        for name, config in self.processes.items():
            config_data[name] = asdict(config)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"进程配置已保存: {config_file}")
    
    def load_config(self, filename: str = "processes.json"):
        """从文件加载进程配置"""
        config_file = self.config_dir / filename
        
        if not config_file.exists():
            logger.warning(f"配置文件不存在: {config_file}")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for name, config_dict in config_data.items():
                config = ProcessConfig(**config_dict)
                self.add_process(config)
            
            logger.info(f"进程配置已加载: {config_file}")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {config_file}, 错误: {e}")
    
    def enable_process(self, name: str):
        """启用进程"""
        if name in self.processes:
            self.processes[name].enabled = True
            logger.info(f"进程已启用: {name}")
    
    def disable_process(self, name: str):
        """禁用进程"""
        if name in self.processes:
            self.processes[name].enabled = False
            self.stop_process(name)
            logger.info(f"进程已禁用: {name}")

# 全局进程管理器实例
process_manager = ProcessManager()