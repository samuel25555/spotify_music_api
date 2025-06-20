# 🎵 Music Downloader API

现代化的音乐下载和管理系统，支持Spotify搜索、多类型搜索、歌单管理等功能。

## ✨ 特性

- 🔍 **智能搜索**: 支持歌曲、歌单、专辑、艺人多类型搜索
- 🎵 **Spotify集成**: 无缝集成Spotify API，获取丰富的音乐信息
- 📱 **响应式前端**: 模块化Vue.js前端，支持移动端
- 🗄️ **MySQL数据库**: 持久化存储音乐信息和用户数据
- ⚡ **Redis缓存**: 高性能缓存提升搜索速度
- 📥 **下载管理**: 支持多种音频格式和质量选择
- 🎼 **歌单管理**: 创建、编辑、分享个人歌单
- 🌍 **多语言支持**: 智能识别歌曲语言和国家信息

## 🏗️ 架构

```
music-downloader-api/
├── 📁 app/                 # 后端应用
│   ├── 📁 api/            # API路由
│   ├── 📁 core/           # 核心配置
│   ├── 📁 database/       # 数据库模型和连接
│   └── 📁 services/       # 业务逻辑服务
├── 📁 frontend/           # 前端应用
│   ├── 📁 js/            # JavaScript模块
│   │   ├── 📁 components/ # Vue组件
│   │   ├── 📁 services/   # API服务
│   │   └── 📁 utils/      # 工具函数
│   ├── 📁 css/           # 样式文件
│   └── 📄 index.html     # 主页面
├── 📁 database/          # 数据库脚本
├── 📄 docker-compose.yml # Docker配置
├── 📄 requirements.txt   # Python依赖
└── 📄 README.md          # 项目文档
```

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- Python 3.8+
- Git

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd music-downloader-api
   ```

2. **启动项目**
   ```bash
   ./start.sh
   ```

3. **访问应用**
   - 前端页面: http://localhost:8000
   - API文档: http://localhost:8000/docs

### 手动启动

如果自动脚本无法使用：

1. **启动数据库**
   ```bash
   docker-compose up -d mysql redis
   ```

2. **安装Python依赖**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **启动后端服务**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 🔧 配置

### 环境变量

复制 `.env.example` 到 `.env` 并修改配置：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=music_user
DB_PASSWORD=music_pass

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=musicredis2024

# Spotify API
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

## 📖 API文档

### 搜索接口

- `GET /api/spotify/search` - 基础搜索
- `GET /api/spotify/search-multi` - 多类型搜索
- `GET /api/spotify/search-playlists` - 歌单搜索
- `POST /api/spotify/parse` - Spotify URL解析

### 下载接口

- `POST /api/download` - 创建下载任务
- `GET /api/tasks` - 获取下载任务列表
- `DELETE /api/tasks/{id}` - 取消下载任务

### 歌单接口

- `GET /api/playlists` - 获取歌单列表
- `POST /api/playlists` - 创建新歌单
- `PUT /api/playlists/{id}` - 更新歌单
- `DELETE /api/playlists/{id}` - 删除歌单

详细API文档请访问: http://localhost:8000/docs

## 🚀 启动项目

```bash
# 快速启动
./start.sh

# 停止项目
./stop.sh
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

⭐ 如果这个项目对你有帮助，请给它一个 Star！