/**
 * 新闻聊天系统首页JavaScript
 * 实现首页的搜索框、动画和聊天功能
 */

document.addEventListener('DOMContentLoaded', () => {
    // 初始化页面元素
    const searchContainer = document.getElementById('search-container');
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const chatContainer = document.getElementById('chat-container');
    const chatMessages = document.getElementById('chat-messages');
    const contextContainer = document.getElementById('context-container');
    const contextList = document.getElementById('context-list');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');
    const newChatBtn = document.getElementById('new-chat-btn');
    const addButton = document.getElementById('add-button');
    
    // 新闻侧边栏相关元素
    const newsSidebar = document.getElementById('news-sidebar');
    const newsSidebarBody = document.getElementById('news-sidebar-body');
    const newsToggleBtn = document.getElementById('news-toggle-btn');
    const newsSidebarClose = document.getElementById('news-sidebar-close');
    
    // RSS添加对话框相关元素
    const addRssModal = new bootstrap.Modal(document.getElementById('addRssModal'), {
        keyboard: true,
        backdrop: true
    });
    const addRssForm = document.getElementById('addRssForm');
    const addRssSubmit = document.getElementById('addRssSubmit');
    const rssLoading = document.getElementById('rss-loading');
    const rssAddStatus = document.getElementById('rss-add-status');
    
    // 查看RSS源对话框相关元素
    const viewRssSourcesBtn = document.getElementById('view-rss-sources-btn');
    const viewRssSourcesModal = new bootstrap.Modal(document.getElementById('viewRssSourcesModal'), {
        keyboard: true,
        backdrop: true
    });
    const rssSourcesList = document.getElementById('rss-sources-list');
    
    // 存储引用的新闻
    let referencedNews = [];
    
    // 如果不在首页，直接返回
    if (!searchInput || !chatContainer) {
        return;
    }
    
    // 侧边栏控制
    if (newsToggleBtn && newsSidebar && newsSidebarClose) {
        // 显示侧边栏
        newsToggleBtn.addEventListener('click', toggleNewsSidebar);
        
        // 关闭侧边栏
        newsSidebarClose.addEventListener('click', () => {
            newsSidebar.classList.remove('active');
            chatContainer.classList.remove('with-sidebar');
        });
    }
    
    // 设置加号按钮点击事件（打开添加RSS源对话框）
    if (addButton) {
        addButton.addEventListener('click', () => {
            // 重置表单和状态
            if (addRssForm) addRssForm.reset();
            if (rssAddStatus) {
                rssAddStatus.classList.add('d-none');
                rssAddStatus.textContent = '';
                rssAddStatus.className = 'alert d-none';
            }
            
            // 打开对话框
            if (addRssModal) addRssModal.show();
        });
    }
    
    // 查看RSS源按钮点击事件
    if (viewRssSourcesBtn) {
        viewRssSourcesBtn.addEventListener('click', () => {
            loadRssSources();
            viewRssSourcesModal.show();
        });
    }
    
    // 添加RSS源提交按钮点击事件
    if (addRssSubmit) {
        addRssSubmit.addEventListener('click', addRssSource);
    }
    
    // 搜索框事件处理
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && searchInput.value.trim()) {
            startChat(searchInput.value.trim());
        }
    });
    
    searchButton.addEventListener('click', () => {
        if (searchInput.value.trim()) {
            startChat(searchInput.value.trim());
        }
    });
    
    // 聊天输入事件处理
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && chatInput.value.trim()) {
            sendMessage(chatInput.value.trim());
        }
    });
    
    sendButton.addEventListener('click', () => {
        if (chatInput.value.trim()) {
            sendMessage(chatInput.value.trim());
        }
    });
    
    // 新对话按钮事件处理
    newChatBtn.addEventListener('click', () => {
        resetChat();
    });
    
    /**
     * 加载RSS源数据
     */
    async function loadRssSources() {
        if (!rssSourcesList) return;
        
        // 显示加载状态
        rssSourcesList.innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">加载中...</p>
            </div>
        `;
        
        try {
            // 从后端获取RSS源数据
            const response = await fetch('/api/news/rss_sources');
            
            if (!response.ok) {
                throw new Error('获取RSS源数据失败');
            }
            
            const data = await response.json();
            
            // 渲染RSS源列表
            if (data && data.sources && data.sources.length > 0) {
                renderRssSources(data.sources);
            } else {
                rssSourcesList.innerHTML = `
                    <div class="text-center py-3 text-muted">
                        <i class="fas fa-info-circle mb-2 d-block" style="font-size: 1.5rem;"></i>
                        <p>暂无订阅的RSS源</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('加载RSS源时出错:', error);
            rssSourcesList.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    加载RSS源失败: ${error.message}
                </div>
            `;
        }
    }
    
    /**
     * 渲染RSS源列表
     * @param {Array} sources - RSS源数组
     */
    function renderRssSources(sources) {
        if (!rssSourcesList) return;
        
        // 创建表格
        let html = `
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>标题</th>
                        <th>URL</th>
                        <th>描述</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        // 添加每个源
        sources.forEach(source => {
            html += `
                <tr>
                    <td>${source.title || '未命名'}</td>
                    <td><a href="${source.url}" target="_blank" class="text-truncate d-inline-block" style="max-width: 250px;">${source.url}</a></td>
                    <td>${source.description || '-'}</td>
                </tr>
            `;
        });
        
        html += `
                </tbody>
            </table>
        `;
        
        rssSourcesList.innerHTML = html;
    }
    
    /**
     * 添加RSS源
     */
    async function addRssSource() {
        // 获取表单数据
        const url = document.getElementById('rss-url').value.trim();
        const title = document.getElementById('rss-title').value.trim();
        const description = document.getElementById('rss-description').value.trim();
        const attribute = document.getElementById('rss-attribute').value.trim();
        
        // 验证必填字段
        if (!url || !title) {
            showRssAddStatus('请填写必填字段', 'error');
            return;
        }
        
        // 显示加载状态
        rssLoading.classList.remove('d-none');
        addRssSubmit.disabled = true;
        
        try {
            // 发送请求添加RSS源
            const response = await fetch('/api/news/add_rss', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url,
                    title,
                    description: description || undefined,
                    attribute: attribute || undefined
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // 添加成功
                showRssAddStatus(data.message, 'success');
                // 延迟关闭对话框
                setTimeout(() => {
                    addRssModal.hide();
                }, 2000);
            } else {
                // 添加失败
                showRssAddStatus(data.message || '添加RSS源失败', 'error');
            }
        } catch (error) {
            console.error('添加RSS源时出错:', error);
            showRssAddStatus('网络错误，请稍后重试', 'error');
        } finally {
            // 隐藏加载状态
            rssLoading.classList.add('d-none');
            addRssSubmit.disabled = false;
        }
    }
    
    /**
     * 显示RSS添加状态信息
     * @param {string} message - 状态信息
     * @param {string} type - 类型: success 或 error
     */
    function showRssAddStatus(message, type) {
        if (!rssAddStatus) return;
        
        rssAddStatus.textContent = message;
        rssAddStatus.className = `alert ${type === 'success' ? 'alert-success' : 'alert-danger'}`;
        rssAddStatus.classList.remove('d-none');
    }
    
    /**
     * 开始聊天 - 从搜索框开始第一次对话
     */
    function startChat(query) {
        // 保存查询内容
        const initialQuery = query;
        
        // 隐藏搜索容器，完全转换为聊天界面
        searchContainer.style.opacity = '0';
        searchContainer.style.transition = 'opacity 0.5s ease';
        
        // 显示聊天容器
        setTimeout(() => {
            // 彻底隐藏搜索容器
            searchContainer.style.display = 'none';
            
            // 启用聊天输入
            chatInput.disabled = false;
            sendButton.disabled = false;
            
            // 显示聊天区域，占据全屏
            chatContainer.classList.add('active', 'fullscreen');
            
            // 显示侧边栏切换按钮
            if (newsToggleBtn) {
                newsToggleBtn.classList.remove('d-none');
            }
            
            // 发送第一条消息
            sendMessage(initialQuery);
        }, 500);
    }
    
    /**
     * 切换新闻侧边栏显示状态
     */
    function toggleNewsSidebar() {
        newsSidebar.classList.toggle('active');
        chatContainer.classList.toggle('with-sidebar');
    }
    
    /**
     * 发送消息到服务器
     */
    function sendMessage(message) {
        // 清空输入框
        chatInput.value = '';
        
        // 添加用户消息到聊天区域
        addMessageToChat('user', message);
        
        // 显示加载状态
        typingIndicator.classList.remove('d-none');
        
        // 发送到服务器
        fetchChatResponse(message);
    }
    
    /**
     * 获取聊天响应
     */
    async function fetchChatResponse(query) {
        try {
            // 显示上下文加载动画
            contextContainer.classList.add('d-none');
            
            // 使用EventSource接收流式响应
            const source = new EventSource(`/api/chat/message?query=${encodeURIComponent(query)}&stream=true`);
            
            let aiResponse = '';
            
            source.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                // 根据消息类型处理
                if (data.type === 'context') {
                    // 显示上下文信息
                    showContextInfo(data.data);
                    
                    // 更新侧边栏新闻
                    updateReferencedNews(data.data);
                } else if (data.type === 'text') {
                    // 更新AI回复
                    if (!data.done) {
                        aiResponse += data.data;
                        updateAIResponse(aiResponse);
                    } else {
                        // 完成响应
                        if (data.data) {
                            aiResponse += data.data;
                            updateAIResponse(aiResponse);
                        }
                        source.close();
                        typingIndicator.classList.add('d-none');
                    }
                } else if (data.type === 'error') {
                    // 处理错误
                    addMessageToChat('error', data.data);
                    source.close();
                    typingIndicator.classList.add('d-none');
                }
            };
            
            source.onerror = function(error) {
                console.error('EventSource 错误:', error);
                addMessageToChat('error', '连接出错，请刷新页面重试');
                source.close();
                typingIndicator.classList.add('d-none');
            };
            
        } catch (error) {
            console.error('获取聊天响应出错:', error);
            addMessageToChat('error', '服务器错误，请稍后重试');
            typingIndicator.classList.add('d-none');
        }
    }
    
    /**
     * 将消息添加到聊天区域
     */
    function addMessageToChat(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message chat-message-${type} mb-4`;
        
        if (type === 'user') {
            messageDiv.innerHTML = `
                <div class="d-flex justify-content-end">
                    <div class="message-content">
                        <div class="message-sender text-end mb-1">
                            <small class="text-muted"><i class="fas fa-user me-1"></i>您</small>
                        </div>
                        <div class="chat-bubble user-bubble p-3">
                            ${content}
                        </div>
                    </div>
                </div>
            `;
        } else if (type === 'ai') {
            messageDiv.innerHTML = `
                <div class="d-flex">
                    <div class="message-content">
                        <div class="message-sender mb-1">
                            <small class="text-muted"><i class="fas fa-robot me-1"></i>AI助手</small>
                        </div>
                        <div class="chat-bubble ai-bubble p-3">
                            ${content}
                        </div>
                    </div>
                </div>
            `;
        } else if (type === 'error') {
            messageDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>${content}
                </div>
            `;
        }
        
        chatMessages.appendChild(messageDiv);
        
        // 滚动到底部
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    /**
     * 更新AI回复内容
     */
    function updateAIResponse(content) {
        // 查找最后一条AI消息，如果存在则更新，否则创建新消息
        const lastAIMessage = chatMessages.querySelector('.chat-message-ai:last-child .ai-bubble');
        
        if (lastAIMessage) {
            lastAIMessage.innerHTML = content;
        } else {
            addMessageToChat('ai', content);
        }
        
        // 滚动到底部
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    /**
     * 显示上下文信息
     */
    function showContextInfo(context) {
        if (!context || context.length === 0) {
            contextContainer.classList.add('d-none');
            return;
        }
        
        contextContainer.classList.remove('d-none');
        contextList.innerHTML = '';
        
        context.forEach(item => {
            const listItem = document.createElement('div');
            listItem.className = 'context-item';
            
            if (item.link) {
                listItem.innerHTML = `<a href="${item.link}" target="_blank">${item.title}</a>`;
            } else {
                listItem.textContent = item.title;
            }
            
            contextList.appendChild(listItem);
        });
    }
    
    /**
     * 更新引用的新闻
     */
    function updateReferencedNews(newsItems) {
        if (!newsItems || newsItems.length === 0 || !newsSidebarBody) {
            return;
        }
        
        // 清空现有内容
        newsSidebarBody.innerHTML = '';
        referencedNews = [...newsItems];
        
        // 添加新闻条目
        newsItems.forEach((item, index) => {
            const newsItem = document.createElement('div');
            newsItem.className = 'news-item';
            
            const dateStr = item.date || '未知日期';
            
            newsItem.innerHTML = `
                <div class="news-item-title">
                    ${item.link ? 
                    `<a href="${item.link}" target="_blank" title="${item.title}">${item.title}</a>` : 
                    item.title}
                </div>
                <div class="news-item-date">
                    <i class="far fa-calendar me-1"></i>${dateStr}
                </div>
            `;
            
            newsSidebarBody.appendChild(newsItem);
        });
        
        // 如果是首次添加新闻，显示侧边栏
        if (referencedNews.length > 0 && !newsSidebar.classList.contains('active')) {
            toggleNewsSidebar();
        }
    }
    
    /**
     * 重置聊天，开始新的对话
     */
    function resetChat() {
        // 清空聊天内容
        chatMessages.innerHTML = '';
        contextContainer.classList.add('d-none');
        contextList.innerHTML = '';
        
        // 清空侧边栏新闻
        if (newsSidebarBody) {
            newsSidebarBody.innerHTML = `
                <div class="empty-message text-center text-muted py-4">
                    <i class="fas fa-info-circle mb-2 d-block" style="font-size: 2rem;"></i>
                    暂无引用的新闻，开始对话后会在这里显示相关文章
                </div>
            `;
        }
        
        // 隐藏侧边栏和切换按钮
        if (newsSidebar && newsSidebar.classList.contains('active')) {
            newsSidebar.classList.remove('active');
            chatContainer.classList.remove('with-sidebar');
        }
        
        if (newsToggleBtn) {
            newsToggleBtn.classList.add('d-none');
        }
        
        // 隐藏聊天区域，重置搜索区域
        chatContainer.classList.remove('active', 'fullscreen');
        
        // 重新显示搜索容器
        searchContainer.style.display = 'flex';
        setTimeout(() => {
            // 延迟显示以实现动画效果
            searchContainer.style.opacity = '1';
        }, 50);
        
        // 清空并聚焦搜索框
        searchInput.value = '';
        setTimeout(() => {
            searchInput.focus();
        }, 300);
        
        // 重置引用新闻数组
        referencedNews = [];
    }
}); 