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
EPG_URL = "http://drewlive24.duckdns.org/DrewLive3.xml.gz"

# 定义输入和输出文件路径
PLAYLIST_PATH = os.path.join(OUT_DIR, "MergedCleanPlaylist.m3u8")
TMP_EPG_PATH = os.path.join(OUT_DIR, "epg_temp.xml.gz")
FINAL_EPG_PATH = os.path.join(OUT_DIR, "DrewLive3.xml.gz")


def download_epg():
    """
    下载 EPG 文件到临时位置。
    """
    print(f"📥  Downloading EPG from {EPG_URL}...")
    try:
        response = requests.get(EPG_URL, timeout=120)
        response.raise_for_status()
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
    这是实现转换逻辑的关键数据。
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
                # 我们需要的是 tvg-id -> title 的映射关系
                id_to_title_map[tvg_id] = title

        print(f"🔍 Found {len(id_to_title_map)} unique channel ID-to-title mappings in the playlist.")
    except FileNotFoundError:
        print(f"❌ Playlist file not found at: {PLAYLIST_PATH}")
    except Exception as e:
        print(f"❌ Error reading playlist file: {e}")
    return id_to_title_map


def clean_and_compress_epg():
    """
    【核心变更】使用流式解析，并将 EPG 中的 id 和 channel 属性从 tvg-id 替换为频道名 title。
    """
    id_to_title_map = get_channel_data_from_playlist()
    if not id_to_title_map:
        print("⚠️ No valid channel data found. Aborting EPG cleaning.")
        return False

    # valid_ids 集合现在存储的是所有需要处理的 tvg-id
    valid_ids = set(id_to_title_map.keys())
    print("🧹 Cleaning EPG content and remapping IDs to channel titles...")

    new_root = ET.Element("tv")

    # 为了防止重复创建相同的 <channel> 标签，我们需要一个集合来跟踪已经添加的 title
    added_channel_titles = set()

    channel_count = 0
    programme_count = 0

    try:
        with gzip.open(TMP_EPG_PATH, 'rb') as f:
            context = ET.iterparse(f, events=('end',))

            for event, elem in context:
                # --- 【变更】处理 <channel> 节点 ---
                if elem.tag == 'channel':
                    original_id = elem.get('id')
                    # 检查原始ID是否在我们的有效 tvg-id 列表中
                    if original_id in valid_ids:
                        # 获取我们想要替换成的目标 title
                        target_title = id_to_title_map[original_id]

                        # 只有当这个 title 对应的 <channel> 还没被添加过时，才创建它
                        if target_title.lower() not in added_channel_titles:
                            # 1. 创建一个全新的 <channel> 元素，其 id 就是频道名
                            new_channel = ET.Element('channel', {'id': target_title})

                            # 2. 创建并附加 <display-name>，内容也是频道名
                            display_name = ET.SubElement(new_channel, 'display-name', {'lang': 'en'})
                            display_name.text = target_title

                            # 3. 将新元素附加到根节点
                            new_root.append(new_channel)
                            added_channel_titles.add(target_title.lower())
                            channel_count += 1

                    # 无论如何都要清理内存
                    elem.clear()

                # --- 【变更】处理 <programme> 节点 ---
                elif elem.tag == 'programme':
                    original_channel_id = elem.get('channel')
                    # 检查原始 channel 属性是否在我们的有效 tvg-id 列表中
                    if original_channel_id in valid_ids:
                        # 获取我们想要替换成的目标 title
                        target_title = id_to_title_map[original_channel_id]

                        # 1. 复制原始属性
                        new_attrib = elem.attrib.copy()
                        # 2. 【关键】将 'channel' 属性的值修改为频道名
                        new_attrib['channel'] = target_title

                        # 3. 创建一个新的 <programme> 元素
                        new_programme = ET.Element('programme', attrib=new_attrib)

                        # 4. 复制 <title> 子节点
                        title_node = elem.find('title')
                        if title_node is not None and title_node.text:
                            ET.SubElement(new_programme, 'title', {'lang': 'en'}).text = title_node.text

                        # 5. 将新元素附加到根节点
                        new_root.append(new_programme)
                        programme_count += 1

                    # 无论如何都要清理内存
                    elem.clear()

                # --- 处理根 <tv> 节点 ---
                elif elem.tag == 'tv':
                    if 'date' in elem.attrib:
                        new_root.set('date', elem.get('date'))
                    elem.clear()

        print(f"ℹ️ Kept {channel_count} channels and {programme_count} programmes (remapped to title).")

        # --- 美化并写入文件 ---
        rough_string = ET.tostring(new_root, 'utf-8', xml_declaration=True)
        reparsed = minidom.parseString(rough_string)
        pretty_xml_as_bytes = reparsed.toprettyxml(indent="  ", encoding='utf-8')

        with gzip.open(FINAL_EPG_PATH, "wb") as f_out:
            f_out.write(pretty_xml_as_bytes)

        print(f"✅ EPG cleaning complete. Saved to {FINAL_EPG_PATH}")
        return True

    except FileNotFoundError:
        print(f"❌ Temporary EPG file not found: {TMP_EPG_PATH}.")
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
    if not download_epg():
        print(f"⚠️ EPG download failed. Will try to use the last downloaded version at {TMP_EPG_PATH}")

    if not os.path.exists(TMP_EPG_PATH):
        print(f"❌ No EPG file found at {TMP_EPG_PATH}. Cannot proceed.")
        sys.exit(1)

    if not clean_and_compress_epg():
        print("❌ EPG processing failed. Please check the logs above.")
        sys.exit(1)

    print(f"✅ EPG processing finished. Temporary file {TMP_EPG_PATH} is kept as a fallback.")


if __name__ == "__main__":
    main()
