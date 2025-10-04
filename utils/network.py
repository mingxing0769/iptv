# utils/network.py
import requests
import time

def fetch_playlist_content(url, retries=3, timeout=15):
    """获取并返回播放列表内容（文本）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempting to fetch {url} (try {attempt})...")
            res = requests.get(url, timeout=timeout, headers=headers)
            res.raise_for_status()
            print(f"✅ Successfully fetched {url}")
            return res.text
        except Exception as e:
            print(f"❌ Attempt {attempt} failed for {url}: {e}")
            time.sleep(2)
    print(f"⚠️ Skipping {url} after {retries} failed attempts.")
    return ""


def is_url_accessible(url, timeout=30):
    """
    通过发送 HEAD 请求快速检查 URL 是否可访问并返回状态码 200。

    Args:
        url (str): 要检查的 URL。
        timeout (int, optional): 请求超时时间（秒）。默认为 30。

    Returns:
        bool: 如果 URL 可访问且状态码为 200，则返回 True，否则返回 False。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        # 使用 HEAD 请求，因为它只获取头部信息，速度更快，适合检查连通性
        # allow_redirects=True 确保在遇到重定向时能追踪到最终地址
        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)

        # 检查最终的响应状态码是否为 200 (OK)
        return response.status_code == 200
        
    except requests.exceptions.RequestException:
        # 捕获所有 requests 相关的异常 (如超时, 连接错误等)，静默处理
        return False
