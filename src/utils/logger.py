import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logger(name, log_file, level=logging.INFO, max_bytes=10 * 1024 * 1024, backup_count=10):
    """
    设置并返回一个日志记录器。

    :param name: 日志记录器的名称。
    :param log_file: 日志文件的路径。
    :param level: 日志级别。
    :param max_bytes: 日志文件的最大字节数，用于日志轮转。
    :param backup_count: 保留的备份日志文件的数量。
    :return: 配置好的日志记录器。
    """
    # 确保日志目录存在
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 防止日志信息被传递到父记录器

    # 如果日志记录器已经配置过，直接返回
    if logger.hasHandlers():
        return logger

    # 定义日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Thread %(thread)d - %(threadName)s] - %(message)s')

    # 创建文件处理器，设置日志轮转
    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
