// 日志查看器 - 用于实时查看爬虫执行日志

class LogViewer {
    constructor(logId) {
        this.logId = logId;
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000; // 3秒
        this.pingInterval = null;
        this.logContentElement = null;
        this.statusElement = null;
        this.progressElement = null;
    }

    // 初始化日志查看器
    init(logContentElement, statusElement, progressElement) {
        this.logContentElement = logContentElement;
        this.statusElement = statusElement;
        this.progressElement = progressElement;
        this.connect();
    }

    // 连接WebSocket
    connect() {
        // 关闭现有连接
        if (this.socket) {
            this.socket.close();
        }

        // 创建新连接
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/logs/${this.logId}`;
        this.socket = new WebSocket(wsUrl);
        console.log('正在连接WebSocket:', wsUrl);

        // 设置事件处理程序
        this.socket.onopen = this.onOpen.bind(this);
        this.socket.onmessage = this.onMessage.bind(this);
        this.socket.onclose = this.onClose.bind(this);
        this.socket.onerror = this.onError.bind(this);
    }

    // 连接打开时的处理
    onOpen() {
        console.log('WebSocket连接已建立');
        this.connected = true;
        this.reconnectAttempts = 0;

        // 设置定时ping以保持连接
        this.pingInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send('ping');
            }
        }, 30000); // 30秒ping一次

        // 更新UI状态
        if (this.statusElement) {
            this.statusElement.innerHTML = '<span class="badge bg-success">已连接</span>';
        }
    }

    // 接收消息时的处理
    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            
            // 处理不同类型的消息
            if (message.type === 'initial' || message.type === 'update') {
                this.updateLogContent(message.data);
            } else if (message.type === 'pong') {
                console.log('收到pong响应');
            }
        } catch (error) {
            console.error('处理消息时出错:', error);
        }
    }

    // 连接关闭时的处理
    onClose(event) {
        console.log('WebSocket连接已关闭', event);
        this.connected = false;
        clearInterval(this.pingInterval);

        // 更新UI状态
        if (this.statusElement) {
            this.statusElement.innerHTML = '<span class="badge bg-danger">已断开</span>';
        }

        // 尝试重新连接
        this.tryReconnect();
    }

    // 连接错误时的处理
    onError(error) {
        console.error('WebSocket错误:', error);
        // 添加更详细的错误信息
        const errorMessage = error.message || '未知错误';
        console.error('WebSocket错误详情:', errorMessage);
        
        // 更新UI状态
        if (this.statusElement) {
            this.statusElement.innerHTML = `<span class="badge bg-danger">连接错误: ${errorMessage}</span>`;
        }
        
        // 错误处理由onClose处理重连，但某些错误可能不会触发onClose
        if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
            this.connected = false;
            clearInterval(this.pingInterval);
            this.tryReconnect();
        }
    }

    // 尝试重新连接
    tryReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            // 更新UI状态
            if (this.statusElement) {
                this.statusElement.innerHTML = `<span class="badge bg-warning">正在重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})</span>`;
            }
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);
        } else {
            console.log('达到最大重连次数，停止重连');
            
            // 更新UI状态
            if (this.statusElement) {
                this.statusElement.innerHTML = '<span class="badge bg-danger">连接失败</span>';
            }
        }
    }

    // 更新日志内容
    updateLogContent(data) {
        // 更新日志内容
        if (this.logContentElement && data.log_content) {
            // 尝试解析JSON格式的日志内容
            try {
                // 先检查log_content是否已经是对象（可能是后端直接传递的JSON对象）
                const logContent = typeof data.log_content === 'object' ? 
                    data.log_content : JSON.parse(data.log_content);
                // 如果解析成功，格式化显示JSON内容
                this.logContentElement.textContent = JSON.stringify(logContent, null, 2);
            } catch (e) {
                console.error('解析日志内容失败:', e);
                // 如果解析失败，直接显示原始内容
                this.logContentElement.textContent = data.log_content;
            }
            // 滚动到底部
            this.logContentElement.scrollTop = this.logContentElement.scrollHeight;
        }

        // 更新错误信息
        if (data.error_message) {
            const errorElement = document.getElementById('error-content');
            if (errorElement) {
                errorElement.textContent = data.error_message;
                errorElement.parentElement.style.display = 'block';
            }
        }

        // 更新状态
        if (data.status) {
            const statusBadge = document.getElementById('log-status-badge');
            if (statusBadge) {
                statusBadge.className = `badge ${getStatusBadgeClass(data.status)}`;
                statusBadge.textContent = getStatusText(data.status);
            }
        }

        // 更新进度条
        if (this.progressElement) {
            if (data.status === 'running') {
                this.progressElement.style.display = 'block';
                this.progressElement.innerHTML = `
                    <div class="progress">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 100%"></div>
                    </div>
                `;
            } else {
                // 如果状态不是running，则显示完成的进度条
                if (data.status === 'success') {
                    this.progressElement.innerHTML = `
                        <div class="progress">
                            <div class="progress-bar bg-success" role="progressbar" 
                                 style="width: 100%">完成</div>
                        </div>
                    `;
                } else if (data.status === 'failed') {
                    this.progressElement.innerHTML = `
                        <div class="progress">
                            <div class="progress-bar bg-danger" role="progressbar" 
                                 style="width: 100%">失败</div>
                        </div>
                    `;
                }
                
                // 3秒后隐藏进度条
                setTimeout(() => {
                    this.progressElement.style.display = 'none';
                }, 3000);
            }
        }
    }

    // 关闭连接
    close() {
        if (this.socket) {
            this.socket.close();
        }
        clearInterval(this.pingInterval);
    }
}

async function viewLogDetailRealtime(logId) {
    try {
        // 获取初始日志数据
        const response = await fetch(`/api/execution-logs/${logId}`);
        const log = await response.json();
        
        // 尝试解析日志内容中的JSON
        let formattedLogContent = log.log_content || '无输出';
        try {
            if (log.log_content) {
                const parsedContent = JSON.parse(log.log_content);
                formattedLogContent = JSON.stringify(parsedContent, null, 2);
            }
        } catch (e) {
            console.log('日志内容不是有效的JSON格式');
        }
        
        // 创建模态框
        const modalHtml = `
            <div class="modal fade" id="logDetailModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">执行日志详情</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <strong>爬虫:</strong> ${log.spider && typeof log.spider === 'object' && log.spider.name ? log.spider.name : '未知爬虫'}
                            </div>
                            <div class="mb-3">
                                <strong>状态:</strong> 
                                <span id="log-status-badge" class="badge ${getStatusBadgeClass(log.status)}">
                                    ${getStatusText(log.status)}
                                </span>
                            </div>
                            <div class="mb-3">
                                <strong>开始时间:</strong> ${formatDateTime(log.start_time)}
                            </div>
                            <div class="mb-3">
                                <strong>结束时间:</strong> <span id="log-end-time">${log.end_time ? formatDateTime(log.end_time) : '-'}</span>
                            </div>
                            <div class="mb-3">
                                <strong>WebSocket状态:</strong> <span id="websocket-status"></span>
                            </div>
                            <div id="log-progress" class="mb-3">
                                <!-- 进度条将在这里显示 -->
                            </div>
                            <div class="mb-3">
                                <strong>输出:</strong>
                                <pre id="log-content" class="bg-dark text-light p-3 mt-2" style="max-height: 300px; overflow-y: auto;">${formattedLogContent}</pre>
                            </div>
                            <div class="mb-3" id="error-container" style="${log.error_message ? '' : 'display: none;'}">
                                <strong>错误:</strong>
                                <pre id="error-content" class="bg-danger text-light p-3 mt-2">${log.error_message || ''}</pre>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 添加到文档中
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer);
        
        // 显示模态框
        const logDetailModal = new bootstrap.Modal(document.getElementById('logDetailModal'));
        logDetailModal.show();
        
        // 初始化日志查看器
        const logViewer = new LogViewer(logId);
        logViewer.init(
            document.getElementById('log-content'),
            document.getElementById('websocket-status'),
            document.getElementById('log-progress')
        );
        
        // 当模态框关闭时，关闭WebSocket连接
        const modalElement = document.getElementById('logDetailModal');
        modalElement.addEventListener('hidden.bs.modal', function () {
            logViewer.close();
            // 检查modalContainer是否仍然是document.body的子节点
            if (modalContainer.parentNode === document.body) {
                document.body.removeChild(modalContainer);
            }
        });
        
    } catch (error) {
        console.error('查看日志详情失败:', error);
        showAlert('查看日志详情失败', 'danger');
    }
}

// 替换原有的查看日志详情函数，使用try-catch包装以捕获可能的错误
try {
    window.viewLogDetail = viewLogDetailRealtime;
} catch (error) {
    console.error('替换viewLogDetail函数失败:', error);
}