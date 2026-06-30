# utils/epg.py

import os
import sys
import traceback
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
# EPG_URL = "http://drewlive24.duckdns.org:8081/DrewLive.xml.gz"
# EPG_URL = "https://tvpass.org/epg.xml"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"

# 定义输入和输出文件路径
PLAYLIST_PATH = os.path.join(OUT_DIR, "MergedCleanPlaylist.m3u8")
TMP_EPG_PATH = os.path.join(OUT_DIR, "epg_temp.xml")
FINAL_EPG_PATH = os.path.join(OUT_DIR, "DrewLive3.xml")


def download_epg():
    """
    下载 EPG 文件到临时位置。
    """
    print(f"📥  Downloading EPG from {EPG_URL}...")
    try:
        response = requests.get(EPG_URL, timeout=20)
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
    从合并后的播放列表中提取映射关系。
    Returns:
        (dict, dict): 返回两个字典
                      1. tvg-id -> title
                      2. title -> tvg-id (用于备用匹配)
    """
    playlist_id_to_title = {}
    playlist_title_to_id = {}
    try:
        with open(PLAYLIST_PATH, "r", encoding="utf-8") as f:
            playlist_content = f.read()

        channels = parse_m3u(playlist_content)

        for tvg_name, tvg_id, tvg_logo, group_title, title, headers, url in channels:
            if tvg_id:
                playlist_id_to_title[tvg_id] = title
            playlist_title_to_id[title] = tvg_id

        print(f"🔍 Found {len(playlist_id_to_title)} unique channel ID-to-title mappings in the playlist.")
        print(f"🔍 Found {len(playlist_title_to_id)} unique channel title_to_id mappings in the playlist.")
    except FileNotFoundError:
        print(f"❌ Playlist file not found at: {PLAYLIST_PATH}")
    except Exception as e:
        print(f"❌ Error reading playlist file: {e}")

    return playlist_id_to_title, playlist_title_to_id

def clean_and_compress_epg():
    """
    【核心重构】使用两步处理法，健壮地筛选并简化 EPG。
    1. 快速扫描 EPG 源文件，建立 `epg_id -> epg_name` 的完整地图。
    2. 根据播放列表和 EPG 地图，建立一个 `epg_id -> final_title` 的主映射。
    3. 再次扫描 EPG 源文件，使用主映射来生成高度简化的新 EPG。
    """
    playlist_id_to_title, playlist_title_to_id = get_channel_data_from_playlist()
    if not playlist_id_to_title:
        print("⚠️ No valid channel data found. Aborting EPG cleaning.")
        return False

    valid_playlist_ids = set(playlist_id_to_title.keys())
    valid_playlist_titles = set(playlist_title_to_id.keys())

    # --- Pass 1: 快速扫描 EPG，建立原始频道地图 ---
    print("🔍 Pass 1: Scanning EPG to map original channel IDs to names...")
    epg_id_to_name_map = {}
    try:
        with open(TMP_EPG_PATH, 'rb') as f:
            for _, elem in ET.iterparse(f, events=('end',)):
                if elem.tag == 'channel':
                    channel_id = elem.get('id')
                    display_name_node = elem.find('display-name')
                    if channel_id and display_name_node is not None and display_name_node.text:
                        epg_id_to_name_map[channel_id] = display_name_node.text
                    # 清理元素以释放内存，
                    elem.clear()

    except Exception as e:
        print(f"❌ An error occurred during Pass 1 (EPG scan): {e}")
        traceback.print_exc()
        return False
    print(f"ℹ️ Found {len(epg_id_to_name_map)} channels in the source EPG.")

    # --- 建立主映射关系 (epg_id -> final_title) ---
    print("🗺️  Building master mapping from EPG to playlist...")
    master_map = {}
    epg_name_set = set()

    for epg_id, epg_name in epg_id_to_name_map.items():
        # 优先策略：通过 tvg-id 匹配
        if epg_id in valid_playlist_ids:
            master_map[epg_id] = playlist_id_to_title[epg_id]
        # 备用策略：通过频道名匹配
        elif epg_name in valid_playlist_titles and epg_name not in epg_name_set:
            master_map[epg_id] = epg_name
            epg_name_set.add(epg_name)
    if not master_map:
        print("⚠️ No matching channels found between playlist and EPG. Aborting.")
        return False

    print(f"✅ Master mapping created. {len(master_map)} EPG channels will be kept.")

    # --- Pass 2: 构建简化的新 EPG ---
    print("🧹 Pass 2: Cleaning, simplifying, and remapping EPG content...")
    new_root = ET.Element("tv")

    # 1. 添加 <channel> 节点
    # 使用 master_map 的值创建唯一的频道列表
    final_channel_titles = sorted(list(set(master_map.values())))
    for title in final_channel_titles:
        new_channel = ET.Element('channel', {'id': title})
        display_name = ET.SubElement(new_channel, 'display-name')
        display_name.text = title
        new_root.append(new_channel)
    channel_count = len(final_channel_titles)

    # 2. 添加 <programme> 节点
    programme_count = 0

    try:
        with open(TMP_EPG_PATH, 'rb') as f:
            for _, elem in ET.iterparse(f, events=('end',)):
                if elem.tag == 'programme':
                    original_channel_id = elem.get('channel')
                    # 如果节目对应的频道在主映射中
                    if original_channel_id in master_map:
                        target_title = master_map[original_channel_id]

                        # 创建简化的 programme 节点
                        new_attrib = {
                            'channel': target_title,
                            'start': elem.get('start', ''),
                            'stop': elem.get('stop', ''),
                        }
                        new_programme = ET.Element('programme', attrib=new_attrib)

                        # 只复制 title 子节点
                        title_node = elem.find('title')
                        if title_node is not None and title_node.text:
                            ET.SubElement(new_programme, 'title', {'lang': 'eng'}).text = title_node.text

                        new_root.append(new_programme)
                        programme_count += 1
                    elem.clear()  # 关键！释放内存
                # 复制根节点的属性
                elif elem.tag == 'tv':
                    if 'date' in elem.attrib:
                        new_root.set('date', elem.get('date'))
                    elem.clear()  # 关键！释放内存


        print(f"ℹ️ Kept {channel_count} channels and {programme_count} programmes (simplified and remapped).")

        # --- 美化并写入文件 ---
        rough_string = ET.tostring(new_root, 'utf-8', xml_declaration=True)
        reparsed = minidom.parseString(rough_string)
        pretty_xml_as_bytes = reparsed.toprettyxml(indent="  ", encoding='utf-8')

        with open(FINAL_EPG_PATH, "wb") as f_out:
            f_out.write(pretty_xml_as_bytes)

        print(f"✅ EPG cleaning and simplification complete. Saved to {FINAL_EPG_PATH}")
        return True

    except FileNotFoundError:
        print(f"❌ Temporary EPG file not found: {TMP_EPG_PATH}.")
        return False
    except ET.ParseError as e:
        print(f"❌ Failed to parse XML from EPG file: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred during EPG cleaning: {e}")
        traceback.print_exc()
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
    # merge_playlists.main(URL_CHECK=False)
    main()
