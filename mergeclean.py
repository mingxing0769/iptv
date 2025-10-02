# merge_playlists.py
import os
import re
from datetime import datetime

from tqdm import tqdm

import config.filter_keywords
from config.sources_urls import playlist_urls
from utils.network import fetch_playlist_content
from utils.m3u_parse import parse_m3u


# --- 配置区 ---
EPG_URL = "https://raw.githubusercontent.com/mingxing0769/iptv/main/out/DrewLive2.xml.gz"
OUTPUT_FILE = "out/MergedCleanPlaylist.m3u8"



def is_nsfw(group_title, title):
    """检查频道的 group-title 或 title 是否包含 NSFW 关键词。"""
    # 从配置文件导入 nsfw_keywords
    nsfw_keywords = nsfw_keywords = ['nsfw', 'xxx', 'porn', 'adult']
    # 将分组和标题合并为一个字符串，并转为小写，方便不区分大小写地搜索
    text_to_check = f"{group_title} {title}".lower()
    return any(keyword in text_to_check for keyword in nsfw_keywords)


def normalize_title(title):
    """
    精确匹配替换
    :param title: 文本
    :return: 文本
    """
    indicators = config.filter_keywords.indicators
    normalized = title
    for indicator in indicators:
        normalized = re.sub(indicator, '', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'[\s\-_|(\[\]]+$', '', normalized).strip()
    normalized = ' '.join(normalized.split())
    return normalized if normalized else title


def process_and_normalize_channels(all_channels_list):
    """
    对频道列表进行规范化、去重和统一化处理。
    1. 过滤掉 NSFW 内容。
    2. 过滤掉 (url, group_title) 完全重复的条目。
    3. 对频道标题进行规范化 (例如，移除 HD, FHD 等)。
    4. 对于同一分组内规范化后标题相同的频道，统一其 tvg-id, tvg-name, tvg-logo。
       这有助于后续 EPG 的匹配。
    """
    print("\n🔍 Starting normalization, de-duplication, and unification process...")

    processed_urls = set()
    # 用于存储每个 (group, normalized_title) 组合的“主”TVG信息
    master_tvg_info = {}
    final_channels = []
    nsfw_count = 0

    for tvg_name, tvg_id, tvg_logo, group_title, title, headers, url in tqdm(all_channels_list,
                                                                             desc="Processing & Unifying"):
        # 步骤 1: 检查是否为 NSFW 内容，如果是则跳过
        if is_nsfw(group_title, title):
            nsfw_count += 1
            continue

        # 步骤 2: 过滤掉 (url, group_title) 完全重复的条目
        if (url, group_title) in processed_urls:
            continue
        processed_urls.add((url, group_title))

        # 步骤 3: 规范化标题
        normalized_title = normalize_title(title.strip())
        key = (group_title, normalized_title)

        # 步骤 4: 检查并统一 TVG 信息
        if key not in master_tvg_info:
            # 如果是第一次遇到这个 (分组, 标题) 组合，
            # 就将它的 TVG 信息存为“主”信息。
            master_tvg_info[key] = (tvg_name, tvg_id, tvg_logo)

        # 获取该组合的“主”TVG信息
        master_tvg_name, master_tvg_id, master_tvg_logo = master_tvg_info[key]

        # 步骤 5: 使用统一后的信息构建最终的频道数据
        unified_channel = (
            master_tvg_name,
            master_tvg_id,
            master_tvg_logo,
            group_title,
            normalized_title,
            headers,
            url
        )
        final_channels.append(unified_channel)

    if nsfw_count > 0:
        print(f"🚫 Filtered out {nsfw_count} NSFW channels.")
    print(f"✅ Kept {len(final_channels)} channels after processing and unification.")
    return final_channels


def write_merged_playlist(final_channels_to_write):

    lines = [f'#EXTM3U url-tvg="{EPG_URL}"', ""]
    sorted_channels = sorted(
        final_channels_to_write,
        key=lambda channel: (str(channel[3]).lower(), str(channel[4]).lower())
    )

    current_group = None
    for channel_data in sorted_channels:
        # 解包元组以获取所需数据
        tvg_name, tvg_id, tvg_logo, group, title, headers, url = channel_data

        # --- 修正：使用原始的 group 名称，而不是小写版本 ---
        if group != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f'#EXTGRP:{group}')
            current_group = group

        # --- 修正：构建正确的 #EXTINF 行 ---
        # 1. 处理可能为空的属性
        # 2. 确保逗号在引号外部
        extinf_parts = ['#EXTINF:-1']
        if tvg_id: extinf_parts.append(f'tvg-id="{tvg_id}"')
        if tvg_name: extinf_parts.append(f'tvg-name="{tvg_name}"')
        if tvg_logo: extinf_parts.append(f'tvg-logo="{tvg_logo}"')
        if group: extinf_parts.append(f'group-title="{group}"')

        # 将属性部分用空格连接，然后加上逗号和标题
        extinf_line = ' '.join(extinf_parts) + f',{title}'

        lines.append(extinf_line)
        lines.extend(headers)
        lines.append(url)

    final_output_string = '\n'.join(lines) + '\n'
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_output_string)
    print(f"\n✅ Merged playlist written to {OUTPUT_FILE}.")
    print(f"📊 Total channels written: {len(final_channels_to_write)}.")


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    start_time = datetime.now()
    print(f"🚀 Starting playlist merge at {start_time.strftime('%Y-%m-%d %H:%M:%S')}...")

    channel_data = []
    for url in playlist_urls:
        content = fetch_playlist_content(url)
        if content:
            parsed_channels = parse_m3u(content)
            print(f"✅ Parsed {len(parsed_channels)} valid channel entries from {url}.")
            channel_data.extend(parsed_channels)

    processed_channels = process_and_normalize_channels(channel_data)
    write_merged_playlist(processed_channels)

    end_time = datetime.now()
    print(f"\n✨ Merging complete at {end_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    print(f"⏱️ Total execution time: {(end_time - start_time).total_seconds():.2f} seconds.")


if __name__ == "__main__":
    # 对config/sources_urls 中的源进行合并操作
    main()
