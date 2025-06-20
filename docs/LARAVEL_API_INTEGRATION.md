# 🎵 Laravel 音乐API集成指南

## 📋 概述

本文档详细说明了如何在Laravel项目中集成音乐下载API的歌单接口，包括获取歌单详情、播放URL、封面图片等完整功能。

## 🔗 核心API接口

### 1. 歌单详情接口

**接口地址：** `GET /api/playlists/{playlist_id}`  
**完整URL：** `https://yourdomain.com/api/playlists/{playlist_id}`

## 📊 完整字段说明

### 🎼 歌单级别字段

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `id` | int | 歌单ID | `1` |
| `name` | string | 歌单名称 | `"我的音乐收藏"` |
| `description` | string\|null | 歌单描述 | `"精选音乐合集"` |
| `category` | string\|null | 歌单分类 | `"流行音乐"` |
| `song_count` | int | 歌曲总数 | `25` |
| `created_at` | datetime | 创建时间 | `"2024-01-15T10:30:00"` |
| `updated_at` | datetime | 更新时间 | `"2024-01-20T15:45:00"` |

### 🎵 歌曲级别字段 (songs数组中的每个对象)

#### 基础信息字段
| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `id` | int | 歌曲数据库ID | `123` |
| `spotify_id` | string | Spotify唯一ID | `"4iV5W9uYEdYUVa79Axb7Rh"` |
| `title` | string | 歌曲标题 | `"Never Gonna Give You Up"` |
| `artist` | string | 艺术家名称 | `"Rick Astley"` |
| `album` | string\|null | 专辑名称 | `"Whenever You Need Somebody"` |

#### 媒体资源字段 (重点)
| 字段名 | 类型 | 说明 | 用途 |
|--------|------|------|------|
| `album_art_url` | string\|null | **专辑封面URL** | 显示封面图片 |
| `preview_url` | string\|null | **30秒试听URL** | Spotify提供的试听 |
| `file_url` | string\|null | **完整播放URL** | 服务器下载文件的完整播放链接 |
| `spotify_url` | string\|null | Spotify完整链接 | 跳转到Spotify |

#### 歌曲属性字段
| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `duration` | int\|null | 时长(秒) | `213` |
| `year` | int\|null | 发行年份 | `1987` |
| `popularity` | int\|null | 流行度(0-100) | `85` |
| `country` | string\|null | 国家/地区 | `"美国"` |
| `language` | string\|null | 语言 | `"english"` |

#### 状态字段
| 字段名 | 类型 | 说明 | 用途 |
|--------|------|------|------|
| `is_downloaded` | bool | **是否已下载** | 判断是否有本地文件 |
| `file_path` | string\|null | 服务器本地路径 | 服务器文件位置 |
| `position` | int | 歌单中位置 | `0` |
| `added_at` | datetime\|null | 添加时间 | `"2024-01-15T10:30:00"` |

## 💻 Laravel集成代码

