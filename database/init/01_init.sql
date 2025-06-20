-- 创建音乐下载器数据库表结构
USE music_downloader;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    spotify_token TEXT,
    preferences JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 歌曲表
CREATE TABLE IF NOT EXISTS songs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    spotify_id VARCHAR(100) UNIQUE,
    title VARCHAR(255) NOT NULL,
    artist VARCHAR(255) NOT NULL,
    album VARCHAR(255),
    album_art_url TEXT,
    preview_url TEXT,
    spotify_url TEXT,
    duration INT,
    year INT,
    country VARCHAR(50),
    region VARCHAR(50),
    language VARCHAR(50),
    genre VARCHAR(100),
    mood VARCHAR(50),
    tags TEXT,
    popularity INT DEFAULT 0,
    track_number INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_spotify_id (spotify_id),
    INDEX idx_title_artist (title, artist),
    INDEX idx_country (country),
    INDEX idx_language (language),
    INDEX idx_genre (genre),
    FULLTEXT idx_search (title, artist, album)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 歌单表
CREATE TABLE IF NOT EXISTS playlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image_url TEXT,
    category VARCHAR(100),
    country VARCHAR(50),
    language VARCHAR(50),
    mood VARCHAR(50),
    tags TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    total_tracks INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_category (category),
    INDEX idx_country (country),
    FULLTEXT idx_search (name, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 歌单歌曲关联表
CREATE TABLE IF NOT EXISTS playlist_songs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    playlist_id INT NOT NULL,
    song_id INT NOT NULL,
    position INT DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    UNIQUE KEY unique_playlist_song (playlist_id, song_id),
    INDEX idx_playlist_id (playlist_id),
    INDEX idx_song_id (song_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 下载任务表
CREATE TABLE IF NOT EXISTS download_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    song_id INT,
    url VARCHAR(500) NOT NULL,
    status ENUM('pending', 'downloading', 'completed', 'failed') DEFAULT 'pending',
    progress INT DEFAULT 0,
    file_path TEXT,
    error_message TEXT,
    format VARCHAR(20) DEFAULT 'mp3',
    quality VARCHAR(20) DEFAULT 'high',
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 搜索历史表
CREATE TABLE IF NOT EXISTS search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    query VARCHAR(255) NOT NULL,
    search_type VARCHAR(50),
    result_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_query (query),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户收藏表
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    song_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_song (user_id, song_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认用户
INSERT IGNORE INTO users (username, email) VALUES ('guest', 'guest@localhost');

-- 创建视图：热门歌曲
CREATE OR REPLACE VIEW popular_songs AS
SELECT 
    s.*,
    COUNT(ps.song_id) as playlist_count,
    COUNT(uf.song_id) as favorite_count,
    COUNT(dt.song_id) as download_count
FROM songs s
LEFT JOIN playlist_songs ps ON s.id = ps.song_id
LEFT JOIN user_favorites uf ON s.id = uf.song_id
LEFT JOIN download_tasks dt ON s.id = dt.song_id AND dt.status = 'completed'
GROUP BY s.id
ORDER BY (COUNT(ps.song_id) + COUNT(uf.song_id) + COUNT(dt.song_id)) DESC;