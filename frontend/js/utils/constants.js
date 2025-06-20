// 应用常量定义

const CONSTANTS = {
    // API配置
    API_BASE_URL: '/api',
    
    // 搜索配置
    SEARCH_TYPES: {
        TRACKS: 'tracks',
        PLAYLISTS: 'playlists', 
        ALBUMS: 'albums',
        ARTISTS: 'artists'
    },
    
    // 下载状态
    DOWNLOAD_STATUS: {
        PENDING: 'pending',
        DOWNLOADING: 'downloading',
        COMPLETED: 'completed',
        FAILED: 'failed'
    },
    
    // 音频格式
    AUDIO_FORMATS: {
        MP3: 'mp3',
        FLAC: 'flac',
        OGG: 'ogg',
        M4A: 'm4a'
    },
    
    // 音频质量
    AUDIO_QUALITY: {
        LOW: 'low',
        MEDIUM: 'medium', 
        HIGH: 'high',
        LOSSLESS: 'lossless'
    },
    
    // 分页配置
    PAGINATION: {
        DEFAULT_PAGE_SIZE: 20,
        MAX_PAGE_SIZE: 100
    },
    
    // 缓存配置
    CACHE: {
        SEARCH_EXPIRE: 30 * 60 * 1000, // 30分钟
        IMAGE_EXPIRE: 60 * 60 * 1000,  // 1小时
        MAX_CACHE_SIZE: 100
    },
    
    // 通知类型
    NOTIFICATION_TYPES: {
        SUCCESS: 'success',
        ERROR: 'error',
        WARNING: 'warning',
        INFO: 'info'
    },
    
    // 国家选项
    COUNTRIES: [
        { code: 'korea', name: '韩国', flag: '🇰🇷' },
        { code: 'japan', name: '日本', flag: '🇯🇵' },
        { code: 'china', name: '中国', flag: '🇨🇳' },
        { code: 'taiwan', name: '台湾', flag: '🇹🇼' },
        { code: 'usa', name: '美国', flag: '🇺🇸' },
        { code: 'uk', name: '英国', flag: '🇬🇧' },
        { code: 'germany', name: '德国', flag: '🇩🇪' },
        { code: 'france', name: '法国', flag: '🇫🇷' }
    ],
    
    // 语言选项
    LANGUAGES: [
        { code: 'korean', name: '韩语' },
        { code: 'japanese', name: '日语' },
        { code: 'chinese', name: '中文' },
        { code: 'english', name: '英语' },
        { code: 'spanish', name: '西班牙语' },
        { code: 'french', name: '法语' },
        { code: 'german', name: '德语' }
    ],
    
    // 音乐类型
    GENRES: [
        'Pop', 'Rock', 'Hip Hop', 'R&B', 'Country', 
        'Electronic', 'Jazz', 'Classical', 'Folk', 
        'Reggae', 'Blues', 'Metal', 'Punk', 'Indie'
    ],
    
    // 心情标签
    MOODS: [
        { code: 'happy', name: '快乐', emoji: '😊' },
        { code: 'sad', name: '忧伤', emoji: '😢' },
        { code: 'energetic', name: '激昂', emoji: '⚡' },
        { code: 'romantic', name: '浪漫', emoji: '💕' },
        { code: 'chill', name: '放松', emoji: '😌' },
        { code: 'party', name: '派对', emoji: '🎉' },
        { code: 'study', name: '学习', emoji: '📚' },
        { code: 'workout', name: '运动', emoji: '💪' }
    ],
    
    // 歌单分类
    PLAYLIST_CATEGORIES: [
        '韩国流行', '日本动漫', '欧美经典', '中文流行',
        '电子音乐', '摇滚金属', '民谣轻音乐', '古典音乐',
        '嘻哈说唱', '爵士蓝调', '乡村民谣', '独立音乐'
    ],
    
    // 默认专辑封面
    DEFAULT_ALBUM_ART: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDIwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0xMDAgNjBDODkuMzkxMyA2MCA4MC44Njk2IDY4LjQyMTQgODAuODY5NiA3OC43NVY5MS44NzVDODAuODY5NiA5Mi45MTA1IDgxLjY5NTcgOTMuNzUgODIuNzE3NCA5My43NUg4NC41NjUyQzg1LjU4NyA5My43NSA4Ni40MTMgOTIuOTEwNSA4Ni40MTMgOTEuODc1Vjc4Ljc1Qzg2LjQxMyA3MS41MzI5IDkyLjQ1NjUgNjUuNjI1IDEwMCA2NS42MjVDMTA3LjU0MyA2NS42MjUgMTEzLjU4NyA3MS41MzI5IDExMy41ODcgNzguNzVWMTIxLjI1QzExMy41ODcgMTI4LjQ2NyAxMDcuNTQzIDEzNC4zNzUgMTAwIDEzNC4zNzVDOTIuNDU2NSAxMzQuMzc1IDg2LjQxMyAxMjguNDY3IDg2LjQxMyAxMjEuMjVWMTA4LjEyNUM4Ni40MTMgMTA3LjA4OSA4NS41ODcgMTA2LjI1IDg0LjU2NTIgMTA2LjI1SDgyLjcxNzRDODEuNjk1NyAxMDYuMjUgODAuODY5NiAxMDcuMDg5IDgwLjg2OTYgMTA4LjEyNVYxMjEuMjVDODAuODY5NiAxMzEuNTc5IDg5LjM5MTMgMTQwIDEwMCAxNDBDMTEwLjYwOSAxNDAgMTE5LjEzIDEzMS41NzkgMTE5LjEzIDEyMS4yNVY3OC43NUMxMTkuMTMgNjguNDIxNCAxMTAuNjA5IDYwIDEwMCA2MFoiIGZpbGw9IiM5Q0EzQUYiLz4KPGNpcmNsZSBjeD0iMTAwIiBjeT0iMTAwIiByPSI2MCIgc3Ryb2tlPSIjOUNBM0FGIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiLz4KPC9zdmc+',
    
    // 错误消息
    ERROR_MESSAGES: {
        NETWORK_ERROR: '网络连接失败，请检查网络设置',
        SEARCH_FAILED: '搜索失败，请稍后重试',
        DOWNLOAD_FAILED: '下载失败，请稍后重试',
        INVALID_URL: '无效的URL地址',
        FILE_TOO_LARGE: '文件太大，无法处理',
        UNSUPPORTED_FORMAT: '不支持的文件格式'
    }
};

// 导出常量
window.CONSTANTS = CONSTANTS;