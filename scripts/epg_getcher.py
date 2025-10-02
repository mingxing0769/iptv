import os
import gzip
import requests
import xml.etree.ElementTree as ET

EPG_URL = "http://drewlive24.duckdns.org:8081/DrewLive2.xml.gz"
TMP_PATH = "out/DrewLive2_tmp.xml.gz"
SAVE_PATH = "out/DrewLive2.xml.gz"
PLAYLIST_PATH = "out/MergedCleanPlaylist.m3u8"

def download_epg():
    try:
        print("📥 正在下载 EPG 文件...")
        response = requests.get(EPG_URL, timeout=30)
        if response.status_code == 200:
            with open(TMP_PATH, "wb") as f:
                f.write(response.content)
            print("✅ 下载成功")
            return True
        else:
            print("❌ 下载失败，状态码：", response.status_code)
            return False
    except Exception as e:
        print("❌ 下载异常：", e)
        return False

def extract_valid_ids():
    ids = set()
    try:
        with open(PLAYLIST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if "tvg-id=" in line:
                    start = line.find('tvg-id="') + 8
                    end = line.find('"', start)
                    ids.add(line[start:end])
        print(f"🔍 提取频道 ID 共 {len(ids)} 个")
    except Exception as e:
        print("❌ 无法读取频道列表：", e)
    return ids

def clean_epg():
    try:
        with gzip.open(TMP_PATH, "rb") as f:
            xml_data = f.read()
        root = ET.fromstring(xml_data)

        valid_ids = extract_valid_ids()
        new_root = ET.Element("tv")

        # 保留频道定义
        for channel in root.findall("channel"):
            cid = channel.attrib.get("id")
            if cid in valid_ids:
                new_channel = ET.Element("channel", id=cid)
                display = channel.find("display-name")
                if display is not None:
                    new_display = ET.SubElement(new_channel, "display-name")
                    new_display.text = display.text
                new_root.append(new_channel)

        # 保留节目内容
        for prog in root.findall("programme"):
            cid = prog.attrib.get("channel")
            if cid in valid_ids:
                new_prog = ET.Element("programme", prog.attrib)
                title = prog.find("title")
                desc = prog.find("desc")
                if title is not None:
                    new_title = ET.SubElement(new_prog, "title")
                    new_title.text = title.text
                if desc is not None:
                    new_desc = ET.SubElement(new_prog, "desc")
                    new_desc.text = desc.text
                new_root.append(new_prog)

        # 保存压缩后的新文件
        tree = ET.ElementTree(new_root)
        with gzip.open(SAVE_PATH, "wb") as f:
            f.write(b"<?xml version='1.0' encoding='UTF-8'?>\n")
            tree.write(f, encoding="utf-8")

        print("✅ 清理完成，已保存精简版 EPG")
    except Exception as e:
        print("❌ 清理失败：", e)

def main():
    print("🚀 启动 epg_getcher")
    if download_epg():
        clean_epg()
        os.remove(TMP_PATH)
    else:
        print("⚠️ 跳过清理，因下载失败")

if __name__ == "__main__":
    main()
