import os
import hashlib
import requests

EPG_URL = "http://drewlive24.duckdns.org:8081/DrewLive2.xml.gz"
SAVE_PATH = "out/DrewLive2.xml.gz"
TMP_PATH = "out/DrewLive2.tmp.gz"

def file_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def download_epg():
    print("尝试下载 EPG 文件...")
    try:        
        response = requests.get(EPG_URL, timeout=30)
        if response.status_code == 200:
            with open(TMP_PATH, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"下载失败，状态码：{response.status_code}")
            return False
    except Exception as e:
        print(f"下载异常：{e}")
        return False

def main():
    if download_epg():
        new_hash = file_hash(TMP_PATH)
        old_hash = file_hash(SAVE_PATH)

        if new_hash != old_hash:
            print("文件有更新，保存新版本。")
            os.replace(TMP_PATH, SAVE_PATH)
        else:
            print("文件无变化，不更新。")
            os.remove(TMP_PATH)
    else:
        print("下载失败，跳过更新。")

if __name__ == "__main__":
    main()
