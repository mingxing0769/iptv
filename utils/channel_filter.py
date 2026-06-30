# utils/channel_filter.py
import os

def load_channels_txt(filepath):
    """
    解析 channels.txt 文件，提取正式名和别名。
    
    返回:
        allowed_channels (set): 包含所有正式名和别名的小写集合
        channel_aliases (dict): 正式名(小写) -> [别名1(小写), 别名2(小写), ...]
    """
    allowed_channels = set()
    channel_aliases = {}
    
    if not os.path.exists(filepath):
        print(f"⚠️ channels.txt not found at {filepath}")
        return allowed_channels, channel_aliases
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if not parts:
                continue
            official_name = parts[0]
            aliases = parts[1:] if len(parts) > 1 else []
            
            official_lower = official_name.lower()
            allowed_channels.add(official_lower)
            for alias in aliases:
                alias_lower = alias.lower()
                allowed_channels.add(alias_lower)
            
            channel_aliases[official_lower] = [a.lower() for a in aliases]
            
    return allowed_channels, channel_aliases


def channel_matches(title, allowed_channels):
    """
    检查频道标题是否匹配 allowed_channels 中的频道或别名。
    """
    from utils.m3u_parse import parse_m3u # 避免循环导入，但这里不需要
    # 规范化标题
    import re
    indicators = [] # 从 filter_keywords 导入 Indicators_key
    # 简单规范化：移除分辨率、Geo-blocked 等后缀
    canonical_title = re.sub(r'\s*\([^)]*\)', '', title)  # 移除 (xxx)
    canonical_title = re.sub(r'\s*\[[^\]]*\]', '', canonical_title)  # 移除 [xxx]
    canonical_title = canonical_title.strip()
    canonical_lower = canonical_title.lower()
    
    return canonical_lower in allowed_channels


def get_missing_channels(current_channels_set, allowed_channels):
    """
    找出 current_channels_set 中缺失的 allowed_channels 里的频道。
    """
    missing = []
    for ac in allowed_channels:
        # 检查是否有任何 current_channel 匹配这个 ac
        matched = False
        for cc in current_channels_set:
            cc_norm = re.sub(r'\s*\([^)]*\)', '', cc).lower().strip()
            cc_norm = re.sub(r'\s*\[[^\]]*\]', '', cc_norm).lower().strip()
            if cc_norm == ac or ac in cc_norm or cc_norm in ac:
                matched = True
                break
        if not matched:
            missing.append(ac)
    return missing
