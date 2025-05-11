import os
import logging
import time
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError, APITimeoutError, APIError
from openai.types.chat import ChatCompletion
from openai.types import Embedding

logger = logging.getLogger(__name__)

class LLMService:
    """
    General Language Model Service Client (based on OpenAI-compatible interface)
    Only handles API interactions, does not include task-specific logic (like prompts or parsing)
    Supports different models for paper analysis and conversation
    """
    
    def __init__(self):
        """Initialize LLM service"""
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.api_url = os.getenv("LLM_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        
        # Conversation model (for user interaction)
        # DashScope支持的模型名称应为"qwen-turbo"或"qwen-plus"
        self.conversation_model = os.getenv("LLM_CONVERSATION_MODEL", "qwen-turbo") 
        # Embedding model
        self.default_embedding_model = os.getenv("LLM_EMBEDDING_MODEL", "text-embedding-v1") 
        self.default_embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
        
        # Default parameters
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4000")) 
        self.conversation_temperature = float(os.getenv("LLM_CONVERSATION_TEMPERATURE", "0.8"))
        self.request_timeout = int(os.getenv("LLM_REQUEST_TIMEOUT", "120"))  # 增加到120秒
        self.retry_delay = int(os.getenv("LLM_RETRY_DELAY", "5")) 
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))  # 增加最大重试次数
        
        if not self.api_key:
            logger.warning("DASHSCOPE API key not set, LLM and Embedding calls will not be available")
            self.client = None
        else:
            try:
                self.client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.api_url,
                    timeout=self.request_timeout, 
                    max_retries=self.max_retries  # 使用配置的重试次数
                )
                logger.info(f"LLMService initialized. Conversation model: {self.conversation_model}, Embedding model: {self.default_embedding_model} at {self.api_url}")
            except Exception as e:
                logger.error(f"Failed to initialize AsyncOpenAI client: {e}")
                self.client = None
    
    async def get_conversation_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = True,
        stream_handler: Optional[callable] = None
    ) -> Optional[ChatCompletion]:
        """
        Call chat model API specifically for conversation purposes.
        By default uses the conversation model (qwen-turbo).
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            stream: 是否使用流式模式
            stream_handler: 流式输出处理函数，接收每个文本块作为参数
        """
        if not self.client:
            logger.error("LLM client not initialized, cannot call API")
            return None
        
        # Use provided parameters or fall back to defaults
        use_temperature = temperature if temperature is not None else self.conversation_temperature
        use_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        try:
            logger.debug(f"Sending conversation request to LLM. Model: {self.conversation_model}, Temp: {use_temperature}, MaxTokens: {use_max_tokens}, Stream: {stream}")
            start_time = time.time()
            
            # Always use stream mode for qwen model as required by the API
            stream_response = await self.client.chat.completions.create(
                model=self.conversation_model,
                messages=messages,
                temperature=use_temperature,
                max_tokens=use_max_tokens,
                stream=True  # 强制使用流式模式
            )
            
            # 如果提供了处理函数，则直接处理流式输出
            if stream_handler and callable(stream_handler):
                # 收集流式响应的所有块，合并为完整的响应
                full_content = ""
                async for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        content_piece = chunk.choices[0].delta.content
                        full_content += content_piece
                        # 调用处理函数处理每个文本块
                        stream_handler(content_piece)
            else:
                # 没有处理函数，收集完整响应
                full_content = ""
                async for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        full_content += chunk.choices[0].delta.content
            
            # 构造类似非流式响应的结构
            duration = time.time() - start_time
            logger.debug(f"Received complete conversation response from stream. Duration: {duration:.2f} seconds.")
            
            # 创建一个模拟的完整响应
            from openai.types.chat.chat_completion import ChatCompletion, Choice, ChatCompletionMessage
            from openai.types.completion_usage import CompletionUsage
            
            # 创建一个模拟的响应对象
            completion = ChatCompletion(
                id="stream-response",
                choices=[
                    Choice(
                        finish_reason="stop",
                        index=0,
                        message=ChatCompletionMessage(
                            content=full_content,
                            role="assistant"
                        )
                    )
                ],
                created=int(time.time()),
                model=self.conversation_model,
                object="chat.completion",
                usage=CompletionUsage(
                    completion_tokens=-1,
                    prompt_tokens=-1,
                    total_tokens=-1
                )
            )
            
            return completion
            
        except RateLimitError as e:
            logger.error(f"LLM API rate limit exceeded: {e}")
            raise Exception(f"API速率限制：{str(e)}")
        except APITimeoutError as e:
            logger.error(f"LLM API timeout: {e}")
            raise Exception(f"API超时：{str(e)}")
        except APIConnectionError as e:
            logger.error(f"LLM API connection error: {e}")
            raise Exception(f"API连接错误：{str(e)}")
        except APIError as e:
            logger.error(f"LLM API error: {e}")
            
            # 尝试从错误消息提取更详细信息
            error_msg = str(e)
            if "data_inspection_failed" in error_msg or "inappropriate content" in error_msg:
                raise Exception("内容检查失败：您的查询可能包含敏感内容，无法处理。请修改问题后重试")
            
            # 对于其他API错误
            error_detail = ""
            if hasattr(e, 'response') and e.response and hasattr(e.response, 'json'):
                try:
                    error_json = e.response.json()
                    if 'error' in error_json and 'message' in error_json['error']:
                        error_detail = error_json['error']['message']
                except:
                    pass
                
            if error_detail:
                raise Exception(f"API错误：{error_detail}")
            else:
                raise Exception(f"API错误：{str(e)}")
        except Exception as e:
            logger.error(f"Unknown error in LLM API: {e.__class__.__name__} - {e}")
            raise Exception(f"调用LLM API时出错: {str(e)}")

    async def get_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        encoding_format: str = "float"
    ) -> Optional[List[List[float]]]:
        """
        Call embedding model API to get vector embeddings for texts.
        """
        if not self.client:
            logger.error("LLM client not initialized, cannot get embeddings")
            return None
        
        if not texts: # Handle empty input list
            return []
             
        use_model = model if model is not None else self.default_embedding_model
        use_dimensions = dimensions if dimensions is not None else self.default_embedding_dimensions 
        
        # 实现自定义重试机制
        max_retries = self.max_retries
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # 检查文本长度
                for i, text in enumerate(texts):
                    if len(text) > 8192:
                        logger.warning(f"文本 #{i} 长度为 {len(text)} 字符，超过DashScope API的8192字符限制")
                
                if retry_count > 0:
                    logger.info(f"尝试获取嵌入 (重试 {retry_count}/{max_retries})...")
                else:
                    logger.debug(f"Sending embedding request to LLM. Model: {use_model}, Target Dimensions: {use_dimensions}, Num Texts: {len(texts)}")
                
                start_time = time.time()
                
                response = await self.client.embeddings.create(
                    model=use_model,
                    input=texts,
                    encoding_format=encoding_format
                )
                
                duration = time.time() - start_time
                logger.debug(f"Received LLM embedding response. Duration: {duration:.2f} seconds. Usage: {response.usage}")
                
                # Extract embeddings
                if response.data:
                    sorted_embeddings = sorted(response.data, key=lambda e: e.index)
                    return [item.embedding for item in sorted_embeddings]
                else:
                    logger.warning(f"LLM embedding response did not contain data for model {use_model}")
                    return None

            except (RateLimitError, APITimeoutError, APIConnectionError) as e:
                retry_count += 1
                last_error = e
                
                error_type = type(e).__name__
                logger.warning(f"可恢复的错误：{error_type} - {str(e)}，重试 {retry_count}/{max_retries}")
                
                if retry_count <= max_retries:
                    # 指数退避重试
                    wait_time = self.retry_delay * (2 ** (retry_count - 1))
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"达到最大重试次数 ({max_retries})，放弃获取嵌入")
                    
                    # 记录详细错误信息
                    if isinstance(e, RateLimitError):
                        logger.error(f"Embedding API rate limit exceeded: {e}")
                    elif isinstance(e, APITimeoutError):
                        logger.error(f"Embedding API timeout: {e}")
                    elif isinstance(e, APIConnectionError):
                        logger.error(f"Embedding API connection error: {e}")
                    
                    return None
                    
            except APIError as e:
                logger.error(f"Embedding API error: {e}")
                
                # 尝试提取更详细的错误信息
                error_detail = str(e)
                if "'message'" in error_detail:
                    try:
                        import json
                        error_dict = json.loads(error_detail.split(" - ", 1)[1])
                        error_message = error_dict.get('error', {}).get('message', '')
                        logger.error(f"Embedding API 详细错误: {error_message}")
                    except Exception:
                        pass
                
                return None
                
            except Exception as e: 
                logger.error(f"Unknown error occurred when calling LLM API (Embeddings): {e.__class__.__name__} - {e}")
                return None
        
        # 如果所有重试都失败
        return None

# Create global LLM service instance
llm_service = LLMService() 