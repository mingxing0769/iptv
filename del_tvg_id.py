"""
此脚本用来删除节目信息中的tvg-id以适应某些播放器 因存在tvg-id而不能显示节目单的问题
"""
import re
import os
from utils.m3u_parse import parse_m3u

# --- 配置区 ---
SOURCE_FILE = "out/MergedCleanPlaylist.m3u8"
NO_TVG_ID_FILE ="out/MergedCleanPlaylist_no_tvg_id.m3u8"

def remove_tvg_id_from_m3u(source_path: str, dest_path: str):
    """
    从 M3U 文件中读取内容，移除 #EXTINF 行中的 tvg-id 属性，然后写入新文件。

    Args:
        source_path (str): 源文件路径。
        dest_path (str): 目标文件路径。
    """
    print(f"正在读取源文件: {source_path}")

    try:
        with open(source_path, 'r', encoding='utf-8') as f_in:
            lines = f_in.readlines()
    except FileNotFoundError:
        print(f"错误: 源文件未找到 -> {source_path}")
        return
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return

    modified_lines = []
    for line in lines:
        # 检查是否是包含频道信息的行
        if line.strip().startswith("#EXTINF:"):
            # 使用正则表达式查找并移除 tvg-id="..." 属性
            # 这个正则表达式会匹配 tvg-id 及其引用的值，以及前后的空白字符
            # re.sub 会用一个空格替换匹配到的内容，以保持格式
            line = re.sub(r'\s*tvg-id="[^"]*"\s*', ' ', line)
        modified_lines.append(line)

    # 确保输出目录存在
    output_dir = os.path.dirname(dest_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已创建输出目录: {output_dir}")

    try:
        with open(dest_path, 'w', encoding='utf-8') as f_out:
            f_out.writelines(modified_lines)
        print(f"处理完成！已移除 tvg-id 并保存到: {dest_path}")
    except Exception as e:
        print(f"写入文件时发生错误: {e}")

def main():
    """
    主函数
    """
    remove_tvg_id_from_m3u(SOURCE_FILE, NO_TVG_ID_FILE)

if __name__ == "__main__":
    main()
