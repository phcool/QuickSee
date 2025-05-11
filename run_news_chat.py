#!/usr/bin/env python
"""
RSS新闻聊天 - 简化运行脚本
不需要命令行参数，直接运行
"""
import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入应用组件
from app.utils.logging_config import setup_logging
from app.parsers.rss_parser import RSSParser
from app.llm.llm_integration import get_embeddings, generate_rag_response
from app.vectordb.faiss_store import vector_store
from app.rag.retriever import rag_retriever
from app.config import FAISS_INDEX_PATH

# 设置日志
logger = setup_logging()

# 检查FAISS是否可用
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    try:
        import faiss_cpu as faiss
        FAISS_AVAILABLE = True
    except ImportError:
        logger.error("无法导入FAISS库。请确保已安装: pip install faiss-cpu 或 conda install -c conda-forge faiss-cpu")
        FAISS_AVAILABLE = False

if not FAISS_AVAILABLE:
    print("错误: FAISS库未安装。请安装FAISS后再次运行：")
    print("    pip install faiss-cpu --no-cache-dir")
    print("或对于macOS用户，尝试:")
    print("    conda install -c conda-forge faiss-cpu")
    sys.exit(1)

def check_index_exists():
    """检查索引文件是否存在"""
    index_file = f"{FAISS_INDEX_PATH}.index"
    metadata_file = f"{FAISS_INDEX_PATH}.meta"
    return os.path.exists(index_file) and os.path.exists(metadata_file)

def show_index_stats():
    """显示索引统计信息"""
    if vector_store and hasattr(vector_store, 'get_stats'):
        stats = vector_store.get_stats()
        print("\n索引统计信息:")
        print(f"文档总数: {stats['total_documents']}")
        print(f"向量总数: {stats['total_vectors']}")
        print(f"索引路径: {stats['index_path']}")
        print(f"向量维度: {stats['dimension']}")
        if stats['total_documents'] > 0:
            print(f"索引状态: 正常")
        else:
            print(f"索引状态: 空")
    else:
        print("无法获取索引统计信息")

def show_help():
    """显示帮助信息"""
    print("\n可用命令:")
    print("  /help - 显示此帮助信息")
    print("  /stats - 显示索引统计信息")
    print("  /search <关键词> - 搜索相关新闻")
    print("  /search <关键词> -n <数量> - 指定搜索结果数量")
    print("  /search <关键词> -sort date|relevance - 按日期或相关度排序")
    print("  /reindex - 重新索引RSS文件")
    print("  /clear - 清空索引")
    print("  /exit, /quit - 退出程序")
    print("  其他任何输入将被视为查询问题")

def parse_search_args(query_string):
    """解析搜索参数"""
    parts = query_string.split()
    search_args = {
        'query': '',
        'top_k': 5,
        'sort': 'relevance'  # 默认按相关度排序
    }
    
    i = 0
    while i < len(parts):
        if parts[i] == '-n' and i + 1 < len(parts):
            try:
                search_args['top_k'] = int(parts[i+1])
                i += 2
            except ValueError:
                # 如果不是有效的数字，将其视为查询的一部分
                search_args['query'] += f" {parts[i]} {parts[i+1]}"
                i += 2
        elif parts[i] == '-sort' and i + 1 < len(parts):
            sort_value = parts[i+1].lower()
            if sort_value in ['date', 'relevance']:
                search_args['sort'] = sort_value
                i += 2
            else:
                search_args['query'] += f" {parts[i]} {parts[i+1]}"
                i += 2
        else:
            search_args['query'] += f" {parts[i]}"
            i += 1
    
    # 清理查询字符串
    search_args['query'] = search_args['query'].strip()
    
    return search_args

# 用于解析日期字符串的辅助函数
def parse_date(date_str):
    """尝试解析日期字符串，返回时间戳或None"""
    from datetime import datetime
    import re
    
    # 如果是空字符串，返回None
    if not date_str:
        return None
        
    # 尝试各种常见日期格式
    formats = [
        '%Y-%m-%d',          # 2023-01-01
        '%Y/%m/%d',          # 2023/01/01
        '%Y年%m月%d日',      # 2023年01月01日
        '%Y-%m-%d %H:%M:%S', # 2023-01-01 12:30:45
        '%Y/%m/%d %H:%M:%S', # 2023/01/01 12:30:45
        '%a, %d %b %Y %H:%M:%S', # Wed, 01 Jan 2023 12:30:45
        '%d %b %Y',          # 01 Jan 2023
    ]
    
    # 首先尝试标准格式
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).timestamp()
        except ValueError:
            continue
    
    # 使用正则表达式尝试提取日期部分
    date_match = re.search(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}', date_str)
    if date_match:
        date_part = date_match.group(0)
        # 替换中文字符
        date_part = date_part.replace('年', '-').replace('月', '-').replace('日', '')
        # 替换斜杠
        date_part = date_part.replace('/', '-')
        
        try:
            return datetime.strptime(date_part, '%Y-%m-%d').timestamp()
        except ValueError:
            pass
            
    return None

