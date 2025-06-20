// 环境配置文件
window.ENV_CONFIG = {
    // API配置
    API_BASE_URL: window.location.origin,
    
    // 开发环境检测
    IS_DEVELOPMENT: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
    
    // CDN配置
    CDN: {
        VUE: 'https://unpkg.com/vue@3/dist/vue.global.js',
        AXIOS: 'https://unpkg.com/axios/dist/axios.min.js',
        TAILWIND: 'https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css',
        FONTAWESOME: 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
    },
    
    // 超时配置
    TIMEOUT: {
        REQUEST: 30000,
        SEARCH_DEBOUNCE: 300,
        RETRY_DELAY: 1000
    },
    
    // 缓存配置
    CACHE: {
        SEARCH_EXPIRE: 5 * 60 * 1000, // 5分钟
        MAX_SIZE: 100
    }
};

// 导出配置
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.ENV_CONFIG;
}