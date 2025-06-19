# Music Downloader API - 安装指南

## 基本安装

项目已经可以正常运行，但为了获得最佳体验，建议安装以下依赖：

## 可选依赖

### FFmpeg (推荐)

为了支持 MP3 格式转换，需要安装 FFmpeg：

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

#### Windows
1. 下载 FFmpeg: https://ffmpeg.org/download.html
2. 解压到 `C:\ffmpeg`
3. 将 `C:\ffmpeg\bin` 添加到系统 PATH

#### macOS
```bash
brew install ffmpeg
```

### 没有 FFmpeg 的情况

如果没有安装 FFmpeg，系统会下载原始音频格式（通常是 WebM），这些文件仍然可以在大多数音乐播放器中播放。

## 功能对比

| 功能 | 有 FFmpeg | 没有 FFmpeg |
|------|----------|------------|
| 下载音乐 | ✅ | ✅ |
| MP3 格式 | ✅ | ❌ |
| WebM 格式 | ✅ | ✅ |
| 元数据标签 | ✅ | ✅ (部分) |
| 专辑封面 | ✅ | ❌ |

## 启动服务

```bash
uv run python start.py
```

## 访问界面

- Web 界面: http://localhost:8000
- API 文档: http://localhost:8000/docs