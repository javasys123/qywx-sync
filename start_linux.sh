#!/bin/bash
# 企业微信会话存档同步系统 - Linux 启动脚本

echo "========================================"
echo "WeChat Archive Sync System - Linux"
echo "========================================"
echo ""

# 检查 Python
echo "[1/3] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.11+"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[OK] Python $PYTHON_VERSION"

# 检查依赖
echo "[2/3] Checking dependencies..."
python3 -c "import loguru, requests, schedule" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] Installing dependencies..."
    pip3 install loguru requests pycryptodome pyyaml schedule
fi

# 检查 SDK
echo "[3/3] Checking SDK..."
if [ ! -f "linux_sdk/libWeWorkFinanceSdk_C.so" ]; then
    echo "[ERROR] SDK not found: linux_sdk/libWeWorkFinanceSdk_C.so"
    exit 1
fi

# 设置执行权限
chmod +x linux_sdk/libWeWorkFinanceSdk_C.so 2>/dev/null

echo ""
echo "========================================"
echo "Please select mode:"
echo "  1. Scheduler Mode (Recommended)"
echo "  2. Single Sync"
echo ""
read -p "Enter your choice (1-2): " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo "Starting scheduler mode..."
    python3 scheduler_linux.py
elif [ "$choice" = "2" ]; then
    echo ""
    echo "Starting single sync..."
    python3 sync_archive_linux.py
else
    echo ""
    echo "Invalid choice. Defaulting to scheduler mode..."
    python3 scheduler_linux.py
fi
