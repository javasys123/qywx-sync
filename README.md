# 企业微信会话存档同步系统

<div align="center">

**自动同步、解密、上传企业微信会话存档消息**

[![Version](https://img.shields.io/badge/version-2.4-blue.svg)](https://github.com/your-repo)
[![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](https://www.microsoft.com/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

</div>

---

##  功能特性

- 🔄 **消息同步** - 自动拉取企业微信会话存档消息
- 🔐 **消息解密** - RSA私钥解密,支持文本、图片、视频、笔记等
- 📥 **媒体下载** - 自动下载图片、视频、文件到本地
-  **自动上传** - HTTP POST上传到指定API,支持多文件
-  **自动清理** - 3天前媒体文件自动删除,节省磁盘空间
-  **断点续传** - 记录同步位置,中断后可继续
- ⏰ **定时调度** - 基于schedule库,可配置同步间隔

---

##  快速开始

### Windows

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置企业微信 (编辑 config/config.yaml)
# 3. 启动服务
python scheduler.py
```

### Linux

```bash
# 1. 安装Python 3.11+
# 2. 安装依赖
pip3.11 install -r requirements_linux.txt

# 3. 设置SDK权限
chmod +x linux_sdk/libWeWorkFinanceSdk_C.so

# 4. 配置企业微信 (编辑 config/config.yaml)
# 5. 启动服务
python3.11 scheduler_linux.py
```

---

## 📁 项目结构

```
qywx/
├── sync_archive.py              # Windows主程序
├── sync_archive_linux.py        # Linux主程序
├── scheduler.py                 # Windows调度器
├── scheduler_linux.py           # Linux调度器
├── upload_client.py             # 上传客户端
├── start.bat                    # Windows启动脚本
├── start_linux.sh               # Linux启动脚本
├── requirements.txt             # Windows依赖
├── requirements_linux.txt       # Linux依赖
├── .gitignore                   # Git配置
│
├── config/
│   └── config.yaml              # 主配置文件
│
├── src/
│   ├── __init__.py
│   ├── utils.py                 # 工具函数
│   ├── wework_finance_sdk.py    # Windows SDK封装
│   └── wework_finance_sdk_linux.py  # Linux SDK封装
│
── windows_sdk/                 # Windows SDK
│   ├── WeWorkFinanceSdk_C.dll
│   └── ... (共7个DLL)
│
├── linux_sdk/                   # Linux SDK
│   ├── libWeWorkFinanceSdk_C.so
│   └── WeWorkFinanceSdk_C.h
│
├── downloads/                   # 数据目录 (运行时生成)
│   ├── .last_seq
│   ├── .uploaded_records
│   └── msg_*.json
│
── logs/                        # 日志目录
    ── sync.log
```

---

## ️ 配置说明

### config/config.yaml

```yaml
# 企业微信配置
qywx:
  corp_id: "企业ID"
  finance_secret: "会话存档密钥"
  finance_private_key: |
    -----BEGIN RSA PRIVATE KEY-----
    ... (RSA私钥)
    -----END RSA PRIVATE KEY-----

# 存储配置
storage:
  base_path: "./downloads"
  auto_cleanup_days: 3  # 3天前媒体文件自动清理

# 调度器配置
scheduler:
  enabled: true
  interval_seconds: 60  # 60秒同步一次
  mode: interval

# 上传配置
upload:
  enabled: true
  api_url: "https://api.example.com/upload"
  auto_upload: true

# 日志配置
logging:
  level: "INFO"
  file: "./logs/sync.log"
  rotation: "10 MB"
  retention: "10 days"
```

---

## 📊 数据流程

```
企业微信服务器
    ↓
同步服务 (拉取消息 → RSA解密 → 下载媒体 → 保存JSON → 清理旧文件)
    ↓
自动上传 (检查记录 → HTTP POST → 记录状态)
    ↓
本地存储 (JSON永久保存, 媒体3天后清理)
```

---

## 🛠️ 常用命令

### Windows

```bash
python scheduler.py          # 定时同步 (推荐)
python sync_archive.py       # 单次同步
type logs\sync.log           # 查看日志
taskkill /f /im python.exe   # 停止服务
```

### Linux

```bash
python3.11 scheduler_linux.py          # 定时同步 (推荐)
python3.11 sync_archive_linux.py       # 单次同步
tail -f logs/sync.log                  # 查看日志
pkill -f scheduler_linux               # 停止服务
```

---

## 🔍 故障排查

### SDK加载失败

**Windows**: 安装VC++ Redistributable 2015-2022  
**Linux**: `chmod +x linux_sdk/libWeWorkFinanceSdk_C.so`

### 依赖缺失

```bash
pip install -r requirements.txt
# 或
pip3.11 install -r requirements_linux.txt
```

### 编码问题

```bash
export PYTHONIOENCODING=utf-8
export LANG=en_US.UTF-8
```

---

## 📈 版本历史

### v2.4 (2026-10-14)
- ✅ 添加Linux版本支持
- ✅ 移除守护进程模式
- ✅ 优化日志输出

### v2.3 (2026-10-14)
- ✅ 添加媒体文件自动清理功能
- ✅ 添加定时任务调度器

### v2.0 (2026-10-13)
- ✅ 添加自动上传功能

### v1.0 (2026-10-12)
- ✅ 初始版本

---

## 📝 许可证

MIT License

---

<div align="center">

**版本**: v2.4 | **更新**: 2026-10-14 | **平台**: Windows 10/11, Linux

</div>
