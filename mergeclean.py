# merge_playlists.py
import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from utils.filter_keywords import Indicators_key, Category_Key, Nsfw_Key
from config.sources_urls import playlist_urls
from utils.network import fetch_playlist_content, is_url_accessible
from utils.m3u_parse import parse_m3u
from utils.channel_filter import load_channels_txt, get_official_name, get_missing_channels

# --- 配置区 ---
EPG_URL = "https://raw.githubusercontent.com/mingxing0769/iptv/main/out/DrewLive3.xml"
# EPG_URL="http://epg.51zmt.top:8000/e.xml"
OUTPUT_FILE = "out/MergedCleanPlaylist.m3u8"

# 是否根据 channels.txt 进行频道筛选（仅保留 channels.txt 中的频道及其别名）
CHANNELS_TXT_FILTER = True
CHANNELS_TXT_PATH = "channels.txt"

# 是否对频道进行筛选, 根据utils.filter_keywords.Category_Key
CategoryFilter = True

# 并发检查URL有效性 ---
URL_CHECK = False

# 并发检查URL时的最大线程数，可以根据你的网络和CPU情况调整
MAX_WORKERS_URL_CHECK = 100


def is_nsfw(group_title, title):
    """检查频道的 group-title 或 title 是否包含 NSFW 关键词。"""
    nsfw_keywords = Nsfw_Key
    text_to_check = f"{group_title} {title}".lower()
    return any(keyword in text_to_check for keyword in nsfw_keywords)


def check_urls_concurrently(channels_to_check):
    """
    使用多线程并发检查频道URL的可访问性。

    Args:
        channels_to_check (list): 待检查的频道列表。

    Returns:
        list: 包含所有可访问频道的列表。
    """
    print(
        f"\n🚀 Starting concurrent URL accessibility check for {len(channels_to_check)} channels (up to {MAX_WORKERS_URL_CHECK} workers)...")
    accessible_channels = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_URL_CHECK) as executor:
        # 创建 future 到 channel_data 的映射
        # channel 元组结构: (..., headers, url)
        # headers 在倒数第2个位置 (channel[-2]), url 在最后 (channel[-1])
        future_to_channel = {
            executor.submit(is_url_accessible, channel[-1], channel[-2], 15): channel
            for channel in channels_to_check
        }

        # 使用 tqdm 显示进度
        for future in tqdm(as_completed(future_to_channel), total=len(channels_to_check), desc="Checking URLs"):
            channel_data = future_to_channel[future]
            try:
                if future.result():
                    accessible_channels.append(channel_data)
            except Exception:
                # 发生任何异常（如超时）都认为URL不可访问
                pass

    inaccessible_count = len(channels_to_check) - len(accessible_channels)
    print(f"✓ Accessible channels: {len(accessible_channels)}")
    if inaccessible_count > 0:
        print(f"✗ Inaccessible or timed-out channels: {inaccessible_count}")
    return accessible_channels


def process_and_normalize_channels(accessible_channels, official_names, official_to_aliases, alias_to_official, official_lower_to_original):
    """
    对频道列表进行规范化、去重和统一化处理。
    - 过滤 NSFW 内容和非指定分类。
    - 根据 channels.txt 过滤频道（仅保留 channels.txt 中的频道及其别名）。
    - 使用 channels.txt 中的正式名作为最终的 title 和 tvg-name。
    - 过滤 url 完全重复的条目。
    - 统一同名频道的 TVG 信息。
    """
    print("\n🔍 Starting data normalization, de-duplication, and unification...")

    processed_urls = set()
    master_tvg_info = {}
    final_channels = []
    filtered_count = 0
    processed_official_names = set()

    for tvg_name, tvg_id, tvg_logo, group_title, title, headers, url in tqdm(accessible_channels,
                                                                             desc="Processing & Unifying"):
        # 检查是否为 NSFW 内容
        if is_nsfw(group_title, title):
            filtered_count += 1
            continue

        # channels.txt 过滤：获取正式名
        if CHANNELS_TXT_FILTER:
            is_match, official_name_lower = get_official_name(title, official_names, official_to_aliases, alias_to_official)
            if not is_match:
                filtered_count += 1
                continue
            # 获取原始正式名
            official_title = official_lower_to_original.get(official_name_lower, official_name_lower)
            processed_official_names.add(official_name_lower)
        else:
            # 如果不启用 channels.txt 过滤，则使用原始 title
            official_title = title
            # 为了缺失频道统计，尝试提取可能的 official_name_lower
            is_match, official_name_lower = get_official_name(title, official_names, official_to_aliases, alias_to_official)
            if is_match:
                processed_official_names.add(official_name_lower)

        # 分类过滤
        if CategoryFilter:
            lower_keywords = [k.lower() for k in Category_Key]
            searchable_text = f'{tvg_name}, {group_title}, {title}'.lower()
            if not any(keyword in searchable_text for keyword in lower_keywords):
                filtered_count += 1
                continue

        # 过滤url完全重复的条目
        if url in processed_urls:
            filtered_count += 1
            continue
        processed_urls.add(url)

        key = official_title.lower()

        # 检查并统一 TVG 信息
        if key not in master_tvg_info:
            master_tvg_info[key] = (tvg_logo, group_title)

        master_tvg_logo, master_group_title = master_tvg_info[key]

        # 使用统一后的信息构建最终的频道数据
        # 使用 official_title 作为 title 和 tvg-name
        unified_channel = (
           official_title, tvg_id, master_tvg_logo, master_group_title, official_title, headers, url
        )
        final_channels.append(unified_channel)

    if filtered_count > 0:
        print(f"🚫 Filtered out {filtered_count} channels based on filters.")
    print(f"✅ Kept {len(final_channels)} channels after processing.")
    return final_channels, processed_official_names


