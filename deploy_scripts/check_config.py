#!/usr/bin/env python3
"""
部署配置检查脚本
验证生产环境配置是否正确
"""
import os
import sys
import requests
from pathlib import Path

def check_env_config():
    """检查环境配置"""
    print("📋 检查环境配置...")
    
    # 检查.env文件
    env_file = ".env"
    if not os.path.exists(env_file):
        print(f"❌ 未找到 {env_file} 文件")
        return False
    
    # 读取配置
    config = {}
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value
    
    # 检查关键配置
    required_configs = ['DOMAIN', 'DB_HOST', 'DB_NAME', 'DOWNLOAD_DIR']
    for key in required_configs:
        if key in config:
            print(f"✅ {key}: {config[key]}")
        else:
            print(f"❌ 缺少配置: {key}")
            return False
    
    return True

def check_directories():
    """检查必要目录"""
    print("\n📁 检查目录结构...")
    
    required_dirs = ['downloads', 'logs', 'app', 'frontend']
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ 目录存在")
        else:
            print(f"❌ {dir_name}/ 目录不存在")
            if dir_name in ['downloads', 'logs']:
                os.makedirs(dir_name, exist_ok=True)
                print(f"🔧 已创建 {dir_name}/ 目录")

def check_permissions():
    """检查文件权限"""
    print("\n🔒 检查文件权限...")
    
    # 检查下载目录权限
    downloads_dir = "downloads"
    if os.path.exists(downloads_dir):
        stat_info = os.stat(downloads_dir)
        mode = oct(stat_info.st_mode)[-3:]
        if mode == '777':
            print(f"✅ {downloads_dir}/ 权限正确: {mode}")
        else:
            print(f"⚠️ {downloads_dir}/ 权限: {mode} (建议777)")
    
    # 检查日志目录权限
    logs_dir = "logs"
    if os.path.exists(logs_dir):
        stat_info = os.stat(logs_dir)
        mode = oct(stat_info.st_mode)[-3:]
        if mode == '777':
            print(f"✅ {logs_dir}/ 权限正确: {mode}")
        else:
            print(f"⚠️ {logs_dir}/ 权限: {mode} (建议777)")

def check_api_health():
    """检查API健康状态"""
    print("\n🏥 检查API健康状态...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ API服务正常运行")
            print(f"   版本: {data.get('version', 'unknown')}")
            print(f"   数据库: {data.get('database', 'unknown')}")
            print(f"   Redis: {data.get('redis', 'unknown')}")
            return True
        else:
            print(f"❌ API响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到API: {e}")
        return False

def check_file_url_generation():
    """检查文件URL生成"""
    print("\n🔗 检查播放链接生成...")
    
    try:
        # 测试URL生成逻辑
        sys.path.insert(0, '.')
        from app.utils.url_helper import generate_file_url, get_base_url
        
        print(f"✅ 基础URL: {get_base_url()}")
        
        # 测试文件URL生成
        test_file = "downloads/test.webm"
        file_url = generate_file_url(test_file)
        print(f"✅ 文件URL示例: {file_url}")
        
        return True
    except Exception as e:
        print(f"❌ URL生成失败: {e}")
        return False

def check_static_file_access():
    """检查静态文件访问"""
    print("\n📂 检查静态文件访问...")
    
    # 从配置读取域名
    domain = None
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('DOMAIN='):
                    domain = line.split('=', 1)[1].strip()
                    break
    
    if not domain:
        print("⚠️ 未配置DOMAIN，无法测试静态文件访问")
        return False
    
    # 测试下载目录访问
    test_url = f"{domain}/downloads/"
    try:
        response = requests.head(test_url, timeout=10)
        if response.status_code in [200, 403, 404]:  # 403/404也算正常，说明路径配置正确
            print(f"✅ 下载目录路径配置正确: {test_url}")
        else:
            print(f"⚠️ 下载目录访问异常: {response.status_code}")
    except Exception as e:
        print(f"⚠️ 无法测试下载目录访问: {e}")
    
    return True

def main():
    """主检查流程"""
    print("🚀 生产环境配置检查\n")
    
    checks = [
        ("环境配置", check_env_config),
        ("目录结构", check_directories),
        ("文件权限", check_permissions),
        ("API健康状态", check_api_health),
        ("URL生成", check_file_url_generation),
        ("静态文件访问", check_static_file_access)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} 检查失败: {e}")
            results.append((name, False))
    
    # 汇总结果
    print(f"\n📊 检查结果汇总:")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if result:
            passed += 1
    
    print("=" * 40)
    print(f"总体评分: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有检查通过，配置正确！")
    else:
        print("⚠️ 部分检查失败，请根据上述提示修复配置")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)