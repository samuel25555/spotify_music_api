// 前端应用主入口文件
// 提供统一的初始化和错误处理

class AppInitializer {
    constructor() {
        this.isReady = false;
        this.dependencies = {
            vue: false,
            axios: false,
            api: false,
            config: false
        };
    }

    // 检查依赖是否加载完成
    checkDependencies() {
        this.dependencies.vue = typeof Vue !== 'undefined';
        this.dependencies.axios = typeof axios !== 'undefined';
        this.dependencies.api = typeof api !== 'undefined';
        this.dependencies.config = typeof window.ENV_CONFIG !== 'undefined';
        
        const allLoaded = Object.values(this.dependencies).every(loaded => loaded);
        
        if (allLoaded && !this.isReady) {
            this.isReady = true;
            this.initializeApp();
        }
        
        return allLoaded;
    }

    // 初始化应用
    initializeApp() {
        console.log('🚀 Music Downloader App initializing...');
        
        // 设置全局错误处理
        window.addEventListener('error', this.handleGlobalError);
        window.addEventListener('unhandledrejection', this.handleUnhandledRejection);
        
        // 设置API加载状态监听
        window.addEventListener('api-loading', this.handleAPILoading);
        
        // 检查浏览器兼容性
        this.checkBrowserCompatibility();
        
        console.log('✅ Music Downloader App initialized');
    }

    // 全局错误处理
    handleGlobalError(event) {
        console.error('Global error:', event.error);
        // 可以在这里添加错误上报或用户通知
    }

    // 未处理的Promise拒绝
    handleUnhandledRejection(event) {
        console.error('Unhandled promise rejection:', event.reason);
        // 可以在这里添加错误上报或用户通知
    }

    // API加载状态处理
    handleAPILoading(event) {
        const isLoading = event.detail;
        // 可以在这里控制全局加载指示器
        if (isLoading) {
            document.body.classList.add('api-loading');
        } else {
            document.body.classList.remove('api-loading');
        }
    }

    // 检查浏览器兼容性
    checkBrowserCompatibility() {
        const requiredFeatures = [
            'fetch',
            'Promise',
            'URLSearchParams',
            'localStorage'
        ];

        const unsupported = requiredFeatures.filter(feature => 
            typeof window[feature] === 'undefined'
        );

        if (unsupported.length > 0) {
            console.warn('Unsupported browser features:', unsupported);
            // 可以显示浏览器兼容性警告
        }
    }

    // 显示加载错误
    showLoadingError() {
        const errorHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.8);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                font-family: Arial, sans-serif;
            ">
                <div style="text-align: center; padding: 2rem;">
                    <h2>⚠️ 应用加载失败</h2>
                    <p>请检查网络连接或刷新页面重试</p>
                    <button onclick="location.reload()" style="
                        background: #3b82f6;
                        color: white;
                        border: none;
                        padding: 0.5rem 1rem;
                        border-radius: 0.25rem;
                        cursor: pointer;
                        margin-top: 1rem;
                    ">刷新页面</button>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', errorHTML);
    }
}

// 创建应用初始化器实例
const appInitializer = new AppInitializer();

// 定期检查依赖加载状态
const checkInterval = setInterval(() => {
    if (appInitializer.checkDependencies()) {
        clearInterval(checkInterval);
    }
}, 100);

// 超时处理 - 如果10秒内依赖还未加载完成，显示错误
setTimeout(() => {
    if (!appInitializer.isReady) {
        clearInterval(checkInterval);
        appInitializer.showLoadingError();
    }
}, 10000);

// 导出初始化器
window.appInitializer = appInitializer;