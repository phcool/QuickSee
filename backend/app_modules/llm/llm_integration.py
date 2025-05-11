import logging
from typing import List, Dict, Any, Optional
from backend.app_modules.llm.llm import llm_service
import hashlib
import pickle
import os
import time

logger = logging.getLogger(__name__)

# DashScope API 文本长度限制
MAX_TEXT_LENGTH = 8192

# 嵌入向量缓存
EMBEDDING_CACHE = {}
CACHE_MAX_ITEMS = 1000
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "embedding_cache.pkl")

# 尝试加载缓存
try:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            EMBEDDING_CACHE = pickle.load(f)
            logger.info(f"已加载嵌入缓存，包含 {len(EMBEDDING_CACHE)} 条记录")
except Exception as e:
    logger.warning(f"加载嵌入缓存失败: {str(e)}")
    EMBEDDING_CACHE = {}

def save_cache():
    """保存嵌入缓存到磁盘"""
    try:
        # 限制缓存大小
        if len(EMBEDDING_CACHE) > CACHE_MAX_ITEMS:
            # 移除最老的项目直到在限制内
            items = sorted(EMBEDDING_CACHE.items(), key=lambda x: x[1]['timestamp'])
            EMBEDDING_CACHE.clear()
            for k, v in items[-CACHE_MAX_ITEMS:]:
                EMBEDDING_CACHE[k] = v
        
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(EMBEDDING_CACHE, f)
            logger.info(f"嵌入缓存已保存，包含 {len(EMBEDDING_CACHE)} 条记录")
    except Exception as e:
        logger.warning(f"保存嵌入缓存失败: {str(e)}")

def truncate_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """截断文本到指定长度"""
    if len(text) <= max_length:
        return text
    return text[:max_length]

def get_text_hash(text: str) -> str:
    """获取文本的唯一哈希值"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

async def get_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    """
    获取文本的向量嵌入，批量处理每次最多10个文本
    使用缓存减少重复调用
    """
    if not texts:
        return []
        
    try:
        # 截断超长文本
        truncated_texts = [truncate_text(text) for text in texts]
        
        # 记录截断情况
        for i, (original, truncated) in enumerate(zip(texts, truncated_texts)):
            if len(original) > MAX_TEXT_LENGTH:
                logger.warning(f"文本 #{i} 已从 {len(original)} 字符截断至 {len(truncated)} 字符")
        
        # 检查缓存
        all_embeddings = []
        texts_to_embed = []
        text_indices = []
        
        for i, text in enumerate(truncated_texts):
            text_hash = get_text_hash(text)
            if text_hash in EMBEDDING_CACHE:
                # 缓存命中
                all_embeddings.append(EMBEDDING_CACHE[text_hash]['embedding'])
                logger.debug(f"缓存命中: 文本 #{i}")
            else:
                # 缓存未命中，需要重新嵌入
                texts_to_embed.append(text)
                text_indices.append((i, text_hash))
        
        # 如果所有文本都在缓存中
        if not texts_to_embed:
            logger.info(f"所有 {len(truncated_texts)} 文本都使用了缓存")
            return all_embeddings
        
        # 对未缓存的文本进行嵌入
        logger.info(f"需要嵌入 {len(texts_to_embed)}/{len(truncated_texts)} 个文本")
        
        # DashScope API限制每批最多10个文本
        BATCH_SIZE = 10
        
        # 分批处理未缓存文本
        for i in range(0, len(texts_to_embed), BATCH_SIZE):
            batch = texts_to_embed[i:i+BATCH_SIZE]
            batch_indices = text_indices[i:i+BATCH_SIZE]
            
            logger.info(f"处理嵌入批次 {i//BATCH_SIZE + 1}/{(len(texts_to_embed)-1)//BATCH_SIZE + 1}, 大小: {len(batch)}")
            
            batch_embeddings = await llm_service.get_embeddings(batch)
            
            if batch_embeddings is None:
                logger.error(f"批次 {i//BATCH_SIZE + 1} 获取向量嵌入失败")
                return None
            
            # 将新嵌入添加到结果和缓存
            for (original_index, text_hash), embedding in zip(batch_indices, batch_embeddings):
                # 更新缓存
                EMBEDDING_CACHE[text_hash] = {
                    'embedding': embedding,
                    'timestamp': time.time()
                }
                
                # 将嵌入插入到原始索引位置
                while len(all_embeddings) <= original_index:
                    all_embeddings.append(None)
                all_embeddings[original_index] = embedding
        
        # 保存更新后的缓存
        save_cache()
            
        # 检查是否有None值（未成功嵌入）
        if None in all_embeddings:
            logger.error("嵌入过程中出现错误，有未处理的文本")
            return None
            
        return all_embeddings
    except Exception as e:
        logger.error(f"使用DashScope获取向量嵌入出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def generate_rag_response(
    query: str, 
    context: List[Dict[str, Any]], 
    stream_handler: Optional[callable] = None
) -> Dict[str, Any]:
    """
    使用RAG生成回答
    
    Args:
        query: 用户查询
        context: 相关上下文
        stream_handler: 可选的流式输出处理函数，接收文本块作为参数
        
    Returns:
        包含生成文本和上下文的字典
    """
    try:
        # 构建提示
        prompt = f"""上下文是最近的一些新闻，请基于这些新闻回答问题

上下文:
{format_context(context)}

问题: {query}

回答:"""

        # 调用LLM生成回答
        messages = [{"role": "user", "content": prompt}]
        
        # 如果没有提供流处理函数，创建一个默认的收集器
        collected_text = []
        
        # 默认流处理函数
        def default_stream_handler(text_chunk):
            collected_text.append(text_chunk)
            return text_chunk
        
        # 使用提供的处理函数或默认函数
        handler_to_use = stream_handler if stream_handler and callable(stream_handler) else default_stream_handler
        
        # 始终使用流式模式
        response = await llm_service.get_conversation_completion(
            messages=messages,
            stream_handler=handler_to_use
        )
        
        if response is None:
            return {"error": "生成响应失败，可能是API调用出错"}
        
        # 如果使用默认处理器，合并收集到的文本
        full_text = response.choices[0].message.content
        if handler_to_use == default_stream_handler and collected_text:
            # 双重保险：优先使用收集到的文本，因为它可能更完整
            full_text = "".join(collected_text)
            
        return {
            "text": full_text,
            "context": context
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"使用LLM生成RAG响应出错: {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 检查是否是内容安全过滤错误
        if "data_inspection_failed" in error_msg or "inappropriate content" in error_msg:
            return {"error": "内容检查失败：您的查询可能包含敏感内容，请修改问题后重试。"}
        
        return {"error": f"生成响应时出错: {error_msg}"}

def format_context(context: List[Dict[str, Any]]) -> str:
    """
    格式化上下文为文本
    """
    formatted = []
    for i, item in enumerate(context, 1):
        title = item.get("title", "无标题")
        content = item.get("content", "")
        pub_date = item.get("pub_date", "")
        
        entry = f"[{i}] {title}"
        if pub_date:
            entry += f" ({pub_date})"
        entry += f"\n{content}\n"
        
        formatted.append(entry)
    
    return "\n".join(formatted)