### 1. 创建API服务类

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class MusicApiService
{
    private $baseUrl;
    
    public function __construct()
    {
        $this->baseUrl = config('music.api_base_url', 'https://yourdomain.com');
    }
    
    /**
     * 获取歌单详情
     * 
     * @param int $playlistId
     * @return array|null
     */
    public function getPlaylistDetail($playlistId)
    {
        try {
            $response = Http::timeout(30)->get("{$this->baseUrl}/api/playlists/{$playlistId}");
            
            if ($response->successful()) {
                return $response->json();
            }
            
            Log::error("获取歌单失败", [
                'playlist_id' => $playlistId,
                'status' => $response->status(),
                'response' => $response->body()
            ]);
            
            return null;
        } catch (\Exception $e) {
            Log::error("歌单API请求异常", [
                'playlist_id' => $playlistId,
                'error' => $e->getMessage()
            ]);
            
            return null;
        }
    }
    
    /**
     * 获取格式化的歌单数据
     * 
     * @param int $playlistId
     * @return array
     */
    public function getFormattedPlaylist($playlistId)
    {
        $data = $this->getPlaylistDetail($playlistId);
        
        if (!$data || !isset($data['data'])) {
            return [
                'success' => false,
                'message' => '歌单不存在或API错误'
            ];
        }
        
        $playlist = $data['data'];
        
        return [
            'success' => true,
            'playlist' => [
                'id' => $playlist['id'],
                'name' => $playlist['name'],
                'description' => $playlist['description'] ?? '',
                'category' => $playlist['category'] ?? '',
                'song_count' => $playlist['song_count'],
                'created_at' => $playlist['created_at'],
                'updated_at' => $playlist['updated_at'],
            ],
            'songs' => $this->formatSongs($playlist['songs'] ?? [])
        ];
    }
    
    /**
     * 格式化歌曲数据
     * 
     * @param array $songs
     * @return array
     */
    private function formatSongs($songs)
    {
        return collect($songs)->map(function ($song) {
            return [
                // 基础信息
                'id' => $song['id'],
                'spotify_id' => $song['spotify_id'],
                'title' => $song['title'],
                'artist' => $song['artist'],
                'album' => $song['album'],
                
                // 媒体资源 (重点)
                'cover_image' => $song['album_art_url'],          // 封面图片
                'preview_url' => $song['preview_url'],            // 试听URL
                'play_url' => $song['file_url'],                  // 完整播放URL
                'spotify_url' => $song['spotify_url'],            // Spotify链接
                
                // 播放控制
                'can_preview' => !empty($song['preview_url']),    // 是否可试听
                'can_play_full' => $song['is_downloaded'] && !empty($song['file_url']), // 是否可完整播放
                
                // 歌曲属性
                'duration' => $song['duration'],
                'duration_formatted' => $this->formatDuration($song['duration']),
                'year' => $song['year'],
                'popularity' => $song['popularity'],
                'country' => $song['country'],
                'language' => $song['language'],
                
                // 状态信息
                'position' => $song['position'],
                'is_downloaded' => $song['is_downloaded'],
                'added_at' => $song['added_at'],
                
                // 收藏库信息
                'library_info' => $song['library_info'] ?? null,
            ];
        })->toArray();
    }
    
    /**
     * 格式化播放时长
     * 
     * @param int|null $seconds
     * @return string
     */
    private function formatDuration($seconds)
    {
        if (!$seconds) return '未知';
        
        $minutes = floor($seconds / 60);
        $seconds = $seconds % 60;
        
        return sprintf('%d:%02d', $minutes, $seconds);
    }
}
```

### 2. 配置文件

创建 `config/music.php`：

```php
<?php

return [
    // 音乐API基础URL
    'api_base_url' => env('MUSIC_API_URL', 'https://yourdomain.com'),
    
    // 默认封面图片
    'default_cover' => '/images/default-album-cover.jpg',
    
    // 超时设置
    'timeout' => 30,
    
    // 缓存设置
    'cache_ttl' => 300, // 5分钟
];
```

在 `.env` 中添加：
```env
MUSIC_API_URL=https://yourdomain.com
```

### 3. 控制器使用示例

```php
<?php

namespace App\Http\Controllers;

use App\Services\MusicApiService;
use Illuminate\Http\Request;

class PlaylistController extends Controller
{
    private $musicApi;
    
    public function __construct(MusicApiService $musicApi)
    {
        $this->musicApi = $musicApi;
    }
    
    /**
     * 显示歌单详情页面
     */
    public function show($id)
    {
        $data = $this->musicApi->getFormattedPlaylist($id);
        
        if (!$data['success']) {
            abort(404, $data['message']);
        }
        
        return view('playlist.show', [
            'playlist' => $data['playlist'],
            'songs' => $data['songs']
        ]);
    }
    
