"""
新闻API路由
处理获取最新新闻的API端点
"""
import asyncio
from flask import Blueprint, request, jsonify, current_app
from backend.app_modules.parsers.rss_parser import RSSParser
import os
import json
from backend.app_modules.utils.date_utils import parse_date
from RSS import add_rss_source

# 创建蓝图
news_bp = Blueprint('news', __name__)

@news_bp.route('/latest', methods=['GET'])
def get_latest_news():
    """
    获取最新新闻API
    
    参数:
        limit: 返回结果数量 (默认10)
    
    返回:
        最新新闻列表
    """
    limit = request.args.get('limit', 10, type=int)
    
    try:
        # 直接从RSS文件获取最新新闻
        rss_dir = os.getenv("RSS_DIR", "data/rss")
        parser = RSSParser(rss_directory=rss_dir)
        articles = parser.parse_all_files()
        
        # 按日期排序(最新的在前)
        # 使用导入的parse_date函数而不是定义局部函数
                
        # 按日期排序
        sorted_articles = sorted(
            articles, 
            key=lambda x: parse_date(x.pub_date) or 0, 
            reverse=True
        )
        
        # 截取要求的数量
        latest_articles = sorted_articles[:limit]
        
        # 格式化结果
        results = []
        for article in latest_articles:
            # 准备内容预览
            preview = article.content[:200] + "..." if len(article.content) > 200 else article.content
            
            results.append({
                'title': article.title,
                'pub_date': article.pub_date,
                'link': article.link,
                'preview': preview,
                'source_file': article.source_file
            })
            
        return jsonify({
            'results': results,
            'total': len(results)
        })
    except Exception as e:
        current_app.logger.error(f"获取最新新闻时出错: {str(e)}")
        return jsonify({'error': f'获取最新新闻失败: {str(e)}'}), 500 

@news_bp.route('/rss_sources', methods=['GET'])
def get_rss_sources():
    """
    获取所有已订阅的RSS源
    
    返回:
        RSS源列表
    """
    try:
        # 读取RSS_source.json文件，从根目录读取
        rss_sources_path = 'RSS_source.json'
        
        if not os.path.exists(rss_sources_path):
            return jsonify({'sources': [], 'total': 0})
        
        with open(rss_sources_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 格式化返回数据
        sources = []
        for item in data:
            source = {
                'url': item.get('url', ''),
                'title': item.get('title', '未命名'),
                'description': item.get('简介', ''),
                'attribute': item.get('属性', '')
            }
            sources.append(source)
        
        return jsonify({
            'sources': sources,
            'total': len(sources)
        })
    except Exception as e:
        current_app.logger.error(f"获取RSS源时出错: {str(e)}")
        return jsonify({'error': f'获取RSS源失败: {str(e)}'}), 500

@news_bp.route('/add_rss', methods=['POST'])
def add_rss_source_api():
    """添加新的RSS源"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': '请提供JSON数据'}), 400
    
    # 获取必要参数
    url = data.get('url')
    title = data.get('title')
    
    if not url or not title:
        return jsonify({'success': False, 'message': '请提供URL和标题'}), 400
    
    # 可选参数
    description = data.get('description')
    attribute = data.get('attribute')
    
    # 调用函数添加RSS源
    success = add_rss_source(url, title, description, attribute)
    
    if success:
        return jsonify({'success': True, 'message': f'成功添加RSS源: {title}'}), 201
    else:
        return jsonify({'success': False, 'message': 'RSS源添加失败，可能URL已存在'}), 400 