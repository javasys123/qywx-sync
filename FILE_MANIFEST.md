# 项目文件清单

## 核心文件

### Python程序
- `sync_archive.py` - Windows版主程序
- `sync_archive_linux.py` - Linux版主程序
- `scheduler.py` - Windows版定时调度器
- `scheduler_linux.py` - Linux版定时调度器
- `upload_client.py` - 上传客户端

### 配置文件
- `config/config.yaml` - 主配置文件
- `requirements.txt` - Windows版依赖
- `requirements_linux.txt` - Linux版依赖

### 启动脚本
- `start.bat` - Windows版启动脚本
- `start_linux.sh` - Linux版启动脚本

### 核心模块
- `src/__init__.py` - 模块初始化
- `src/utils.py` - 工具函数
- `src/wework_finance_sdk.py` - Windows版SDK封装
- `src/wework_finance_sdk_linux.py` - Linux版SDK封装

### SDK文件
- `windows_sdk/` - Windows版SDK (7个DLL)
  - `WeWorkFinanceSdk_C.dll` - 主SDK
  - `libcrypto-3-x64.dll` - 加密库
  - `libcurl-x64.dll` - HTTP库
  - `libssl-3-x64.dll` - SSL库
  - `msvcp140.dll` - VC++运行时
  - `vcruntime140.dll` - VC++运行时
  - `vcruntime140_1.dll` - VC++运行时

- `linux_sdk/` - Linux版SDK
  - `libWeWorkFinanceSdk_C.so` - 主SDK库
  - `WeWorkFinanceSdk_C.h` - 头文件
  - `md5.txt` - MD5校验
  - `version.txt` - 版本信息

### 文档
- `README.md` - 项目主文档
- `LICENSE` - MIT许可证

### 配置文件
- `.gitignore` - Git忽略文件配置

---

## 运行时生成的文件

### 数据目录 (downloads/)
- `.last_seq` - 同步位置记录
- `.uploaded_records` - 上传记录
- `msg_*.json` - 消息记录
- `note_image_*.jpg` - 笔记图片
- `note_video_*.mp4` - 笔记视频
- `note_text_*.txt` - 笔记文本

### 日志目录 (logs/)
- `sync.log` - 同步日志

---

## 文件统计

| 类型 | 数量 | 说明 |
|------|------|------|
| Python文件 | 8 | 主程序、调度器、SDK封装等 |
| 配置文件 | 4 | config.yaml, requirements等 |
| 启动脚本 | 2 | Windows和Linux版 |
| SDK文件 | 11 | Windows(7) + Linux(4) |
| 文档文件 | 2 | README.md, LICENSE |
| 配置文件 | 1 | .gitignore |

**总计**: 28个核心文件

---

## 依赖包

### Windows
```
loguru          # 日志
requests        # HTTP请求
pycryptodome    # RSA加密
pyyaml          # YAML配置
schedule        # 定时任务
```

### Linux
```
loguru          # 日志
requests        # HTTP请求
pycryptodome    # RSA加密
pyyaml          # YAML配置
schedule        # 定时任务
```

---

## 目录结构

```
qywx/
├── 📄 sync_archive.py              # Windows主程序
├──  sync_archive_linux.py        # Linux主程序
── 📄 scheduler.py                 # Windows调度器
├── 📄 scheduler_linux.py           # Linux调度器
├── 📄 upload_client.py             # 上传客户端
├──  start.bat                    # Windows启动脚本
├── 📄 start_linux.sh               # Linux启动脚本
├── 📄 requirements.txt             # Windows依赖
├── 📄 requirements_linux.txt       # Linux依赖
├── 📄 .gitignore                  # Git配置
├──  LICENSE                     # MIT许可证
│
├── 📂 config/
│   └── config.yaml                 # 主配置文件
│
├── 📂 src/
│   ├── __init__.py
│   ├── utils.py
│   ├── wework_finance_sdk.py
│   └── wework_finance_sdk_linux.py
│
├── 📂 windows_sdk/
│   ├── WeWorkFinanceSdk_C.dll
│   ├── libcrypto-3-x64.dll
│   ├── libcurl-x64.dll
│   ├── libssl-3-x64.dll
│   ├── msvcp140.dll
│   ├── vcruntime140.dll
│   └── vcruntime140_1.dll
│
├── 📂 linux_sdk/
│   ├── libWeWorkFinanceSdk_C.so
│   ├── WeWorkFinanceSdk_C.h
│   ├── md5.txt
│   └── version.txt
│
├── 📂 downloads/                  # (运行时生成,已gitignore)
│
└── 📂 logs/                       # (运行时生成,已gitignore)
    └── sync.log
```

---

**整理时间**: 2026-10-14  
**版本**: v2.4  
**状态**: ✅ 完整干净,可上传GitHub
