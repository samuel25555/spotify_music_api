#!/bin/bash
# 设置日志自动清理的cron任务

echo "设置日志自动清理任务..."

# 获取项目路径
PROJECT_DIR="/www/wwwroot/api.music171.com"
SCRIPT_PATH="$PROJECT_DIR/scripts/clean_logs.py"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

# 创建cron任务
CRON_JOB="0 2 * * * $VENV_PYTHON $SCRIPT_PATH --days 7 >> /var/log/music-api-cleanup.log 2>&1"

# 检查cron任务是否已存在
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "日志清理任务已存在"
else
    # 添加cron任务
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "已添加日志清理任务: 每天凌晨2点执行"
fi

# 显示当前的cron任务
echo "当前的cron任务:"
crontab -l | grep music

echo "完成！"