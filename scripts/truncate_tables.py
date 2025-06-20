#!/usr/bin/env python3
"""
清空所有表数据（保留表结构）
适用于MySQL/PostgreSQL等数据库
"""
import os
import sys
import argparse
from sqlalchemy import text

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.database.connection import engine
from app.database.models import Song, Playlist, DownloadTask, MusicLibrary, PlaylistSong


def truncate_all_tables(confirm: bool = False):
    """清空所有表数据"""
    if not confirm:
        response = input("⚠️  警告：此操作将清空所有表数据！是否继续？(yes/no): ")
        if response.lower() != 'yes':
            print("操作已取消")
            return
    
    print("\n开始清空表数据...")
    
    # 定义要清空的表（顺序很重要，先清空有外键关系的表）
    tables = [
        'playlist_songs',      # 关联表先清空
        'download_tasks',      # 下载任务
        'music_library',       # 音乐库
        'songs',              # 歌曲表
        'playlists',          # 播放列表
    ]
    
    try:
        with engine.begin() as conn:
            # 对于MySQL，临时禁用外键检查
            if 'mysql' in str(engine.url):
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # 清空每个表
            for table in tables:
                try:
                    if 'mysql' in str(engine.url):
                        conn.execute(text(f"TRUNCATE TABLE {table}"))
                    else:
                        # PostgreSQL 或 SQLite
                        conn.execute(text(f"DELETE FROM {table}"))
                    print(f"✅ 已清空表: {table}")
                except Exception as e:
                    print(f"⚠️  清空表 {table} 时出错: {e}")
            
            # 恢复外键检查
            if 'mysql' in str(engine.url):
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            # 对于PostgreSQL，重置序列
            if 'postgresql' in str(engine.url):
                for table in tables:
                    try:
                        conn.execute(text(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1"))
                    except:
                        pass
        
        print("\n✅ 所有表数据已清空！")
        print("📝 表结构保持不变，可以立即使用")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("请检查数据库连接配置")


def show_table_counts():
    """显示各表的记录数"""
    print("\n当前表记录数：")
    print("-" * 40)
    
    tables = {
        'songs': '歌曲',
        'playlists': '播放列表', 
        'playlist_songs': '播放列表歌曲',
        'download_tasks': '下载任务',
        'music_library': '音乐库'
    }
    
    try:
        with engine.connect() as conn:
            for table, name in tables.items():
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"{name} ({table}): {count} 条记录")
    except Exception as e:
        print(f"查询失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='清空数据库表数据')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过确认提示')
    parser.add_argument('--show', '-s', action='store_true', help='仅显示表记录数')
    
    args = parser.parse_args()
    
    print("🗄️  Music Downloader 数据库清空工具")
    print("=" * 50)
    
    if args.show:
        show_table_counts()
    else:
        # 先显示当前状态
        show_table_counts()
        
        # 执行清空
        truncate_all_tables(confirm=args.yes)
        
        # 显示清空后的状态
        if not args.yes:
            print("\n清空后的状态：")
            show_table_counts()
    
    print("\n💡 提示：如需清理下载文件和日志，请运行：")
    print("   python scripts/reset_database_simple.py --downloads --logs")


if __name__ == "__main__":
    main()