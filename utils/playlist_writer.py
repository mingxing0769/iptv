"""
播放列表写入和频道处理模块
"""
from tqdm import tqdm
from utils.channel_filter import get_official_name


def process_and_normalize_channels(accessible_channels, official_names, official_to_aliases, alias_to_official, official_lower_to_original, is_nsfw_func, channels_txt_filter, category_filter, category_key):
    """
    对频道列表进行规范化、去重和统一化处理。
    - 过滤 NSFW 内容和非指定分类。
    - 根据 channels.txt 过滤频道（仅保留 channels.txt 中的频道及其别名）。
    - 使用 channels.txt 中的正式名作为最终的 title 和 tvg-name。
    - 过滤 url 完全重复的条目。
    - 统一同名频道的 TVG 信息。
    """
    print("\n🔍 Starting data normalization, de-duplication, and unification...")

    processed_urls = set()
    master_tvg_info = {}
    final_channels = []
    filtered_count = 0
    processed_official_names = set()

    for tvg_name, tvg_id, tvg_logo, group_title, title, headers, url in tqdm(accessible_channels,
                                                                             desc="Processing & Unifying"):
        # 检查是否为 NSFW 内容
        # 检查是否为 NSFW 内容
        if is_nsfw_func(group_title, title):
            filtered_count += 1
            continue

        # channels.txt 过滤：获取正式名
        if channels_txt_filter:
            is_match, official_name_lower = get_official_name(title, official_names, official_to_aliases, alias_to_official)
            if not is_match:
                filtered_count += 1
                continue
            # 获取原始正式名
            official_title = official_lower_to_original.get(official_name_lower, official_name_lower)
            processed_official_names.add(official_name_lower)
        else:
            # 如果不启用 channels.txt 过滤，则使用原始 title
            official_title = title
            # 为了缺失频道统计，尝试提取可能的 official_name_lower
            is_match, official_name_lower = get_official_name(title, official_names, official_to_aliases, alias_to_official)
            if is_match:
                processed_official_names.add(official_name_lower)

        # 分类过滤
        if category_filter:
            lower_keywords = [k.lower() for k in category_key]
            searchable_text = f'{tvg_name}, {group_title}, {title}'.lower()
            if not any(keyword in searchable_text for keyword in lower_keywords):
                filtered_count += 1
                continue

        # 过滤 url 完全重复的条目
        if url in processed_urls:
            filtered_count += 1
            continue
        processed_urls.add(url)

        key = official_title.lower()

        # 检查并统一 TVG 信息
        if key not in master_tvg_info:
            master_tvg_info[key] = (tvg_logo, group_title)

        master_tvg_logo, master_group_title = master_tvg_info[key]

        # 使用统一后的信息构建最终的频道数据
        # 使用 official_title 作为 title 和 tvg-name
        unified_channel = (
           official_title, tvg_id, master_tvg_logo, master_group_title, official_title, headers, url
        )
        final_channels.append(unified_channel)

    if filtered_count > 0:
        print(f"🚫 Filtered out {filtered_count} channels based on filters.")
    print(f"✅ Kept {len(final_channels)} channels after processing.")
    return final_channels, processed_official_names


def write_merged_playlist(final_channels_to_write, epg_url, output_file):
    """将最终的频道列表写入 M3U 文件。"""
    lines = [f'#EXTM3U url-tvg="{epg_url}"', ""]
    # 按 group-title 和 title 排序
    sorted_channels = sorted(
        final_channels_to_write,
        key=lambda channel: (str(channel[3]).lower(), str(channel[4]).lower())
    )

    current_group = None
    for channel_data in sorted_channels:
        tvg_name, tvg_id, tvg_logo, group, title, headers, url = channel_data

        if group != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f'#EXTGRP:{group}')
            current_group = group

        extinf_parts = ['#EXTINF:-1']
        if tvg_id: extinf_parts.append(f'tvg-id="{tvg_id}"')
        if tvg_name:
            extinf_parts.append(f'tvg-name="{tvg_name}"')
        else:
            extinf_parts.append(f'tvg-name="{title}"')

        if tvg_logo: extinf_parts.append(f'tvg-logo="{tvg_logo}"')
        if group: extinf_parts.append(f'group-title="{group}"')

        extinf_line = ' '.join(extinf_parts) + f',{title}'
        lines.append(extinf_line)
        lines.extend(headers)
        lines.append(url)

    final_output_string = '\n'.join(lines) + '\n'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_output_string)
    print(f"\n✅ Merged playlist written to {output_file}.")
    print(f"📊 Total channels written: {len(final_channels_to_write)}.")
