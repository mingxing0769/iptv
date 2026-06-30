# utils/channel_filter.py
import os
import re

def load_channels_txt(filepath):
    """
    解析 channels.txt 文件，提取正式名和别名。
    
    返回:
        official_names (set): 包含所有正式名的小写集合
        official_to_aliases (dict): 正式名(小写) -> [别名1(小写), 别名2(小写), ...]
        alias_to_official (dict): 别名(小写) -> 正式名(小写)
        official_lower_to_original (dict): 正式名(小写) -> 正式名(原始字符串)
    """
    official_names = set()
    official_to_aliases = {}
    alias_to_official = {}
    official_lower_to_original = {}
    
    if not os.path.exists(filepath):
        print(f"⚠️ channels.txt not found at {filepath}")
        return official_names, official_to_aliases, alias_to_official, official_lower_to_original
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if not parts or not parts[0]:
                continue
            official_name = parts[0]
            aliases = parts[1:] if len(parts) > 1 else []
            
            official_lower = official_name.lower()
            official_names.add(official_lower)
            official_lower_to_original[official_lower] = official_name
            official_to_aliases[official_lower] = []
            
            for alias in aliases:
                if alias:
                    alias_lower = alias.lower()
                    official_to_aliases[official_lower].append(alias_lower)
                    alias_to_official[alias_lower] = official_lower
            
    return official_names, official_to_aliases, alias_to_official, official_lower_to_original


def normalize_title_for_match(title):
    """
    规范化频道标题用于匹配：
    - 移除 (xxx)、[xxx] 等后缀
    - 移除分辨率标识如 1080p, 720p, HD, SD, 576i 等
    - 移除 Geo-blocked 标识
    - 移除 Not 24/7 等标识
    """
    canonical_title = re.sub(r'\s*\([^)]*\)', '', title)  # 移除 (xxx)
    canonical_title = re.sub(r'\s*\[[^\]]*\]', '', canonical_title)  # 移除 [xxx]
    # 移除分辨率标识
    canonical_title = re.sub(r'\b(?:1080p|720p|576i|4k|hd|sd|uhd)\b', '', canonical_title, flags=re.IGNORECASE)
    # 移除 Geo-blocked
    canonical_title = re.sub(r'\[Geo-blocked\]', '', canonical_title, flags=re.IGNORECASE)
    # 移除 Not 24/7 等标识
    canonical_title = re.sub(r'\[Not 24/7\]', '', canonical_title, flags=re.IGNORECASE)
    canonical_title = canonical_title.strip()
    return canonical_title.lower()


def get_official_name(title, official_names, official_to_aliases, alias_to_official):
    """
    根据频道标题获取对应的正式名。
    
    返回:
        (is_match, official_name_lower)
        is_match: 是否匹配
        official_name_lower: 正式名（小写）
    """
    norm_title = normalize_title_for_match(title)
    
    # 1. 直接匹配正式名
    if norm_title in official_names:
        return True, norm_title
    
    # 2. 匹配别名 -> 正式名
    if norm_title in alias_to_official:
        return True, alias_to_official[norm_title]
    
    # 3. 检查规范化标题是否匹配某个正式名或别名（精确匹配或别名列表中的项）
    for official, aliases in official_to_aliases.items():
        # 检查是否匹配正式名
        if norm_title == official:
            return True, official
        
        # 检查是否匹配某个别名
        for alias in aliases:
            if norm_title == alias:
                return True, official
            
            # 支持别名部分匹配：如果 norm_title 包含 alias 或反之
            # 但仅限于别名列表中的项，避免过度匹配
            if alias in norm_title or norm_title in alias:
                # 确保匹配是有意义的（例如，避免 'tv' 匹配所有包含 'tv' 的频道）
                # 要求匹配长度至少为3，或包含数字
                if len(alias) >= 3 or re.search(r'\d', alias):
                    return True, official
                    
    return False, None


def get_missing_channels(processed_official_names, official_names):
    """
    找出 official_names 中未在 processed_official_names 中出现的正式名。
    """
    missing = []
    for off in official_names:
        if off not in processed_official_names:
            missing.append(off)
    return missing
