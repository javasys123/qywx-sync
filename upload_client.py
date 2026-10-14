"""
笔记数据上传客户端

将同步的笔记消息上传到指定 API 接口

接口文档:
- URL: https://api.chaopaiclub.cn/wx-item-register/syncAddByContent
- Method: POST
- Content-Type: multipart/form-data
- 表单字段:
  - content: 笔记文本内容
  - sourceId: 消息 ID (msgid)
  - files: 文件列表(图片、视频等)

curl 示例:
curl -X POST \
  -H "Accept:*/*" \
  -H "Content-Type:multipart/form-data" \
  -F "content=笔记内容" \
  -F "files=@图片文件.png" \
  -F "sourceId=消息ID" \
  "https://api.chaopaiclub.cn/wx-item-register/syncAddByContent"
"""

import os
import json
import requests
import logging
from typing import Dict, Any, List
from datetime import datetime

from src.utils import load_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


class NoteUploader:
    """笔记数据上传器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化上传器

        Args:
            config: 配置字典
        """
        self.config = config

        # API 配置
        upload_config = config.get('upload', {})
        self.api_url = upload_config.get('api_url', 'https://api.chaopaiclub.cn/wx-item-register/syncAddByContent')
        self.api_timeout = upload_config.get('timeout', 120)
        self.enabled = upload_config.get('enabled', True)

        # 存储配置
        storage_config = config.get('storage', {})
        self.save_dir = os.path.abspath(storage_config.get('base_path', './downloads'))

        # 上传记录文件
        self.uploaded_file = os.path.join(self.save_dir, '.uploaded_records')
        self.uploaded_msgids = self._load_uploaded_records()

        logger.info(f"上传器初始化完成")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"上传功能: {'启用' if self.enabled else '禁用'}")
        logger.info(f"已上传记录: {len(self.uploaded_msgids)} 条")

    def _load_uploaded_records(self) -> set:
        """加载已上传的消息 ID 记录"""
        if os.path.exists(self.uploaded_file):
            try:
                with open(self.uploaded_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"加载上传记录失败: {e}")
        return set()

    def _save_uploaded_records(self):
        """保存已上传的消息 ID 记录"""
        try:
            with open(self.uploaded_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.uploaded_msgids), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存上传记录失败: {e}")

    def _extract_text_content(self, msg_data: Dict[str, Any]) -> str:
        """
        提取笔记中的文本内容

        Args:
            msg_data: 消息数据

        Returns:
            合并的文本内容
        """
        texts = []
        items = msg_data.get('items', [])

        for item in items:
            if item.get('msg_type') == 'text':
                content = item.get('content', '')
                if content:
                    texts.append(content)

        return '\n'.join(texts)

    def _extract_files(self, msg_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        提取笔记中的文件信息

        Args:
            msg_data: 消息数据

        Returns:
            文件列表 [{"type": "image", "url": "...", "fileName": "..."}]
        """
        files = []
        items = msg_data.get('items', [])

        for idx, item in enumerate(items):
            msg_type = item.get('msg_type', '')

            if msg_type == 'image':
                media_url = item.get('media_url', '')
                if media_url:
                    files.append({
                        'type': 'image',
                        'url': media_url,
                        'fileName': os.path.basename(media_url)
                    })

            elif msg_type == 'video':
                media_url = item.get('media_url', '')
                if media_url:
                    files.append({
                        'type': 'video',
                        'url': media_url,
                        'fileName': os.path.basename(media_url)
                    })

            elif msg_type == 'voice':
                media_url = item.get('media_url', '')
                if media_url:
                    files.append({
                        'type': 'voice',
                        'url': media_url,
                        'fileName': os.path.basename(media_url)
                    })

            elif msg_type == 'file':
                media_url = item.get('media_url', '')
                if media_url:
                    files.append({
                        'type': 'file',
                        'url': media_url,
                        'fileName': os.path.basename(media_url)
                    })

            elif msg_type == 'text':
                # 文本文件
                file_list = item.get('files', [])
                if file_list:
                    for text_file in file_list:
                        files.append({
                            'type': 'text',
                            'url': text_file,
                            'fileName': os.path.basename(text_file)
                        })

        return files

    def _build_upload_data(self, msg_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建上传数据

        Args:
            msg_data: 消息数据

        Returns:
            上传数据字典
        """
        msgid = msg_data.get('msgid', '')
        content = self._extract_text_content(msg_data)
        files = self._extract_files(msg_data)

        return {
            'sourceId': msgid,  # 来源标识
            'content': content,
            'fileDetails': files  # 文件详细信息(包含路径)
        }

    def upload_message(self, msg_data: Dict[str, Any]) -> bool:
        """
        上传单条消息

        Args:
            msg_data: 消息数据

        Returns:
            是否上传成功
        """
        if not self.enabled:
            logger.debug("上传功能已禁用")
            return False

        msgid = msg_data.get('msgid', '')

        # 检查是否已上传
        if msgid in self.uploaded_msgids:
            logger.info(f"消息已上传,跳过: {msgid}")
            return True

        # 构建上传数据
        upload_data = self._build_upload_data(msg_data)

        logger.info("=" * 60)
        logger.info(f"[UPLOAD] 上传参数详情:")
        logger.info(f"  - API URL: {self.api_url}")
        logger.info(f"  - sourceId: {upload_data.get('sourceId')}")
        logger.info(f"  - content: {upload_data.get('content')[:100]}...")
        logger.info(f"  - content 长度: {len(upload_data.get('content', ''))} 字符")
        logger.info(f"  - fileDetails 数量: {len(upload_data.get('fileDetails', []))} 个")
        logger.info(f"  - fileDetails 列表:")
        for i, file_info in enumerate(upload_data.get('fileDetails', []), 1):
            file_url = file_info.get('url', '')
            exists = "[OK]" if os.path.exists(file_url) else "[FAIL]"
            logger.info(f"    {i}. [{exists}] {file_url}")

        logger.info(f"")
        logger.info(f"[UPLOAD] 实际发送的请求结构:")
        logger.info(f"  - form_data (表单字段):")
        logger.info(f"    * content: {upload_data.get('content', '')[:50]}...")
        logger.info(f"    * sourceId: {upload_data.get('sourceId', '')}")
        logger.info("=" * 60)

        try:
            # 准备文件列表
            files_to_upload = []

            # 只允许上传的媒体文件类型
            ALLOWED_MEDIA_TYPES = {'image', 'video'}

            # 读取实际文件(从 fileDetails 中提取文件路径并读取二进制内容)
            for file_info in upload_data.get('fileDetails', []):
                file_type = file_info.get('type', '')
                file_url = file_info.get('url', '')

                # 只处理图片和视频类型
                if file_type not in ALLOWED_MEDIA_TYPES:
                    logger.info(f"[FILE] 跳过非媒体文件: {file_type} - {file_url}")
                    continue

                if file_url and os.path.exists(file_url):
                    try:
                        # 读取二进制文件内容
                        with open(file_url, 'rb') as f:
                            file_content = f.read()

                        # 使用文件名(fileDetails 中的 fileName 或从路径提取)
                        file_name = file_info.get('fileName', os.path.basename(file_url))

                        # 根据文件类型设置 MIME 类型
                        if file_type == 'image':
                            mime_type = 'image/jpeg'
                        elif file_type == 'video':
                            mime_type = 'video/mp4'
                        else:
                            mime_type = 'application/octet-stream'

                        # 添加到文件列表(字段名为 'files')
                        files_to_upload.append(
                            ('files', (file_name, file_content, mime_type))
                        )
                        logger.info(f"[FILE] 读取文件成功: {file_name} ({len(file_content)} bytes, {mime_type})")
                    except Exception as e:
                        logger.warning(f"[FILE] 读取文件失败 {file_url}: {e}")
                else:
                    logger.warning(f"[FILE] 文件不存在: {file_url}")

            # 打印实际发送的文件列表
            logger.info(f"")
            logger.info(f"[UPLOAD] 实际发送的文件列表: {len(files_to_upload)} 个")
            for i, (field_name, (fname, fcontent, ftype)) in enumerate(files_to_upload, 1):
                logger.info(f"  {i}. {field_name}: {fname} ({len(fcontent)} bytes, {ftype})")
            logger.info("=" * 60)

            # 发送 POST 请求 (使用 multipart/form-data 格式)
            # 根据 curl 示例,content 和 sourceId 是表单字段,files 是文件字段
            request_headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': '*/*'
            }

            # 构建表单数据
            form_data = {
                'content': upload_data.get('content', ''),
                'sourceId': upload_data.get('sourceId', '')
            }

            logger.info(f"[REQUEST] 请求方法: POST")
            logger.info(f"[REQUEST] 请求头: {request_headers}")
            logger.info(f"[REQUEST] Content-Type: multipart/form-data")
            logger.info(f"[REQUEST] 表单字段:")
            logger.info(f"  - content: {form_data['content'][:50]}...")
            logger.info(f"  - sourceId: {form_data['sourceId']}")
            logger.info(f"[REQUEST] 文件字段: {len(files_to_upload)} 个")

            response = requests.post(
                self.api_url,
                files=files_to_upload,
                data=form_data,  # 直接使用表单数据,不需要 JSON 包装
                timeout=self.api_timeout,
                headers=request_headers
            )

            # 打印实际请求的信息
            logger.info(f"[REQUEST] 实际请求头: {response.request.headers}")
            logger.info(f"[REQUEST] 请求 URL: {response.request.url}")
            logger.info(f"[REQUEST] 请求体类型: {type(response.request.body)}")

            # 打印响应信息
            logger.info(f"[RESPONSE] 响应状态码: {response.status_code}")
            logger.info(f"[RESPONSE] 响应头: {dict(response.headers)}")
            logger.info(f"[RESPONSE] 响应体: {response.text}")

            # 检查响应
            if response.status_code == 200:
                result = response.json()
                # 成功的条件: success=true 或 code=0/200/10001(同步成功)
                if result.get('success') or result.get('code') in [0, 200, 10001]:
                    logger.info(f"[OK] 消息上传成功: {msgid}")
                    logger.info(f"  - 文本内容: {len(upload_data['content'])} 字符")
                    logger.info(f"  - 文件数量: {len(files_to_upload)} 个")
                    logger.info(f"  - API 响应: {result}")

                    # 记录已上传
                    self.uploaded_msgids.add(msgid)
                    self._save_uploaded_records()
                    return True
                else:
                    logger.error(f"[FAIL] 上传失败: {result}")
                    logger.error(f"  - 请求参数: {json.dumps(upload_data, ensure_ascii=False)}")
                    return False
            else:
                logger.error(f"[FAIL] HTTP 错误: {response.status_code}")
                logger.error(f"  - 响应: {response.text}")
                logger.error(f"  - 请求参数: {json.dumps(upload_data, ensure_ascii=False)}")
                return False

        except requests.exceptions.Timeout:
            logger.error(f"[TIMEOUT] 上传超时: {msgid}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"[ERROR] 请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"[ERROR] 上传失败: {e}", exc_info=True)
            return False

    def upload_batch(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        批量上传消息

        Args:
            messages: 消息列表

        Returns:
            统计信息 {"success": 成功数, "failed": 失败数, "skipped": 跳过数}
        """
        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        for msg in messages:
            msgid = msg.get('msgid', '')

            # 跳过非笔记消息
            if msg.get('msgtype') != 'note':
                logger.debug(f"跳过非笔记消息: {msgid}")
                continue

            # 检查是否已上传
            if msgid in self.uploaded_msgids:
                logger.debug(f"消息已上传,跳过: {msgid}")
                stats['skipped'] += 1
                continue

            # 上传
            if self.upload_message(msg):
                stats['success'] += 1
            else:
                stats['failed'] += 1

        return stats

    def upload_from_file(self, filepath: str) -> bool:
        """
        从 JSON 文件上传消息

        Args:
            filepath: JSON 文件路径

        Returns:
            是否上传成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                msg_data = json.load(f)

            return self.upload_message(msg_data)

        except Exception as e:
            logger.error(f"加载文件失败 {filepath}: {e}")
            return False


def upload_all_notes():
    """上传所有笔记消息"""
    logger.info("=" * 60)
    logger.info("开始上传笔记消息")
    logger.info("=" * 60)

    # 加载配置
    config = load_config()

    # 创建上传器
    uploader = NoteUploader(config)

    # 查找所有消息文件
    import glob
    pattern = os.path.join(uploader.save_dir, 'msg_*.json')
    files = glob.glob(pattern)

    logger.info(f"找到 {len(files)} 个消息文件")

    # 加载消息
    messages = []
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                msg_data = json.load(f)
            messages.append(msg_data)
        except Exception as e:
            logger.error(f"加载文件失败 {filepath}: {e}")

    # 批量上传
    stats = uploader.upload_batch(messages)

    logger.info("=" * 60)
    logger.info(f"上传完成 | 成功: {stats['success']} | 失败: {stats['failed']} | 跳过: {stats['skipped']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    upload_all_notes()
