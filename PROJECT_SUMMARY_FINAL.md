# 企业微信会话存档同步系统 - 项目总结

## 📋 项目信息

| 项目 | 内容 |
|------|------|
| 名称 | 企业微信会话存档同步系统 |
| 版本 | v2.4 |
| 平台 | Windows 10/11, Linux (CentOS/Ubuntu/Debian) |
| Python | 3.8+ (Windows), 3.11+ (Linux) |
| 许可证 | MIT License |
| 更新日期 | 2026-10-14 |

---

## 🎯 核心功能

1. **消息同步** - 自动拉取企业微信会话存档消息
2. **消息解密** - RSA私钥解密消息内容
3. **媒体下载** - 自动下载图片、视频、文件
4. **自动上传** - HTTP POST上传到指定API
5. **自动清理** - 3天前媒体文件自动删除
6. **断点续传** - 记录同步位置
7. **定时调度** - 基于schedule库的定时任务

---

## 📁 项目结构

```
qywx/
├── 8个Python文件
├── 4个配置文件
├── 2个启动脚本
├── 11个SDK文件
├── 2个文档文件
└── 2个运行时目录 (已gitignore)
```

**总计**: 28个核心文件

---

## 🚀 快速部署

### Windows

```bash
pip install -r requirements.txt
python scheduler.py
```

### Linux

```bash
pip3.11 install -r requirements_linux.txt
chmod +x linux_sdk/libWeWorkFinanceSdk_C.so
python3.11 scheduler_linux.py
```

---

##  技术栈

- **语言**: Python 3.8+
- **加密**: pycryptodome (RSA)
- **HTTP**: requests
- **日志**: loguru
- **配置**: pyyaml
- **调度**: schedule
- **SDK**: 企业微信Finance SDK (C库)

---

## 📊 数据流程

```
企业微信 → 同步 → 解密 → 下载 → 保存 → 上传 → 清理
```

---

## 📝 文档

- `README.md` - 项目主文档
- `FILE_MANIFEST.md` - 文件清单
- `LICENSE` - MIT许可证

---

## ✅ 整理完成

项目已整理为完整、干净、专业的状态,可直接上传到GitHub。

**整理时间**: 2026-10-14  
**状态**: ✅ 就绪