    /**
     * API接口：获取歌单数据
     */
    public function api($id)
    {
        $data = $this->musicApi->getFormattedPlaylist($id);
        
        return response()->json($data);
    }
}
```

### 4. Blade模板示例

创建 `resources/views/playlist/show.blade.php`：

```blade
@extends('layouts.app')

@section('content')
<div class="container">
    <!-- 歌单信息 -->
    <div class="playlist-header mb-4">
        <h1>{{ $playlist['name'] }}</h1>
        @if($playlist['description'])
            <p class="text-muted">{{ $playlist['description'] }}</p>
        @endif
        <div class="playlist-meta">
            <span class="badge badge-primary">{{ $playlist['category'] ?? '未分类' }}</span>
            <span class="text-muted">{{ $playlist['song_count'] }} 首歌曲</span>
            <span class="text-muted">创建于 {{ \Carbon\Carbon::parse($playlist['created_at'])->format('Y-m-d') }}</span>
        </div>
    </div>
    
    <!-- 歌曲列表 -->
    <div class="songs-list">
        @foreach($songs as $song)
            <div class="song-item card mb-2" data-song-id="{{ $song['id'] }}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <!-- 封面图片 -->
                        <div class="col-md-1">
                            <img src="{{ $song['cover_image'] ?? config('music.default_cover') }}" 
                                 alt="封面" 
                                 class="img-thumbnail" 
                                 style="width: 50px; height: 50px; object-fit: cover;">
                        </div>
                        
                        <!-- 歌曲信息 -->
                        <div class="col-md-6">
                            <h6 class="mb-1">{{ $song['title'] }}</h6>
                            <p class="mb-1 text-muted">{{ $song['artist'] }}</p>
                            @if($song['album'])
                                <small class="text-muted">{{ $song['album'] }}</small>
                            @endif
                        </div>
                        
                        <!-- 播放控制 -->
                        <div class="col-md-3">
                            @if($song['can_play_full'])
                                <!-- 完整播放按钮 -->
                                <button class="btn btn-success btn-sm play-full" 
                                        data-url="{{ $song['play_url'] }}"
                                        title="播放完整版">
                                    <i class="fas fa-play"></i> 播放
                                </button>
                            @elseif($song['can_preview'])
                                <!-- 试听按钮 -->
                                <button class="btn btn-primary btn-sm play-preview" 
                                        data-url="{{ $song['preview_url'] }}"
                                        title="30秒试听">
                                    <i class="fas fa-headphones"></i> 试听
                                </button>
                            @else
                                <span class="text-muted">无法播放</span>
                            @endif
                            
                            @if($song['spotify_url'])
                                <a href="{{ $song['spotify_url'] }}" 
                                   target="_blank" 
                                   class="btn btn-outline-success btn-sm ml-1"
                                   title="在Spotify中打开">
                                    <i class="fab fa-spotify"></i>
                                </a>
                            @endif
                        </div>
                        
                        <!-- 歌曲属性 -->
                        <div class="col-md-2 text-right">
                            <small class="text-muted">{{ $song['duration_formatted'] }}</small>
                            @if($song['year'])
                                <br><small class="text-muted">{{ $song['year'] }}</small>
                            @endif
                            @if($song['is_downloaded'])
                                <br><span class="badge badge-success">已下载</span>
                            @endif
                        </div>
                    </div>
                </div>
            </div>
        @endforeach
    </div>
</div>

<!-- 音频播放器 -->
<audio id="audioPlayer" controls class="fixed-bottom p-3" style="width: 100%; display: none;">
    您的浏览器不支持音频播放。
</audio>
@endsection

