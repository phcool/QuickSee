"""
索引管理API路由
处理索引状态查询
"""
import os
from flask import Blueprint, jsonify, current_app
from backend.app_modules.vectordb.faiss_store import vector_store
from backend.app_modules.config import FAISS_INDEX_PATH

# 创建蓝图
index_bp = Blueprint('index', __name__)

@index_bp.route('/status', methods=['GET'])
def get_index_status():
    """
    获取索引状态API
    
    返回:
        索引状态信息，包括是否存在、文档数量等
    """
    # 检查索引是否存在
    index_exists = check_index_exists()
    
    # 获取索引统计信息
    stats = None
    if index_exists and vector_store and hasattr(vector_store, 'get_stats'):
        stats = vector_store.get_stats()
    
    return jsonify({
        'exists': index_exists,
        'stats': stats
    })

def check_index_exists():
    """检查索引文件是否存在"""
    index_file = f"{FAISS_INDEX_PATH}.index"
    metadata_file = f"{FAISS_INDEX_PATH}.meta"
    return os.path.exists(index_file) and os.path.exists(metadata_file) 