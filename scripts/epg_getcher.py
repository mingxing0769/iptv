# utils/epg.py
import gzip
import os
import xml.etree.ElementTree as ET

import requests
# 导入我们需要的 m3u 解析工具
from utils.m3u_parse import parse_m3u

# --- 路径配置 ---
# 自动计算项目根目录，让路径在任何地方运行都正确
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_ROOT, "out")

# EPG 源地址
EPG_URL = "http://drewlive24.duckdns.org:8081/DrewLive3.xml.gz"

# 定义输入和输出文件路径
PLAYLIST_PATH = os.path.join(OUT_DIR, "MergedCleanPlaylist.m3u8")
TMP_EPG_PATH = os.path.join(OUT_DIR, "epg_temp.xml.gz")
FINAL_EPG_PATH = os.path.join(OUT_DIR, "DrewLive2.xml.gz")


def download_epg():
    """
    下载 EPG 文件到临时位置。
    如果下载成功，会覆盖旧的临时文件。
    如果下载失败，会保留旧的临时文件（如果存在）。
    """
    print(f"📥  Downloading EPG from {EPG_URL}...")
    try:
        response = requests.get(EPG_URL, timeout=60)
        response.raise_for_status()

        # 确保输出目录存在
        os.makedirs(OUT_DIR, exist_ok=True)

        with open(TMP_EPG_PATH, "wb") as f:
            f.write(response.content)
        print("✅ EPG downloaded successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ EPG download failed: {e}")
        return False


def get_channel_data_from_playlist():
    """
    从合并后的播放列表中提取 tvg-id 到 title 的映射。
    Returns:
        dict: 一个从 tvg-id 映射到其规范化 title 的字典。
              例如: {'id1.us': 'Channel One', 'id2.ca': 'Channel Two'}
    """
    id_to_title_map = {}
    try:
        with open(PLAYLIST_PATH, "r", encoding="utf-8") as f:
            playlist_content = f.read()

        # 使用 parse_m3u 函数获取详细的频道数据
        channels = parse_m3u(playlist_content)

        for channel_data in channels:
            # channel_data 是一个元组: (tvg_name, tvg_id, tvg_logo, group_title, title, headers, url)
            tvg_id = channel_data[1]
            title = channel_data[4]

            if tvg_id and title:
                # 我们只关心 tvg-id 到最终 title 的映射
                id_to_title_map[tvg_id] = title

        print(f"🔍 Found {len(id_to_title_map)} unique channel ID-to-title mappings in the playlist.")
    except FileNotFoundError:
        print(f"❌ Playlist file not found at: {PLAYLIST_PATH}")
    except Exception as e:
        print(f"❌ Error reading playlist file: {e}")
    return id_to_title_map


def clean_and_compress_epg():
    """
    清理 EPG 内容，只保留有效频道的节目单，更新 display-name, 并直接生成最终的压缩文件。
    """
    id_to_title_map = get_channel_data_from_playlist()
    if not id_to_title_map:
        print("⚠️ No valid channel data found. Aborting EPG cleaning.")
        return

    # 有效的 ID 集合就是我们 map 的键
    valid_ids = set(id_to_title_map.keys())
    print("🧹 Cleaning EPG content and updating display names...")
    try:
        with gzip.open(TMP_EPG_PATH, "rb") as f:
            xml_data = f.read()

        original_root = ET.fromstring(xml_data)

        # 创建一个新的 XML 根元素
        new_root = ET.Element("tv")

        # 复制原始 EPG 的 date 属性（如果存在）
        if 'date' in original_root.attrib:
            new_root.set('date', original_root.get('date'))

        # 1. 保留并更新有效的频道定义 <channel>
        for channel_node in original_root.findall("channel"):
            channel_id = channel_node.get("id")
            if channel_id in valid_ids:
                # 找到 display-name 元素
                display_name_node = channel_node.find("display-name")
                if display_name_node is not None:
                    # 用我们从播放列表里读到的规范化 title 来更新它的文本
                    display_name_node.text = id_to_title_map[channel_id]

                # 将修改后的节点附加到新的 XML 树中
                new_root.append(channel_node)

        # 2. 保留有效频道的节目单 <programme>
        for programme_node in original_root.findall("programme"):
            if programme_node.get("channel") in valid_ids:
                new_root.append(programme_node)

        # 3. 在内存中生成 XML 字符串，并直接压缩
        xml_str_in_memory = ET.tostring(new_root, encoding="utf-8", xml_declaration=True)

        with gzip.open(FINAL_EPG_PATH, "wb") as f_out:
            f_out.write(xml_str_in_memory)

        print(f"✅ EPG cleaning complete. Saved to {FINAL_EPG_PATH}")

    except FileNotFoundError:
        print(f"❌ Temporary EPG file not found: {TMP_EPG_PATH}. Was the download successful?")
    except ET.ParseError as e:
        print(f"❌ Failed to parse XML from EPG file: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred during EPG cleaning: {e}")


def main():
    """主执行函数"""
    print("🚀 Starting EPG processing...")

    # 步骤 1: 尝试下载新的 EPG 文件
    download_successful = download_epg()

    if not download_successful:
        print(f"⚠️ EPG download failed. Will try to use the last downloaded version at {TMP_EPG_PATH}")

    # 步骤 2: 检查是否存在可用的 EPG 文件（无论是新的还是旧的）
    if not os.path.exists(TMP_EPG_PATH):
        print(f"❌ No EPG file found at {TMP_EPG_PATH}. Cannot proceed with cleaning.")
        return

    # 步骤 3: 清理并生成最终文件
    # 只要有临时文件（新的或旧的），就执行清理
    clean_and_compress_epg()

    # 步骤 4: 脚本结束，保留临时文件作为备份
    print(f"✅ EPG processing finished. Temporary file {TMP_EPG_PATH} is kept as a fallback for the next run.")


if __name__ == "__main__":
    main()
