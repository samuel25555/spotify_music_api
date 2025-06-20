#!/usr/bin/env python3
"""
重置数据库脚本
清理所有数据，重新开始
"""
import os
import sys
import shutil
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.database.connection import engine, create_tables
from app.database.models import Base


def reset_database(confirm: bool = False):
    """重置数据库"""
    if not confirm:
        response = input("⚠️  警告：此操作将删除所有数据！是否继续？(yes/no): ")
        if response.lower() != 'yes':
            print("操作已取消")
            return
    
    print("\n开始重置数据库...")
    
    # 检查数据库配置
    if not settings.DATABASE_URL:
        print("❌ 错误：DATABASE_URL 未配置")
        print("请检查 .env 文件是否存在并包含 DATABASE_URL 配置")
        return
    
    # 1. 删除数据库文件（如果是SQLite）
    if settings.DATABASE_URL.startswith('sqlite'):
        db_file = settings.DATABASE_URL.replace('sqlite:///', '')
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"✅ 已删除数据库文件: {db_file}")
    
    # 2. 删除所有表
    try:
        Base.metadata.drop_all(bind=engine)
        print("✅ 已删除所有数据表")
    except Exception as e:
        print(f"⚠️  删除表时出错: {e}")
    
    # 3. 重新创建表
    create_tables()
    print("✅ 已重新创建数据表")
    
    print("\n数据库重置完成！")


def clean_downloads(confirm: bool = False):
    """清理下载文件"""
    download_path = settings.DOWNLOAD_PATH
    
    if not os.path.exists(download_path):
        print(f"下载目录不存在: {download_path}")
        return
    
    if not confirm:
        response = input(f"⚠️  是否清理下载目录 {download_path}？(yes/no): ")
        if response.lower() != 'yes':
            print("跳过清理下载目录")
            return
    
    # 统计文件
    files = list(Path(download_path).glob('*'))
    file_count = len(files)
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    
    print(f"\n准备删除 {file_count} 个文件，总大小: {total_size / 1024 / 1024:.2f} MB")
    
    # 清空目录
    for file in files:
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    
    print("✅ 下载目录已清空")


def clean_logs(confirm: bool = False):
    """清理日志文件"""
    log_dir = os.path.dirname(settings.LOG_FILE)
    
    if not os.path.exists(log_dir):
        print(f"日志目录不存在: {log_dir}")
        return
    
    if not confirm:
        response = input(f"⚠️  是否清理日志目录 {log_dir}？(yes/no): ")
        if response.lower() != 'yes':
            print("跳过清理日志目录")
            return
    
    # 清理日志文件
    for file in Path(log_dir).glob('*.log*'):
        file.unlink()
    
    print("✅ 日志文件已清理")


def clean_cache(confirm: bool = False):
    """清理缓存"""
    cache_dirs = [
        '.cache',
        '__pycache__',
        '.pytest_cache',
    ]
    
    if not confirm:
        response = input("⚠️  是否清理缓存目录？(yes/no): ")
        if response.lower() != 'yes':
            print("跳过清理缓存")
            return
    
    # 清理缓存目录
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"✅ 已删除缓存目录: {cache_dir}")
    
    # 清理Python缓存
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            shutil.rmtree(os.path.join(root, '__pycache__'))
    
    print("✅ 缓存清理完成")


def main():
    parser = argparse.ArgumentParser(description='重置数据库和清理数据')
    parser.add_argument('--all', action='store_true', help='清理所有数据（数据库、下载、日志、缓存）')
    parser.add_argument('--database', action='store_true', help='仅重置数据库')
    parser.add_argument('--downloads', action='store_true', help='仅清理下载文件')
    parser.add_argument('--logs', action='store_true', help='仅清理日志文件')
    parser.add_argument('--cache', action='store_true', help='仅清理缓存')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过确认提示')
    
    args = parser.parse_args()
    
    # 如果没有指定任何选项，显示帮助
    if not any([args.all, args.database, args.downloads, args.logs, args.cache]):
        parser.print_help()
        print("\n示例:")
        print("  python reset_database.py --all          # 清理所有数据")
        print("  python reset_database.py --database     # 仅重置数据库")
        print("  python reset_database.py --all --yes    # 清理所有数据（无需确认）")
        return
    
    print("🧹 Music Downloader 数据清理工具")
    print("=" * 50)
    
    if args.all or args.database:
        reset_database(confirm=args.yes)
    
    if args.all or args.downloads:
        clean_downloads(confirm=args.yes)
    
    if args.all or args.logs:
        clean_logs(confirm=args.yes)
    
    if args.all or args.cache:
        clean_cache(confirm=args.yes)
    
    print("\n✨ 清理完成！")


if __name__ == "__main__":
    main()