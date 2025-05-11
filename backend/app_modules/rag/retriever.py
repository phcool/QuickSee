from typing import List, Dict, Any, Optional
import asyncio
import logging
from backend.app_modules.vectordb.faiss_store import vector_store
from backend.app_modules.llm.llm_integration import get_embeddings
from backend.app_modules.utils.helpers import chunk_text

logger = logging.getLogger(__name__)

class RAGRetriever:
    """Retrieval-Augmented Generation retriever component."""
    
    def __init__(self, vector_store_instance=vector_store):
        self.vector_store = vector_store_instance
    
    async def retrieve(self, query: str, top_k: int = 5, max_retries: int = 2) -> List[Dict[str, Any]]:
        """获取查询的相关上下文
        
        Args:
            query: 用户查询
            top_k: 返回的结果数量
            max_retries: 最大重试次数
            
        Returns:
            相关文章列表
        """
        retry_count = 0
        while retry_count <= max_retries:
            try:
                # 获取查询的向量嵌入
                logger.info(f"为查询生成向量嵌入: '{query}'")
                query_embedding = await get_embeddings([query])
                
                if not query_embedding or not query_embedding[0]:
                    logger.error("无法获取查询的向量嵌入")
                    return []
                    
                # 搜索相似文章
                logger.info(f"使用FAISS搜索相关文章 (top_k={top_k})")
                results = self.vector_store.search(query_embedding[0], top_k=top_k)
                logger.info(f"找到 {len(results)} 篇相关文章")
                return results
                
            except Exception as e:
                retry_count += 1
                logger.error(f"检索上下文时出错: {str(e)}")
                
                if retry_count <= max_retries:
                    # 指数退避重试
                    wait_time = 2 ** (retry_count - 1)
                    logger.info(f"等待 {wait_time} 秒后重试获取上下文... (尝试 {retry_count}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"达到最大重试次数 ({max_retries})，放弃获取上下文")
                    break
        
        # 如果所有重试都失败，返回空列表            
        return []
    
    def format_retrieved_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context for the LLM."""
        context_parts = []
        
        for i, doc in enumerate(retrieved_docs):
            title = doc.get("title", "Untitled")
            date = doc.get("pub_date", "")
            
            context_part = f"Document {i+1}:\n"
            context_part += f"Title: {title}\n"
            if date:
                context_part += f"Date: {date}\n"
            context_part += f"Content: {doc.get('content', '')}\n"
            
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)
    
    async def get_context_for_query(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Get context for a query."""
        return await self.retrieve(query, top_k=top_k)


# Create a singleton instance
rag_retriever = RAGRetriever() 