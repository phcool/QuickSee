"""
前端页面路由
处理网站主页和聊天页的渲染
"""
from flask import Blueprint, render_template, current_app, redirect, url_for
import os
from backend.app_modules.vectordb.faiss_store import vector_store
from backend.app_modules.config import FAISS_INDEX_PATH

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/')
def index():
    """渲染网站主页"""
    # 检查是否有索引文件
    has_index = check_index_exists()
    # 获取索引统计信息
    stats = get_index_stats() if has_index else None
    return render_template('index.html', has_index=has_index, stats=stats)

@frontend_bp.route('/chat')
def chat_page():
    """渲染聊天页面"""
    return render_template('chat.html')

@frontend_bp.errorhandler(404)
def page_not_found(e):
    """404错误处理"""
    return render_template('404.html'), 404

def check_index_exists():
    """检查索引文件是否存在"""
    index_file = f"{FAISS_INDEX_PATH}.index"
    metadata_file = f"{FAISS_INDEX_PATH}.meta"
    return os.path.exists(index_file) and os.path.exists(metadata_file)

def get_index_stats():
    """获取索引统计信息"""
    if vector_store and hasattr(vector_store, 'get_stats'):
        return vector_store.get_stats()
    return None 