@push('scripts')
<script>
document.addEventListener('DOMContentLoaded', function() {
    const audioPlayer = document.getElementById('audioPlayer');
    
    // 完整播放
    document.querySelectorAll('.play-full').forEach(button => {
        button.addEventListener('click', function() {
            const url = this.dataset.url;
            playAudio(url, '正在播放完整版');
        });
    });
    
    // 试听播放
    document.querySelectorAll('.play-preview').forEach(button => {
        button.addEventListener('click', function() {
            const url = this.dataset.url;
            playAudio(url, '正在试听 (30秒)');
        });
    });
    
    function playAudio(url, message) {
        if (!url) {
            alert('播放链接不可用');
            return;
        }
        
        audioPlayer.src = url;
        audioPlayer.style.display = 'block';
        audioPlayer.play().catch(error => {
            console.error('播放失败:', error);
            alert('播放失败，请检查网络连接');
        });
        
        // 显示播放状态
        console.log(message + ': ' + url);
    }
});
</script>
@endpush
```

### 5. 路由配置

在 `routes/web.php` 中添加：

```php
Route::get('/playlist/{id}', [PlaylistController::class, 'show'])->name('playlist.show');
Route::get('/api/playlist/{id}', [PlaylistController::class, 'api'])->name('playlist.api');
```

## 🎯 播放URL使用说明

### 🔊 三种播放方式

1. **完整播放** (`file_url`)
   - **条件**：`is_downloaded = true` 且 `file_url` 不为空
   - **格式**：`https://yourdomain.com/downloads/abc123.webm`
   - **用途**：完整歌曲播放，无时长限制

2. **试听播放** (`preview_url`)
   - **条件**：`preview_url` 不为空
   - **格式**：`https://p.scdn.co/mp3-preview/...`
   - **用途**：30秒试听，来自Spotify

3. **Spotify跳转** (`spotify_url`)
   - **格式**：`https://open.spotify.com/track/...`
   - **用途**：跳转到Spotify应用

### 📱 前端播放逻辑

```javascript
function getPlayUrl(song) {
    // 优先级：完整播放 > 试听 > Spotify
    if (song.is_downloaded && song.file_url) {
        return {
            url: song.file_url,
            type: 'full',
            duration: song.duration
        };
    } else if (song.preview_url) {
        return {
            url: song.preview_url,
            type: 'preview',
            duration: 30
        };
    } else if (song.spotify_url) {
        return {
            url: song.spotify_url,
            type: 'external',
            action: 'redirect'
        };
    }
    
    return null;
}
```

## 🛡️ 错误处理

### API响应格式

**成功响应：**
```json
{
  "data": {
    "id": 1,
    "name": "歌单名称",
    "songs": [...]
  },
  "status": "success"
}
```

**错误响应：**
```json
{
  "error": "歌单未找到",
  "status_code": 404
}
```

### Laravel错误处理

```php
public function handleApiError($response, $playlistId)
{
    if ($response->status() === 404) {
        throw new ModelNotFoundException("歌单 {$playlistId} 不存在");
    } elseif ($response->status() === 500) {
        throw new ServiceUnavailableHttpException(null, "音乐服务暂时不可用");
    } else {
        throw new HttpException($response->status(), "API请求失败");
    }
}
```

## 🚀 性能优化建议

1. **缓存歌单数据**
```php
$data = Cache::remember("playlist.{$id}", 300, function() use ($id) {
    return $this->musicApi->getFormattedPlaylist($id);
});
```

2. **异步加载封面图片**
```javascript
// 懒加载封面图片
<img data-src="{{ $song['cover_image'] }}" class="lazy-load">
```

3. **批量预加载**
```php
// 预加载多个歌单
$playlists = $this->musicApi->getMultiplePlaylists([1, 2, 3]);
```

## 📋 完整集成清单

- ✅ 歌单基础信息显示
- ✅ 歌曲列表展示  
- ✅ 封面图片显示
- ✅ 多种播放方式支持
- ✅ 播放状态判断
- ✅ 时长格式化
- ✅ 错误处理
- ✅ 缓存优化
- ✅ 响应式设计

通过以上集成，您的Laravel应用就可以完整使用音乐API的所有功能了！🎉