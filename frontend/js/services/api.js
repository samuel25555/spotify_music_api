// API服务层

class ApiService {
    constructor() {
        // 从环境配置获取API基础URL
        this.baseURL = window.ENV_CONFIG?.API_BASE_URL || window.location.origin;
        this.cache = new Map();
        
        // 配置axios默认设置
        const timeout = window.ENV_CONFIG?.TIMEOUT?.REQUEST || 30000;
        axios.defaults.timeout = timeout;
        axios.defaults.headers.common['Content-Type'] = 'application/json';
        
        // 请求拦截器
        axios.interceptors.request.use(
            config => {
                // 添加loading状态
                if (!config.hideLoading) {
                    this.showLoading();
                }
                return config;
            },
            error => {
                this.hideLoading();
                return Promise.reject(error);
            }
        );
        
        // 响应拦截器
        axios.interceptors.response.use(
            response => {
                this.hideLoading();
                return response;
            },
            error => {
                this.hideLoading();
                return Promise.reject(error);
            }
        );
    }

    // 显示加载状态
    showLoading() {
        // 可以在这里触发全局加载状态
        window.dispatchEvent(new CustomEvent('api-loading', { detail: true }));
    }

    // 隐藏加载状态
    hideLoading() {
        window.dispatchEvent(new CustomEvent('api-loading', { detail: false }));
    }

