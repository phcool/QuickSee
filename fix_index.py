#!/usr/bin/env python
"""
修复FAISS索引问题的脚本
- 清空现有索引
- 重新创建索引
- 确保索引位置正确
"""
import os
import logging
import shutil
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_index')

# 路径设置
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
FAISS_INDEX_DIR = os.path.join(DATA_DIR, "faiss_index")
RSS_DIR = os.path.join(DATA_DIR, "rss")

# 设置环境变量确保两个应用使用相同的路径
os.environ["FAISS_INDEX_PATH"] = FAISS_INDEX_DIR
os.environ["RSS_DIR"] = RSS_DIR

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RSS_DIR, exist_ok=True)

def clean_old_indexes():
    """清除所有旧的索引文件"""
    logger.info("正在清除旧的索引文件...")
    
    # 删除主索引文件
    for ext in [".index", ".meta"]:
        index_file = f"{FAISS_INDEX_DIR}{ext}"
        if os.path.exists(index_file):
            logger.info(f"删除: {index_file}")
            os.remove(index_file)
    
    # 如果存在，也删除backend/data/faiss_index目录
    backend_index_dir = os.path.join(ROOT_DIR, "backend", "data", "faiss_index")
    if os.path.exists(backend_index_dir):
        logger.info(f"删除目录: {backend_index_dir}")
        shutil.rmtree(backend_index_dir)
    
    logger.info("所有旧索引文件已清除")

async def create_new_index():
    """创建新的索引"""
    logger.info("开始创建新索引...")
    
    # 导入后端模块
    try:
        from backend.app_modules.parsers.rss_parser import RSSParser
        from backend.app_modules.llm.llm_integration import get_embeddings
        from backend.app_modules.vectordb.faiss_store import vector_store
        
        # 解析RSS文件
        parser = RSSParser(rss_directory=RSS_DIR)
        articles = parser.parse_all_files()
        
        if not articles or len(articles) == 0:
            logger.error(f"在 {RSS_DIR} 中没有找到RSS文件")
            return False
        
        logger.info(f"找到 {len(articles)} 篇文章需要索引")
        
        # 获取向量嵌入
        texts = [article.content for article in articles]
        logger.info(f"正在为 {len(texts)} 篇文章生成向量嵌入...")
        embeddings = await get_embeddings(texts)
        
        if embeddings is None or len(embeddings) == 0:
            logger.error("获取向量嵌入失败")
            return False
        
        logger.info(f"成功获取 {len(embeddings)} 个向量嵌入")
        
        # 添加到向量存储
        logger.info("正在添加文章到索引...")
        vector_store.add_articles(articles, embeddings)
        
        # 验证索引已正确创建
        stats = vector_store.get_stats()
        logger.info(f"索引统计信息:")
        logger.info(f"文档总数: {stats['total_documents']}")
        logger.info(f"向量总数: {stats['total_vectors']}")
        logger.info(f"索引路径: {stats['index_path']}")
        
        if stats['total_documents'] > 0:
            logger.info("索引创建成功!")
            return True
        else:
            logger.error("索引创建失败: 没有文档被索引")
            return False
        
    except Exception as e:
        logger.error(f"创建索引时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """主函数"""
    logger.info("=== 开始修复FAISS索引问题 ===")
    
    # 清理旧索引
    clean_old_indexes()
    
    # 创建新索引
    success = await create_new_index()
    
    if success:
        logger.info("=== 索引修复完成 ===")
        logger.info(f"新索引位置: {FAISS_INDEX_DIR}")
        logger.info("现在可以重启Web服务器应用")
    else:
        logger.error("=== 索引修复失败 ===")
        logger.error("请检查日志信息并解决问题")
    
    return success

if __name__ == "__main__":
    try:
        import faiss
    except ImportError:
        try:
            import faiss_cpu as faiss
        except ImportError:
            logger.error("FAISS库未安装。请安装后重试: pip install faiss-cpu")
            exit(1)
    
    asyncio.run(main()) 