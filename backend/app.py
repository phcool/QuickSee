"""
新闻聊天系统后端应用
"""
import os
import logging
from flask import Flask
from flask_cors import CORS

def create_app():
    """创建并配置Flask应用"""
    app = Flask(
        __name__, 
        static_folder='../frontend/static',
        template_folder='../frontend/templates'
    )
    
    # 允许跨域请求
    CORS(app)
    
    # 配置密钥
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_change_in_production')
    
    # 导入并注册API蓝图
    from backend.api.news_routes import news_bp
    from backend.api.chat_routes import chat_bp
    from backend.api.index_routes import index_bp
    
    app.register_blueprint(news_bp, url_prefix='/api/news')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(index_bp, url_prefix='/api/index')
    
    # 导入并注册前端路由
    from backend.api import frontend_routes
    app.register_blueprint(frontend_routes.frontend_bp)
    
    # 配置日志
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
    
    # 初始化FAISS检查
    _check_faiss()
    
    return app

def _check_faiss():
    """检查FAISS是否可用"""
    try:
        import faiss
        logging.info("FAISS库已成功加载")
    except ImportError:
        try:
            import faiss_cpu as faiss
            logging.info("FAISS-CPU库已成功加载")
        except ImportError:
            logging.error("无法加载FAISS库。向量搜索功能将不可用。请安装: pip install faiss-cpu") 