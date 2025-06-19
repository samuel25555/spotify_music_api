# Laravel 集成指南

## 🎯 概述

这个Music Downloader API专为Laravel后端设计，提供简单的RESTful接口来下载Spotify音乐。

## 🚀 快速开始

### 1. 启动API服务

```bash
cd music-downloader-api
uv sync
uv run python start.py
```

服务启动后可访问：
- API文档: http://localhost:8000/docs
- Web管理: http://localhost:8000

### 2. Laravel HTTP客户端调用

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class MusicDownloaderService
{
    private $apiBase;
    
    public function __construct()
    {
        $this->apiBase = config('services.music_downloader.url', 'http://localhost:8000/api');
    }
    
    /**
     * 下载单首歌曲
     */
    public function downloadSong(string $spotifyUrl, array $options = [])
    {
        $payload = array_merge([
            'url' => $spotifyUrl,
            'format' => 'mp3',
            'quality' => '320k',
            'callback_url' => route('music.download.complete')
        ], $options);
        
        try {
            $response = Http::timeout(30)->post($this->apiBase . '/download', $payload);
            
            if ($response->successful()) {
                return $response->json();
            }
            
            throw new \Exception('API request failed: ' . $response->body());
            
        } catch (\Exception $e) {
            Log::error('Music download failed', [
                'url' => $spotifyUrl,
                'error' => $e->getMessage()
            ]);
            
            throw $e;
        }
    }
    
    /**
     * 下载播放列表
     */
    public function downloadPlaylist(string $spotifyUrl, array $options = [])
    {
        $payload = array_merge([
            'url' => $spotifyUrl,
            'format' => 'mp3',
            'quality' => '320k',
            'callback_url' => route('music.playlist.complete')
        ], $options);
        
        $response = Http::timeout(30)->post($this->apiBase . '/download-playlist', $payload);
        
        return $response->json();
    }
    
    /**
     * 检查下载状态
     */
    public function getDownloadStatus(string $taskId)
    {
        $response = Http::get($this->apiBase . "/status/{$taskId}");
        
        return $response->json();
    }
    
    /**
     * 获取歌曲列表
     */
    public function getSongs(int $page = 1, int $perPage = 50, array $filters = [])
    {
        $params = array_merge([
            'page' => $page,
            'per_page' => $perPage
        ], $filters);
        
        $response = Http::get($this->apiBase . '/songs', $params);
        
        return $response->json();
    }
    
    /**
     * 获取统计信息
     */
    public function getStats()
    {
        $response = Http::get($this->apiBase . '/stats');
        
        return $response->json();
    }
    
    /**
     * 搜索YouTube
     */
    public function searchYoutube(string $query, int $limit = 10)
    {
        $response = Http::post($this->apiBase . '/search-youtube', [
            'query' => $query,
            'limit' => $limit
        ]);
        
        return $response->json();
    }
}
```

### 3. Laravel控制器示例

```php
<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\MusicDownloaderService;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class MusicController extends Controller
{
    protected $musicService;
    
    public function __construct(MusicDownloaderService $musicService)
    {
        $this->musicService = $musicService;
    }
    
    /**
     * 下载音乐
     */
    public function download(Request $request): JsonResponse
    {
        $request->validate([
            'url' => 'required|url',
            'format' => 'sometimes|in:mp3,flac,m4a',
            'quality' => 'sometimes|in:128k,320k,best'
        ]);
        
        try {
            $result = $this->musicService->downloadSong(
                $request->url,
                $request->only(['format', 'quality'])
            );
            
            // 保存任务到本地数据库
            \App\Models\DownloadTask::create([
                'task_id' => $result['task_id'],
                'user_id' => auth()->id(),
                'spotify_url' => $request->url,
                'status' => $result['status']
            ]);
            
            return response()->json([
                'success' => true,
                'data' => $result
            ]);
            
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => $e->getMessage()
            ], 500);
        }
    }
    
    /**
     * 检查下载状态
     */
    public function status(string $taskId): JsonResponse
    {
        try {
            $status = $this->musicService->getDownloadStatus($taskId);
            
            // 更新本地数据库状态
            $task = \App\Models\DownloadTask::where('task_id', $taskId)->first();
            if ($task) {
                $task->update(['status' => $status['status']]);
            }
            
            return response()->json([
                'success' => true,
                'data' => $status
            ]);
            
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => $e->getMessage()
            ], 500);
        }
    }
    
    /**
     * 下载完成回调
     */
    public function downloadComplete(Request $request): JsonResponse
    {
        // 处理下载完成的回调
        $taskId = $request->input('task_id');
        $status = $request->input('status');
        
        $task = \App\Models\DownloadTask::where('task_id', $taskId)->first();
        if ($task) {
            $task->update([
                'status' => $status,
                'completed_at' => now()
            ]);
            
            // 触发事件或队列任务
            event(new \App\Events\MusicDownloadCompleted($task));
        }
        
        return response()->json(['success' => true]);
    }
    
    /**
     * 获取歌曲列表
     */
    public function songs(Request $request): JsonResponse
    {
        $songs = $this->musicService->getSongs(
            $request->get('page', 1),
            $request->get('per_page', 20)
        );
        
        return response()->json($songs);
    }
}
```

### 4. 路由配置

```php
// routes/api.php

