#!/bin/bash
# Trading Hub 启动脚本

cd "$(dirname "$0")"

# 激活虚拟环境
source ../.venv/bin/activate

# 安装依赖
pip install fastapi uvicorn websockets -q

# 启动 API 服务器
echo "🚀 Starting Trading Hub API on http://localhost:8082"
echo "📊 Dashboard: file://$(pwd)/web/index.html"
echo ""

cd api
PYTHONPATH=.. python3 server.py
