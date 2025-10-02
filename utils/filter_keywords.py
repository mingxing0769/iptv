# utils/filter_keywords.py

# 用于筛选频道的分类关键词
Category_Key = [
    # --- 体育 (Sports) ---
    "sports", "sport", "espn", "bein", "dazn", "tnt", "tsn", "tva",
    "f1", "football", "soccer", "nfl", "nba", "mlb", "nhl",
    "cricket", "golf", "racing", "tennis", "fight", "wwe",

    # --- 新闻 (News) ---
    "news", "cnn", "bbc", "abc", "nbc", "cbs", "fox", "sky",
    "euronews", "global", "newsmax", "newsnation",

    # --- 电影 & 剧集 (Movies & Series) ---
    "movie", "cinema", "hbo", "showtime", "amc", "fx", "tbs", "usa", "hgtv",

    # --- 纪录片 & 纪实 (Documentary & Factual) ---
    "discovery", "nat geo", "history", "docu", "science",

    # --- 儿童 (Kids) ---
    "kids", "cartoon", "nick", "disney"
]

# 用于过滤成人内容的关键词
Nsfw_Key = ['nsfw', 'xxx', 'porn', 'adult']

# 用于从频道标题中移除的质量指示符 (支持正则表达式)
Indicators_key = [
    r'\bFHD\b', r'\bHD\b', r'\bSD\b', r'\bUHD\b',
    r'\b4K\b', r'\b2K\b', r'\b8K\b',
    r'\bHEVC\b', r'\bH265\b', r'\bH264\b',
    r'\s*\[.*?\]',  # 移除方括号及其内容，例如 [Geo-blocked]
    r'\s*\(.*?\)'   # 移除圆括号及其内容，例如 (US)
]
