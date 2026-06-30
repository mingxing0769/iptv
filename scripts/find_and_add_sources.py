# scripts/find_and_add_sources.py
"""
自动化脚本：搜索并验证新的 M3U 源，如果源中包含 channels.txt 中的频道，则添加到 config/sources_urls.py 中。
同时，适时的增加别名，以增加匹配率。
"""
import os
import re
import requests
from urllib.parse import urlparse

from utils.channel_filter import load_channels_txt, normalize_title_for_match, get_official_name
from config.sources_urls import playlist_urls

CHANNELS_TXT_PATH = "channels.txt"
SOURCES_URLS_PATH = "config/sources_urls.py"

# 潜在的 M3U 源搜索列表（可以从 GitHub 搜索获取）
POTENTIAL_SOURCES = [
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv4.m3u",
    "https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv6.m3u",
    "https://raw.githubusercontent.com/kimwang1978/collect-txt/main/iptv.m3u",
]

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
    print("=== 自动化源搜索与验证脚本 ===")
    
    # 加载 channels.txt
    official_names, official_to_aliases, alias_to_official, official_lower_to_original = load_channels_txt(CHANNELS_TXT_PATH)
    print(f"✅ 已加载 {len(official_names)} 个正式频道和 {len(alias_to_official)} 个别名。")
    
    new_sources_added = 0
    
    for source_url in POTENTIAL_SOURCES:
        print(f"\n🔍 检查源: {source_url}")
        
        # 检查源是否有效
        match_count, matched_channels = check_source_channels(source_url, official_names, alias_to_official)
        
        if match_count > 0:
            print(f"  ✅ 匹配到 {match_count} 个频道: {', '.join(matched_channels[:10])}{'...' if match_count > 10 else ''}")
            
            # 添加到 sources_urls.py
            if update_sources_urls(source_url):
                new_sources_added += 1
        else:
            print(f"  ❌ 未匹配到任何 channels.txt 中的频道，跳过。")
    
    print(f"\n=== 总结 ===")
    print(f"✅ 共添加了 {new_sources_added} 个新源到 config/sources_urls.py。")
    print("💡 提示：请运行 mergeclean.py 验证新源的有效性，并检查缺失频道列表。")


if __name__ == "__main__":
    main()