async def clear_index():
    """清空索引"""
    if vector_store and hasattr(vector_store, 'clear'):
        confirm = input("确定要清空索引吗？此操作不可恢复 (y/n): ")
        if confirm.lower() in ['y', 'yes', '是']:
            vector_store.clear()
            print("索引已清空")
            return True
        else:
            print("已取消清空操作")
            return False
    else:
        print("无法清空索引")
        return False

async def run_index():
    """索引RSS文件"""
    rss_dir = os.getenv("RSS_DIR", "data/rss")
    
    print(f"开始索引RSS文件: {rss_dir}")
    parser = RSSParser(rss_directory=rss_dir)
    articles = parser.parse_all_files()
    
    print(f"找到 {len(articles)} 篇文章需要索引。")
    
    if len(articles) == 0:
        print(f"警告: 在 {rss_dir} 中没有找到RSS文件。请确保正确路径并且包含有效的RSS文件。")
        return
    
    # 统计文本长度
    MAX_LENGTH = 8192  # DashScope API 最大长度限制
    contents_lengths = [len(article.content) for article in articles]
    avg_length = sum(contents_lengths) / len(contents_lengths) if contents_lengths else 0
    max_length = max(contents_lengths) if contents_lengths else 0
    over_limit_count = sum(1 for length in contents_lengths if length > MAX_LENGTH)
    
    print(f"文章内容统计:")
    print(f"  平均长度: {avg_length:.0f} 字符")
    print(f"  最大长度: {max_length} 字符")
    print(f"  超过限制({MAX_LENGTH}字符)的文章数: {over_limit_count}/{len(articles)}")
    
    if over_limit_count > 0:
        print(f"注意: {over_limit_count} 篇文章超过了DashScope API的长度限制，这些文章将被自动截断")
    
    # 获取文章内容的向量嵌入
    texts = [article.content for article in articles]  # 使用对象属性
    print(f"正在为 {len(texts)} 篇文章生成向量嵌入（分批处理中）...")
    embeddings = await get_embeddings(texts)
    
    if embeddings is None:
        print("错误: 获取向量嵌入失败")
        return
    
    print(f"成功获取 {len(embeddings)} 个向量嵌入，正在添加到索引...")
    # 将文章和嵌入添加到向量存储
    await add_articles_to_vector_store(articles, embeddings)
    print(f"成功索引了 {len(articles)} 篇文章并保存到 {FAISS_INDEX_PATH}")

# 辅助函数，用于异步添加文章
async def add_articles_to_vector_store(articles, embeddings):
    """异步添加文章到向量存储"""
    # 这里我们直接调用vector_store.add_articles
    # 由于它是同步方法，不需要await
    vector_store.add_articles(articles, embeddings)

