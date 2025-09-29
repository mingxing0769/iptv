import requests
import re
import time
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
import os

# --- 配置区 ---
# 播放列表源
playlist_urls = [
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/DaddyLive.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/DaddyLiveEvents.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/DrewAll.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/JapanTV.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/PlexTV.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/PlutoTV.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/TubiTV.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/DrewLiveVOD.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/TVPass.m3u",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/Radio.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/Roku.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/TheTVApp.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/LGTV.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/AriaPlus.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/LocalNowTV.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/PPVLand.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/SamsungTVPlus.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/main/Xumo.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/FSTV24.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/MoveOnJoy.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/A1x.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/StreamedSU.m3u8",
    "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/SportsWebcast.m3u8"
]

# EPG 电子节目单地址
EPG_URL = "http://drewlive24.duckdns.org:8081/merged2_epg.xml.gz"
# 输出文件名
OUTPUT_FILE = "out/MergedCleanPlaylist.m3u8"
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# --- 功能开关 ---
# 是否开启 URL 可用性检测 (会显著增加运行时间)
CHECK_URLS = True
# 检测时的超时时间 (秒)
URL_TIMEOUT = 5
# 检测时使用的最大线程数
MAX_WORKERS = 20


def fetch_playlist(url, retries=3, timeout=15):
    """获取并返回播放列表内容"""
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempting to fetch {url} (try {attempt})...")
            res = requests.get(url, timeout=timeout, headers=headers)
            res.raise_for_status()
            print(f"✅ Successfully fetched {url}")
            return res.text.strip().splitlines()
        except Exception as e:
            print(f"❌ Attempt {attempt} failed for {url}: {e}")
            time.sleep(2)
    print(f"⚠️ Skipping {url} after {retries} failed attempts.")
    return []


def parse_playlist(lines, source_url="Unknown"):
    """
    一个健壮的M3U解析器，使用状态机模型处理频道和分组。
    - 正确处理 #EXTGRP 上下文。
    - 只有当一个频道同时拥有 #EXTINF 和 URL 时才被视为有效。
    - 自动为缺少 group-title 的频道补充分组信息。
    """
    channels = []
    current_group = "Other"  # 默认分组

    # 临时存储当前正在解析的频道信息
    extinf = None
    headers = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('#EXTGRP:'):
            # 1. 遇到新的分组定义
            current_group = line.split(':', 1)[-1].strip()
            # 一个新的分组开始，意味着上一个不完整的频道（如果有的话）应该被丢弃
            extinf = None
            headers = []

        elif line.startswith('#EXTINF:'):
            # 2. 遇到新的频道信息行
            # 如果之前有一个待处理的频道但没有URL，它将被这个新的#EXTINF覆盖（即丢弃）
            extinf = line
            headers = []  # 重置头部信息

        elif line.startswith('#') and extinf:
            # 3. 遇到其他头部信息（如 #EXTVLCOPT），且我们正处于一个频道块中
            headers.append(line)

        elif extinf and not line.startswith('#'):
            # 4. 遇到一个非'#'开头的行，这应该是URL
            url_line = line

            # 检查 #EXTINF 行是否已有 group-title
            group_title_match = re.search(r'group-title="([^"]+)"', extinf)

            if not group_title_match:
                # 如果 #EXTINF 中没有 group-title，使用我们从 #EXTGRP 追踪的当前分组
                # 尝试在最后一个引号后注入，这是一个比较稳妥的位置
                new_extinf, count = re.subn(r'(")(?!.*")', rf'\1 group-title="{current_group}"', extinf,
                                            count=1)
                if count == 0:  # 如果没有找到引号，就直接追加
                    new_extinf = f'{extinf} group-title="{current_group}"'
            else:
                # 如果 #EXTINF 中已有 group-title，则使用它自己的
                new_extinf = extinf

            # 添加完整频道记录
            channels.append((new_extinf, tuple(headers), url_line))

            # 重置状态，准备解析下一个频道
            extinf = None
            headers = []

    print(f"✅ Parsed {len(channels)} valid channel entries from {source_url}.")
    return channels


def normalize_title(title):
    """
    移除频道名称中的清晰度、来源等标识，实现同名化。
    例如: 'ESPN HD' -> 'ESPN', 'Fox Sports 501 FHD' -> 'Fox Sports 501'
    """
    # 定义要移除的关键词列表，\b确保匹配的是完整单词
    indicators = [
        r'\bFHD\b', r'\bHD\b', r'\bSD\b', r'\bUHD\b', r'\b4K\b', r'\b2K\b', r'\b8K\b',

    ]

    normalized = title
    for indicator in indicators:
        normalized = re.sub(indicator, '', normalized, flags=re.IGNORECASE)

    # 清理可能留下的多余空格、末尾的连字符或括号
    normalized = re.sub(r'[\s\-_|(\[\]]+$', '', normalized).strip()
    # 将多个连续空格合并为一个
    normalized = ' '.join(normalized.split())

    return normalized if normalized else title


