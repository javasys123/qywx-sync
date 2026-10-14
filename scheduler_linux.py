#!/usr/bin/env python3
"""
企业微信会话存档定时同步调度器 (Linux 版本)

功能:
- 使用 schedule 库实现定时任务
- 可配置的同步间隔
- 支持多种调度模式
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime

from sync_archive_linux import WeWorkArchiveSync, setup_logging
from src.utils import load_config

# 配置日志
logger = logging.getLogger(__name__)


class SyncScheduler:
    """同步任务调度器"""

    def __init__(self, config):
        self.config = config
        self.syncer = WeWorkArchiveSync(config)

        # 调度配置
        scheduler_config = config.get('scheduler', {})
        self.sync_interval = scheduler_config.get('interval_seconds', 60)
        self.enabled = scheduler_config.get('enabled', True)

        logger.info(f"调度器初始化完成, 同步间隔: {self.sync_interval}秒")

    def job_sync(self):
        """定时同步任务"""
        try:
            self.syncer.sync_messages()
        except Exception as e:
            logger.error(f"定时同步异常: {e}", exc_info=True)

    def start(self):
        """启动调度器"""
        if not self.enabled:
            logger.warning("调度器已禁用")
            return

        # 注册定时任务
        schedule.every(self.sync_interval).seconds.do(self.job_sync)

        logger.info(f"定时任务已启动, 每 {self.sync_interval} 秒执行一次")
        logger.info("按 Ctrl+C 停止...")

        # 立即执行一次
        self.job_sync()

        # 循环执行
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到停止信号, 正在退出...")
        except Exception as e:
            logger.error(f"调度器异常: {e}", exc_info=True)


def main():
    """主函数"""
    setup_logging()

    # 加载配置
    config = load_config()

    # 创建调度器
    try:
        scheduler = SyncScheduler(config)
    except Exception as e:
        logger.error(f"初始化调度器失败: {e}")
        sys.exit(1)

    # 启动调度器
    scheduler.start()


if __name__ == '__main__':
    main()
