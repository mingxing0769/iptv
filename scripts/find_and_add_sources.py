# scripts/find_and_add_sources.py
"""
自动化脚本：从 GitHub 搜索持续有更新的 IPTV 仓库，自动提取其中的 M3U 源并验证，
如果源中包含 channels.txt 中的频道，则添加到 config/sources_urls.py 中。
"""
import os
import re
import requests
import json
from datetime import datetime, timedelta

from utils.channel_filter import load_channels_txt, normalize_title_for_match, get_official_name
from config.sources_urls import playlist_urls

CHANNELS_TXT_PATH = "channels.txt"
SOURCES_URLS_PATH = "config/sources_urls.py"

# 潜在的 IPTV 仓库列表（按更新频率和稳定性排序）
POTENTIAL_IPTV_REPOS = [
    "iptv-org/iptv",
    "vbskycn/iptv",
    "fanmingming/live",
    "dler-io/iptv",
    "yuanzl77/IPTV",
    "freeiptv/iptv",
    "iptv-store/iptv",
    "newupc/iptv",
    "gasanov777/iptv",
    "xzw832/cmys",
]

# GitHub API 配置
GITHUB_API_BASE = "https://api.github.com"
GITHUB_SEARCH_ENDPOINT = f"{GITHUB_API_BASE}/search/repositories"

def get_recently_updated_iptv_repos(limit=20):
    """
    使用 GitHub Search API 搜索最近更新的 IPTV 相关仓库。
    
    返回:
        repos (list): 仓库列表，每个元素包含 {'full_name', 'updated_at', 'html_url'}
    """
    print("🔍 使用 GitHub API 搜索最近更新的 IPTV 仓库...")
    
    # 搜索关键词：包含 m3u 或 iptv 或 playlist 的仓库
    query = "iptv m3u OR iptv playlist OR iptv.txt OR iptv.m3u"
    params = {
        "q": query,
        "sort": "updated",
        "order": "desc",
        "per_page": limit,
        "page": 1
    }
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "IPTV-Source-Finder"
    }
    
    try:
        response = requests.get(GITHUB_SEARCH_ENDPOINT, params=params, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"  ⚠️ GitHub API 请求失败，状态码: {response.status_code}")
            return []
        
        data = response.json()
        items = data.get("items", [])
        
        repos = []
        for item in items:
            full_name = item.get("full_name")
            if full_name and not full_name.startswith("iptv-org/") and not full_name.startswith("vbskycn/"):
                # 排除已知仓库，避免重复
                if full_name not in POTENTIAL_IPTV_REPOS:
                    repos.append({
                        "full_name": full_name,
                        "updated_at": item.get("updated_at"),
                        "html_url": item.get("html_url"),
                        "stargazers_count": item.get("stargazers_count", 0)
                    })
        
        print(f"  ✅ 从 GitHub API 搜索到 {len(repos)} 个近期更新的 IPTV 仓库。")
        return repos
        
    except Exception as e:
        print(f"  ⚠️ GitHub API 搜索失败: {e}")
        return []


