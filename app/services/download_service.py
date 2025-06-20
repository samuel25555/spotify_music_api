import yt_dlp
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC
import requests
from datetime import datetime

class DownloadService:
    def __init__(self, download_path: str = None):
        self.download_path = Path(download_path or os.getenv("DOWNLOAD_PATH", "./downloads"))
        self.download_path.mkdir(exist_ok=True)
        # 延迟初始化 FFmpeg 以加快启动速度
        self.has_ffmpeg = False
        self.ffmpeg_command = None
        print("✅ 下载服务初始化完成")
    
    def _setup_ffmpeg(self):
        """设置 ffmpeg 环境"""
        import subprocess
        
        self.has_ffmpeg = False
        self.ffmpeg_command = os.getenv("FFMPEG_COMMAND", "ffmpeg")
        
        # 检测 FFmpeg 是否可用
        try:
            # 尝试使用环境变量中配置的命令
            if self.ffmpeg_command.startswith("uv run"):
                # 对于 uv run ffmpeg，切换到项目根目录执行
                result = subprocess.run(
                    self.ffmpeg_command.split() + ['-version'], 
                    capture_output=True, 
                    timeout=5, 
                    cwd=str(self.download_path.parent)
                )
            else:
                # 对于普通命令，直接执行
                result = subprocess.run(
                    [self.ffmpeg_command, '-version'], 
                    capture_output=True, 
                    timeout=5
                )
            
            if result.returncode == 0:
                self.has_ffmpeg = True
                print(f"✅ 使用 FFmpeg: {self.ffmpeg_command}")
            else:
                print(f"❌ FFmpeg 命令失败: {self.ffmpeg_command}")
                
        except Exception as e:
            print(f"❌ FFmpeg 检测失败: {e}")
            # 如果配置的命令失败，尝试系统 ffmpeg
            try:
                import shutil
                system_ffmpeg = shutil.which('ffmpeg')
                if system_ffmpeg:
                    self.ffmpeg_command = system_ffmpeg
                    self.has_ffmpeg = True
                    print(f"✅ 使用系统 FFmpeg: {system_ffmpeg}")
            except:
                pass
    
    def get_ydl_opts(self, format: str = "mp3", quality: str = "320k") -> Dict:
        """获取yt-dlp配置"""
        postprocessors = []
        
        # 暂时禁用 FFmpeg 转换，直接下载高质量原始音频格式
        # WebM 是优秀的音频格式，质量高且兼容性好
        print(f"📁 下载格式: 高质量原始音频 (WebM/M4A)")
        
        ydl_opts = {
            'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best[height<=?720]',
            'outtmpl': str(self.download_path / '%(artist)s - %(title)s.%(ext)s'),
            'postprocessors': postprocessors,
            'extract_flat': False,
            'writethumbnail': True,
            'writeinfojson': False,
            'prefer_free_formats': True,
        }
        
        # FFmpeg 已禁用，不需要设置
        # 直接下载原始音频格式，无需后处理
            
        return ydl_opts
    
    def get_stream_url(self, youtube_url: str) -> Dict:
        """获取 YouTube 直接播放链接（无需下载）"""
        ydl_opts = {
            'quiet': True,
            'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio[protocol!=hls]/best[height<=480]',
            'extract_flat': False,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(youtube_url, download=False)
                
                # 获取直接播放链接
                formats = info.get('formats', [])
                audio_url = None
                
                # 优先选择浏览器兼容的音频格式
                preferred_codecs = ['opus', 'aac', 'mp3', 'vorbis']
                
                # 首先寻找纯音频格式
                for codec in preferred_codecs:
                    for fmt in formats:
                        if (fmt.get('acodec', '').startswith(codec) and 
                            fmt.get('vcodec') == 'none' and 
                            fmt.get('protocol') != 'hls' and
                            fmt.get('url')):
                            audio_url = fmt.get('url')
                            print(f"🎵 选择音频格式: {fmt.get('ext', 'unknown')} - {codec}")
                            break
                    if audio_url:
                        break
                
                # 如果没找到合适的纯音频，尝试低质量视频（通常是音频）
                if not audio_url:
                    for fmt in formats:
                        if (fmt.get('height', 1000) <= 360 and 
                            fmt.get('protocol') != 'hls' and
                            fmt.get('url')):
                            audio_url = fmt.get('url')
                            print(f"🎵 使用低质量视频: {fmt.get('ext', 'unknown')}")
                            break
                
                # 最后的备选方案
                if not audio_url and formats:
                    for fmt in formats:
                        if fmt.get('url') and fmt.get('protocol') != 'hls':
                            audio_url = fmt.get('url')
                            print(f"🎵 备选格式: {fmt.get('ext', 'unknown')}")
                            break
                
                return {
                    'success': True,
                    'stream_url': audio_url,
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'thumbnail': info.get('thumbnail')
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def search_youtube(self, query: str, limit: int = 5) -> List[Dict]:
        """在YouTube上搜索歌曲"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                search_results = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                results = []
                
                for entry in search_results.get('entries', []):
                    results.append({
                        'id': entry.get('id'),
                        'title': entry.get('title'),
                        'uploader': entry.get('uploader'),
                        'duration': entry.get('duration'),
                        'view_count': entry.get('view_count'),
                        'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        'thumbnail': entry.get('thumbnail')
                    })
                
                return results
            except Exception as e:
                raise Exception(f"YouTube search failed: {str(e)}")
    
    def download_from_youtube(self, url: str, song_info: Dict = None, format: str = "mp3", quality: str = "320k") -> Dict:
        """从YouTube下载音频"""
        ydl_opts = self.get_ydl_opts(format, quality)
        
        # 生成自动文件名
        if song_info:
            # 直接使用 WebM 格式（高质量原始音频）
            file_ext = "webm"
            
            # 生成哈希文件名
            auto_filename = self.generate_filename(song_info, file_ext)
            ydl_opts['outtmpl'] = str(self.download_path / auto_filename.replace(f'.{file_ext}', '.%(ext)s'))
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # 获取视频信息
                info = ydl.extract_info(url, download=False)
                
                # 下载文件
                ydl.download([url])
                
                # 确定输出文件路径
                if song_info:
                    # 使用 WebM 格式的哈希文件名
                    file_ext = "webm"
                    hash_filename = self.generate_filename(song_info, file_ext)
                    base_path = self.download_path / hash_filename.replace(f'.{file_ext}', '')
                    
                    # 直接使用 WebM 格式，尝试找到实际下载的文件
                    audio_exts = ['webm', 'm4a', 'opus', 'aac']
                    video_exts = ['mp4', 'mkv']
                    
                    file_path = None
                    # 先尝试音频格式
                    for ext in audio_exts:
                        potential_path = base_path.with_suffix(f'.{ext}')
                        if potential_path.exists():
                            file_path = potential_path
                            break
                    
                    # 如果没找到音频格式，再尝试视频格式（但内容可能是音频）
                    if not file_path:
                        for ext in video_exts:
                            potential_path = base_path.with_suffix(f'.{ext}')
                            if potential_path.exists():
                                file_path = potential_path
                                break
                                
                    if not file_path:
                        file_path = base_path.with_suffix('.webm')  # 默认
                else:
                    # 没有歌曲信息时，使用随机文件名
                    random_filename = self.generate_filename(None, "webm")
                    file_path = self.download_path / random_filename
                
                # 添加元数据
                if song_info and file_path.exists():
                    self.add_metadata(str(file_path), song_info)
                
                return {
                    'success': True,
                    'file_path': str(file_path),
                    'file_size': file_path.stat().st_size if file_path.exists() else 0,
                    'youtube_id': info.get('id'),
                    'title': info.get('title'),
                    'uploader': info.get('uploader'),
                    'duration': info.get('duration')
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def generate_filename(self, song_info: Dict = None, file_extension: str = "webm") -> str:
        """生成自动文件名"""
        import uuid
        import hashlib
        
        if song_info and song_info.get('spotify_id'):
            # 与API保持一致的hash生成方式
            hash_source = f"{song_info.get('spotify_id', '')}_{song_info.get('name', '')}_{song_info.get('artist', '')}"
            file_hash = hashlib.md5(hash_source.encode('utf-8')).hexdigest()
            filename = file_hash
        elif song_info:
            # 没有spotify_id时的备用方式
            song_data = f"{song_info.get('name', '')}-{song_info.get('artist', '')}"
            hash_obj = hashlib.md5(song_data.encode('utf-8'))
            filename = hash_obj.hexdigest()
        else:
            # 使用UUID生成唯一文件名
            filename = str(uuid.uuid4()).replace('-', '')
        
        return f"{filename}.{file_extension}"
    
    def clean_filename(self, filename: str) -> str:
        """清理文件名中的非法字符（保留用于兼容性）"""
        return re.sub(r'[<>:"/\\|?*]', '', filename).strip()
    
    def add_metadata(self, file_path: str, song_info: Dict):
        """为MP3文件添加元数据"""
        try:
            if not file_path.endswith('.mp3'):
                return
            
            # 加载或创建ID3标签
            try:
                audio = MP3(file_path, ID3=ID3)
            except:
                audio = MP3(file_path)
                audio.add_tags()
            
            # 添加基本标签
            audio.tags.add(TIT2(encoding=3, text=song_info.get('name', '')))
            audio.tags.add(TPE1(encoding=3, text=song_info.get('artist', '')))
            audio.tags.add(TALB(encoding=3, text=song_info.get('album', '')))
            
            if song_info.get('year'):
                audio.tags.add(TDRC(encoding=3, text=str(song_info['year'])))
            
            if song_info.get('track_number'):
                audio.tags.add(TRCK(encoding=3, text=str(song_info['track_number'])))
            
            # 下载并添加专辑封面
            if song_info.get('album_art'):
                try:
                    response = requests.get(song_info['album_art'], timeout=10)
                    if response.status_code == 200:
                        audio.tags.add(APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,
                            desc='Cover',
                            data=response.content
                        ))
                except:
                    pass
            
            audio.save()
            
        except Exception as e:
            print(f"Failed to add metadata: {str(e)}")
    
    async def download_song(self, song_info: Dict, format: str = "mp3", quality: str = "320k") -> Dict:
        """下载单首歌曲"""
        # 构建搜索查询
        query = f"{song_info.get('artist', '')} {song_info.get('name', '')}"
        
        try:
            # 搜索YouTube
            search_results = self.search_youtube(query, limit=3)
            
            if not search_results:
                return {
                    'success': False,
                    'error': 'No YouTube results found'
                }
            
            # 尝试下载第一个结果
            best_match = search_results[0]
            result = self.download_from_youtube(
                best_match['url'], 
                song_info, 
                format, 
                quality
            )
            
            result['youtube_info'] = best_match
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def download_playlist(self, playlist_info: Dict, format: str = "mp3", quality: str = "320k") -> Dict:
        """下载播放列表"""
        results = {
            'success': True,
            'total_songs': len(playlist_info.get('tracks', [])),
            'completed': 0,
            'failed': 0,
            'downloads': [],
            'errors': []
        }
        
        for track in playlist_info.get('tracks', []):
            try:
                download_result = await self.download_song(track, format, quality)
                
                if download_result['success']:
                    results['completed'] += 1
                    results['downloads'].append({
                        'song': track['name'],
                        'artist': track['artist'],
                        'file_path': download_result.get('file_path')
                    })
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'song': track['name'],
                        'artist': track['artist'],
                        'error': download_result.get('error')
                    })
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'song': track.get('name', 'Unknown'),
                    'artist': track.get('artist', 'Unknown'),
                    'error': str(e)
                })
        
        results['success'] = results['failed'] == 0
        return results