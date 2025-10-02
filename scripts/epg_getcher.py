import os
import gzip
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

EPG_URL = "http://drewlive24.duckdns.org:8081/DrewLive2.xml.gz"
TMP_PATH = "out/DrewLive2_tmp.xml.gz"
XML_PATH = "out/DrewLive2_clean.xml"
SAVE_PATH = "out/DrewLive2.xml.gz"
PLAYLIST_PATH = "out/MergedCleanPlaylist.m3u8"

def download_epg():
    print("📥 下载 EPG 文件中...")
    try:
        response = requests.get(EPG_URL, timeout=30)
        response.raise_for_status()
        with open(TMP_PATH, "wb") as f:
            f.write(response.content)
        print("✅ 下载成功")
        return True
    except Exception as e:
        print(f"❌ 下载失败：{e}")
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
        print(f"❌ 无法读取频道列表：{e}")
    return ids


def clean_epg():
    print("🧹 清理 EPG 内容中...")
    try:
        with gzip.open(TMP_PATH, "rb") as f:
            xml_data = f.read()
        root = ET.fromstring(xml_data)
        valid_ids = extract_valid_ids()

        new_root = ET.Element("tv", attrib={"date": datetime.now().strftime("%Y%m%d%H%M%S +0800")})

        # 保留频道定义
        for channel in root.findall("channel"):
            cid = channel.attrib.get("id")
            if cid in valid_ids:
                ch_elem = ET.SubElement(new_root, "channel", {"id": cid})
                name = channel.find("display-name")
                if name is not None:
                    name_elem = ET.SubElement(ch_elem, "display-name", {"lang": "en"})
                    name_elem.text = name.text

        # 保留节目内容
        for prog in root.findall("programme"):
            cid = prog.attrib.get("channel")
            if cid in valid_ids:                
                new_prog = ET.Element("programme", prog.attrib)
                title = prog.find("title")
                desc = prog.find("desc")
                if title is not None:
                    ET.SubElement(new_prog, "title", {"lang": "en"}).text = title.text
                if desc is not None:
                    ET.SubElement(new_prog, "desc", {"lang": "en"}).text = desc.text
                new_root.append(new_prog)

        # 美化并保存 XML
        xml_str = ET.tostring(new_root, encoding="utf-8")
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ", newl="\n")
        with open(XML_PATH, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

        # 压缩为 .gz
        with open(XML_PATH, "rb") as f_in, gzip.open(SAVE_PATH, "wb") as f_out:
            f_out.write(f_in.read())

        print("✅ 清理完成，已保存压缩版 EPG")
    except Exception as e:
        print(f"❌ 清理失败：{e}")

def main():
    print("🚀 启动 epg_getcher")
    if download_epg():
        clean_epg()
        os.remove(TMP_PATH)
        os.remove(XML_PATH)
    else:
        print("⚠️ 跳过清理，因下载失败")

if __name__ == "__main__":
    main()