def get_m3u_urls_from_repo(repo_full_name):
    """
    从 GitHub 仓库中提取 M3U 源 URL。
    
    返回:
        m3u_urls (list): M3U 源 URL 列表
    """
    print(f"  🔍 检查仓库: {repo_full_name}")
    m3u_urls = []
    
    try:
        # 尝试从仓库的 README 或主要文件中提取 M3U 链接
        # 使用 GitHub API 获取仓库内容
        contents_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "IPTV-Source-Finder"
        }
        
        response = requests.get(contents_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return m3u_urls
        
        contents = response.json()
        if not isinstance(contents, list):
            return m3u_urls
        
        # 查找包含 m3u 或 txt 的文件
        for item in contents:
            name = item.get("name", "")
            if name.endswith(('.m3u', '.m3u8', '.txt')) and 'iptv' in name.lower():
                download_url = item.get("download_url")
                if download_url and download_url.startswith('https://raw.githubusercontent.com'):
                    m3u_urls.append(download_url)
        
        # 如果从根目录没找到，尝试常见的目录结构
        common_paths = [
            "tv/m3u/ipv6.m3u",
            "tv/m3u/ipv4.m3u",
            "tv/m3u/index.m3u",
            "m3u/ipv6.m3u",
            "m3u/ipv4.m3u",
            "m3u/index.m3u",
            "list.m3u8",
            "iptv.m3u",
            "iptv.txt",
        ]
        
        for path in common_paths:
            path_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{path}"
            resp = requests.get(path_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "download_url" in data:
                    dl_url = data["download_url"]
                    if dl_url.startswith('https://raw.githubusercontent.com'):
                        if dl_url not in m3u_urls:
                            m3u_urls.append(dl_url)
                            
    except Exception as e:
        print(f"  ⚠️ 获取仓库 {repo_full_name} 内容失败: {e}")
        
    return m3u_urls


def check_source_channels(source_url, official_names, alias_to_official):
    """
    检查 M3U 源中是否包含 channels.txt 中的频道。
    
    返回:
        match_count (int): 匹配的频道数量
        matched_channels (list): 匹配的频道列表
    """
    try:
        response = requests.get(source_url, timeout=10)
        if response.status_code != 200:
            return 0, []
        
        lines = response.text.splitlines()
        matched_channels = []
        match_count = 0
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                # 提取频道标题
                try:
                    title = line.rsplit(",", 1)[-1].strip()
                except IndexError:
                    continue
                
                # 规范化标题
                norm_title = normalize_title_for_match(title)
                
                # 检查是否匹配 channels.txt 中的频道
                is_match, official_name = get_official_name(title, official_names, {}, alias_to_official)
                if is_match:
                    if official_name not in matched_channels:
                        matched_channels.append(official_name)
                        match_count += 1
                        
        return match_count, matched_channels
        
    except Exception as e:
        print(f"  ⚠️ Error fetching {source_url}: {e}")
        return 0, []


def update_sources_urls(source_url):
    """
    将新的 M3U 源添加到 config/sources_urls.py 中。
    """
    if source_url in playlist_urls:
        print(f"  ℹ️ 源已存在: {source_url}")
        return False
    
    # 读取当前的 sources_urls.py
    with open(SOURCES_URLS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在 playlist_urls 列表中添加新源
    new_source_line = f'   "{source_url}",\n'
    
    # 找到 playlist_urls 列表的结束位置
    lines = content.split('\n')
    insert_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == ']' and i > 0:
            insert_idx = i
            break
    
    if insert_idx != -1:
        # 在 ']' 之前插入新源
        lines.insert(insert_idx, new_source_line.strip())
        new_content = '\n'.join(lines)
        
        with open(SOURCES_URLS_PATH, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✅ 已添加新源: {source_url}")
        return True
    
    return False


def main():
    print("=== 自动化源搜索与验证脚本 (GitHub API 版本) ===")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载 channels.txt
    official_names, official_to_aliases, alias_to_official, official_lower_to_original = load_channels_txt(CHANNELS_TXT_PATH)
    print(f"✅ 已加载 {len(official_names)} 个正式频道和 {len(alias_to_official)} 个别名。")
    
    new_sources_added = 0
    
    # 1. 从 GitHub API 搜索最近更新的 IPTV 仓库
    updated_repos = get_recently_updated_iptv_repos(limit=15)
    
    # 2. 检查潜在的 IPTV 仓库列表
    repos_to_check = POTENTIAL_IPTV_REPOS.copy()
    for repo_info in updated_repos:
        if repo_info["full_name"] not in repos_to_check:
            repos_to_check.append(repo_info["full_name"])
    
    # 去重
    repos_to_check = list(set(repos_to_check))
    
    print(f"\n📋 总共检查 {len(repos_to_check)} 个 IPTV 仓库...")
    
    for repo_full_name in repos_to_check:
        m3u_urls = get_m3u_urls_from_repo(repo_full_name)
        
        for source_url in m3u_urls:
            if source_url in playlist_urls:
                continue
                
            print(f"\n  🔍 验证源: {source_url}")
            match_count, matched_channels = check_source_channels(source_url, official_names, alias_to_official)
            
            if match_count > 0:
                print(f"    ✅ 匹配到 {match_count} 个频道: {', '.join(matched_channels[:10])}{'...' if match_count > 10 else ''}")
                
                # 添加到 sources_urls.py
                if update_sources_urls(source_url):
                    new_sources_added += 1
            else:
                print(f"    ❌ 未匹配到任何 channels.txt 中的频道，跳过。")
    
    print(f"\n=== 总结 ===")
    print(f"✅ 共添加了 {new_sources_added} 个新源到 config/sources_urls.py。")
    print("💡 提示：请运行 mergeclean.py 验证新源的有效性，并检查缺失频道列表。")


if __name__ == "__main__":
    main()