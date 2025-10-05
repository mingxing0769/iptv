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
    return match.group(1) if match else 'None'

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

def _parse_m3u_headers(m3u_headers):
    """
    解析M3U中的头部信息行 (如 #EXTVLCOPT) 并转换为requests库可用的字典。

    Args:
        m3u_headers (tuple): 包含原始头部字符串的元组。
        e.g., ('#EXTVLCOPT:http-referrer=https://mlbwebcast.com/',)

    Returns:
        dict: 可用于requests的headers字典。
        e.g., {'Referer': 'https://mlbwebcast.com/'}
    """
    if not m3u_headers:
        return {}

    headers_dict = {}
    # 匹配 #EXTVLCOPT 或 #EXTHTTP 后面的内容
    pattern = re.compile(r'#(?:EXTVLCOPT|EXTHTTP):(.*)')

    for header_line in m3u_headers:
        match = pattern.match(header_line.strip())
        if not match:
            continue

        content = match.group(1).strip()
        try:
            # 按第一个等号分割键值
            key, value = content.split('=', 1)
            key = key.strip().lower()
            value = value.strip()

            # 将M3U中的键名映射为标准的HTTP头名称
            if key == 'http-referrer':
                headers_dict['Referer'] = value
            elif key == 'http-user-agent':
                headers_dict['User-Agent'] = value
            elif key == 'http-origin':
                headers_dict['Origin'] = value
            # 你可以在这里添加更多的映射规则
        except ValueError:
            # 如果行中不包含'='，则忽略
            pass
    return headers_dict
