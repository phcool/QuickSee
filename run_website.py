#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新闻聊天系统Web服务启动脚本
提供命令行参数，加载Flask应用并启动Web服务
"""

import os
import sys
import argparse
import logging
from waitress import serve

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('news_chat_web')

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动新闻聊天Web服务')
    
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='监听主机 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000,
                        help='监听端口 (默认: 5000)')
    parser.add_argument('--debug', action='store_true',
                        help='启用Flask调试模式')
    parser.add_argument('--rss-dir', type=str, default=os.path.join('data', 'rss'),
                        help='RSS文件目录路径 (默认: data/rss)')
    parser.add_argument('--faiss-index', type=str,
                        default=os.path.join('data', 'faiss_index'),
                        help='FAISS索引文件路径 (默认: data/faiss_index)')
    
    return parser.parse_args()

def create_directories(args):
    """创建必要的目录"""
    os.makedirs(args.rss_dir, exist_ok=True)
    os.makedirs(os.path.dirname(args.faiss_index), exist_ok=True)

def main():
    """主函数，解析参数并启动Web服务"""
    args = parse_args()
    
    # 设置环境变量
    os.environ['RSS_DIR'] = os.path.abspath(args.rss_dir)
    os.environ['FAISS_INDEX_PATH'] = os.path.abspath(args.faiss_index)
    
    # 创建必要的目录
    create_directories(args)
    
    try:
        # 导入后端应用
        from backend.app import create_app
        app = create_app()
        
        if args.debug:
            # 开发模式，使用Flask内置服务器
            logger.info(f"以开发模式启动服务器，地址: {args.host}:{args.port}")
            app.run(host=args.host, port=args.port, debug=True)
        else:
            # 生产模式，使用waitress服务器
            logger.info(f"以生产模式启动服务器，地址: {args.host}:{args.port}")
            serve(app, host=args.host, port=args.port, threads=4)
    except ModuleNotFoundError as e:
        logger.error(f"加载应用失败: {e}")
        print(f"错误: {e}")
        print("请确保已安装所有依赖，并且项目目录结构正确。")
        sys.exit(1)
    except Exception as e:
        logger.error(f"启动服务器时出错: {e}", exc_info=True)
        print(f"启动服务器时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 