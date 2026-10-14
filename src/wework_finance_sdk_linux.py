"""
企业微信会话存档 SDK 封装 (Linux 版本)

通过 ctypes 调用 libWeWorkFinanceSdk_C.so，实现：
- 拉取聊天记录（GetChatData）
- RSA 解密 encrypt_random_key
- 解密消息内容（DecryptData）
- 下载媒体文件（GetMediaData）
"""

import ctypes
import json
import os
import base64
import logging
from typing import Optional, Dict, Any

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

logger = logging.getLogger(__name__)


class WeWorkFinanceSDK:
    """
    企业微信会话存档 C SDK 的 Python 封装（Linux 版本）

    依赖 linux_sdk/libWeWorkFinanceSdk_C.so
    """

    def __init__(self, corp_id: str, secret: str, private_key: str, sdk_lib_path: str = None):
        """
        初始化 SDK

        Args:
            corp_id: 企业 ID
            secret: 会话存档应用的 secret
            private_key: RSA 私钥（PEM 格式，用于解密消息）
            sdk_lib_path: SDK SO 路径（默认从 linux_sdk 目录加载）
        """
        self.corp_id = corp_id
        self.secret = secret
        self.private_key = private_key

        # 加载 SDK SO
        if sdk_lib_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sdk_lib_path = os.path.join(project_root, "linux_sdk", "libWeWorkFinanceSdk_C.so")

        if not os.path.exists(sdk_lib_path):
            raise FileNotFoundError(
                f"SDK SO 不存在：{sdk_lib_path}\n"
                f"请确保 SO 文件位于：linux_sdk/libWeWorkFinanceSdk_C.so"
            )

        try:
            # Linux 下直接加载
            self.sdk = ctypes.CDLL(sdk_lib_path)
            logger.info(f"SDK 加载成功：{sdk_lib_path}")
        except OSError as e:
            logger.error(f"SDK 加载失败：{e}")
            logger.error(
                f"请检查:\n"
                f"  1. SO 文件是否存在：{sdk_lib_path}\n"
                f"  2. 文件权限是否正确 (chmod +x)\n"
                f"  3. 依赖库是否完整 (ldd {sdk_lib_path})"
            )
            raise

        # 设置函数签名并初始化
        self._setup_function_signatures()
        self._init_sdk()

    def _setup_function_signatures(self):
        """预设置所有 C 函数签名，避免重复设置"""
        # NewSdk
        self.sdk.NewSdk.argtypes = []
        self.sdk.NewSdk.restype = ctypes.c_void_p

        # Init
        self.sdk.Init.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        self.sdk.Init.restype = ctypes.c_int

        # NewSlice / FreeSlice
        self.sdk.NewSlice.argtypes = []
        self.sdk.NewSlice.restype = ctypes.c_void_p
        self.sdk.FreeSlice.argtypes = [ctypes.c_void_p]
        self.sdk.FreeSlice.restype = None

        # GetContentFromSlice / GetSliceLen
        self.sdk.GetContentFromSlice.argtypes = [ctypes.c_void_p]
        self.sdk.GetContentFromSlice.restype = ctypes.c_char_p
        self.sdk.GetSliceLen.argtypes = [ctypes.c_void_p]
        self.sdk.GetSliceLen.restype = ctypes.c_int

        # GetChatData
        self.sdk.GetChatData.argtypes = [
            ctypes.c_void_p,      # sdk
            ctypes.c_ulonglong,   # seq
            ctypes.c_uint,        # limit
            ctypes.c_char_p,      # proxy
            ctypes.c_char_p,      # passwd
            ctypes.c_int,         # timeout
            ctypes.c_void_p,      # chatDatas (Slice*)
        ]
        self.sdk.GetChatData.restype = ctypes.c_int

        # DecryptData
        self.sdk.DecryptData.argtypes = [
            ctypes.c_char_p,      # encrypt_key (解密后的 random key 原始字节)
            ctypes.c_char_p,      # encrypt_msg
            ctypes.c_void_p,      # msg (Slice*)
        ]
        self.sdk.DecryptData.restype = ctypes.c_int

        # MediaData 相关
        self.sdk.NewMediaData.argtypes = []
        self.sdk.NewMediaData.restype = ctypes.c_void_p
        self.sdk.FreeMediaData.argtypes = [ctypes.c_void_p]
        self.sdk.FreeMediaData.restype = None

        self.sdk.GetMediaData.argtypes = [
            ctypes.c_void_p,      # sdk
            ctypes.c_char_p,      # indexbuf
            ctypes.c_char_p,      # sdkFileid
            ctypes.c_char_p,      # proxy
            ctypes.c_char_p,      # passwd
            ctypes.c_int,         # timeout
            ctypes.c_void_p,      # media_data (MediaData*)
        ]
        self.sdk.GetMediaData.restype = ctypes.c_int

        # GetData 返回 POINTER(c_char) 而非 c_char_p，因为二进制数据含 null 字节
        self.sdk.GetData.argtypes = [ctypes.c_void_p]
        self.sdk.GetData.restype = ctypes.POINTER(ctypes.c_char)
        self.sdk.GetDataLen.argtypes = [ctypes.c_void_p]
        self.sdk.GetDataLen.restype = ctypes.c_int
        self.sdk.IsMediaDataFinish.argtypes = [ctypes.c_void_p]
        self.sdk.IsMediaDataFinish.restype = ctypes.c_int
        self.sdk.GetOutIndexBuf.argtypes = [ctypes.c_void_p]
        self.sdk.GetOutIndexBuf.restype = ctypes.POINTER(ctypes.c_char)

    def _init_sdk(self):
        """初始化 SDK 实例"""
        self.sdk_ptr = self.sdk.NewSdk()
        if not self.sdk_ptr:
            raise RuntimeError("NewSdk() 返回空指针")

        ret = self.sdk.Init(
            self.sdk_ptr,
            self.corp_id.encode('utf-8'),
            self.secret.encode('utf-8')
        )
        if ret != 0:
            raise RuntimeError(f"SDK Init() 失败，错误码：{ret}")

        logger.info("SDK 初始化成功")

    def get_chat_data(self, seq: int, limit: int = 1000) -> Dict[str, Any]:
        """
        拉取聊天记录

        Args:
            seq: 起始序号（从上次拉取的 seq 继续）
            limit: 每次拉取条数（最大 1000）

        Returns:
            包含 chatdata 列表的字典，失败返回空字典
        """
        slice_ptr = self.sdk.NewSlice()
        if not slice_ptr:
            logger.error("NewSlice() 返回空指针")
            return {}

        try:
            ret = self.sdk.GetChatData(
                self.sdk_ptr, seq, limit,
                None,   # proxy
                None,   # passwd
                30,     # timeout (秒)
                slice_ptr
            )

            if ret != 0:
                logger.error(f"GetChatData() 失败，错误码：{ret}")
                return {}

            content = self.sdk.GetContentFromSlice(slice_ptr)
            length = self.sdk.GetSliceLen(slice_ptr)

            if not content or length <= 0:
                return {}

            chat_data_str = ctypes.string_at(content, length).decode('utf-8')
            return json.loads(chat_data_str)

        except Exception as e:
            logger.error(f"get_chat_data 异常：{e}")
            return {}
        finally:
            self.sdk.FreeSlice(slice_ptr)

    def _decrypt_random_key(self, encrypt_key: str) -> bytes:
        """
        使用 RSA 私钥解密 encrypt_random_key

        企业微信在每条消息中用随机 AES key 加密消息内容，
        再用 RSA 公钥加密该随机 key。这里用私钥还原出该随机 key。

        Args:
            encrypt_key: Base64 编码的 RSA 加密数据

        Returns:
            解密后的 AES key 原始字节
        """
        try:
            private_key = RSA.import_key(self.private_key.encode('utf-8'))
            cipher = PKCS1_v1_5.new(private_key)
            encrypted_data = base64.b64decode(encrypt_key)
            decrypted_data = cipher.decrypt(encrypted_data, None)
            return decrypted_data
        except Exception as e:
            logger.error(f"RSA 解密 random key 失败：{e}")
            return b""

    def decrypt_data(self, encrypt_key: str, encrypt_msg: str) -> Dict[str, Any]:
        """
        解密聊天消息

        流程:
        1. RSA 解密 encrypt_random_key 得到 AES key
        2. 用 AES key 调用 DecryptData 解密消息体

        Args:
            encrypt_key: 加密的 random key（Base64）
            encrypt_msg: 加密的消息内容

        Returns:
            解密后的消息字典，失败返回空字典
        """
        decrypted_key = self._decrypt_random_key(encrypt_key)
        if not decrypted_key:
            return {}

        slice_ptr = self.sdk.NewSlice()
        if not slice_ptr:
            logger.error("NewSlice() 返回空指针")
            return {}

        try:
            ret = self.sdk.DecryptData(
                decrypted_key,
                encrypt_msg.encode('utf-8'),
                slice_ptr
            )

            if ret != 0:
                logger.error(f"DecryptData() 失败，错误码：{ret}")
                return {}

            content = self.sdk.GetContentFromSlice(slice_ptr)
            length = self.sdk.GetSliceLen(slice_ptr)

            if not content or length <= 0:
                return {}

            decrypt_str = ctypes.string_at(content, length).decode('utf-8')
            return json.loads(decrypt_str)

        except Exception as e:
            logger.error(f"decrypt_data 异常：{e}")
            return {}
        finally:
            self.sdk.FreeSlice(slice_ptr)

    def get_media_data(self, sdk_file_id: str, save_path: str) -> bool:
        """
        下载媒体文件（图片/视频/语音/文件）

        通过循环调用 GetMediaData 下载所有分片，直到 is_finish 为 True。

        Args:
            sdk_file_id: 媒体文件的 sdkfileid
            save_path: 本地保存路径

        Returns:
            是否下载成功
        """
        media_data_ptr = self.sdk.NewMediaData()
        if not media_data_ptr:
            logger.error("NewMediaData() 返回空指针")
            return False

        try:
            indexbuf = None  # 首次调用为 None
            all_data = b''

            while True:
                ret = self.sdk.GetMediaData(
                    self.sdk_ptr,
                    indexbuf,
                    sdk_file_id.encode('utf-8'),
                    None,   # proxy
                    None,   # passwd
                    60,     # timeout (秒)
                    media_data_ptr
                )

                if ret != 0:
                    logger.error(f"GetMediaData() 失败，错误码：{ret}")
                    return False

                data_ptr = self.sdk.GetData(media_data_ptr)
                data_len = self.sdk.GetDataLen(media_data_ptr)
                is_finish = self.sdk.IsMediaDataFinish(media_data_ptr)

                if data_ptr and data_len > 0:
                    data_bytes = ctypes.string_at(data_ptr, data_len)
                    all_data += data_bytes

                if is_finish:
                    break

                # 获取下一个分片的索引
                indexbuf = self.sdk.GetOutIndexBuf(media_data_ptr)

            if not all_data:
                logger.warning(f"媒体文件内容为空：{sdk_file_id}")
                return False

            # 确保保存目录存在
            save_dir = os.path.dirname(save_path)
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)

            with open(save_path, 'wb') as f:
                f.write(all_data)

            logger.info(f"媒体文件已保存：{save_path} ({len(all_data)} bytes)")
            return True

        except Exception as e:
            logger.error(f"get_media_data 异常：{e}")
            return False
        finally:
            self.sdk.FreeMediaData(media_data_ptr)
