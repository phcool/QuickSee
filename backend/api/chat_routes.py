"""
聊天API路由
处理与AI助手的对话功能
"""
import asyncio
from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
from backend.app_modules.rag.retriever import rag_retriever
from backend.app_modules.llm.llm_integration import generate_rag_response
from backend.app_modules.llm.llm import llm_service
from backend.app_modules.llm.llm_integration import format_context
import json
import traceback
import gc

# 创建蓝图
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/message', methods=['POST', 'GET'])
def chat_message():
    """
    发送消息到AI助手
    
    参数(JSON或URL查询参数):
        query: 用户的问题
        stream: 是否使用流式响应 (默认False)
    
    返回:
        AI助手的回复
    """
    # 获取参数 - 支持GET和POST请求
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供JSON数据'}), 400
        query = data.get('query')
        use_stream = data.get('stream', False)
    else:  # GET请求
        query = request.args.get('query')
        use_stream = request.args.get('stream', 'false').lower() == 'true'
    
    if not query:
        return jsonify({'error': '请提供查询参数 (query)'}), 400
        
    # 如果请求流式响应
    if use_stream:
        return Response(
            stream_with_context(stream_chat_response(query)),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
            }
        )
    
    # 否则使用常规响应(但内部也是流式处理)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 获取相关上下文
        context = loop.run_until_complete(rag_retriever.get_context_for_query(query, top_k=5))
        
        if not context:
            loop.close()
            return jsonify({
                'text': '我没有找到与您问题相关的新闻信息。请尝试其他问题或者索引更多新闻。',
                'context': [],
                'has_context': False
            })
        
        # 创建文本收集器
        collected_text = []
        
        # 定义收集处理函数
        def collect_text(text_chunk):
            collected_text.append(text_chunk)
            return text_chunk
        
        # 生成回答，使用流式处理但收集为完整文本
        response = loop.run_until_complete(generate_rag_response(query, context, stream_handler=collect_text))
        loop.close()
        
        # 检查是否有错误
        if 'error' in response:
            return jsonify({'error': response['error']}), 500
        
        # 格式化上下文信息（简化版，只包含标题和链接）
        context_info = []
        for item in context:
            context_info.append({
                'title': item.get('title', '无标题'),
                'link': item.get('link', ''),
                'date': item.get('pub_date', '未知日期')
            })
        
        # 优先使用收集到的完整文本，这样更可靠
        text_content = "".join(collected_text) if collected_text else response.get('text', '无法生成回答')
            
        return jsonify({
            'text': text_content,
            'context': context_info,
            'has_context': True
        })
        
    except Exception as e:
        current_app.logger.error(f"生成聊天回复时出错: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': f'生成回复失败: {str(e)}'}), 500

def stream_chat_response(query):
    """生成流式聊天响应"""
    # 每次请求创建一个独立的事件循环
    loop = None
    try:
        # 创建并设置事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 设置更长的超时时间
        loop.slow_callback_duration = 1.0  # 增加慢回调警告阈值
        
        # 获取上下文 - 运行异步函数
        context_future = asyncio.ensure_future(
            rag_retriever.get_context_for_query(query, top_k=5),
            loop=loop
        )
        
        try:
            context = loop.run_until_complete(context_future)
        except asyncio.TimeoutError:
            current_app.logger.error("获取查询上下文时超时")
            yield f"data: {json.dumps({'type': 'error', 'data': '服务器处理超时，请稍后再试或简化您的问题。', 'done': True})}\n\n"
            return
        except Exception as e:
            current_app.logger.error(f"获取查询上下文时出错: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'data': '获取相关信息时出错，请稍后再试。', 'done': True})}\n\n"
            return
        
        # 如果没有找到上下文
        if not context:
            error_msg = '我没有找到与您问题相关的新闻信息。请尝试其他问题或者索引更多新闻。'
            yield f"data: {json.dumps({'type': 'text', 'data': error_msg, 'done': True})}\n\n"
            return
        
        # 格式化上下文信息
        context_info = []
        for item in context:
            context_info.append({
                'title': item.get('title', '无标题'),
                'link': item.get('link', ''),
                'date': item.get('pub_date', '未知日期')
            })
        
        # 先发送上下文信息
        yield f"data: {json.dumps({'type': 'context', 'data': context_info})}\n\n"
        
        try:
            # 构建提示
            prompt = f"""/nothink 基于以下上下文回答问题。如果上下文中没有相关信息，请说明无法回答。

上下文:
{format_context(context)}

问题: {query}

回答:"""

            # 准备消息
            messages = [{"role": "user", "content": prompt}]
            
            # 创建流式响应
            stream_response = None
            try:
                # 使用run_until_complete，避免异步嵌套太深
                stream_response = loop.run_until_complete(
                    llm_service.client.chat.completions.create(
                        model=llm_service.conversation_model,
                        messages=messages,
                        temperature=llm_service.conversation_temperature,
                        max_tokens=llm_service.max_tokens,
                        stream=True
                    )
                )
                
                # 检查stream_response是否支持异步迭代
                if not hasattr(stream_response, '__aiter__'):
                    raise TypeError("返回的对象不是异步迭代器")
                
                # 定义异步迭代处理函数
                async def process_stream():
                    token_count = 0
                    try:
                        # 这里需要使用async for
                        async for chunk in stream_response:
                            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                token_count += 1
                                content_piece = chunk.choices[0].delta.content
                                # 产生token计数作为一个元组的一部分
                                yield (content_piece, token_count)
                    except Exception as e:
                        current_app.logger.error(f"异步迭代流时出错: {str(e)}")
                        # 确保迭代器结束
                        raise StopAsyncIteration
                    finally:
                        # 最后一次yield可以包含最终的计数
                        yield (None, token_count)
                
                # 执行异步生成器
                gen = process_stream()
                token_count = 0
                
                # 循环处理生成的内容
                while True:
                    try:
                        # 获取下一个内容片段
                        result = loop.run_until_complete(
                            anext_coro(gen)
                        )
                        
                        content_piece, current_count = result
                        token_count = current_count  # 更新token数
                        
                        # 发送给客户端
                        if content_piece:
                            event_data = json.dumps({'type': 'text', 'data': content_piece, 'done': False})
                            yield f"data: {event_data}\n\n"
                    
                    except StopAsyncIteration:
                        # 生成器结束
                        break
                    except asyncio.TimeoutError:
                        current_app.logger.error("流式生成响应时超时")
                        yield f"data: {json.dumps({'type': 'error', 'data': '生成回答时超时，请稍后重试或提问不同的问题。', 'done': True})}\n\n"
                        break
                    except Exception as e:
                        current_app.logger.error(f"处理流式响应时出错: {str(e)}")
                        current_app.logger.error(traceback.format_exc())
                        break
                
                # 检查是否生成了任何内容
                if token_count == 0:
                    yield f"data: {json.dumps({'type': 'text', 'data': '抱歉，我无法生成回答。请尝试其他问题。', 'done': True})}\n\n"
                else:
                    # 发送完成标志
                    yield f"data: {json.dumps({'type': 'text', 'data': '', 'done': True})}\n\n"
                    
            except TypeError as type_error:
                # 处理不是异步迭代器的情况
                current_app.logger.error(f"LLM返回了不支持异步迭代的对象: {type_error}")
                
                # 尝试获取完整回复作为备用方案
                try:
                    # 使用普通方式生成回复
                    current_app.logger.info("尝试使用非流式处理作为备用方案...")
                    backup_response = loop.run_until_complete(
                        generate_rag_response(query, context)
                    )
                    
                    if backup_response and 'text' in backup_response:
                        content = backup_response['text']
                        yield f"data: {json.dumps({'type': 'text', 'data': content, 'done': True})}\n\n"
                        return
                except Exception as backup_error:
                    current_app.logger.error(f"备用方案也失败了: {backup_error}")
                
                # 如果备用方案也失败，才显示错误
                yield f"data: {json.dumps({'type': 'error', 'data': '服务器内部错误：LLM响应格式不正确', 'done': True})}\n\n"
            except Exception as e:
                raise e  # 将其他错误传递给外部异常处理程序
            finally:
                # 确保流响应资源被释放
                if stream_response and hasattr(stream_response, 'close'):
                    try:
                        loop.run_until_complete(stream_response.close())
                    except Exception as close_error:
                        current_app.logger.error(f"关闭流响应时出错: {close_error}")
        
        except Exception as e:
            # 处理API调用中的异常
            error_msg = str(e)
            if 'data_inspection_failed' in error_msg or 'inappropriate content' in error_msg:
                error_display = '很抱歉，您的请求可能包含敏感内容，无法生成回答。请尝试修改您的问题。'
            else:
                error_display = '生成回答时出错，请稍后再试。'
            
            current_app.logger.error(f"LLM API错误: {error_msg}")
            yield f"data: {json.dumps({'type': 'error', 'data': error_display, 'done': True})}\n\n"
            
    except Exception as e:
        # 记录详细错误信息
        current_app.logger.error(f"生成流式聊天回复时出错: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        yield f"data: {json.dumps({'type': 'error', 'data': '服务器处理出错，请稍后再试。', 'done': True})}\n\n"
    
    finally:
        # 确保事件循环被关闭
        if loop:
            try:
                # 运行所有待处理的任务和回调
                pending = asyncio.all_tasks(loop) if hasattr(asyncio, 'all_tasks') else asyncio.Task.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # 确保所有任务处理完毕
                if pending:
                    try:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception as gather_error:
                        current_app.logger.error(f"取消待处理任务时出错: {gather_error}")
                # 关闭事件循环
                if not loop.is_closed():
                    loop.close()
            except Exception as loop_error:
                current_app.logger.error(f"关闭事件循环时出错: {loop_error}")
            # 确保事件循环被重置
            asyncio.set_event_loop(None)
        # 手动清理可能的循环引用
        gc.collect()

# 帮助函数来处理异步迭代器
async def anext_coro(ait):
    """用于获取异步迭代器的下一个元素，兼容Python 3.8+"""
    try:
        # 使用__anext__代替anext (适用于Python 3.8+)
        return await ait.__anext__()
    except StopAsyncIteration:
        raise 