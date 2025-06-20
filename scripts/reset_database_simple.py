#!/usr/bin/env python3
"""
简化版数据库重置脚本
直接使用文件系统操作，不依赖复杂的配置
"""
import os
import sys
import shutil
import argparse
from pathlib import Path

def reset_database(db_path='data/music_downloader.db', confirm=False):
    """重置数据库"""
    if not confirm:
        response = input("⚠️  警告：此操作将删除所有数据！是否继续？(yes/no): ")
        if response.lower() != 'yes':
            print("操作已取消")
            return False
    
    print("\n开始重置数据库...")
    
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✅ 已删除数据库文件: {db_path}")
    else:
        print(f"ℹ️  数据库文件不存在: {db_path}")
    
    return True

def clean_downloads(download_dir='downloads', confirm=False):
    """清理下载文件"""
    if not os.path.exists(download_dir):
        print(f"ℹ️  下载目录不存在: {download_dir}")
        return
    
    if not confirm:
        response = input(f"⚠️  是否清理下载目录 {download_dir}？(yes/no): ")
        if response.lower() != 'yes':
            print("跳过清理下载目录")
            return
    
    # 统计文件
    files = list(Path(download_dir).glob('*'))
    file_count = len([f for f in files if f.name != '.gitkeep'])
    
    if file_count == 0:
        print("ℹ️  下载目录已经是空的")
        return
    
    print(f"\n准备删除 {file_count} 个文件")
    
    # 清空目录（保留.gitkeep）
    for file in files:
        if file.name != '.gitkeep':
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)
    
    print("✅ 下载目录已清空")

def clean_logs(log_dir='logs', confirm=False):
    """清理日志文件"""
    if not os.path.exists(log_dir):
        print(f"ℹ️  日志目录不存在: {log_dir}")
        return
    
    if not confirm:
        response = input(f"⚠️  是否清理日志目录 {log_dir}？(yes/no): ")
        if response.lower() != 'yes':
            print("跳过清理日志目录")
            return
    
    # 清理日志文件（保留.gitkeep）
    log_files = list(Path(log_dir).glob('*.log*'))
    if not log_files:
        print("ℹ️  没有日志文件需要清理")
        return
    
    for file in log_files:
        file.unlink()
    
    print(f"✅ 已清理 {len(log_files)} 个日志文件")

def clean_cache(confirm=False):
    """清理缓存"""
    cache_patterns = [
        '__pycache__',
        '.pytest_cache',
        '*.pyc',
        '.cache'
    ]
    
    if not confirm:
        response = input("⚠️  是否清理缓存文件？(yes/no): ")
        if response.lower() != 'yes':
            print("跳过清理缓存")
            return
    
    cleaned = 0
    # 清理Python缓存
    for root, dirs, files in os.walk('.'):
        # 跳过.venv目录
        if '.venv' in root:
            continue
            
        if '__pycache__' in dirs:
            cache_dir = os.path.join(root, '__pycache__')
            shutil.rmtree(cache_dir)
            cleaned += 1
    
    print(f"✅ 已清理 {cleaned} 个缓存目录")

def main():
    parser = argparse.ArgumentParser(description='重置数据库和清理数据（简化版）')
    parser.add_argument('--all', action='store_true', help='清理所有数据')
    parser.add_argument('--database', action='store_true', help='仅重置数据库')
    parser.add_argument('--downloads', action='store_true', help='仅清理下载文件')
    parser.add_argument('--logs', action='store_true', help='仅清理日志文件')
    parser.add_argument('--cache', action='store_true', help='仅清理缓存')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过确认提示')
    parser.add_argument('--db-path', default='data/music_downloader.db', help='数据库文件路径')
    parser.add_argument('--download-dir', default='downloads', help='下载目录路径')
    parser.add_argument('--log-dir', default='logs', help='日志目录路径')
    
    args = parser.parse_args()
    
    # 如果没有指定任何选项，显示帮助
    if not any([args.all, args.database, args.downloads, args.logs, args.cache]):
        parser.print_help()
        print("\n示例:")
        print("  python reset_database_simple.py --all          # 清理所有数据")
        print("  python reset_database_simple.py --database     # 仅重置数据库")
        print("  python reset_database_simple.py --all --yes    # 清理所有数据（无需确认）")
        return
    
    print("🧹 Music Downloader 数据清理工具（简化版）")
    print("=" * 50)
    
    try:
        if args.all or args.database:
            if reset_database(args.db_path, confirm=args.yes):
                print("✅ 数据库重置完成")
        
        if args.all or args.downloads:
            clean_downloads(args.download_dir, confirm=args.yes)
        
        if args.all or args.logs:
            clean_logs(args.log_dir, confirm=args.yes)
        
        if args.all or args.cache:
            clean_cache(confirm=args.yes)
        
        print("\n✨ 清理完成！")
        
        # 提示重启服务
        if args.all or args.database:
            print("\n💡 提示：数据库已重置，建议重启服务：")
            print("   systemctl restart music-api")
            print("   或: pm2 restart app")
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()