def process_and_normalize_channels(all_channels_list):
    """
    核心处理函数：
    1. 基于URL进行精确去重。
    2. 对频道名称进行标准化处理。
    """
    print("\n🔍 Starting normalization and de-duplication process...")

    processed_urls = set()
    final_channels = []

    for extinf, headers, url in tqdm(all_channels_list, desc="Processing Channels"):
        # 1. URL去重：如果这个流地址已经处理过，就跳过
        if url in processed_urls:
            continue
        processed_urls.add(url)

        # 2. 名称标准化
        try:
            info_part, original_title = extinf.rsplit(',', 1)
            original_title = original_title.strip()
        except ValueError:
            # 跳过格式不正确的 #EXTINF 行
            continue

        normalized_display_title = normalize_title(original_title)

        # 重新构建 #EXTINF 行，只更新末尾的显示名称
        new_extinf = f"{info_part},{normalized_display_title}"

        final_channels.append((new_extinf, headers, url))

    print(f"✅ Kept {len(final_channels)} unique channels after processing.")
    return final_channels


def is_nsfw(extinf, headers, url):
    """检查频道条目是否包含NSFW关键词"""
    nsfw_keywords = ['nsfw', 'xxx', 'porn', 'adult']
    combined_text = f"{extinf.lower()} {' '.join(headers).lower()} {url.lower()}"
    group_match = re.search(r'group-title="([^"]+)"', extinf.lower())
    if group_match and any(k in group_match.group(1) for k in nsfw_keywords):
        return True
    return any(k in combined_text for k in nsfw_keywords)


def is_url_accessible(channel_data):
    """
    检查单个URL是否可访问。
    如果可访问，返回原始频道数据；否则返回None。
    """
    extinf, headers, url = channel_data
    try:
        response = requests.head(url, timeout=URL_TIMEOUT, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        if 200 <= response.status_code < 400:
            return channel_data
    except (requests.exceptions.Timeout, requests.exceptions.RequestException):
        pass
    return None


def check_channel_urls(channels_to_check):
    """使用多线程并行检查所有频道的URL可用性。"""
    accessible_channels = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(is_url_accessible, data): data for data in channels_to_check}

        for future in tqdm(concurrent.futures.as_completed(future_to_url), total=len(channels_to_check),
                           desc="Checking URLs"):
            result = future.result()
            if result:
                accessible_channels.append(result)

    return accessible_channels


def write_merged_playlist(final_channels_to_write):
    """将最终的频道列表排序并写入文件"""
    lines = [f'#EXTM3U url-tvg="{EPG_URL}"', ""]
    sortable_channels = []

    for extinf, headers, url in final_channels_to_write:
        group_match = re.search(r'group-title="([^"]+)"', extinf)
        group = group_match.group(1) if group_match else "Other"
        try:
            # 使用我们已经标准化过的名称进行排序
            title = extinf.rsplit(',', 1)[-1].strip()
        except IndexError:
            title = "Unknown Title"
        sortable_channels.append((group.lower(), title.lower(), extinf, headers, url))

    sorted_channels = sorted(sortable_channels)
    current_group = None
    total_channels_written = 0

    for _, _, extinf, headers, url in sorted_channels:
        group_match = re.search(r'group-title="([^"]+)"', extinf)
        actual_group_name = group_match.group(1) if group_match else "Other"

        if actual_group_name != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f'#EXTGRP:{actual_group_name}')
            current_group = actual_group_name

        lines.append(extinf)
        lines.extend(headers)
        lines.append(url)
        total_channels_written += 1

    if lines and lines[-1] == "":
        lines.pop()

    final_output_string = '\n'.join(lines) + '\n'

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_output_string)

    print(f"\n✅ Merged playlist written to {OUTPUT_FILE}.")
    print(f"📊 Total channels written: {total_channels_written}.")
    print(f"📝 Total lines in output file: {len(final_output_string.splitlines())}.")


if __name__ == "__main__":
    start_time = time.time()
    print(f"🚀 Starting playlist merge at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")

    # 1. 获取所有源的原始频道数据
    raw_channels_list = []
    for url in playlist_urls:
        lines = fetch_playlist(url)
        if lines:
            parsed_channels = parse_playlist(lines, source_url=url)
            raw_channels_list.extend(parsed_channels)

    # 2. 统一处理：URL去重和名称标准化
    processed_channels = process_and_normalize_channels(raw_channels_list)

    # 3. 过滤NSFW内容
    non_nsfw_channels = [entry for entry in processed_channels if not is_nsfw(*entry)]
    removed_nsfw_count = len(processed_channels) - len(non_nsfw_channels)
    if removed_nsfw_count > 0:
        print(f"🗑️ Filtered out {removed_nsfw_count} NSFW channels.")

    # 4. 可选的URL可用性检测
    if CHECK_URLS:
        print("\n🌐 Starting URL accessibility check (this may take a while)...")
        final_list_to_write = check_channel_urls(non_nsfw_channels)
        inaccessible_count = len(non_nsfw_channels) - len(final_list_to_write)
        print(f"\n👍 Found {len(final_list_to_write)} accessible channels.")
        if inaccessible_count > 0:
            print(f"🗑️ Removed {inaccessible_count} inaccessible or timed-out channels.")
    else:
        print("\n⚠️ URL accessibility check is disabled. Skipping.")
        final_list_to_write = non_nsfw_channels

    # 5. 写入最终文件
    write_merged_playlist(final_list_to_write)

    end_time = time.time()
    print(f"\n✨ Merging complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")

    print(f"⏱️ Total execution time: {end_time - start_time:.2f} seconds.")



