"""
日期与时间工具函数
"""
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

def parse_date(date_str):
    """
    尝试解析多种格式的日期字符串为时间戳
    
    参数:
        date_str (str): 日期字符串
        
    返回:
        int: Unix时间戳(秒)，解析失败返回None
    """
    if not date_str:
        return None
        
    # 常见的RSS日期格式
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',     # RFC 822 format: Wed, 02 Oct 2023 15:00:00 +0000
        '%a, %d %b %Y %H:%M:%S %Z',     # Wed, 02 Oct 2023 15:00:00 GMT
        '%Y-%m-%dT%H:%M:%S%z',          # ISO 8601: 2023-10-02T15:00:00+0000
        '%Y-%m-%dT%H:%M:%SZ',           # ISO 8601 UTC: 2023-10-02T15:00:00Z
        '%Y-%m-%d %H:%M:%S',            # 2023-10-02 15:00:00
        '%Y/%m/%d %H:%M:%S',            # 2023/10/02 15:00:00
        '%Y-%m-%d',                     # 2023-10-02
        '%Y/%m/%d',                     # 2023/10/02
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return int(dt.timestamp())
        except ValueError:
            continue
    
    # 所有格式都尝试失败
    logger.warning(f"无法解析日期字符串: {date_str}")
    return None

def format_date(timestamp, format_str='%Y-%m-%d %H:%M:%S'):
    """
    将时间戳格式化为日期字符串
    
    参数:
        timestamp: 时间戳
        format_str: 格式化字符串
        
    返回:
        格式化后的日期字符串
    """
    if timestamp is None:
        return ""
        
    try:
        return datetime.fromtimestamp(timestamp).strftime(format_str)
    except Exception:
        return "" 