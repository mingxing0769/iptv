# utils/epg.py

import os
import sys
import traceback
import logging
import xml.etree.ElementTree as ET
# 导入 minidom 库用于美化 XML 输出
from xml.dom import minidom

import requests
import gzip
import io

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- EPG 自动识别与流式解析 ---
def is_gzip_bytes(content: bytes) -> bool:
    """判断字节是否为 gzip 格式。"""
    return content[:2] == bytes([0x1F, 0x8B])


def looks_like_xml(content: bytes) -> bool:
    """判断字节是否像 XML 文本，兼容 BOM、空白和声明。"""
    if not content:
        return False
    sample = content[:1024].lstrip()
    sample = sample.lstrip(bytes([0xEF, 0xBB, 0xBF]))
    return sample.startswith(b"<?xml") or sample.startswith(b"<tv") or sample.startswith(bytes([60, 33, 10]))


def get_epg_fileobj(raw_content: bytes):
    """按 EPG_URL 返回的原始格式返回可迭代解析的文件对象，避免写入巨大临时文件。"""
    if is_gzip_bytes(raw_content):
        return gzip.GzipFile(fileobj=io.BytesIO(raw_content))
    return io.BytesIO(raw_content)


def iter_epg_elements(raw_content: bytes, target_tag: str | None = None):
    """按 EPG 原始格式流式迭代 XML 元素，避免一次性加载巨大解压内容。"""
    with get_epg_fileobj(raw_content) as epg_file:
        for _, elem in ET.iterparse(epg_file, events=("end",)):
            if target_tag is None or elem.tag == target_tag:
                yield elem



# --- 路径配置 ---
# 自动计算项目根目录，让路径在任何地方运行都正确
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_ROOT, "out")

# 允许直接运行 python scripts/epg_getcher.py，同时兼容 GitHub Actions 的 PYTHONPATH。
if os.path.basename(sys.path[0]) == "scripts":
    sys.path.insert(0, PROJECT_ROOT)

# 导入我们需要的 m3u 解析工具
from utils.m3u_parse import parse_m3u

# EPG 源地址列表（按优先级排序，主源失效时自动尝试备用源）
EPG_URLS = [
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
    "http://epg.51zmt.top:8000/e.xml",
    "https://raw.githubusercontent.com/fanmingming/live/main/e.xml",
]

# 定义输入和输出文件路径
PLAYLIST_PATH = os.path.join(OUT_DIR, "MergedCleanPlaylist.m3u8")
FINAL_EPG_PATH = os.path.join(OUT_DIR, "DrewLive3.xml")


