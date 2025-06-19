#!/usr/bin/env python3
"""
Music Downloader API 测试脚本
"""
import requests
import time
import json

API_BASE = "http://localhost:8000/api"

def test_health():
    """测试健康检查"""
    print("🔍 Testing health check...")
    response = requests.get("http://localhost:8000/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_download_song():
    """测试单曲下载"""
    print("🎵 Testing song download...")
    
    # 使用一个示例Spotify链接 (实际使用时需要有效链接)
    test_url = "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
    
    payload = {
        "url": test_url,
        "format": "mp3",
        "quality": "320k"
    }
    
    try:
        response = requests.post(f"{API_BASE}/download", json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Task ID: {result['task_id']}")
            print(f"Status: {result['status']}")
            return result['task_id']
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def test_status_check(task_id):
    """测试状态检查"""
    if not task_id:
        return
        
    print(f"📊 Testing status check for task: {task_id}")
    
    for i in range(5):  # 检查5次
        try:
            response = requests.get(f"{API_BASE}/status/{task_id}")
            
            if response.status_code == 200:
                status = response.json()
                print(f"Check {i+1}: {status['status']} - Progress: {status['progress']}%")
                
                if status['status'] in ['completed', 'failed']:
                    break
                    
            time.sleep(2)  # 等待2秒
            
        except Exception as e:
            print(f"Status check failed: {e}")
            break
    print()

def test_youtube_search():
    """测试YouTube搜索"""
    print("🔍 Testing YouTube search...")
    
    payload = {
        "query": "The Weeknd Blinding Lights",
        "limit": 3
    }
    
    try:
        response = requests.post(f"{API_BASE}/search-youtube", json=payload)
        
        if response.status_code == 200:
            results = response.json()
            print(f"Found {len(results)} results:")
            
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']} - {result['uploader']}")
                print(f"   Duration: {result.get('duration', 'Unknown')}s")
                print(f"   URL: {result['url']}")
                print()
        else:
            print(f"Search failed: {response.text}")
            
    except Exception as e:
        print(f"Search request failed: {e}")

def test_get_songs():
    """测试获取歌曲列表"""
    print("🎵 Testing get songs...")
    
    try:
        response = requests.get(f"{API_BASE}/songs?page=1&per_page=5")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total songs: {data['total']}")
            print(f"Page: {data['page']}/{data['pages']}")
            
            for song in data['items']:
                print(f"- {song['artist']} - {song['title']} [{song['download_status']}]")
        else:
            print(f"Failed to get songs: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")
    print()

def test_get_stats():
    """测试获取统计信息"""
    print("📊 Testing get stats...")
    
    try:
        response = requests.get(f"{API_BASE}/stats")
        
        if response.status_code == 200:
            stats = response.json()
            print("📈 Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        else:
            print(f"Failed to get stats: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")
    print()

def test_laravel_integration():
    """测试Laravel集成示例"""
    print("🐘 Testing Laravel integration example...")
    
    # 模拟Laravel HTTP客户端调用
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Laravel/9.x'
    }
    
    # 测试下载请求
    payload = {
        "url": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",
        "format": "mp3", 
        "quality": "320k",
        "callback_url": "https://your-laravel-app.com/api/download-complete"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/download", 
            json=payload, 
            headers=headers
        )
        
        print(f"Laravel-style request status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Laravel integration test successful")
            print(f"Task ID: {result['task_id']}")
        else:
            print(f"❌ Laravel integration test failed: {response.text}")
            
    except Exception as e:
        print(f"Laravel integration test failed: {e}")
    print()

def main():
    """运行所有测试"""
    print("🎵 Music Downloader API Test Suite")
    print("=" * 50)
    
    # 基础测试
    test_health()
    test_get_stats()
    test_get_songs()
    
    # YouTube搜索测试
    test_youtube_search()
    
    # 下载测试 (需要有效的Spotify凭据)
    print("⚠️  Note: Download tests require valid Spotify credentials")
    print("   Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env")
    
    task_id = test_download_song()
    test_status_check(task_id)
    
    # Laravel集成测试
    test_laravel_integration()
    
    print("✅ All tests completed!")
    print("\n🌐 Access points:")
    print("  - API Documentation: http://localhost:8000/docs")
    print("  - Web Interface: http://localhost:8000")
    print("  - Health Check: http://localhost:8000/health")

if __name__ == "__main__":
    main()