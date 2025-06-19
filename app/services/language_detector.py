import re
from typing import Tuple, Optional, Dict

class LanguageDetector:
    """音乐国家语言智能识别服务"""
    
    def __init__(self):
        # 韩国艺术家/组合名称模式
        self.korean_patterns = [
            r'BTS|BLACKPINK|TWICE|Red Velvet|ITZY|aespa|NewJeans|IVE|LE SSERAFIM',
            r'BIGBANG|WINNER|iKON|TREASURE|ENHYPEN|TXT|Stray Kids',
            r'Girls\s*Generation|Wonder Girls|f\(x\)|Apink|MAMAMOO|T-ara',
            r'EXO|Super Junior|SHINee|NCT|WayV|RIIZE',
            r'SEVENTEEN|MONSTA X|ATEEZ|PENTAGON|THE BOYZ',
            r'IU|Taeyeon|Jennie|Lisa|Rosé|Jisoo',
            r'김|이|박|최|정|강|조|윤|장|임|한|오|서|신|권|황|안|송|전|홍',  # 韩文姓氏
            r'[가-힣]+'  # 韩文字符
        ]
        
        # 日本艺术家/组合名称模式
        self.japanese_patterns = [
            r'AKB48|乃木坂46|欅坂46|日向坂46|STU48|NMB48|HKT48|SKE48',
            r'嵐|SMAP|関ジャニ∞|NEWS|Hey!\s*Say!\s*JUMP|Kis-My-Ft2|SixTONES|Snow Man',
            r'ONE OK ROCK|X JAPAN|LUNA SEA|B\'z|L\'Arc-en-Ciel|GLAY',
            r'宇多田ヒカル|安室奈美恵|浜崎あゆみ|倉木麻衣|大塚愛',
            r'[ひらがな]|[カタカナ]|[一-龯]',  # 日文字符
            r'山田|田中|佐藤|鈴木|高橋|伊藤|渡辺|中村|小林|加藤'  # 日文姓氏
        ]
        
        # 中文艺术家名称模式
        self.chinese_patterns = [
            r'周杰伦|蔡依林|张学友|刘德华|邓紫棋|林俊杰|王力宏|陈奕迅|李荣浩|毛不易',
            r'五月天|苏打绿|信乐团|飞儿乐团|S\.H\.E|F\.I\.R|动力火车',
            r'邓丽君|王菲|那英|田震|孙燕姿|梁静茹|张惠妹|莫文蔚',
            r'tfboys|时代少年团|SNH48|火箭少女|THE9|硬糖少女',
            r'薛之谦|华晨宇|张艺兴|易烊千玺|王俊凯|王源|鹿晗|吴亦凡',
            r'[一-龯]+'  # 中文字符
        ]
        
        # 国家关键词映射
        self.country_keywords = {
            'korea': ['korea', 'korean', 'k-pop', 'kpop', 'seoul', 'busan', '한국', '서울'],
            'japan': ['japan', 'japanese', 'j-pop', 'jpop', 'tokyo', 'osaka', '日本', '東京'],
            'china': ['china', 'chinese', 'c-pop', 'cpop', 'mandarin', 'taiwan', 'hong kong', '中国', '台湾', '香港'],
            'usa': ['usa', 'america', 'american', 'us', 'new york', 'los angeles', 'california'],
            'uk': ['uk', 'britain', 'british', 'england', 'london', 'scotland'],
            'germany': ['germany', 'german', 'deutschland', 'berlin', 'munich'],
            'france': ['france', 'french', 'paris', 'lyon'],
            'spain': ['spain', 'spanish', 'madrid', 'barcelona'],
            'italy': ['italy', 'italian', 'rome', 'milan'],
            'russia': ['russia', 'russian', 'moscow', 'petersburg']
        }
        
        # 语言检测模式
        self.language_patterns = {
            'korean': self.korean_patterns,
            'japanese': self.japanese_patterns,
            'chinese': self.chinese_patterns,
            'english': [r'^[a-zA-Z\s\-\'\.]+$'],  # 纯英文
            'spanish': [r'ñ|ü|á|é|í|ó|ú|¿|¡'],
            'french': [r'ç|à|è|é|ê|ë|î|ï|ô|ù|û|ü|ÿ'],
            'german': [r'ä|ö|ü|ß'],
            'russian': [r'[а-яё]+']
        }
        
    def detect_country_and_language(self, title: str, artist: str, album: str = None) -> Tuple[Optional[str], Optional[str]]:
        """
        检测歌曲的国家和语言
        
        Args:
            title: 歌曲标题
            artist: 艺术家名称
            album: 专辑名称（可选）
        
        Returns:
            Tuple[country, language]: 国家和语言，如果无法确定则返回None
        """
        text = f"{title} {artist}"
        if album:
            text += f" {album}"
        
        text_lower = text.lower()
        
        # 检测韩国
        if self._match_patterns(text, self.korean_patterns):
            return "韩国", "韩语"
        
        # 检测日本
        if self._match_patterns(text, self.japanese_patterns):
            return "日本", "日语"
        
        # 检测中国
        if self._match_patterns(text, self.chinese_patterns):
            # 进一步区分大陆、台湾、香港
            if any(kw in text_lower for kw in ['taiwan', 'taiwanese', '台湾', '台語']):
                return "台湾", "中文"
            elif any(kw in text_lower for kw in ['hong kong', 'hongkong', '香港', '粤语']):
                return "香港", "粤语"
            else:
                return "中国", "中文"
        
        # 检测其他国家（基于关键词）
        for country, keywords in self.country_keywords.items():
            if any(kw in text_lower for kw in keywords):
                country_name = self._get_country_chinese_name(country)
                language = self._get_country_main_language(country)
                return country_name, language
        
        # 检测语言（如果无法确定国家）
        detected_language = self._detect_language(text)
        if detected_language:
            # 根据语言推测可能的国家
            country = self._infer_country_from_language(detected_language)
            return country, detected_language
        
        # 默认处理：如果包含英文字符且无其他语言特征，判断为英语
        if re.search(r'^[a-zA-Z\s\-\'\.&,\(\)]+$', text.strip()):
            return "美国", "英语"  # 默认英语歌曲归为美国
        
        return None, None
    
    def _match_patterns(self, text: str, patterns: list) -> bool:
        """检查文本是否匹配给定的模式列表"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _detect_language(self, text: str) -> Optional[str]:
        """检测文本语言"""
        for language, patterns in self.language_patterns.items():
            if self._match_patterns(text, patterns):
                return self._get_language_chinese_name(language)
        return None
    
    def _get_country_chinese_name(self, country_code: str) -> str:
        """获取国家的中文名称"""
        mapping = {
            'korea': '韩国',
            'japan': '日本',
            'china': '中国',
            'usa': '美国',
            'uk': '英国',
            'germany': '德国',
            'france': '法国',
            'spain': '西班牙',
            'italy': '意大利',
            'russia': '俄罗斯'
        }
        return mapping.get(country_code, country_code.title())
    
    def _get_language_chinese_name(self, language_code: str) -> str:
        """获取语言的中文名称"""
        mapping = {
            'korean': '韩语',
            'japanese': '日语',
            'chinese': '中文',
            'english': '英语',
            'spanish': '西班牙语',
            'french': '法语',
            'german': '德语',
            'russian': '俄语'
        }
        return mapping.get(language_code, language_code.title())
    
    def _get_country_main_language(self, country_code: str) -> str:
        """获取国家的主要语言"""
        mapping = {
            'korea': '韩语',
            'japan': '日语',
            'china': '中文',
            'usa': '英语',
            'uk': '英语',
            'germany': '德语',
            'france': '法语',
            'spain': '西班牙语',
            'italy': '意大利语',
            'russia': '俄语'
        }
        return mapping.get(country_code, '英语')
    
    def _infer_country_from_language(self, language: str) -> Optional[str]:
        """从语言推测国家"""
        mapping = {
            '韩语': '韩国',
            '日语': '日本',
            '中文': '中国',
            '英语': '美国',
            '德语': '德国',
            '法语': '法国',
            '西班牙语': '西班牙',
            '意大利语': '意大利',
            '俄语': '俄罗斯'
        }
        return mapping.get(language)
    
    def suggest_mood_from_genre(self, genre: str) -> Optional[str]:
        """根据风格建议情绪标签"""
        if not genre:
            return None
        
        genre_lower = genre.lower()
        
        if any(g in genre_lower for g in ['pop', '流行', 'dance', '舞曲']):
            return '快乐'
        elif any(g in genre_lower for g in ['rock', '摇滚', 'metal', '金属', 'punk']):
            return '激昂'
        elif any(g in genre_lower for g in ['ballad', '抒情', 'slow', 'sad', '伤感']):
            return '忧伤'
        elif any(g in genre_lower for g in ['jazz', '爵士', 'blues', '蓝调', 'classical', '古典']):
            return '放松'
        elif any(g in genre_lower for g in ['love', '爱情', 'romantic', '浪漫']):
            return '浪漫'
        elif any(g in genre_lower for g in ['electronic', '电子', 'edm', 'techno']):
            return '激昂'
        elif any(g in genre_lower for g in ['folk', '民谣', 'country', '乡村', 'acoustic']):
            return '放松'
        
        return '快乐'  # 默认

# 创建全局实例
language_detector = LanguageDetector()