def download_epg():
    """
    下载 EPG 内容，并按返回格式流式解析。

    支持 EPG_URL 返回以下格式：
    1. gzip 二进制（.gz 或文件头 1f 8b）
    2. 普通 XML 文本
    3. URL 重定向后仍是 XML 文本
    4. 错误页面/非 XML 文本（明确失败，避免后续按 XML 解析崩溃）
    """
    raw_content = None
    for epg_url in EPG_URLS:
        logger.info(f"📥  Trying to download EPG from {epg_url}...")
        try:
            response = requests.get(epg_url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            os.makedirs(OUT_DIR, exist_ok=True)

            raw_content = response.content
            logger.info(f"ℹ️  Raw EPG bytes: {len(raw_content)} bytes, Content-Type: {response.headers.get('content-type', 'n/a')}")

            if is_gzip_bytes(raw_content):
                logger.info("ℹ️  Detected gzip EPG, streaming decompression during parsing...")
            elif looks_like_xml(raw_content):
                logger.info("ℹ️  Detected plain XML EPG, streaming parsing...")
            else:
                preview = raw_content[:500].decode("utf-8", errors="replace")
                logger.error(f"❌ EPG response from {epg_url} is not gzipped XML or XML text. Response preview:\n{preview}")
                raw_content = None
                continue

            logger.info(f"✅ EPG downloaded successfully from {epg_url}; parsing without writing a huge decompressed temp file.")
            return raw_content
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ EPG download failed from {epg_url}: {e}")
            continue
        except (OSError, UnicodeDecodeError, gzip.BadGzipFile, ET.ParseError) as e:
            logger.error(f"❌ EPG processing failed from {epg_url}: {e}")
            traceback.print_exc()
            raw_content = None
            continue

    logger.error("❌ All EPG sources failed. Cannot proceed.")
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

        logger.info(f"🔍 Found {len(playlist_id_to_title)} unique channel ID-to-title mappings in the playlist.")
        logger.info(f"🔍 Found {len(playlist_title_to_id)} unique channel title_to_id mappings in the playlist.")
    except FileNotFoundError:
        logger.error(f"❌ Playlist file not found at: {PLAYLIST_PATH}")
    except Exception as e:
        logger.error(f"❌ Error reading playlist file: {e}")

    return playlist_id_to_title, playlist_title_to_id

def clean_and_compress_epg(raw_content: bytes):
    """
    【核心重构】使用两步处理法，健壮地筛选并简化 EPG。
    1. 从 EPG_URL 原始内容流式扫描，建立 `epg_id -> epg_name` 的完整地图。
    2. 根据播放列表和 EPG 地图，建立一个 `epg_id -> final_title` 的主映射。
    3. 再次流式扫描 EPG 内容，使用主映射来生成高度简化的新 EPG。
    """
    playlist_id_to_title, playlist_title_to_id = get_channel_data_from_playlist()
    if not playlist_id_to_title:
        logger.warning("⚠️ No valid channel data found. Aborting EPG cleaning.")
        return False

    valid_playlist_ids = set(playlist_id_to_title.keys())
    valid_playlist_titles = set(playlist_title_to_id.keys())

    # --- Pass 1: 快速扫描 EPG，建立原始频道地图 ---
    logger.info("🔍 Pass 1: Scanning EPG to map original channel IDs to names...")
    epg_id_to_name_map = {}
    try:
        for elem in iter_epg_elements(raw_content, 'channel'):
            channel_id = elem.get('id')
            display_name_node = elem.find('display-name')
            if channel_id and display_name_node is not None and display_name_node.text:
                epg_id_to_name_map[channel_id] = display_name_node.text
            # 清理元素以释放内存
            elem.clear()

    except Exception as e:
        logger.error(f"❌ An error occurred during Pass 1 (EPG scan): {e}")
        traceback.print_exc()
        return False
    logger.info(f"ℹ️ Found {len(epg_id_to_name_map)} channels in the source EPG.")

    # --- 建立主映射关系 (epg_id -> final_title) ---
    logger.info("🗺️  Building master mapping from EPG to playlist...")
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
        logger.warning("⚠️ No matching channels found between playlist and EPG. Aborting.")
        return False

    logger.info(f"✅ Master mapping created. {len(master_map)} EPG channels will be kept.")

    # --- Pass 2: 构建简化的新 EPG ---
    logger.info("🧹 Pass 2: Cleaning, simplifying, and remapping EPG content...")
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
        for elem in iter_epg_elements(raw_content, 'programme'):
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
        for elem in iter_epg_elements(raw_content, 'tv'):
            if 'date' in elem.attrib:
                new_root.set('date', elem.get('date'))
            elem.clear()  # 关键！释放内存


        logger.info(f"ℹ️ Kept {channel_count} channels and {programme_count} programmes (simplified and remapped).")

        # --- 美化并写入文件 ---
        rough_string = ET.tostring(new_root, 'utf-8', xml_declaration=True)
        reparsed = minidom.parseString(rough_string)
        pretty_xml_as_bytes = reparsed.toprettyxml(indent="  ", encoding='utf-8')

        with open(FINAL_EPG_PATH, "wb") as f_out:
            f_out.write(pretty_xml_as_bytes)

        logger.info(f"✅ EPG cleaning and simplification complete. Saved to {FINAL_EPG_PATH}")
        return True

    except ET.ParseError as e:
        logger.error(f"❌ Failed to parse XML from EPG file: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred during EPG cleaning: {e}")
        traceback.print_exc()
        return False

def main():
    """主执行函数"""
    logger.info("🚀 Starting EPG processing...")
    raw_content = download_epg()
    if raw_content is None or raw_content is False:
        logger.error("❌ EPG download failed or returned invalid content. Cannot proceed.")
        sys.exit(1)

    try:
        if not clean_and_compress_epg(raw_content):
            logger.error("❌ EPG processing failed. Please check the logs above.")
            sys.exit(1)
    except (OSError, UnicodeDecodeError, gzip.BadGzipFile, ET.ParseError) as e:
        logger.error(f"❌ EPG processing failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    logger.info(f"✅ EPG processing finished. Final EPG saved to {FINAL_EPG_PATH}.")

if __name__ == "__main__":
    # merge_playlists.main(URL_CHECK=False)
    main()
