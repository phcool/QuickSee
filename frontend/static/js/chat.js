/**
 * 聊天页面JS
 * 负责处理用户与AI的对话交互
 */

// 全局变量
let controller = null;  // 用于中断fetch请求

document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const chatForm = document.getElementById('chatForm');
    const userMessageInput = document.getElementById('userMessage');
    const chatContainer = document.getElementById('chatContainer');
    const clearChatBtn = document.getElementById('clearChatBtn');
    
    // 滚动到底部
    scrollToBottom();
    
    // 绑定提交事件
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // 获取用户输入
        const userMessage = userMessageInput.value.trim();
        if (!userMessage) return;
        
        // 清空输入框
        userMessageInput.value = '';
        
        // 添加用户消息到聊天界面
        appendUserMessage(userMessage);
        
        // 滚动到底部
        scrollToBottom();
        
        // 发送请求前，先中断之前的请求（如果有）
        if (controller) {
            controller.abort();
        }
        
        // 创建新的AbortController
        controller = new AbortController();
        
        try {
            // 显示AI正在思考的状态
            const thinkingIndicator = appendThinkingIndicator();
            
            // 使用流式输出
            await handleStreamingChat(userMessage, thinkingIndicator);
        } catch (error) {
            // 移除思考状态指示器
            const thinkingIndicator = document.querySelector('.thinking-indicator');
            if (thinkingIndicator) {
                thinkingIndicator.remove();
            }
            
            // 添加错误消息
            if (error.name !== 'AbortError') {
                appendAIMessage(`发生错误: ${error.message || '无法连接到服务器'}`);
                console.error('聊天出错:', error);
            }
        } finally {
            // 重置controller
            controller = null;
        }
    });
    
    // 绑定清空聊天按钮
    clearChatBtn.addEventListener('click', function() {
        clearChat();
    });
});

/**
 * 处理流式聊天请求
 * @param {string} message - 用户消息
 * @param {Element} thinkingIndicator - 思考状态指示器元素
 */
