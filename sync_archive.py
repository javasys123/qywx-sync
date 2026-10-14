"""
企业微信会话存档同步系统

功能:
- 自动拉取企业微信会话存档消息
- 解密消息内容(文本、图片、视频、笔记等)
- 下载媒体文件到本地
- 每条消息保存为独立 JSON 文件,媒体路径写入记录
- 自动清理3天前的媒体文件

使用方式:
    python sync_archive.py              # 单次同步
"""

import os
import sys
import json
import time
import logging
import glob
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.wework_finance_sdk import WeWorkFinanceSDK
from src.utils import load_config, ensure_dir

# 导入上传客户端
try:
    from upload_client import NoteUploader
    UPLOAD_ENABLED = True
except ImportError:
    UPLOAD_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.warning("上传客户端导入失败,自动上传功能禁用")


def setup_logging():
    """配置日志系统"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(project_root, "logs")
    ensure_dir(log_dir)

    log_file = os.path.join(log_dir, "sync.log")

    # 设置环境变量解决 Windows GBK 编码问题
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


logger = logging.getLogger(__name__)


class WeWorkArchiveSync:
    """企业微信会话存档同步器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        qywx_config = config.get('qywx', {})

        # 企业微信配置
        self.corp_id = qywx_config.get('corp_id', '')
        self.finance_secret = qywx_config.get('finance_secret', '')
        self.private_key = qywx_config.get('finance_private_key', '')

        # 存储配置
        storage_config = config.get('storage', {})
        self.save_dir = os.path.abspath(storage_config.get('base_path', './downloads'))
        self.auto_cleanup_days = storage_config.get('auto_cleanup_days', 3)  # 默认3天
        ensure_dir(self.save_dir)

        # 微信笔记处理配置
        wechat_config = config.get('wechat', {})
        self.note_only = wechat_config.get('note_only', True)  # 默认只处理笔记消息

        # 上传配置
        self.auto_upload = False
        self.uploader = None
        if UPLOAD_ENABLED:
            upload_config = config.get('upload', {})
            self.auto_upload = upload_config.get('auto_upload', False)
            if self.auto_upload:
                try:
                    self.uploader = NoteUploader(config)
                    logger.info("自动上传功能已启用")
                except Exception as e:
                    logger.error(f"上传器初始化失败: {e}")
                    self.uploader = None

        # 校验必要配置
        missing = []
        if not self.corp_id:
            missing.append('corp_id')
        if not self.finance_secret:
            missing.append('finance_secret')
        if not self.private_key:
            missing.append('finance_private_key')
        if missing:
            raise ValueError(f"缺少必要的配置项: {', '.join(missing)}")

        # 初始化 SDK
        self.sdk = WeWorkFinanceSDK(
            corp_id=self.corp_id,
            secret=self.finance_secret,
            private_key=self.private_key
        )

        # 上次同步的 seq
        self.last_seq_file = os.path.join(self.save_dir, '.last_seq')
        self.last_seq = self._load_last_seq()

        logger.info(f"同步器初始化完成, 上次同步 seq: {self.last_seq}")
        logger.info(f"消息过滤模式: {'仅笔记消息' if self.note_only else '所有消息'}")
        logger.info(f"自动上传: {'启用' if self.auto_upload else '禁用'}")
        logger.info(f"自动清理: {self.auto_cleanup_days} 天前的媒体文件")

    def _load_last_seq(self) -> int:
        """加载上次同步的 seq"""
        if os.path.exists(self.last_seq_file):
            try:
                with open(self.last_seq_file, 'r', encoding='utf-8') as f:
                    return int(f.read().strip())
            except (ValueError, IOError) as e:
                logger.warning(f"加载 seq 失败: {e}")
        return 0

    def _save_last_seq(self, seq: int):
        """保存上次同步的 seq"""
        try:
            with open(self.last_seq_file, 'w', encoding='utf-8') as f:
                f.write(str(seq))
        except IOError as e:
            logger.error(f"保存 seq 失败: {e}")

    def _save_message(self, msg_data: Dict[str, Any], msg_id: str) -> str:
        """
        保存消息记录为独立 JSON 文件

        Args:
            msg_data: 消息数据（含解密内容和媒体文件路径）
            msg_id: 消息 ID

        Returns:
            保存的文件路径，失败返回空字符串
        """
        # 添加同步时间戳
        msg_data['synced_at'] = datetime.now().isoformat()

        # 文件名：msg_{seq}_{msgid}.json
        seq = msg_data.get('seq', 0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"msg_{seq}_{msg_id}_{timestamp}.json"
        filepath = os.path.join(self.save_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(msg_data, f, ensure_ascii=False, indent=2)
            logger.info(f"消息已保存: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"保存消息失败: {e}")
            return ""

    def _download_media(self, sdk_file_id: str, filename: str) -> str:
        """
        下载媒体文件并返回保存路径

        Args:
            sdk_file_id: 媒体文件 ID
            filename: 保存的文件名

        Returns:
            文件路径，失败返回空字符串
        """
        if not sdk_file_id:
            return ""

        filepath = os.path.join(self.save_dir, filename)
        if self.sdk.get_media_data(sdk_file_id, filepath):
            return filepath
        return ""

    def _parse_item_content(self, content_raw: Any) -> Dict[str, Any]:
        """
        解析笔记项的 content 字段（可能是 JSON 字符串或字典）

        Args:
            content_raw: 原始 content 值

        Returns:
            解析后的字典
        """
        if isinstance(content_raw, dict):
            return content_raw
        if isinstance(content_raw, str):
            try:
                return json.loads(content_raw)
            except (json.JSONDecodeError, ValueError):
                return {'content': content_raw}
        return {}

    def _process_note_item(self, item: Dict[str, Any], msg_id: str, idx: int) -> Dict[str, Any]:
        """
        处理笔记中的单个项目

        Args:
            item: 项目数据
            msg_id: 消息 ID
            idx: 项目索引

        Returns:
            处理结果（含文件路径）
        """
        item_type = item.get('msg_type', '')
        content_data = self._parse_item_content(item.get('content', ''))

        result: Dict[str, Any] = {
            'msg_type': item_type,
            'index': idx,
            'files': []
        }

        if item_type == 'text':
            text = content_data.get('content', '') if isinstance(content_data, dict) else str(content_data)
            if text:
                result['content'] = text
                text_file = os.path.join(self.save_dir, f"note_text_{msg_id}_{idx}.txt")
                try:
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                    result['files'].append(text_file)
                    logger.info(f"  -> 保存文本: {text_file}")
                except IOError as e:
                    logger.error(f"  保存文本失败: {e}")

        elif item_type == 'image':
            sdk_file_id = content_data.get('sdkfileid', '')
            media_info = {
                'md5sum': content_data.get('md5sum', ''),
                'filesize': content_data.get('filesize', 0)
            }
            filepath = self._download_media(sdk_file_id, f"note_image_{msg_id}_{idx}.jpg")
            if filepath:
                result['files'].append(filepath)
                result['media_url'] = filepath
                result['media_info'] = media_info
                logger.info(f"  -> 保存图片: {filepath}")

        elif item_type == 'video':
            sdk_file_id = content_data.get('sdkfileid', '')
            media_info = {
                'md5sum': content_data.get('md5sum', ''),
                'filesize': content_data.get('filesize', 0),
                'play_length': content_data.get('play_length', 0)
            }
            filepath = self._download_media(sdk_file_id, f"note_video_{msg_id}_{idx}.mp4")
            if filepath:
                result['files'].append(filepath)
                result['media_url'] = filepath
                result['media_info'] = media_info
                logger.info(f"  -> 保存视频: {filepath}")

        elif item_type == 'voice':
            sdk_file_id = content_data.get('sdkfileid', '')
            filepath = self._download_media(sdk_file_id, f"note_voice_{msg_id}_{idx}.amr")
            if filepath:
                result['files'].append(filepath)
                result['media_url'] = filepath
                logger.info(f"  -> 保存语音: {filepath}")

        elif item_type == 'link':
            result['content'] = {
                'title': content_data.get('title', ''),
                'description': content_data.get('description', ''),
                'link_url': content_data.get('link_url', ''),
                'image_url': content_data.get('image_url', '')
            }

        elif item_type == 'file':
            sdk_file_id = content_data.get('sdkfileid', '')
            original_name = content_data.get('filename', 'unknown')
            filepath = self._download_media(sdk_file_id, f"note_file_{msg_id}_{idx}_{original_name}")
            if filepath:
                result['files'].append(filepath)
                result['media_url'] = filepath
                result['media_info'] = {
                    'filename': original_name,
                    'md5sum': content_data.get('md5sum', ''),
                    'filesize': content_data.get('filesize', 0)
                }
                logger.info(f"  -> 保存文件: {filepath}")

        return result

    def _process_message(self, decrypted: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理解密后的消息，下载媒体文件并构建记录

        Args:
            decrypted: 解密后的消息数据

        Returns:
            处理结果（含文件路径和媒体信息）
        """
        msg_id = decrypted.get('msgid', '')
        msg_type = decrypted.get('msgtype', '')

        # 如果启用 note_only 模式，跳过非笔记消息
        if self.note_only and msg_type != 'note':
            logger.info(f"跳过非笔记消息: {msg_id} (类型: {msg_type})")
            return {
                'msgid': msg_id,
                'msgtype': msg_type,
                'skipped': True,
                'success': False
            }

        result: Dict[str, Any] = {
            'msgid': msg_id,
            'msgtype': msg_type,
            'action': decrypted.get('action', ''),
            'from': decrypted.get('from', ''),
            'tolist': decrypted.get('tolist', []),
            'msgtime': decrypted.get('msgtime', 0),
            'files': [],
            'success': False
        }

        try:
            if msg_type == 'text':
                text = decrypted.get('content', '')
                result['content'] = text
                text_file = os.path.join(self.save_dir, f"text_{msg_id}.txt")
                try:
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                    result['files'].append(text_file)
                    result['success'] = True
                except IOError as e:
                    logger.error(f"保存文本失败: {e}")

            elif msg_type == 'image':
                image_info = decrypted.get('image', {})
                sdk_file_id = image_info.get('sdkfileid', '')
                filepath = self._download_media(sdk_file_id, f"image_{msg_id}.jpg")
                if filepath:
                    result['files'].append(filepath)
                    result['media_url'] = filepath
                    result['media_info'] = image_info
                    result['success'] = True

            elif msg_type == 'video':
                video_info = decrypted.get('video', {})
                sdk_file_id = video_info.get('sdkfileid', '')
                filepath = self._download_media(sdk_file_id, f"video_{msg_id}.mp4")
                if filepath:
                    result['files'].append(filepath)
                    result['media_url'] = filepath
                    result['media_info'] = video_info
                    result['success'] = True

            elif msg_type == 'voice':
                voice_info = decrypted.get('voice', {})
                sdk_file_id = voice_info.get('sdkfileid', '')
                filepath = self._download_media(sdk_file_id, f"voice_{msg_id}.amr")
                if filepath:
                    result['files'].append(filepath)
                    result['media_url'] = filepath
                    result['media_info'] = voice_info
                    result['success'] = True

            elif msg_type == 'note':
                # 笔记消息 - 核心处理
                info = decrypted.get('info', {})
                items = info.get('items', [])
                result['items'] = []

                for idx, item in enumerate(items):
                    item_result = self._process_note_item(item, msg_id, idx)
                    result['items'].append(item_result)
                    result['files'].extend(item_result.get('files', []))

                result['success'] = len(items) > 0

            elif msg_type == 'file':
                file_info = decrypted.get('file', {})
                sdk_file_id = file_info.get('sdkfileid', '')
                filename = file_info.get('filename', 'unknown')
                filepath = self._download_media(sdk_file_id, f"file_{msg_id}_{filename}")
                if filepath:
                    result['files'].append(filepath)
                    result['media_url'] = filepath
                    result['media_info'] = file_info
                    result['success'] = True

            else:
                # 其他消息类型，保存原始数据
                logger.warning(f"未处理的消息类型: {msg_type}")
                result['raw_data'] = decrypted
                result['success'] = True

        except Exception as e:
            logger.error(f"处理消息异常: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    def cleanup_old_media(self):
        """
        清理指定天数前的媒体文件(图片、视频)
        保留 JSON 记录文件,只删除媒体文件
        """
        if self.auto_cleanup_days <= 0:
            return

        logger.info(f"开始清理 {self.auto_cleanup_days} 天前的媒体文件...")

        cutoff_time = datetime.now() - timedelta(days=self.auto_cleanup_days)
        cutoff_timestamp = cutoff_time.timestamp()

        # 要清理的媒体文件模式
        media_patterns = [
            os.path.join(self.save_dir, 'note_image_*.jpg'),
            os.path.join(self.save_dir, 'note_video_*.mp4'),
            os.path.join(self.save_dir, 'image_*.jpg'),
            os.path.join(self.save_dir, 'video_*.mp4'),
        ]

        deleted_count = 0
        kept_count = 0

        try:
            for pattern in media_patterns:
                for filepath in glob.glob(pattern):
                    try:
                        # 检查文件修改时间
                        file_mtime = os.path.getmtime(filepath)

                        if file_mtime < cutoff_timestamp:
                            # 文件超过指定天数,删除
                            os.remove(filepath)
                            deleted_count += 1
                            logger.debug(f"已删除旧媒体文件: {filepath}")
                        else:
                            kept_count += 1
                    except Exception as e:
                        logger.error(f"删除文件失败 {filepath}: {e}")

            logger.info(f"媒体文件清理完成 | 删除: {deleted_count} 个 | 保留: {kept_count} 个")

        except Exception as e:
            logger.error(f"清理媒体文件异常: {e}", exc_info=True)

    def sync_messages(self):
        """同步所有新消息"""
        logger.info("=" * 60)
        logger.info("开始同步企业微信聊天记录")

        # 每次同步前清理旧媒体文件
        self.cleanup_old_media()

        current_seq = self.last_seq
        total_processed = 0
        total_success = 0
        total_skipped = 0  # 跳过的消息数

        try:
            while True:
                logger.info(f"拉取消息, seq={current_seq}")
                chat_data = self.sdk.get_chat_data(seq=current_seq, limit=1000)

                if not chat_data:
                    logger.warning("未获取到消息数据")
                    break

                chat_list = chat_data.get('chatdata', [])
                if not chat_list:
                    logger.info("没有新消息")
                    break

                logger.info(f"本次拉取到 {len(chat_list)} 条消息")

                for item in chat_list:
                    seq = item.get('seq', 0)
                    msg_id = item.get('msgid', '')
                    encrypt_key = item.get('encrypt_random_key', '')
                    encrypt_msg = item.get('encrypt_chat_msg', '')

                    logger.info(f"处理消息 seq={seq}, msgid={msg_id}")

                    try:
                        # 解密
                        decrypted = self.sdk.decrypt_data(encrypt_key, encrypt_msg)
                        if not decrypted:
                            logger.error(f"消息解密失败: {msg_id}")
                            current_seq = max(current_seq, seq)
                            total_processed += 1
                            continue

                        # 记录 seq 到结果中
                        decrypted['seq'] = seq

                        # 处理消息（下载媒体）
                        result = self._process_message(decrypted)

                        # 检查是否被跳过
                        if result.get('skipped'):
                            total_skipped += 1
                            logger.info(f"[SKIP] 消息已跳过 (类型: {result.get('msgtype')})")
                        # 保存 JSON 记录
                        elif result['files'] or result.get('success'):
                            filepath = self._save_message(result, msg_id)
                            if filepath:
                                total_success += 1
                                logger.info(f"[OK] 消息处理成功, 生成 {len(result['files'])} 个文件")

                                # 自动上传
                                if self.auto_upload and self.uploader and result.get('msgtype') == 'note':
                                    try:
                                        if self.uploader.upload_message(result):
                                            logger.info(f"[UPLOAD] 消息已上传: {msg_id}")
                                        else:
                                            logger.warning(f"[UPLOAD] 消息上传失败: {msg_id}")
                                    except Exception as e:
                                        logger.error(f"[UPLOAD] 上传异常: {e}")
                        else:
                            logger.warning(f"[FAIL] 消息处理失败: {msg_id}")

                        total_processed += 1
                        current_seq = max(current_seq, seq)

                    except Exception as e:
                        logger.error(f"处理消息异常: {msg_id} - {e}", exc_info=True)
                        total_processed += 1
                        current_seq = max(current_seq, seq)

                # 返回消息数少于 limit，说明已拉取完毕
                if len(chat_list) < 1000:
                    break

                time.sleep(0.5)

        except Exception as e:
            logger.error(f"同步异常: {e}", exc_info=True)

        finally:
            self._save_last_seq(current_seq)
            self.last_seq = current_seq

            logger.info("=" * 60)
            logger.info(f"同步完成 | 处理: {total_processed} | 成功: {total_success} | 跳过: {total_skipped} | 最新 seq: {current_seq}")


def main():
    """主函数"""
    setup_logging()

    # 加载配置
    config = load_config()

    # 创建同步器
    try:
        syncer = WeWorkArchiveSync(config)
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)

    # 仅支持单次同步模式
    syncer.sync_messages()


if __name__ == '__main__':
    main()
