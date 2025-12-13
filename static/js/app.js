// AI桌面机器人前端应用
class AIChatApp {
    constructor() {
        this.currentSessionId = null;
        this.messageCount = 0;
        this.isConnected = true;
        this.apiEndpoint = '/api/chat';

        this.init();
    }

    init() {
        // 获取DOM元素
        this.elements = {
            chatContainer: document.getElementById('chat-container'),
            messageInput: document.getElementById('message-input'),
            sendBtn: document.getElementById('send-btn'),
            newChatBtn: document.getElementById('new-chat-btn'),
            sessionsList: document.getElementById('sessions-list'),
            currentSessionInfo: document.getElementById('current-session-info'),
            sessionTime: document.getElementById('session-time'),
            connectionStatus: document.getElementById('connection-status'),
            quickPromptBtns: document.querySelectorAll('.quick-prompt-btn'),
            toggleSidebar: document.getElementById('toggle-sidebar'),
            sidebar: document.getElementById('sidebar'),
            clearHistoryBtn: document.getElementById('clear-history'),
            searchSessions: document.getElementById('search-sessions')
        };

        // 初始化会话
        this.initSession();

        // 绑定事件
        this.bindEvents();

        // 加载历史会话
        this.loadSessions();

        // 测试连接
        this.testConnection();
    }

    // 初始化会话
    initSession() {
        // 尝试从URL参数获取session_id
        const urlParams = new URLSearchParams(window.location.search);
        const urlSessionId = urlParams.get('session_id');

        if (urlSessionId) {
            this.currentSessionId = urlSessionId;
            localStorage.setItem('ai_chat_session_id', urlSessionId);
        } else {
            // 从本地存储获取
            this.currentSessionId = localStorage.getItem('ai_chat_session_id');

            // 如果没有，创建一个新的
            if (!this.currentSessionId) {
                this.currentSessionId = this.generateSessionId();
                localStorage.setItem('ai_chat_session_id', this.currentSessionId);
            }
        }

        // 更新会话显示
        this.updateSessionDisplay();

        console.log('当前会话ID:', this.currentSessionId);
    }

    // 生成会话ID
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // 更新会话显示
    updateSessionDisplay() {
        if (this.elements.currentSessionInfo) {
            const sessionInfoEl = this.elements.currentSessionInfo.querySelector('.font-medium');
            if (sessionInfoEl) {
                // 显示简化的会话ID
                const shortId = this.currentSessionId.substring(0, 12) + '...';
                sessionInfoEl.textContent = `会话: ${shortId}`;
            }
        }

        if (this.elements.sessionTime) {
            this.elements.sessionTime.textContent = new Date().toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    // 绑定事件
    bindEvents() {
        // 发送消息
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());

        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 输入框自动调整高度
        this.elements.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });

        // 新对话
        this.elements.newChatBtn.addEventListener('click', () => this.startNewSession());