async function handleStreamingChat(message, thinkingIndicator) {
    // 声明变量，确保在finally块中可以访问
    let response = null;
    let reader = null;
    
    try {
        // 创建AI消息元素，但内容为空
        const aiMessageElement = createAIMessageElement('');
        
        // 添加typing类以显示光标效果
        aiMessageElement.classList.add('typing');
        
        // 移除思考状态指示器
        thinkingIndicator.remove();
        
        // 添加AI消息元素到聊天容器
        const chatContainer = document.getElementById('chatContainer');
        chatContainer.appendChild(aiMessageElement);
        
        // 获取消息内容元素
        const messageBubble = aiMessageElement.querySelector('.chat-bubble p');
        
        // 上下文容器的引用
        let contextElement = null;
        let streamCompleted = false;
        let responseText = '';
        let lastScrollTime = 0;
        const SCROLL_THROTTLE = 100; // 限制滚动频率，防止过度滚动
        
        // 发送流式请求
        response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: message,
                stream: true
            }),
            signal: controller.signal
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '请求失败');
        }
        
        // 高效流式处理
        reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // 使用DocumentFragment提高渲染效率
        const createFragment = (html) => {
            const template = document.createElement('template');
            template.innerHTML = html;
            return template.content;
        };
        
        // 限制滚动频率的函数
        const throttledScroll = () => {
            const now = Date.now();
            if (now - lastScrollTime > SCROLL_THROTTLE) {
                lastScrollTime = now;
                scrollToBottom();
            }
        };
        
        try {
            let buffer = '';  // 用于处理不完整的JSON
            
            while (true) {
                const { value, done } = await reader.read();
                
                if (done) {
                    console.log("Stream is done");
                    break;
                }
                
                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;
                
                // 分割并处理完整的数据行
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || ''; // 最后一行可能不完整，保留到下一次处理
                
                for (const line of lines) {
                    if (!line.trim() || !line.startsWith('data: ')) continue;
                    
                    try {
                        // 提取JSON部分
                        const jsonStr = line.slice(6);
                        const data = JSON.parse(jsonStr);
                        
                        if (data.type === 'context') {
                            // 收到上下文数据
                            const contextData = data.data;
                            if (contextData && contextData.length > 0) {
                                // 创建上下文元素
                                contextElement = createContextElement(contextData);
                                aiMessageElement.appendChild(contextElement);
                            }
                        } else if (data.type === 'text') {
                            // 收到文本数据 - 立即添加到显示
                            if (data.data) {
                                responseText += data.data;
                                // 使用innerHTML更高效地批量更新，而不是逐字符添加
                                messageBubble.innerHTML = formatMessageContent(responseText);
                                // 限制滚动频率
                                throttledScroll();
                            }
                            
                            // 检查是否是最终消息
                            if (data.done === true) {
                                streamCompleted = true;
                                // 移除typing类，停止光标闪烁
                                aiMessageElement.classList.remove('typing');
                                console.log("Stream completed successfully");
                                
                                // 如果消息为空，添加一个友好提示
                                if (!responseText.trim()) {
                                    messageBubble.innerHTML = '<em>AI没有生成回答。请尝试其他问题。</em>';
                                }
                                // 最后一次滚动确保显示完整内容
                                scrollToBottom();
                            }
                        } else if (data.type === 'error') {
                            // 收到错误信息
                            console.error("Received error from server:", data.data);
                            messageBubble.innerHTML = `<div class="chat-error"><i class="fas fa-exclamation-circle me-2"></i>${data.data}</div>`;
                            // 移除typing类，停止光标闪烁
                            aiMessageElement.classList.remove('typing');
                            scrollToBottom();
                            streamCompleted = true;
                        }
                    } catch (parseError) {
                        console.error('解析JSON数据出错:', parseError, "原始数据:", line);
                    }
                }
            }
        } catch (streamError) {
            console.error('流读取错误:', streamError);
            
            // 只有在未完成的情况下才显示错误
            if (!streamCompleted) {
                messageBubble.innerHTML += `<div class="chat-error"><i class="fas fa-wifi me-2"></i>连接中断，请重试</div>`;
                // 移除typing类，停止光标闪烁
                aiMessageElement.classList.remove('typing');
            }
        } finally {
            // 标记流已关闭
            streamCompleted = true;
            
            // 确保移除typing类
            aiMessageElement.classList.remove('typing');
        }
        
        // 最后确保滚动到底部
        scrollToBottom();
        
    } catch (error) {
        console.error('聊天请求出错:', error);
        throw error;
    } finally {
        // 清理资源
        try {
            // 释放reader资源
            if (reader) {
                try {
                    reader.releaseLock();
                    console.log("Reader lock released");
                } catch (e) {
                    console.error('释放reader锁时出错:', e);
                }
            }
            
            // 关闭响应体
            if (response && response.body) {
                try {
                    await response.body.cancel();
                    console.log("Response body canceled");
                } catch (e) {
                    console.error('取消响应体时出错:', e);
                }
            }
        } catch (cleanupError) {
            console.error('清理资源时出错:', cleanupError);
        }
        
        // 重置控制器，允许发送新消息
        controller = null;
    }
}

/**
 * 添加用户消息到聊天界面
 * @param {string} message - 用户消息内容
 */
function appendUserMessage(message) {
    // 获取模板
    const template = document.getElementById('userMessageTemplate');
    const messageElement = document.importNode(template.content, true);
    
    // 设置消息内容
    const messageText = messageElement.querySelector('.chat-bubble p');
    messageText.innerHTML = formatMessageContent(message);
    
    // 设置时间
    const timeElement = messageElement.querySelector('.chat-time');
    timeElement.textContent = getCurrentTimeString();
    
    // 添加到聊天容器
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.appendChild(messageElement);
}

/**
 * 添加AI消息到聊天界面
 * @param {string} message - AI消息内容
 * @param {Array} context - 上下文数据（可选）
 */
