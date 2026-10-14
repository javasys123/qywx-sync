"""
工具函数模块

提供配置加载、目录创建等基础功能
"""

import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载 YAML 配置文件

    Args:
        config_path: 配置文件路径,默认使用 config/config.yaml

    Returns:
        配置字典
    """
    if config_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, 'config', 'config.yaml')

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"配置文件加载成功: {config_path}")
        return config
    except ImportError:
        logger.error("缺少 PyYAML 依赖,请执行: pip install pyyaml")
        raise
    except Exception as e:
        logger.error(f"配置文件加载失败: {e}")
        raise


def ensure_dir(dir_path: str) -> bool:
    """
    确保目录存在,不存在则创建

    Args:
        dir_path: 目录路径

    Returns:
        是否成功
    """
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"创建目录: {dir_path}")
        return True
    except Exception as e:
        logger.error(f"创建目录失败: {dir_path} - {e}")
        return False


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串 (如: 1.5 MB)
    """
    if size_bytes < 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    size = float(size_bytes)

    while size >= 1024.0 and index < len(units) - 1:
        size /= 1024.0
        index += 1

    return f"{size:.2f} {units[index]}"
