#!/bin/bash

# 新闻聊天系统Web应用启动脚本
# 提供命令行参数，启动Flask Web服务

# 默认配置
HOST="127.0.0.1"
PORT=5002
DEBUG=false
RSS_DIR="data/rss"
FAISS_INDEX="data/faiss_index"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --host=*)
      HOST="${1#*=}"
      shift
      ;;
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    --rss-dir=*)
      RSS_DIR="${1#*=}"
      shift
      ;;
    --faiss-index=*)
      FAISS_INDEX="${1#*=}"
      shift
      ;;
    -h|--help)
      echo "使用方法: ./start_website.sh [选项]"
      echo
      echo "选项:"
      echo "  --host=HOST        服务器监听主机 (默认: 127.0.0.1)"
      echo "  --port=PORT        服务器监听端口 (默认: 5002)"
      echo "  --debug            启用调试模式"
      echo "  --rss-dir=DIR      RSS文件目录路径 (默认: data/rss)"
      echo "  --faiss-index=FILE FAISS索引文件路径 (默认: data/faiss_index)"
      echo "  -h, --help         显示此帮助信息"
      exit 0
      ;;
    *)
      echo "未知选项: $1"
      echo "使用 --help 查看帮助信息"
      exit 1
      ;;
  esac
done

# 确保目录存在
mkdir -p "$RSS_DIR"
mkdir -p "$(dirname "$FAISS_INDEX")"

# 设置环境变量
export RSS_DIR="$RSS_DIR"
export FAISS_INDEX_PATH="$FAISS_INDEX"
export FLASK_APP=server.py

# 输出配置信息
echo "启动新闻聊天系统Web应用..."
echo "主机: $HOST"
echo "端口: $PORT"
echo "调试模式: $DEBUG"
echo "RSS目录: $RSS_DIR"
echo "FAISS索引: $FAISS_INDEX"
echo
echo "按 Ctrl+C 停止服务"
echo "------------------------------"

# 启动服务器
if [ "$DEBUG" = true ]; then
  export FLASK_DEBUG=1
  python server.py
else
  python server.py
fi 