async def search_news(query: str, top_k: int = 5, sort_by: str = 'relevance'):
    """搜索相关新闻，只显示结果而不生成AI回答"""
    print(f"正在搜索: '{query}'... (最多显示{top_k}条结果，排序方式: {sort_by})")
    
    # 从检索器获取上下文
    try:
        results = await rag_retriever.get_context_for_query(query, top_k=top_k)
        
        if not results or len(results) == 0:
            print("没有找到相关新闻。")
            return
            
        # 根据排序方式对结果排序
        if sort_by == 'date':
            # 解析日期，按日期从新到旧排序（无法解析的日期放在最后）
            def get_date_key(item):
                date_ts = parse_date(item.get('pub_date', ''))
                return date_ts if date_ts is not None else 0
                
            results = sorted(results, key=get_date_key, reverse=True)
        # 相关度排序是默认的，不需要额外处理
        
        print(f"\n找到 {len(results)} 条相关新闻:")
        print("-" * 80)
        
        for i, item in enumerate(results, 1):
            title = item.get("title", "无标题")
            pub_date = item.get("pub_date", "未知日期")
            link = item.get("link", "")
            content = item.get("content", "")
            score = item.get("score", 0.0)
            
            # 计算相似度百分比
            similarity = 100 - min(100, max(0, score * 100))
            
            # 截取内容预览（最多200字符）
            preview = content[:200] + "..." if len(content) > 200 else content
            
            print(f"[{i}] {title} ({pub_date})")
            print(f"    相关度: {similarity:.1f}%")
            print(f"    预览: {preview}")
            if link:
                print(f"    链接: {link}")
            print()
        
        print("-" * 80)
        
        # 提供阅读全文选项
        while True:
            choice = input("输入编号查看全文 (例如: 1)，或输入'q'返回: ")
            if choice.lower() in ['q', 'quit', 'exit', '返回']:
                break
                
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    article = results[idx]
                    print("\n" + "=" * 80)
                    print(f"标题: {article.get('title', '无标题')}")
                    print(f"日期: {article.get('pub_date', '未知日期')}")
                    if article.get('link'):
                        print(f"链接: {article.get('link')}")
                    print("-" * 80)
                    print(article.get('content', '无内容'))
                    print("=" * 80)
                else:
                    print("无效的编号，请重新输入")
            except ValueError:
                print("请输入有效的编号或'q'退出")
                
    except Exception as e:
        print(f"搜索时出错: {str(e)}")

async def run_chat():
    """聊天模式"""
    print("欢迎使用新闻聊天助手！输入问题进行交流，输入 /help 查看可用命令。")
    
    while True:
        query = input("\n请输入您的问题: ")
        
        # 处理特殊命令
        if query.lower() in ['/exit', '/quit', '退出']:
            print("感谢使用，再见！")
            break
        elif query.lower() == '/help':
            show_help()
            continue
        elif query.lower() == '/stats':
            show_index_stats()
            continue
        elif query.lower() == '/reindex':
            await run_index()
            continue
        elif query.lower() == '/clear':
            await clear_index()
            continue
        elif query.lower().startswith('/search'):
            # 提取搜索关键词和参数
            search_input = query[7:].strip()
            if not search_input:
                print("请提供搜索关键词，例如: /search 气候变化")
                continue
            
            # 解析搜索参数
            search_args = parse_search_args(search_input)
            
            if not search_args['query']:
                print("请提供有效的搜索关键词")
                continue
                
            await search_news(
                search_args['query'], 
                top_k=search_args['top_k'],
                sort_by=search_args['sort']
            )
            continue
        
        # 从检索器获取上下文 - 使用await
        print("正在搜索相关新闻...")
        context = await rag_retriever.get_context_for_query(query, top_k=5)
        
        if not context:
            print("没有找到相关新闻，请尝试其他问题或先索引一些RSS新闻。")
            continue
        
        # 定义流式输出处理函数
        print("\nAI助手回答:")
        print("-" * 80)
        
        # 使用sys.stdout实现逐字输出效果
        import sys
        
        def stream_output_handler(text_chunk):
            """处理流式输出的文本块"""
            sys.stdout.write(text_chunk)
            sys.stdout.flush()  # 立即刷新输出
            
        # 使用LLM生成响应 (流式输出)
        print("", end="", flush=True)  # 确保光标位置正确
        response = await generate_rag_response(query, context, stream_handler=stream_output_handler)
        
        # 输出已完成
        print("\n" + "-" * 80)
        
        if "error" in response:
            print(f"错误: {response['error']}")

async def main():
    """主函数"""
    print("RSS新闻聊天系统 (使用DashScope LLM)")
    print("-" * 50)
    
    # 检查RSS文件夹
    rss_dir = os.getenv("RSS_DIR", "data/rss")
    os.makedirs(rss_dir, exist_ok=True)
    
    # 检查索引是否存在
    if check_index_exists():
        print(f"发现已存在的FAISS索引文件: {FAISS_INDEX_PATH}")
        print("已自动加载索引，可以开始聊天。")
        show_index_stats()
    else:
        print("未找到FAISS索引文件，需要先索引RSS文件。")
        index_files = input("是否现在开始索引RSS文件？(y/n): ")
        if index_files.lower() in ['y', 'yes', '是']:
            await run_index()
        else:
            print("警告: 没有索引文件，聊天功能可能无法正常工作。")
    
    # 运行聊天模式
    await run_chat()

if __name__ == "__main__":
    asyncio.run(main()) 