    // 基础请求方法
    async request(url, options = {}) {
        const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;
        
        try {
            const response = await axios({
                url: fullUrl,
                method: 'GET',
                ...options
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    // GET请求
    async get(url, params = {}, useCache = false) {
        const cacheKey = `${url}_${JSON.stringify(params)}`;
        
        if (useCache && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < 5 * 60 * 1000) { // 5分钟缓存
                return cached.data;
            }
        }

        const data = await this.request(url, { params });
        
        if (useCache) {
            this.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            this.cleanCache();
        }
        
        return data;
    }

    // POST请求
    async post(url, data = {}) {
        return await this.request(url, {
            method: 'POST',
            data
        });
    }

    // PUT请求
    async put(url, data = {}) {
        return await this.request(url, {
            method: 'PUT',
            data
        });
    }

    // DELETE请求
    async delete(url) {
        return await this.request(url, {
            method: 'DELETE'
        });
    }

    // 清理缓存
    cleanCache() {
        if (this.cache.size > 100) {
            const entries = Array.from(this.cache.entries());
            entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
            const toDelete = entries.slice(0, entries.length - 100);
            toDelete.forEach(([key]) => this.cache.delete(key));
        }
    }

    // 清除所有缓存
    clearCache() {
        this.cache.clear();
    }

    // 错误处理
    handleError(error) {
        const message = error.response?.data?.detail || error.message || '请求失败';
        console.error('API Error:', error);
        return new Error(message);
    }

    // =============  Spotify API方法  =============

    // 搜索音乐
    async searchMusic(query, options = {}) {
        const params = {
            q: query,
            limit: options.limit || 20,
            country_filter: options.countryFilter,
            language_filter: options.languageFilter,
            deduplicate: options.deduplicate !== false,
            preview_only: options.previewOnly || false
        };
        
        return await this.get('/api/spotify/search', params, true);
    }

    // 多类型搜索
    async searchMultiType(query, types = ['track'], limit = 10) {
        const params = {
            q: query,
            types: types.join(','),
            limit,
            market: 'US'
        };
        
        return await this.get('/api/spotify/search-multi', params, true);
    }

    // 搜索歌单
    async searchPlaylists(query, limit = 20) {
        const params = { q: query, limit, market: 'US' };
        return await this.get('/api/spotify/search-playlists', params, true);
    }

    // 解析Spotify URL
    async parseSpotifyUrl(url) {
        return await this.post('/api/spotify/parse', { url });
    }

    // =============  音乐收藏库API方法  =============

    // 添加到收藏库
    async addToLibrary(spotifyId, options = {}) {
        return await this.post('/api/library/add', {
            spotify_id: spotifyId,
            category: options.category,
            country: options.country,
            language: options.language,
            tags: options.tags,
            notes: options.notes,
            custom_country: options.custom_country,
            custom_region: options.custom_region,
            custom_language: options.custom_language
        });
    }

    // 获取收藏库
    async getLibrary(params = {}) {
        return await this.get('/api/library', params);
    }

    // 删除收藏
    async deleteFromLibrary(libraryId) {
        return await this.delete(`/api/library/${libraryId}`);
    }

    // 从收藏库创建歌单
    async createPlaylistFromLibrary(name, songIds, description = '') {
        return await this.post('/api/library/create-playlist', {
            name: name,
            song_ids: songIds,
            description: description
        });
    }

    // 获取收藏库分类
    async getLibraryCategories() {
        return await this.get('/api/library/categories');
    }

    // 获取收藏库统计
    async getLibraryStats() {
        return await this.get('/api/library/stats');
    }

    // =============  下载API方法  =============

    // 创建单曲下载
    async downloadSingle(spotifyId, format = 'mp3', quality = 'high') {
        return await this.post('/api/download', {
            spotify_id: spotifyId,
            format: format,
            quality: quality
        });
    }

    // 从收藏库批量下载
    async downloadFromLibrary(libraryIds, format = 'mp3', quality = 'high') {
        return await this.post('/api/download/library', {
            library_ids: libraryIds,
            format: format,
            quality: quality
        });
    }

    // 下载整个歌单
    async downloadPlaylist(playlistId, format = 'mp3', quality = 'high') {
        return await this.post('/api/download/playlist', {
            playlist_id: playlistId,
            format: format,
            quality: quality
        });
    }

    // 获取下载任务
    async getDownloadTasks(params = {}) {
        return await this.get('/api/tasks', params);
    }

    // 取消下载任务
    async cancelDownloadTask(taskId) {
        return await this.delete(`/api/tasks/${taskId}`);
    }

    // 获取下载统计
    async getDownloadStats() {
        return await this.get('/api/download/stats');
    }
    
    // 清除下载记录
    async clearDownloadTasks(status = null) {
        const url = status ? `/api/tasks/clear-all?status=${status}` : '/api/tasks/clear-all';
        return await this.delete(url);
    }

    // =============  歌单API方法  =============

    // 获取歌单列表
    async getPlaylists(params = {}) {
        return await this.get('/api/playlists', params);
    }

    // 获取歌单详情
    async getPlaylistDetail(playlistId) {
        return await this.get(`/api/playlists/${playlistId}`);
    }

    // 创建歌单
    async createPlaylist(name, description = '', category = null) {
        return await this.post('/api/playlists', {
            name: name,
            description: description,
            category: category
        });
    }

    // 更新歌单
    async updatePlaylist(playlistId, data) {
        return await this.put(`/api/playlists/${playlistId}`, data);
    }

    // 删除歌单
    async deletePlaylist(playlistId) {
        return await this.delete(`/api/playlists/${playlistId}`);
    }

    // 添加歌曲到歌单
    async addSongsToPlaylist(playlistId, songIds) {
        return await this.post(`/api/playlists/${playlistId}/songs`, {
            song_ids: songIds
        });
    }

    // 从歌单移除歌曲
    async removeSongFromPlaylist(playlistId, songId) {
        return await this.delete(`/api/playlists/${playlistId}/songs/${songId}`);
    }

    // =============  系统API方法  =============

    // 健康检查
    async healthCheck() {
        return await this.get('/api/health');
    }

    // =============  批量任务API方法  =============

    // 启动批量导入任务
    async startBatchImport(request) {
        return await this.post('/api/batch/import-library', request);
    }

    // 启动批量下载任务
    async startBatchDownload(request) {
        return await this.post('/api/batch/download-tracks', request);
    }

    // 获取任务状态
    async getTaskStatus(taskId) {
        return await this.get(`/api/batch/task/${taskId}`);
    }

    // 取消任务
    async cancelTask(taskId) {
        return await this.delete(`/api/batch/task/${taskId}`);
    }

    // 获取活动任务列表
    async getActiveTasks() {
        return await this.get('/api/batch/active-tasks');
    }

    // 获取任务历史记录
    async getTaskHistory(limit = 50) {
        return await this.get(`/api/batch/task-history?limit=${limit}`);
    }

    // 获取工作进程状态
    async getWorkerStatus() {
        return await this.get('/api/batch/worker-status');
    }
}

// 创建全局API实例
const api = new ApiService();

// 确保API实例在全局作用域中可用
window.api = api;
window.ApiService = ApiService;

// API实例已创建并暴露到全局作用域
console.log('🔌 API服务已加载，实例:', api);