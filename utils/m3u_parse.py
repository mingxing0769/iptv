# utils/m3u_parse.py
import re


def parse_m3u(m3u_content):
    """
    m3u解析器：#EXTINF 和 URL，返回一个详细的记录列表。
    输入：m3u文本内容
    包含信息：tvg-name, tvg-id, tvg-logo, group-title, title, headers, url
    输出：元组列表 [(), (), ...]
    """
    if not m3u_content:
        return []

    lines = m3u_content.splitlines()
    channels = []
    extinf = None
    headers = []


    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('#EXTINF:'):
            # 如果我们找到一个新的 #EXTINF，但前一个没有URL，就丢弃前一个。
            extinf = line
            headers = []
        elif line.startswith('#') and extinf:
            # 这是与当前 #EXTINF 关联的头部信息行
            headers.append(line)
        elif extinf and not line.startswith('#'):
            # 这应该是当前频道的 URL
            url = line
            tvg_id = get_attr(r'tvg-id="([^"]+)"', extinf)
            tvg_name = get_attr(r'tvg-name="([^"]+)"', extinf)
            tvg_logo = get_attr(r'tvg-logo="([^"]+)"', extinf)
            group_title = get_attr(r'group-title="([^"]+)"', extinf)

            try:
                title = extinf.rsplit(",", 1)[-1].strip()
            except IndexError:
                title = tvg_name if tvg_name else "Unknown"

            # 添加完整的频道数据
            channels.append((tvg_name, tvg_id, tvg_logo, group_title, title, tuple(headers), url))

            # 为下一个频道重置状态
            extinf = None
            headers = []

    return channels


def get_attr(pattern, text):
    """
    :param pattern:
    :param text:
    :return:
    """
    match = re.search(pattern, text)
    return match.group(1) if match else None

def parse_simple(m3u_text):
    """
    简化版解析器：只解析 #EXTINF 和 URL，返回一个扁平的记录列表。
    用于 check_streams.py。
    """
    lines = iter(m3u_text.splitlines())
    header = ""
    try:
        first_line = next(lines).strip()
        if first_line.upper().startswith("#EXTM3U"):
            header = first_line
    except StopIteration:
        return "", []

    records = []
    idx = 0
    for line in lines:
        sline = line.strip()
        if not sline or not sline.startswith("#EXTINF"):
            continue
        try:
            url = next(lines).strip()
            if not url or url.startswith('#'):
                continue

            attr = sline
            name = attr.rsplit(",", 1)[-1]

            idx += 1
            rec = {"idx": idx, "attr": attr, "name": name, "url": url}
            records.append(rec)
        except (StopIteration, IndexError):
            break

    return header, records