def write_merged_playlist(final_channels_to_write):
    """将最终的频道列表写入 M3U 文件。"""
    lines = [f'#EXTM3U url-tvg="{EPG_URL}"', ""]
    # 按 group-title 和 title 排序
    sorted_channels = sorted(
        final_channels_to_write,
        key=lambda channel: (str(channel[3]).lower(), str(channel[4]).lower())
    )

    current_group = None
    for channel_data in sorted_channels:
        tvg_name, tvg_id, tvg_logo, group, title, headers, url = channel_data

        if group != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f'#EXTGRP:{group}')
            current_group = group

        extinf_parts = ['#EXTINF:-1']
        if tvg_id: extinf_parts.append(f'tvg-id="{tvg_id}"')
        if tvg_name:
            extinf_parts.append(f'tvg-name="{tvg_name}"')
        else:
            extinf_parts.append(f'tvg-name="{title}"')

        if tvg_logo: extinf_parts.append(f'tvg-logo="{tvg_logo}"')
        if group: extinf_parts.append(f'group-title="{group}"')

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

    # Load channels.txt if filtering is enabled
    official_names = set()
    official_to_aliases = {}
    alias_to_official = {}
    official_lower_to_original = {}
    if CHANNELS_TXT_FILTER:
        print(f"📂 Loading allowed channels from {CHANNELS_TXT_PATH}...")
        official_names, official_to_aliases, alias_to_official, official_lower_to_original = load_channels_txt(CHANNELS_TXT_PATH)
        print(f"✅ Loaded {len(official_names)} official channels and {len(alias_to_official)} aliases.")
    else:
        print("⚠️ CHANNELS_TXT_FILTER is False, skipping channels.txt filter.")

    all_channels = []
    for url in playlist_urls:
        content = fetch_playlist_content(url)
        if content:
            parsed_channels = parse_m3u(content)
            print(f"✅ Parsed {len(parsed_channels)} valid channel entries from {url}.")
            all_channels.extend(parsed_channels)

    if URL_CHECK:
        all_channels = check_urls_concurrently(all_channels)

    # --- 优化步骤：只处理可访问的频道 ---
    processed_channels, processed_official_names = process_and_normalize_channels(all_channels, official_names, official_to_aliases, alias_to_official, official_lower_to_original)
    write_merged_playlist(processed_channels)

    # 检查缺失的频道
    if CHANNELS_TXT_FILTER and official_names:
        missing_channels = get_missing_channels(processed_official_names, official_names)
        if missing_channels:
            print(f"\n⚠️ Missing channels from {CHANNELS_TXT_PATH} (not found in sources): {len(missing_channels)} channels.")
            print(f"   Missing: {', '.join(missing_channels[:20])}{'...' if len(missing_channels) > 20 else ''}")
            print("   💡 Consider adding new sources or expanding aliases in channels.txt to cover these channels.")
        else:
            print(f"\n✅ All {len(official_names)} channels from {CHANNELS_TXT_PATH} found in sources.")

    end_time = datetime.now()
    print(f"\n✨ Merging complete at {end_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    print(f"⏱️ Total execution time: {(end_time - start_time).total_seconds():.2f} seconds.")


if __name__ == "__main__":
    main()