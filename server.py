#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新闻聊天系统Web服务简化入口
"""

import os
import sys
from flask import Flask
from flask_cors import CORS

# 静态内容文件夹
STATIC_FOLDER = os.path.join('frontend', 'static')
TEMPLATE_FOLDER = os.path.join('frontend', 'templates')

app = Flask(__name__, 
    static_folder=STATIC_FOLDER,
    template_folder=TEMPLATE_FOLDER)

# 允许跨域请求
CORS(app)

# 配置密钥
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_change_in_production')

# 导入路由
from backend.api.news_routes import news_bp
from backend.api.chat_routes import chat_bp
from backend.api.index_routes import index_bp
from backend.api import frontend_routes

# 注册蓝图
app.register_blueprint(news_bp, url_prefix='/api/news')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(index_bp, url_prefix='/api/index')
app.register_blueprint(frontend_routes.frontend_bp)

# 主函数
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True) 