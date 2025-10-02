# utils/epg.py
import gzip
import os
import xml.etree.ElementTree as ET

import requests

# --- 路径配置 ---
# 自动计算项目根目录，让路径在任何地方运行都正确


# EPG 源地址
EPG_URL = "http://drewlive24.duckdns.org:8081/DrewLive3.xml.gz"

# --- 路径配置 ---
# 自动计算项目根目录，让路径在任何地方运行都正确
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_ROOT, "out")

# 定义输入和输出文件路径
PLAYLIST_PATH = os.path.join(OUT_DIR, "MergedCleanPlaylist.m3u8")
TMP_EPG_PATH = os.path.join(OUT_DIR, "epg_temp.xml.gz")
FINAL_EPG_PATH = os.path.join(OUT_DIR, "DrewLive2.xml.gz")

def download_epg():
    """下载 EPG 文件到临时位置。"""
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


def extract_valid_ids_from_playlist():
    """从合并后的播放列表中提取所有有效的 tvg-id。"""
    valid_ids = set()
    try:
        with open(PLAYLIST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if 'tvg-id="' in line:
                    # 使用更稳健的方式提取 ID
                    start = line.find('tvg-id="') + len('tvg-id="')
                    end = line.find('"', start)
                    if end != -1:
                        channel_id = line[start:end].strip()
                        if channel_id:
                            valid_ids.add(channel_id)
        print(f"🔍 Found {len(valid_ids)} unique channel IDs in the playlist.")
    except FileNotFoundError:
        print(f"❌ Playlist file not found at: {PLAYLIST_PATH}")
    except Exception as e:
        print(f"❌ Error reading playlist file: {e}")
    return valid_ids


def clean_and_compress_epg():
    """
    清理 EPG 内容，只保留有效频道的节目单，并直接生成最终的压缩文件。
    """
    valid_ids = extract_valid_ids_from_playlist()
    if not valid_ids:
        print("⚠️ No valid channel IDs found. Aborting EPG cleaning.")
        return

    print("🧹 Cleaning EPG content...")
    try:
        with gzip.open(TMP_EPG_PATH, "rb") as f:
            xml_data = f.read()

        original_root = ET.fromstring(xml_data)

        # 创建一个新的 XML 根元素
        new_root = ET.Element("tv")

        # 复制原始 EPG 的 date 属性（如果存在）
        if 'date' in original_root.attrib:
            new_root.set('date', original_root.get('date'))

        # 1. 保留有效的频道定义 <channel>
        for channel_node in original_root.findall("channel"):
            if channel_node.get("id") in valid_ids:
                new_root.append(channel_node)

        # 2. 保留有效频道的节目单 <programme>
        for programme_node in original_root.findall("programme"):
            if programme_node.get("channel") in valid_ids:
                new_root.append(programme_node)

        # 3. 在内存中生成 XML 字符串，并直接压缩
        # xml_declaration=True 会自动添加 <?xml version='1.0' encoding='utf-8'?>
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
    print("🚀 Starting EPG processing...")

    # 步骤 1: 下载 EPG 文件
    if not download_epg():
        print("⚠️ Skipping cleaning process due to download failure.")
        return

    # 步骤 2: 清理并生成最终文件
    try:
        clean_and_compress_epg()
    finally:
        # 步骤 3: 无论成功与否，都清理临时文件
        if os.path.exists(TMP_EPG_PATH):
            os.remove(TMP_EPG_PATH)
            print(f"🗑️ Temporary file {TMP_EPG_PATH} deleted.")

if __name__ == "__main__":
    main()