function appendAIMessage(message, context = null) {
    // 创建AI消息元素
    const messageElement = createAIMessageElement(message);
    
    // 添加到聊天容器
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.appendChild(messageElement);
    
    // 如果有上下文数据，添加到消息下方
    if (context && context.length > 0) {
        const contextElement = createContextElement(context);
        messageElement.appendChild(contextElement);
    }
}

/**
 * 创建AI消息元素
 * @param {string} message - 消息内容
 * @return {Element} 消息DOM元素
 */
function createAIMessageElement(message) {
    // 获取模板
    const template = document.getElementById('aiMessageTemplate');
    const messageElement = document.importNode(template.content, true);
    
    // 设置消息内容
    const messageText = messageElement.querySelector('.chat-bubble p');
    messageText.innerHTML = formatMessageContent(message);
    
    // 设置时间
    const timeElement = messageElement.querySelector('.chat-time');
    timeElement.textContent = getCurrentTimeString();
    
    return messageElement.querySelector('.chat-message');
}

/**
 * 创建上下文元素
 * @param {Array} contextItems - 上下文项目数组
 * @return {Element} 上下文DOM元素
 */
function createContextElement(contextItems) {
    // 获取模板
    const template = document.getElementById('contextTemplate');
    const contextElement = document.importNode(template.content, true);
    
    // 获取上下文项目容器
    const itemsContainer = contextElement.querySelector('.context-items');
    
    // 添加上下文项目
    contextItems.forEach(item => {
        // 获取项目模板
        const itemTemplate = document.getElementById('contextItemTemplate');
        const itemElement = document.importNode(itemTemplate.content, true);
        
        // 设置链接和标题
        const link = itemElement.querySelector('.context-link');
        link.href = item.link || '#';
        
        const title = itemElement.querySelector('.context-title');
        title.textContent = item.title || '未知标题';
        
        // 添加到容器
        itemsContainer.appendChild(itemElement);
    });
    
    return contextElement;
}

/**
 * 添加AI思考状态指示器
 * @return {Element} 思考状态指示器DOM元素
 */
function appendThinkingIndicator() {
    // 获取模板
    const template = document.getElementById('aiThinkingTemplate');
    const indicatorElement = document.importNode(template.content, true);
    
    // 添加到聊天容器
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.appendChild(indicatorElement);
    
    // 滚动到底部
    scrollToBottom();
    
    return chatContainer.querySelector('.thinking-indicator');
}

/**
 * 格式化消息内容，处理换行符和链接
 * @param {string} content - 原始消息内容
 * @return {string} 格式化后的HTML
 */
function formatMessageContent(content) {
    if (!content) return '';
    
    // 替换换行符为<br>
    let formattedContent = content.replace(/\n/g, '<br>');
    
    // 将URL转为可点击链接
    formattedContent = formattedContent.replace(
        /(https?:\/\/[^\s]+)/g, 
        '<a href="$1" target="_blank" class="text-primary">$1</a>'
    );
    
    return formattedContent;
}

/**
 * 获取当前时间字符串
 * @return {string} 格式化的时间字符串
 */
function getCurrentTimeString() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
}

/**
 * 滚动聊天容器到底部
 */
function scrollToBottom() {
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * 清空聊天历史记录，只保留欢迎消息
 */
function clearChat() {
    const chatContainer = document.getElementById('chatContainer');
    
    // 保留第一个AI消息（欢迎消息）
    const firstMessage = chatContainer.querySelector('.chat-message');
    
    // 清空容器
    chatContainer.innerHTML = '';
    
    // 重新添加欢迎消息
    if (firstMessage && firstMessage.classList.contains('ai-message')) {
        chatContainer.appendChild(firstMessage);
    } else {
        // 如果没有找到欢迎消息，创建一个新的
        appendAIMessage('你好！我是AI助手，可以为你提供新闻信息和相关解读。有什么可以帮你的吗？');
    }
} 