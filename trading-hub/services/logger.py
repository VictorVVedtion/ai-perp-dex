"""
统一日志配置
"""
import logging
import sys

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """创建标准化的 logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(handler)
    
    return logger

# 默认 logger
default_logger = setup_logger("trading-hub")
