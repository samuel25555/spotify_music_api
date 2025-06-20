// 工具函数库

const HELPERS = {
    // 格式化时长（秒转为 mm:ss 格式）
    formatDuration(seconds) {
        if (!seconds || seconds <= 0) return '0:00';
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    },

    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // 格式化日期
    formatDate(date) {
        if (!date) return '';
        const d = new Date(date);
        return d.toLocaleDateString('zh-CN') + ' ' + d.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    },

    // 格式化相对时间
    formatRelativeTime(date) {
        if (!date) return '';
        const now = new Date();
        const diff = now - new Date(date);
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}天前`;
        if (hours > 0) return `${hours}小时前`;
        if (minutes > 0) return `${minutes}分钟前`;
        return '刚刚';
    },

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // 深拷贝
    deepClone(obj) {
        if (obj === null || typeof obj !== "object") return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === "object") {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = this.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    },

    // 生成随机ID
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    },

    // 验证URL
    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    },

    // 验证Spotify URL
    isSpotifyUrl(url) {
        return url && url.includes('spotify.com');
    },

    // 从Spotify URL提取ID
    extractSpotifyId(url) {
        const match = url.match(/spotify\.com\/(track|playlist|album|artist)\/([a-zA-Z0-9]+)/);
        return match ? { type: match[1], id: match[2] } : null;
    },

    // 截断文本
    truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    // 高亮搜索关键词
    highlightText(text, keyword) {
        if (!keyword || !text) return text;
        const regex = new RegExp(`(${keyword})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    },

    // 获取文件扩展名
    getFileExtension(filename) {
        return filename.split('.').pop().toLowerCase();
    },

    // 检查是否为移动设备
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },

    // 复制到剪贴板
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // 降级方案
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                document.body.removeChild(textArea);
                return true;
            } catch (err) {
                document.body.removeChild(textArea);
                return false;
            }
        }
    },

    // 下载文件
    downloadFile(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },

    // 颜色工具
    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    },

    // 获取对比色
    getContrastColor(hex) {
        const rgb = this.hexToRgb(hex);
        if (!rgb) return '#000000';
        const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
        return brightness > 128 ? '#000000' : '#ffffff';
    },

    // 数组去重
    uniqueArray(array, key) {
        if (!key) return [...new Set(array)];
        const seen = new Set();
        return array.filter(item => {
            const value = item[key];
            if (seen.has(value)) return false;
            seen.add(value);
            return true;
        });
    },

    // 数组分组
    groupBy(array, key) {
        return array.reduce((groups, item) => {
            const group = item[key];
            groups[group] = groups[group] || [];
            groups[group].push(item);
            return groups;
        }, {});
    },

    // 数组排序
    sortBy(array, key, direction = 'asc') {
        return array.sort((a, b) => {
            const aVal = a[key];
            const bVal = b[key];
            if (direction === 'desc') {
                return bVal > aVal ? 1 : -1;
            }
            return aVal > bVal ? 1 : -1;
        });
    },

    // 搜索数组
    searchArray(array, searchTerm, keys) {
        if (!searchTerm) return array;
        const term = searchTerm.toLowerCase();
        return array.filter(item => {
            return keys.some(key => {
                const value = item[key];
                return value && value.toString().toLowerCase().includes(term);
            });
        });
    },

    // 检测语言
    detectLanguage(text) {
        if (!text) return null;
        
        // 中文检测
        if (/[\u4e00-\u9fff]/.test(text)) return 'chinese';
        // 韩文检测
        if (/[\uac00-\ud7af]/.test(text)) return 'korean';
        // 日文检测
        if (/[\u3040-\u309f\u30a0-\u30ff]/.test(text)) return 'japanese';
        
        return 'english';
    },

    // 错误处理
    handleError(error, defaultMessage = '操作失败') {
        console.error('Error:', error);
        
        if (error.response?.data?.detail) {
            return error.response.data.detail;
        }
        
        if (error.message) {
            return error.message;
        }
        
        return defaultMessage;
    },

    // 重试机制
    async retry(fn, maxAttempts = 3, delay = 1000) {
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                return await fn();
            } catch (error) {
                if (attempt === maxAttempts) throw error;
                await new Promise(resolve => setTimeout(resolve, delay * attempt));
            }
        }
    }
};

// 导出工具函数
window.HELPERS = HELPERS;