        // 快速提示
        this.elements.quickPromptBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const text = e.currentTarget.querySelector('.font-medium').textContent;
                this.elements.messageInput.value = text;
                this.autoResizeTextarea();
                this.sendMessage();
            });
        });

        // 切换侧边栏
        this.elements.toggleSidebar.addEventListener('click', () => {
            this.elements.sidebar.classList.toggle('hidden');
        });

        // 清空历史
        this.elements.clearHistoryBtn.addEventListener('click', () => {
            if (confirm('确定要清空所有历史会话吗？此操作不可撤销。')) {
                this.clearAllSessions();
            }
        });

        // 搜索会话
        this.elements.searchSessions.addEventListener('input', (e) => {
            this.filterSessions(e.target.value);
        });

        // 点击外部关闭侧边栏（移动端）
        document.addEventListener('click', (e) => {
            if (window.innerWidth < 768 &&
                this.elements.sidebar &&
                !this.elements.sidebar.contains(e.target) &&
                !this.elements.toggleSidebar.contains(e.target)) {
                this.elements.sidebar.classList.add('hidden');
            }
        });
    }

    // 自动调整输入框高度
    autoResizeTextarea() {
        const textarea = this.elements.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    // 发送消息
    async sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message) return;

        // 清除输入框
        this.elements.messageInput.value = '';
        this.autoResizeTextarea();

        // 添加用户消息到界面
        this.addMessageToUI('user', message);

        // 显示思考中指示器
        const thinkingId = this.showThinkingIndicator();

        try {
            // 发送请求到服务器
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.currentSessionId
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP错误 ${response.status}: ${errorText}`);
            }

            const data = await response.json();

            // 移除思考中指示器
            this.removeThinkingIndicator(thinkingId);

            // 添加AI回复到界面
            this.addMessageToUI('assistant', data.reply);

            // 更新消息计数
            this.messageCount += 2;

            // 更新连接状态
            this.updateConnectionStatus(true);

            // 更新会话列表
            this.loadSessions();

            // 可以添加一个延迟，确保数据库已更新
            setTimeout(() => {
    this.loadSessions();
}, 500);

        } catch (error) {
            // 移除思考中指示器
            this.removeThinkingIndicator(thinkingId);

            // 显示错误消息
            this.addMessageToUI('system', `发送失败: ${error.message}`);
            console.error('发送消息失败:', error);

            // 更新连接状态
            this.updateConnectionStatus(false);
        }

        // 聚焦输入框
        this.elements.messageInput.focus();
    }

    // 添加消息到UI（支持时间戳）
    addMessageToUI(role, content, showTimestamp = true, timestamp = null) {
        const messageId = 'msg_' + Date.now();

        // 使用传入的时间戳，如果没有则使用当前时间
        const msgTime = timestamp ? new Date(timestamp) : new Date();
        const timeStr = showTimestamp ? msgTime.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        }) : '';

        // 如果消息是今天的，只显示时间，否则显示日期和时间
        let displayTime = timeStr;
        if (timestamp) {
            const now = new Date();
            const msgDate = new Date(timestamp);

            if (msgDate.toDateString() !== now.toDateString()) {
                // 不是今天，显示日期
                displayTime = msgDate.toLocaleDateString() + ' ' + timeStr;
            }
        }

        let messageClass, avatar, name;

        switch(role) {
            case 'user':
                messageClass = 'message-user';
                avatar = '<div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold">你</div>';
                name = '你';
                break;
            case 'assistant':
                messageClass = 'message-ai';
                avatar = '<div class="w-8 h-8 gradient-bg rounded-full flex items-center justify-center text-white"><i class="fas fa-robot"></i></div>';
                name = 'AI助手';
                break;
            default:
                messageClass = 'message-system';
                avatar = '<div class="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-gray-600"><i class="fas fa-info-circle"></i></div>';
                name = '系统';
        }

        const messageHTML = `
            <div id="${messageId}" class="message ${messageClass} flex space-x-3 fade-in">
                <div class="flex-shrink-0">${avatar}</div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-2 mb-1">
                        <span class="font-semibold text-sm">${name}</span>
                        ${showTimestamp && displayTime ? `<span class="text-xs text-gray-500">${displayTime}</span>` : ''}
                    </div>
                    <div class="text-gray-800 whitespace-pre-wrap">${this.escapeHtml(content)}</div>
                </div>
            </div>
        `;

        // 添加到聊天容器
        this.elements.chatContainer.insertAdjacentHTML('beforeend', messageHTML);

        // 滚动到底部（如果是新消息，没有timestamp）
        if (!timestamp) {
            this.scrollToBottom();
        }

        return messageId;
    }

    // 显示思考中指示器
    showThinkingIndicator() {
        const thinkingId = 'thinking_' + Date.now();
        const thinkingHTML = `
            <div id="${thinkingId}" class="message message-ai flex space-x-3 fade-in">
                <div class="flex-shrink-0">
                    <div class="w-8 h-8 gradient-bg rounded-full flex items-center justify-center text-white">
                        <i class="fas fa-robot"></i>
                    </div>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-2 mb-1">
                        <span class="font-semibold text-sm">AI助手</span>
                        <span class="text-xs text-gray-500">正在思考...</span>
                    </div>
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;

        this.elements.chatContainer.insertAdjacentHTML('beforeend', thinkingHTML);
        this.scrollToBottom();

        return thinkingId;
    }

    // 移除思考中指示器
    removeThinkingIndicator(thinkingId) {
        const element = document.getElementById(thinkingId);
        if (element) {
            element.remove();
        }
    }

    // 滚动到底部
    scrollToBottom() {
        this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
    }

    // 开始新会话
    startNewSession() {
        if (this.messageCount > 0 && !confirm('开始新对话将清空当前聊天记录，是否继续？')) {
            return;
        }

        // 生成新的会话ID
        this.currentSessionId = this.generateSessionId();
        localStorage.setItem('ai_chat_session_id', this.currentSessionId);

        // 重置消息计数
        this.messageCount = 0;

        // 清空聊天界面
        this.elements.chatContainer.innerHTML = '';

        // 显示欢迎消息
        this.showWelcomeMessage();

        // 更新显示
        this.updateSessionDisplay();

        // 添加系统消息
        this.addMessageToUI('system', '已开始新对话。');

        console.log('新会话ID:', this.currentSessionId);
    }

    // 显示欢迎消息
    showWelcomeMessage() {
        const welcomeHTML = `
            <div class="max-w-3xl mx-auto fade-in">
                <div class="text-center mb-8 mt-4">
                    <div class="inline-flex items-center justify-center w-16 h-16 gradient-bg rounded-2xl mb-4">
                        <i class="fas fa-robot text-white text-2xl"></i>
                    </div>
                    <h2 class="text-2xl font-bold text-gray-900 mb-2">欢迎使用 AI 桌面机器人</h2>
                    <p class="text-gray-600 max-w-md mx-auto">
                        我是您的智能助手，可以回答问题、提供建议，或只是陪您聊天。
                    </p>
                </div>
                
                <div id="quick-prompts" class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
                    <button class="quick-prompt-btn bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50 rounded-xl p-4 text-left transition-all duration-200">
                        <div class="font-medium text-gray-900 mb-1">你好，介绍一下你自己</div>
                        <div class="text-xs text-gray-500">了解AI助手的功能</div>
                    </button>
                    <button class="quick-prompt-btn bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50 rounded-xl p-4 text-left transition-all duration-200">
                        <div class="font-medium text-gray-900 mb-1">今天天气怎么样？</div>
                        <div class="text-xs text-gray-500">获取天气信息和建议</div>
                    </button>
                    <button class="quick-prompt-btn bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50 rounded-xl p-4 text-left transition-all duration-200">
                        <div class="font-medium text-gray-900 mb-1">讲一个笑话</div>
                        <div class="text-xs text-gray-500">放松心情，开心一下</div>
                    </button>
                    <button class="quick-prompt-btn bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50 rounded-xl p-4 text-left transition-all duration-200">
                        <div class="font-medium text-gray-900 mb-1">如何设置提醒？</div>
                        <div class="text-xs text-gray-500">帮助您记住重要事项</div>
                    </button>
                </div>
            </div>
        `;

        this.elements.chatContainer.innerHTML = welcomeHTML;

        // 重新绑定快速提示按钮事件
        this.elements.quickPromptBtns = document.querySelectorAll('.quick-prompt-btn');
        this.elements.quickPromptBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const text = e.currentTarget.querySelector('.font-medium').textContent;
                this.elements.messageInput.value = text;
                this.autoResizeTextarea();
                this.sendMessage();
            });
        });
    }

    // 加载历史会话
    async loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        if (!response.ok) throw new Error('加载会话列表失败');

        const data = await response.json();
        this.updateSessionsList(data.sessions);
    } catch (error) {
        console.error('加载会话列表失败:', error);
        // 如果API不可用，显示本地存储的会话
        this.showLocalSessions();
    }
}

    // 更新会话列表
    updateSessionsList(sessions) {
        const sessionsListEl = this.elements.sessionsList;

        if (!sessions || sessions.length === 0) {
            sessionsListEl.innerHTML = `
                <div class="text-center py-8 text-gray-400">
                    <i class="fas fa-comments text-3xl mb-3 opacity-30"></i>
                    <p class="text-sm">暂无历史对话</p>
                    <p class="text-xs mt-1">开始新对话后，历史记录会显示在这里</p>
                </div>
            `;
            return;
        }

        let sessionsHTML = '';

        sessions.forEach(session => {
            // 处理时间显示
            let timeDisplay = '';
            if (session.last_activity) {
                const lastActivity = new Date(session.last_activity);
                const now = new Date();
                const diffMs = now - lastActivity;
                const diffMins = Math.floor(diffMs / 60000);
                const diffHours = Math.floor(diffMs / 3600000);
                const diffDays = Math.floor(diffMs / 86400000);

                if (diffMins < 1) {
                    timeDisplay = '刚刚';
                } else if (diffMins < 60) {
                    timeDisplay = `${diffMins}分钟前`;
                } else if (diffHours < 24) {
                    timeDisplay = `${diffHours}小时前`;
                } else if (diffDays < 7) {
                    timeDisplay = `${diffDays}天前`;
                } else {
                    timeDisplay = lastActivity.toLocaleDateString();
                }
            }

            const isActive = session.session_id === this.currentSessionId;

            sessionsHTML += `
                <div class="session-item ${isActive ? 'active bg-blue-50 border-blue-200' : 'hover:bg-gray-50'} 
                    border rounded-lg p-3 mb-2 cursor-pointer transition-all duration-200"
                    data-session-id="${session.session_id}">
                    <div class="flex items-start justify-between">
                        <div class="flex-1 min-w-0">
                            <div class="font-medium text-gray-900 truncate ${isActive ? 'text-blue-700' : ''}">
                                ${this.escapeHtml(session.last_message || '新会话')}
                            </div>
                            <div class="text-xs text-gray-500 truncate mt-1">
                                ${session.message_count || 0} 条消息
                            </div>
                        </div>
                        <div class="ml-2 text-right">
                            <div class="text-xs ${isActive ? 'text-blue-600' : 'text-gray-400'}">${timeDisplay}</div>
                            <button class="delete-session-btn mt-1 text-xs text-gray-400 hover:text-red-600" 
                                    data-session-id="${session.session_id}">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });

        sessionsListEl.innerHTML = sessionsHTML;

        // 绑定会话点击事件
        document.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', (e) => {
                // 如果点击的是删除按钮，不切换会话
                if (e.target.closest('.delete-session-btn')) {
                    return;
                }
                const sessionId = e.currentTarget.getAttribute('data-session-id');
                this.loadSession(sessionId);
            });
        });

        // 绑定删除按钮事件
        document.querySelectorAll('.delete-session-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation(); // 阻止事件冒泡
                const sessionId = e.currentTarget.getAttribute('data-session-id');
                if (confirm(`确定要删除会话 "${sessionId.substring(0, 12)}..." 吗？`)) {
                    await this.deleteSession(sessionId);
                }
            });
        });
    }

    // 显示本地存储的会话
    showLocalSessions() {
        const sessions = JSON.parse(localStorage.getItem('ai_chat_sessions') || '[]');
        this.updateSessionsList(sessions);
    }

    // 加载特定会话
    async loadSession(sessionId) {
        // 更新当前会话ID
        this.currentSessionId = sessionId;
        localStorage.setItem('ai_chat_session_id', sessionId);

        // 更新显示
        this.updateSessionDisplay();

        // 显示加载中
        this.elements.chatContainer.innerHTML = '<div class="text-center py-12"><div class="loading-spinner mx-auto mb-4"></div><p class="text-gray-600">正在加载会话历史...</p></div>';

        try {
            // 1. 先获取会话的所有消息
            console.log(`正在加载会话: ${sessionId}`);
            const messagesResponse = await fetch(`/api/sessions/${sessionId}/messages`);

            if (!messagesResponse.ok) {
                const errorText = await messagesResponse.text();
                console.error('获取消息失败:', errorText);
                throw new Error(`获取消息失败: ${messagesResponse.status}`);
            }

            const messagesData = await messagesResponse.json();
            console.log(`收到消息数据: ${messagesData.count} 条消息`);

            // 2. 清空聊天界面
            this.elements.chatContainer.innerHTML = '';

            // 3. 显示会话信息标题
            if (messagesData.count > 0 && messagesData.messages && messagesData.messages.length > 0) {
                // 使用第一条用户消息作为标题
                const firstUserMsg = messagesData.messages.find(msg => msg.role === 'user');
                const title = firstUserMsg ?
                    (firstUserMsg.content.substring(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '')) :
                    '历史对话';

                const sessionInfoHTML = `
                    <div class="message-system text-center max-w-md mx-auto">
                        <div class="font-medium">${this.escapeHtml(title)}</div>
                        <div class="text-xs text-gray-500 mt-1">
                            共 ${messagesData.count} 条消息
                        </div>
                    </div>
                `;
                this.elements.chatContainer.insertAdjacentHTML('beforeend', sessionInfoHTML);
            }

            // 4. 显示所有历史消息
            if (messagesData.messages && messagesData.messages.length > 0) {
                console.log(`显示 ${messagesData.messages.length} 条消息`);

                messagesData.messages.forEach((msg, index) => {
                    // 为每条消息添加显示时间戳
                    const timestamp = msg.created_at ? new Date(msg.created_at) : null;
                    const showTimestamp = true; // 历史消息显示时间戳

                    // 使用原始的时间戳，不要使用当前时间
                    this.addMessageToUI(msg.role, msg.content, showTimestamp, timestamp);
                });

                // 更新消息计数
                this.messageCount = messagesData.count;

                // 添加系统消息
                this.addMessageToUI('system', `已加载 ${messagesData.count} 条历史消息。`, false);

                // 滚动到底部
                this.scrollToBottom();
            } else {
                // 如果会话没有消息，显示欢迎消息
                this.showWelcomeMessage();
                this.addMessageToUI('system', '这是一个新的或空的会话，开始对话吧！', false);
            }

            // 5. 重新加载会话列表（更新高亮状态）
            this.loadSessions();

        } catch (error) {
            console.error('加载会话失败:', error);

            // 清空聊天界面并显示错误
            this.elements.chatContainer.innerHTML = '';
            this.addMessageToUI('system', `加载会话失败: ${error.message}`, false);
            this.showWelcomeMessage();

            // 显示详细错误信息（开发模式）
            if (error.message.includes('获取消息失败')) {
                this.addMessageToUI('system', '请确保服务器已启动且API可用', false);
            }
        }
    }

    // 删除会话
    async deleteSession(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('删除会话失败');
        }

        const data = await response.json();

        // 如果删除的是当前会话，切换到新会话
        if (sessionId === this.currentSessionId) {
            this.startNewSession();
        }

        // 重新加载会话列表
        this.loadSessions();

        // 显示成功消息
        this.addMessageToUI('system', data.message || '会话已删除');

        return true;
    } catch (error) {
        console.error('删除会话失败:', error);
        this.addMessageToUI('system', '删除会话失败，请重试');
        return false;
    }
}

    // 清空所有会话
    async clearAllSessions() {
        try {
            const response = await fetch('/api/sessions', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.elements.sessionsList.innerHTML = `
                    <div class="text-center py-8 text-gray-400">
                        <i class="fas fa-comments text-3xl mb-3 opacity-30"></i>
                        <p class="text-sm">暂无历史对话</p>
                    </div>
                `;

                this.addMessageToUI('system', '已清空所有历史会话。');
            }
        } catch (error) {
            console.error('清空会话失败:', error);
            this.addMessageToUI('system', '清空会话失败，请重试。');
        }
    }

    // 过滤会话
    filterSessions(searchText) {
        const sessionItems = document.querySelectorAll('.session-item');
        searchText = searchText.toLowerCase();

        sessionItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(searchText) ? 'block' : 'none';
        });
    }

    // 测试连接
    async testConnection() {
        try {
            const response = await fetch('/api/status');
            if (response.ok) {
                this.updateConnectionStatus(true);
            } else {
                this.updateConnectionStatus(false);
            }
        } catch (error) {
            console.error('连接测试失败:', error);
            this.updateConnectionStatus(false);
        }
    }

    // 更新连接状态
    updateConnectionStatus(connected) {
        this.isConnected = connected;

        const statusEl = this.elements.connectionStatus;
        if (!statusEl) return;

        if (connected) {
            statusEl.textContent = '已连接';
            statusEl.parentElement.classList.remove('bg-red-50', 'text-red-700');
            statusEl.parentElement.classList.add('bg-green-50', 'text-green-700');
            statusEl.previousElementSibling.classList.remove('bg-red-500');
            statusEl.previousElementSibling.classList.add('bg-green-500');

            // 启用发送按钮
            this.elements.sendBtn.disabled = false;
        } else {
            statusEl.textContent = '连接失败';
            statusEl.parentElement.classList.remove('bg-green-50', 'text-green-700');
            statusEl.parentElement.classList.add('bg-red-50', 'text-red-700');
            statusEl.previousElementSibling.classList.remove('bg-green-500');
            statusEl.previousElementSibling.classList.add('bg-red-500');

            // 禁用发送按钮
            this.elements.sendBtn.disabled = true;
        }
    }

    // HTML转义
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new AIChatApp();
});

// 全局键盘快捷键
document.addEventListener('keydown', (e) => {
    // Ctrl+N: 新对话
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        if (window.chatApp) {
            window.chatApp.startNewSession();
        }
    }

    // Esc: 隐藏侧边栏（移动端）
    if (e.key === 'Escape' && window.innerWidth < 768) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.add('hidden');
        }
    }
});