use App\Http\Controllers\Api\MusicController;

Route::prefix('music')->group(function () {
    Route::post('download', [MusicController::class, 'download']);
    Route::post('download-playlist', [MusicController::class, 'download']);
    Route::get('status/{taskId}', [MusicController::class, 'status']);
    Route::get('songs', [MusicController::class, 'songs']);
    
    // 回调路由
    Route::post('download-complete', [MusicController::class, 'downloadComplete'])
         ->name('music.download.complete');
    Route::post('playlist-complete', [MusicController::class, 'downloadComplete'])
         ->name('music.playlist.complete');
});
```

### 5. 配置文件

```php
// config/services.php

return [
    // ... 其他服务配置
    
    'music_downloader' => [
        'url' => env('MUSIC_DOWNLOADER_URL', 'http://localhost:8000/api'),
        'timeout' => env('MUSIC_DOWNLOADER_TIMEOUT', 30),
    ],
];
```

```env
# .env 文件
MUSIC_DOWNLOADER_URL=http://localhost:8000/api
MUSIC_DOWNLOADER_TIMEOUT=30
```

### 6. 数据库迁移

```php
// database/migrations/xxxx_create_download_tasks_table.php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateDownloadTasksTable extends Migration
{
    public function up()
    {
        Schema::create('download_tasks', function (Blueprint $table) {
            $table->id();
            $table->string('task_id')->unique();
            $table->foreignId('user_id')->constrained();
            $table->text('spotify_url');
            $table->string('status')->default('pending');
            $table->string('format')->default('mp3');
            $table->string('quality')->default('320k');
            $table->json('metadata')->nullable();
            $table->timestamp('completed_at')->nullable();
            $table->timestamps();
            
            $table->index(['user_id', 'status']);
        });
    }
    
    public function down()
    {
        Schema::dropIfExists('download_tasks');
    }
}
```

## 📱 前端调用示例

### Vue.js 示例

```javascript
// 音乐下载组件
export default {
    data() {
        return {
            downloadUrl: '',
            downloading: false,
            downloadResult: null
        }
    },
    methods: {
        async downloadMusic() {
            this.downloading = true;
            
            try {
                const response = await this.$http.post('/api/music/download', {
                    url: this.downloadUrl,
                    format: 'mp3',
                    quality: '320k'
                });
                
                this.downloadResult = response.data;
                this.monitorProgress(response.data.data.task_id);
                
            } catch (error) {
                this.$message.error('下载失败: ' + error.message);
            } finally {
                this.downloading = false;
            }
        },
        
        async monitorProgress(taskId) {
            const checkStatus = async () => {
                try {
                    const response = await this.$http.get(`/api/music/status/${taskId}`);
                    const status = response.data.data;
                    
                    if (status.status === 'processing') {
                        setTimeout(checkStatus, 2000);
                    } else if (status.status === 'completed') {
                        this.$message.success('下载完成!');
                    } else if (status.status === 'failed') {
                        this.$message.error('下载失败');
                    }
                } catch (error) {
                    console.error('检查状态失败:', error);
                }
            };
            
            checkStatus();
        }
    }
}
```

## 🔧 高级功能

### 批量下载管理

```php
class BatchDownloadService
{
    public function batchDownload(array $urls)
    {
        $tasks = [];
        
        foreach ($urls as $url) {
            $result = app(MusicDownloaderService::class)->downloadSong($url);
            $tasks[] = $result['task_id'];
        }
        
        return $tasks;
    }
    
    public function getBatchStatus(array $taskIds)
    {
        $musicService = app(MusicDownloaderService::class);
        $statuses = [];
        
        foreach ($taskIds as $taskId) {
            $statuses[$taskId] = $musicService->getDownloadStatus($taskId);
        }
        
        return $statuses;
    }
}
```

### 队列处理

```php
// App\Jobs\ProcessMusicDownload

class ProcessMusicDownload implements ShouldQueue
{
    protected $spotifyUrl;
    protected $userId;
    
    public function handle()
    {
        $musicService = app(MusicDownloaderService::class);
        
        $result = $musicService->downloadSong($this->spotifyUrl);
        
        // 保存到数据库
        DownloadTask::create([
            'task_id' => $result['task_id'],
            'user_id' => $this->userId,
            'spotify_url' => $this->spotifyUrl,
            'status' => $result['status']
        ]);
    }
}
```

## 🛡️ 安全考虑

1. **API限流**: 在Laravel中添加API限流
2. **认证**: 确保只有授权用户可以调用下载接口
3. **URL验证**: 验证Spotify URL格式
4. **文件安全**: 定期清理下载文件

## 📊 监控和日志

```php
// 在服务中添加监控
class MusicDownloaderService
{
    public function downloadSong(string $spotifyUrl, array $options = [])
    {
        Log::info('Music download started', ['url' => $spotifyUrl]);
        
        try {
            $result = // ... 下载逻辑
            
            Log::info('Music download successful', [
                'url' => $spotifyUrl,
                'task_id' => $result['task_id']
            ]);
            
            return $result;
            
        } catch (\Exception $e) {
            Log::error('Music download failed', [
                'url' => $spotifyUrl,
                'error' => $e->getMessage()
            ]);
            
            throw $e;
        }
    }
}
```

这样你就可以在Laravel项目中完美集成音乐下载功能了！