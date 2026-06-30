"""
IPTV 播放列表合并与清理脚本
"""
import os
import re
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from utils.filter_keywords import Indicators_key, Category_Key, Nsfw_Key
from config.sources_urls import playlist_urls
from utils.network import fetch_playlist_content, is_url_accessible
from utils.m3u_parse import parse_m3u
from utils.channel_filter import load_channels_txt, get_official_name, get_missing_channels
from utils.playlist_writer import process_and_normalize_channels, write_merged_playlist

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 配置区 ---
EPG_URL = "https://raw.githubusercontent.com/mingxing0769/iptv/main/out/DrewLive3.xml"
OUTPUT_FILE = "out/MergedCleanPlaylist.m3u8"

# 是否根据 channels.txt 进行频道筛选（仅保留 channels.txt 中的频道及其别名）
CHANNELS_TXT_FILTER = True
CHANNELS_TXT_PATH = "channels.txt"

# 是否对频道进行筛选，根据 utils.filter_keywords.Category_Key
CategoryFilter = True

# 并发检查 URL 有效性 ---
URL_CHECK = False

# 并发检查 URL 时的最大线程数，可以根据你的网络和 CPU 情况调整
MAX_WORKERS_URL_CHECK = 100


def is_nsfw(group_title, title):
    """检查频道的 group-title 或 title 是否包含 NSFW 关键词。"""
    nsfw_keywords = Nsfw_Key
    text_to_check = f"{group_title} {title}".lower()
    return any(keyword in text_to_check for keyword in nsfw_keywords)


def check_urls_concurrently(channels_to_check):
    """
    使用多线程并发检查频道 URL 的可访问性。

    Args:
        channels_to_check (list): 待检查的频道列表。

    Returns:
        list: 包含所有可访问频道的列表。
    """
    logger.info(f"\n🚀 Starting concurrent URL accessibility check for {len(channels_to_check)} channels (up to {MAX_WORKERS_URL_CHECK} workers)...")
    accessible_channels = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_URL_CHECK) as executor:
        # 创建 future 到 channel_data 的映射
        # channel 元组结构：(..., headers, url)
        # headers 在倒数第 2 个位置 (channel[-2]), url 在最后 (channel[-1])
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
                # 发生任何异常（如超时）都认为 URL 不可访问
                pass

    inaccessible_count = len(channels_to_check) - len(accessible_channels)
    logger.info(f"✓ Accessible channels: {len(accessible_channels)}")
    if inaccessible_count > 0:
        logger.warning(f"✗ Inaccessible or timed-out channels: {inaccessible_count}")
    return accessible_channels


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    start_time = datetime.now()
    logger.info(f"🚀 Starting playlist merge at {start_time.strftime('%Y-%m-%d %H:%M:%S')}...")

    # Load channels.txt if filtering is enabled
    official_names = set()
    official_to_aliases = {}
    alias_to_official = {}
    official_lower_to_original = {}
    if CHANNELS_TXT_FILTER:
        logger.info(f"📂 Loading allowed channels from {CHANNELS_TXT_PATH}...")
        official_names, official_to_aliases, alias_to_official, official_lower_to_original = load_channels_txt(CHANNELS_TXT_PATH)
        logger.info(f"✅ Loaded {len(official_names)} official channels and {len(alias_to_official)} aliases.")
    else:
        logger.warning("⚠️ CHANNELS_TXT_FILTER is False, skipping channels.txt filter.")

    all_channels = []
    for url in playlist_urls:
        content = fetch_playlist_content(url)
        if content:
            parsed_channels = parse_m3u(content)
            logger.info(f"✅ Parsed {len(parsed_channels)} valid channel entries from {url}.")
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
            logger.warning(f"\n⚠️ Missing channels from {CHANNELS_TXT_PATH} (not found in sources): {len(missing_channels)} channels.")
            logger.warning(f"   Missing: {', '.join(missing_channels[:20])}{'...' if len(missing_channels) > 20 else ''}")
            logger.info("   💡 Consider adding new sources or expanding aliases in channels.txt to cover these channels.")
        else:
            logger.info(f"\n✅ All {len(official_names)} channels from {CHANNELS_TXT_PATH} found in sources.")

    end_time = datetime.now()
    logger.info(f"\n✨ Merging complete at {end_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    logger.info(f"⏱️ Total execution time: {(end_time - start_time).total_seconds():.2f} seconds.")


if __name__ == "__main__":
    main()