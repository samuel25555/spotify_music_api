// CDN 降级策略
// 当CDN资源加载失败时，提供本地或备用资源

class CDNFallback {
    constructor() {
        this.fallbacks = {
            'vue': [
                'https://unpkg.com/vue@3/dist/vue.global.js',
                'https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js'
            ],
            'axios': [
                'https://unpkg.com/axios/dist/axios.min.js',
                'https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js'
            ],
            'tailwind': [
                'https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css',
                'https://cdn.jsdelivr.net/npm/tailwindcss@^2/dist/tailwind.min.css'
            ],
            'fontawesome': [
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
                'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.0.0/css/all.min.css'
            ]
        };
    }

    // 加载脚本并提供降级
    async loadScript(name, index = 0) {
        const urls = this.fallbacks[name];
        if (!urls || index >= urls.length) {
            throw new Error(`无法加载 ${name}`);
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = urls[index];
            script.onload = () => resolve(script);
            script.onerror = () => {
                console.warn(`CDN ${urls[index]} 加载失败，尝试下一个...`);
                this.loadScript(name, index + 1).then(resolve).catch(reject);
            };
            document.head.appendChild(script);
        });
    }

    // 加载样式表并提供降级
    async loadStylesheet(name, index = 0) {
        const urls = this.fallbacks[name];
        if (!urls || index >= urls.length) {
            throw new Error(`无法加载 ${name}`);
        }

        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = urls[index];
            link.onload = () => resolve(link);
            link.onerror = () => {
                console.warn(`CDN ${urls[index]} 加载失败，尝试下一个...`);
                this.loadStylesheet(name, index + 1).then(resolve).catch(reject);
            };
            document.head.appendChild(link);
        });
    }

    // 检查依赖是否已加载
    checkDependency(name) {
        switch (name) {
            case 'vue':
                return typeof Vue !== 'undefined';
            case 'axios':
                return typeof axios !== 'undefined';
            default:
                return false;
        }
    }

    // 加载所有必需的依赖
    async loadAllDependencies() {
        const dependencies = ['vue', 'axios'];
        const promises = [];

        for (const dep of dependencies) {
            if (!this.checkDependency(dep)) {
                promises.push(this.loadScript(dep));
            }
        }

        if (promises.length > 0) {
            try {
                await Promise.all(promises);
                console.log('✅ 所有CDN依赖加载完成');
            } catch (error) {
                console.error('❌ CDN依赖加载失败:', error);
                throw error;
            }
        }
    }
}

// 导出CDN降级实例
window.cdnFallback = new CDNFallback();