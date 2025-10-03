# utils/epg.py
import gzip
import os
import sys
import xml.etree.ElementTree as ET
# 导入 minidom 库用于美化 XML 输出
from xml.dom import minidom

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
FINAL_EPG_PATH = os.path.join(OUT_DIR, "DrewLive3.xml.gz")


def download_epg():
    """
    下载 EPG 文件到临时位置。
    如果下载成功，会覆盖旧的临时文件。
    如果下载失败，会保留旧的临时文件（如果存在）。
    """
    print(f"📥  Downloading EPG from {EPG_URL}...")
    try:
        response = requests.get(EPG_URL, timeout=120)  # 增加超时时间
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
    """
    id_to_title_map = {}
    try:
        with open(PLAYLIST_PATH, "r", encoding="utf-8") as f:
            playlist_content = f.read()

        channels = parse_m3u(playlist_content)

        for channel_data in channels:
            tvg_id = channel_data[1]
            title = channel_data[4]
            if tvg_id and title:
                id_to_title_map[tvg_id] = title

        print(f"🔍 Found {len(id_to_title_map)} unique channel ID-to-title mappings in the playlist.")
    except FileNotFoundError:
        print(f"❌ Playlist file not found at: {PLAYLIST_PATH}")
    except Exception as e:
        print(f"❌ Error reading playlist file: {e}")
    return id_to_title_map


def clean_and_compress_epg():
    """
    【核心优化】使用流式解析，并根据要求生成一个极度精简的 EPG 文件。
    """
    id_to_title_map = get_channel_data_from_playlist()
    if not id_to_title_map:
        print("⚠️ No valid channel data found. Aborting EPG cleaning.")
        return False

    valid_ids = set(id_to_title_map.keys())
    print("🧹 Cleaning EPG content and stripping to absolute minimum...")

    # 创建一个新的 XML 根元素，用于存放清理后的数据
    new_root = ET.Element("tv")

    channel_count = 0
    programme_count = 0

    try:
        # 直接以二进制模式打开 .gz 文件进行流式解压和解析
        with gzip.open(TMP_EPG_PATH, 'rb') as f:
            context = ET.iterparse(f, events=('end',))

            for event, elem in context:
                # --- 【精简版】处理 <channel> 节点 ---
                if elem.tag == 'channel':
                    channel_id = elem.get('id')
                    if channel_id in valid_ids:
                        # 1. 创建一个全新的、精简的 <channel> 元素
                        new_channel = ET.Element('channel', {'id': channel_id})

                        # 2. 创建并附加 <display-name>，使用播放列表中的名称
                        display_name = ET.SubElement(new_channel, 'display-name', {'lang': 'en'})
                        display_name.text = id_to_title_map[channel_id]

                        # 3. 将这个精简后的新元素附加到根节点
                        new_root.append(new_channel)
                        channel_count += 1

                    # 4. 清理原始元素以释放内存
                    elem.clear()

                # --- 【精简版】处理 <programme> 节点 ---
                elif elem.tag == 'programme':
                    if elem.get('channel') in valid_ids:
                        # 1. 创建一个新的 <programme> 元素，并复制所有属性 (start, stop, channel)
                        new_programme = ET.Element('programme', attrib=elem.attrib)

                        # 2. 只查找并复制第一个 <title> 的文本内容
                        title_node = elem.find('title')
                        if title_node is not None and title_node.text:
                            # 创建一个新的 title 元素，确保 lang="en"
                            ET.SubElement(new_programme, 'title', {'lang': 'en'}).text = title_node.text

                        # 3. 将这个精简后的新元素附加到根节点
                        new_root.append(new_programme)
                        programme_count += 1

                    # 4. 清理原始元素以释放内存
                    elem.clear()

                # --- 处理根 <tv> 节点 ---
                elif elem.tag == 'tv':
                    # 复制 'date' 属性
                    if 'date' in elem.attrib:
                        new_root.set('date', elem.get('date'))
                    elem.clear()

        print(f"ℹ️ Kept {channel_count} channels and {programme_count} programmes (minimal structure).")

        # --- 【新增】美化 XML 输出 ---
        # 1. 先用 ElementTree 生成一个紧凑的字节串
        rough_string = ET.tostring(new_root, 'utf-8')

        # 2. 使用 minidom 重新解析这个字节串
        reparsed = minidom.parseString(rough_string)

        # 3. 使用 toprettyxml 生成带缩进和换行的、美化后的字符串，并指定编码
        pretty_xml_as_bytes = reparsed.toprettyxml(indent="  ", encoding='utf-8')

        # --- 修改写入部分 ---
        # 将美化后的字节串写入 Gzip 文件
        with gzip.open(FINAL_EPG_PATH, "wb") as f_out:
            f_out.write(pretty_xml_as_bytes)

        print(f"✅ EPG cleaning complete. Saved to {FINAL_EPG_PATH}")
        return True

    except FileNotFoundError:
        print(f"❌ Temporary EPG file not found: {TMP_EPG_PATH}. Was the download successful?")
        return False
    except ET.ParseError as e:
        print(f"❌ Failed to parse XML from EPG file: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred during EPG cleaning: {e}")
        return False


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
        sys.exit(1)  # 关键：如果没有任何 EPG 文件，就以失败状态退出

    # 步骤 3: 清理并生成最终文件
    cleaning_successful = clean_and_compress_epg()

    # 步骤 4: 脚本结束，保留临时文件作为备份
    if cleaning_successful:
        print(f"✅ EPG processing finished. Temporary file {TMP_EPG_PATH} is kept as a fallback for the next run.")
    else:
        print("❌ EPG processing failed. Please check the logs above.")
        sys.exit(1)  # 关键：如果清理失败，也以失败状态退出


if __name__ == "__main__":
    main()
