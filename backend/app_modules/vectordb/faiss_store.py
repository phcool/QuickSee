import os
import pickle
import json
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
import time

# 尝试不同方式导入FAISS
try:
    import faiss
except ImportError:
    try:
        # 尝试通过faiss-cpu导入
        import faiss_cpu as faiss
    except ImportError:
        # 如果仍然失败，设置为None并在后续检查
        faiss = None
        logging.getLogger(__name__).error("无法导入FAISS库。请确保已安装: pip install faiss-cpu 或 conda install -c conda-forge faiss-cpu")

from backend.app_modules.config import FAISS_INDEX_PATH, EMBEDDING_DIMENSION
from backend.app_modules.parsers.rss_parser import NewsArticle
# Use the integration layer instead of directly using the embedding service
from backend.app_modules.llm.llm_integration import get_embeddings

logger = logging.getLogger(__name__)

class FAISSVectorStore:
    """FAISS-based vector store for embeddings."""
    
    def __init__(
        self,
        index_path: str = FAISS_INDEX_PATH,
        dimension: int = EMBEDDING_DIMENSION
    ):
        # 检查FAISS是否可用
        if faiss is None:
            logger.error("FAISS库未安装，无法创建索引")
            self.index = None
            return
            
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.document_store = {}
        self.metadata_store = {}
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        # Initialize or load existing index
        success = self._initialize_index()
        if success:
            logger.info(f"FAISS索引初始化完成，共加载了 {len(self.document_store)} 篇文章")
        else:
            logger.info(f"创建了新的FAISS索引，维度: {dimension}")
    
    def _initialize_index(self) -> bool:
        """Initialize FAISS index or load existing one. Returns True if loaded existing index."""
        index_file = f"{self.index_path}.index"
        metadata_file = f"{self.index_path}.meta"
        
        if os.path.exists(index_file) and os.path.exists(metadata_file):
            try:
                # Load existing index and metadata
                logger.info(f"正在加载现有索引: {index_file}")
                self.index = faiss.read_index(index_file)
                
                with open(metadata_file, 'rb') as f:
                    stored_data = pickle.load(f)
                    self.document_store = stored_data.get('document_store', {})
                    self.metadata_store = stored_data.get('metadata_store', {})
                
                logger.info(f"成功加载索引，包含 {len(self.document_store)} 篇文章")
                return True
            except Exception as e:
                logger.error(f"加载索引失败: {e}，将创建新索引")
                # 如果加载失败，创建新索引
                self.index = faiss.IndexFlatL2(self.dimension)
                self.document_store = {}
                self.metadata_store = {}
                return False
        else:
            # Create new index
            logger.info(f"索引文件不存在，创建新索引: {index_file}")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.document_store = {}
            self.metadata_store = {}
            return False
    
    def _save_index(self) -> bool:
        """Save FAISS index and metadata to disk. Returns True if successful."""
        index_file = f"{self.index_path}.index"
        metadata_file = f"{self.index_path}.meta"
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            
            # 更新元数据中的时间戳
            current_time = int(time.time())
            if 'system' not in self.metadata_store:
                self.metadata_store['system'] = {}
            self.metadata_store['system']['last_updated'] = current_time
            
            # Save FAISS index
            logger.info(f"保存FAISS索引到: {index_file}")
            faiss.write_index(self.index, index_file)
            
            # Save metadata
            with open(metadata_file, 'wb') as f:
                pickle.dump({
                    'document_store': self.document_store,
                    'metadata_store': self.metadata_store
                }, f)
            
            logger.info(f"成功保存索引和元数据，包含 {len(self.document_store)} 篇文章")
            return True
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
            return False
    
    def add_articles(self, articles: List[NewsArticle], embeddings: Optional[List[List[float]]] = None) -> None:
        """Add articles to the vector store."""
        if not articles:
            logger.warning("没有提供文章进行索引")
            return
            
        if self.index is None:
            logger.error("FAISS索引未初始化，无法添加文章")
            return
            
        # Create mapping of document IDs to texts
        texts_with_ids = {}
        start_id = len(self.document_store)
        
        for i, article in enumerate(articles):
            # Generate a unique ID for each article
            doc_id = f"article_{start_id + i}"
            
            # Store full article text
            texts_with_ids[doc_id] = article.content
            
            # Store article metadata
            self.metadata_store[doc_id] = {
                "title": article.title,
                "link": article.link,
                "pub_date": article.pub_date,
                "source_file": article.source_file
            }
        
        # Store document texts
        for doc_id, text in texts_with_ids.items():
            self.document_store[doc_id] = text
            
        # 如果提供了嵌入，直接使用
        if embeddings is not None:
            # 确保嵌入数量匹配文章数量
            if len(embeddings) != len(articles):
                logger.error(f"嵌入数量({len(embeddings)})与文章数量({len(articles)})不匹配")
                return
                
            # 添加到FAISS索引
            logger.info(f"将 {len(embeddings)} 个嵌入添加到FAISS索引...")
            embeddings_np = np.array(embeddings).astype('float32')
            self.index.add(embeddings_np)
            
            # 保存索引和元数据
            save_success = self._save_index()
            if save_success:
                logger.info(f"成功添加并保存 {len(articles)} 篇文章到索引")
            else:
                logger.error("添加文章成功，但保存索引失败")
        else:
            # 如果没有提供嵌入，记录错误
            # 现在我们不再在这里异步计算嵌入，应该由调用方提供
            logger.error("未提供嵌入向量，无法添加文章到索引")
    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for most similar documents to the query embedding."""
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS索引为空或未初始化，无法执行搜索")
            return []
        
        # Convert to numpy array
        query_embedding_np = np.array([query_embedding]).astype('float32')
        
        # Search in FAISS index
        distances, indices = self.index.search(query_embedding_np, min(top_k, self.index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
                
            # Get document ID based on index
            doc_id = list(self.document_store.keys())[idx]
            
            # Get document text and metadata
            text = self.document_store.get(doc_id, "")
            metadata = self.metadata_store.get(doc_id, {})
            
            results.append({
                "content": text,
                "title": metadata.get("title", "Untitled"),
                "link": metadata.get("link", ""),
                "pub_date": metadata.get("pub_date", ""),
                "source_file": metadata.get("source_file", ""),
                "score": float(distances[0][i])
            })
        
        return results
    
    def clear(self) -> None:
        """Clear the vector store."""
        logger.info("清空FAISS索引和文档存储")
        self.index = faiss.IndexFlatL2(self.dimension)
        self.document_store = {}
        self.metadata_store = {}
        self._save_index()
        
    def get_stats(self) -> Dict[str, Any]:
        """获取向量存储的统计信息"""
        last_updated = None
        if 'system' in self.metadata_store and 'last_updated' in self.metadata_store['system']:
            last_updated = self.metadata_store['system']['last_updated']
        
        return {
            "total_documents": len(self.document_store),
            "total_vectors": self.index.ntotal if self.index is not None else 0,
            "index_path": self.index_path,
            "dimension": self.dimension,
            "last_updated": last_updated
        }


# Create a singleton instance
try:
    vector_store = FAISSVectorStore()
except ImportError as e:
    logging.getLogger(__name__).error(f"无法初始化FAISS向量存储: {e}")
    vector_store = None