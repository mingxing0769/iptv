# utils/network.py
import re
import time

import requests

from utils.m3u_parse import _parse_m3u_headers


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


def is_url_accessible(url, m3u_headers=None, timeout=30):
    """
    通过发送 HEAD 请求快速检查 URL 是否可访问并返回状态码 200。
    此版本已支持 M3U 中的自定义头部信息。

    Args:
        url (str): 要检查的 URL。
        m3u_headers (tuple, optional): 从 M3U 文件解析的原始头部行。
        timeout (int, optional): 请求超时时间（秒）。默认为 30。

    Returns:
        bool: 如果 URL 可访问且状态码为 200，则返回 True，否则返回 False。
    """
    # 默认的 User-Agent
    final_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # 解析并合并来自M3U的自定义头部
    # 如果M3U中也定义了User-Agent，它将覆盖上面的默认值
    custom_headers = _parse_m3u_headers(m3u_headers)
    final_headers.update(custom_headers)

    try:
        # 使用 HEAD 请求，因为它只获取头部信息，速度更快，适合检查连通性
        # allow_redirects=True 确保在遇到重定向时能追踪到最终地址
        response = requests.head(url, timeout=timeout, headers=final_headers, allow_redirects=True)

        # 检查最终的响应状态码是否为 200 (OK)
        return response.status_code == 200

    except requests.exceptions.RequestException:
        # 捕获所有 requests 相关的异常 (如超时, 连接错误等)，静默处理
        return False
