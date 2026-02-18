# utils/filter_keywords.py

# 用于筛选频道的分类关键词
Category_Key = [
    # --- 体育 (Sports) ---
    "F1","F1TV","Sky sport","Sky sports","Ziggo Sport","ESPN","Fox Sports","BeIN Sports","TSN","TNT","rac"

    # --- 新闻 (News) ---
    "cnn", "bbc news", "abc news", "fox news", "sky news","CCTV"    

    # # --- 电影 & 剧集 (Movies & Series) ---
    # "movie", "cinema", "hbo"

    # # --- 纪录片 & 纪实 (Documentary & Factual) ---
    # "discovery", "nat geo", "history", "docu", "science",

    # # --- 儿童 (Kids) ---
    # "kids", "cartoon", "nick", "disney"
]

# 用于过滤成人内容的关键词
Nsfw_Key = ['nsfw', 'xxx', 'porn', 'adult']

# 用于从频道标题中移除的质量指示符 (支持正则表达式)
Indicators_key = [
    r'\bFHD\b', r'\bHD\b', r'\bSD\b', r'\bUHD\b',
    r'\b4K\b', r'\b2K\b', r'\b8K\b',
    # r'\bHEVC\b', r'\bH265\b', r'\bH264\b',
    # r'\s*\[.*?\]',  # 移除方括号及其内容，例如 [Geo-blocked]
    # r'\s*\(.*?\)'   # 移除圆括号及其内容，例如 (US)
]
