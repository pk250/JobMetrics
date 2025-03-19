// 爬虫管理平台 - 后台管理脚本

// 当前页面
let currentPage = 'dashboard';

// 初始化脚本编辑器
const scriptEditor = new ScriptEditor();

// 当文档加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    loadPage('dashboard');
    
    // 注册侧边栏导航事件
    // 导航菜单激活状态切换
    document.addEventListener('DOMContentLoaded', function() {
        // 初始化菜单点击事件
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                // 切换激活状态
                document.querySelectorAll('.nav-link').forEach(item => 
                    item.classList.remove('active'));
                this.classList.add('active');
                
                // 显示加载状态
                const loading = document.getElementById('loading');
                loading.style.display = 'flex';
                
                // 加载子页面
                const page = this.dataset.page;
                const iframe = document.getElementById('content-frame');
                iframe.onload = () => {
                    loading.style.display = 'none';
                    // 通知子页面激活状态
                    iframe.contentWindow.postMessage({ activePage: page }, '*');
                };
                iframe.src = `/admin/${page}`;
            });
        });
    
        // 处理子页面通信
        window.addEventListener('message', function(e) {
            if (e.data.updateNav) {
                document.querySelector(`[data-page="${e.data.updateNav}"]`).click();
            }
        });
    
        // 默认加载dashboard
        document.querySelector('[data-page="dashboard"]').click();
    });
});

// 加载页面内容
function loadPage(page) {
    currentPage = page;
    const iframe = document.getElementById('content-iframe');
    const loadingIndicator = document.getElementById('loading');
    
    loadingIndicator.style.display = 'block';
    
    // 获取对应模板
    const template = document.getElementById(`template-${page}`);
    if (template) {
        iframe.contentDocument.open();
        iframe.contentDocument.write(template.innerHTML);
        iframe.contentDocument.close();
        
        // 根据页面类型加载数据
        switch (page) {
            case 'dashboard':
                loadDashboardData();
                break;
            case 'spiders':
                loadSpiders();
                setupSearchFunction();
                break;
            case 'schedules':
                loadSchedules();
                break;
            case 'environments':
                loadEnvironments();
                break;
            case 'logs':
                loadLogs();
                break;
        }
    } else {
        iframe.contentDocument.body.innerHTML = '<div class="alert alert-danger">页面不存在</div>';
    }
    
    loadingIndicator.style.display = 'none';
}

// 加载仪表盘数据
async function loadDashboardData(doc = document) {
    try {
        const spidersResponse = await fetch('/api/spiders/');
        const spiders = await spidersResponse.json();
        doc.getElementById('spider-count').textContent = spiders.length;
        
        // 获取调度任务总数
        const schedulesResponse = await fetch('/api/schedules/');
        const schedules = await schedulesResponse.json();
        document.getElementById('schedule-count').textContent = schedules.length;
        
        // 获取最近的执行日志（倒序排列）
        const logsResponse = await fetch('/api/execution-logs/?limit=5');
        const logs = await logsResponse.json();
        
        // 计算成功率
        if (logs.length > 0) {
            const successCount = logs.filter(log => log.status === 'success').length;
            const successRate = (successCount / logs.length * 100).toFixed(1);
            document.getElementById('success-rate').textContent = `${successRate}%`;
        } else {
            document.getElementById('success-rate').textContent = 'N/A';
        }
        
        // 渲染最近日志
        const recentLogsElement = document.getElementById('recent-logs');
        recentLogsElement.innerHTML = '';
        
        for (const log of logs) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${log.id}</td>
                <td>${log.spider && log.spider.name ? log.spider.name : '未知爬虫'}</td>
                <td>${formatDateTime(log.start_time)}</td>
                <td>${log.end_time ? formatDateTime(log.end_time) : '-'}</td>
                <td>
                    <span class="badge ${getStatusBadgeClass(log.status)}">
                        ${getStatusText(log.status)}
                    </span>
                </td>
            `;
            recentLogsElement.appendChild(row);
        }
    } catch (error) {
        console.error('加载仪表盘数据失败:', error);
        showAlert('加载仪表盘数据失败', 'danger');
    }
}

// 分页配置
const paginationConfig = {
    spiders: {
        currentPage: 1,
        pageSize: 10,
        currentSearch: ''
    },
    schedules: {
        currentPage: 1,
        pageSize: 10
    },
    logs: {
        currentPage: 1,
        pageSize: 10
    }
};

// 加载爬虫列表
async function loadSpiders(page = 1, search = '') {
    try {
        paginationConfig.spiders.currentPage = page;
        paginationConfig.spiders.currentSearch = search;
        const skip = (page - 1) * paginationConfig.spiders.pageSize;
        const searchParams = new URLSearchParams({
            skip: skip.toString(),
            limit: paginationConfig.spiders.pageSize.toString(),
            ...(search && { search })
        });
        const response = await fetch(`/api/spiders/?${searchParams.toString()}`);
        const spiders = await response.json();
        
        const spiderListElement = document.getElementById('spider-list');
        spiderListElement.innerHTML = '';
        
        for (const spider of spiders) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${spider.id}</td>
                <td>${spider.name}</td>
                <td>${spider.description || '-'}</td>
                <td>${spider.script_path}</td>
                <td>
                    <span class="badge ${spider.is_active ? 'bg-success' : 'bg-danger'}">
                        ${spider.is_active ? '激活' : '禁用'}
                    </span>
                </td>
                <td>${formatDateTime(spider.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-primary edit-spider" data-id="${spider.id}">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-danger delete-spider" data-id="${spider.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            spiderListElement.appendChild(row);
        }

        // 添加分页控件
        updatePagination(spiders.length);
        
        // 重新绑定事件监听器
        setupSpiderEvents();
    } catch (error) {
        console.error('加载爬虫列表失败:', error);
        showAlert('加载爬虫列表失败', 'danger');
    }
}

// 更新分页控件
function updatePagination(totalItems) {
    const paginationElement = document.getElementById('spider-pagination');
    if (!paginationElement) {
        const paginationContainer = document.createElement('div');
        paginationContainer.className = 'mt-3';
        
        // 计算总页数
        const totalPages = Math.ceil(totalItems / paginationConfig.spiders.pageSize);
        const currentPage = paginationConfig.spiders.currentPage;
        
        let paginationHtml = `
            <nav aria-label="爬虫列表分页">
                <ul class="pagination justify-content-center">
                    <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="#" data-page="${currentPage - 1}" aria-label="上一页">
                            <span aria-hidden="true">&laquo;</span>
                        </a>
                    </li>
        `;
        
        // 显示页码按钮
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, startPage + 4);
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }
        
        paginationHtml += `
                    <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                        <a class="page-link" href="#" data-page="${currentPage + 1}" aria-label="下一页">
                            <span aria-hidden="true">&raquo;</span>
                        </a>
                    </li>
                </ul>
            </nav>
        `;
        
        paginationContainer.innerHTML = paginationHtml;
        document.querySelector('.table-responsive').after(paginationContainer);

        // 添加分页事件监听
        document.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                if (!this.parentElement.classList.contains('disabled')) {
                    const page = parseInt(this.getAttribute('data-page'));
                    loadSpiders(page, paginationConfig.spiders.currentSearch);
                }
            });
        });
    }
}

// 设置搜索功能
function setupSearchFunction() {
    const searchButton = document.getElementById('searchSpider');
    const searchInput = document.getElementById('spiderSearch');

    if (searchButton && searchInput) {
        // 搜索按钮点击事件
        searchButton.addEventListener('click', () => {
            loadSpiders(1, searchInput.value.trim());
        });

        // 输入框回车事件
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                loadSpiders(1, searchInput.value.trim());
            }
        });
    }
}

// 设置爬虫相关事件
function setupSpiderEvents() {
    // 添加爬虫按钮
    const addSpiderBtn = document.getElementById('btn-add-spider');
    if (addSpiderBtn) {
        addSpiderBtn.addEventListener('click', function() {
            // 重置表单
            document.getElementById('spiderForm').reset();
            document.getElementById('spiderId').value = '';
            document.getElementById('spiderModalTitle').textContent = '添加爬虫';
            
            // 显示模态框
            const spiderModal = new bootstrap.Modal(document.getElementById('spiderModal'));
            spiderModal.show();
        });
    }

    // 文件上传按钮事件
    const uploadScriptBtn = document.getElementById('uploadScript');
    if (uploadScriptBtn) {
        uploadScriptBtn.addEventListener('click', function() {
            document.getElementById('scriptFileInput').click();
        });
    }

    // 文件选择事件
    const scriptFileInput = document.getElementById('scriptFileInput');
    if (scriptFileInput) {
        scriptFileInput.addEventListener('change', async function(e) {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/api/spiders/upload-script', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        document.getElementById('spiderScriptPath').value = data.path;
                        showAlert('脚本上传成功', 'success');
                    } else {
                        const error = await response.json();
                        throw new Error(error.detail || '上传失败');
                    }
                } catch (error) {
                    console.error('上传脚本失败:', error);
                    showAlert(`上传脚本失败: ${error.message}`, 'danger');
                }
            }
        });
    }

    // 编辑脚本按钮事件
    const editScriptBtn = document.getElementById('editScript');
    if (editScriptBtn) {
        editScriptBtn.addEventListener('click', function() {
            const scriptPath = document.getElementById('spiderScriptPath').value;
            if (!scriptPath) {
                showAlert('请先指定脚本路径', 'warning');
                return;
            }
            
            scriptEditor.open(scriptPath, '', (path) => {
                document.getElementById('spiderScriptPath').value = path;
            });
        });
    }
    
    // 保存爬虫按钮
    const saveSpiderBtn = document.getElementById('saveSpider');
    if (saveSpiderBtn) {
        saveSpiderBtn.addEventListener('click', saveSpider);
    }
    
    // 编辑爬虫按钮
    document.querySelectorAll('.edit-spider').forEach(btn => {
        btn.addEventListener('click', function() {
            const spiderId = this.getAttribute('data-id');
            editSpider(spiderId);
        });
    });
    
    // 删除爬虫按钮
    document.querySelectorAll('.delete-spider').forEach(btn => {
        btn.addEventListener('click', function() {
            const spiderId = this.getAttribute('data-id');
            deleteSpider(spiderId);
        });
    });
}

// 保存爬虫
async function saveSpider() {
    try {
        const spiderId = document.getElementById('spiderId').value;
        const isUpdate = spiderId !== '';
        
        const spiderData = {
            name: document.getElementById('spiderName').value,
            description: document.getElementById('spiderDescription').value,
            script_path: document.getElementById('spiderScriptPath').value,
            is_active: document.getElementById('spiderIsActive').checked,
            user_id: 1  // 假设用户ID为1，实际应从登录用户获取
        };
        
        let response;
        if (isUpdate) {
            // 更新爬虫
            response = await fetch(`/api/spiders/${spiderId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(spiderData)
            });
        } else {
            // 创建爬虫
            response = await fetch('/api/spiders/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(spiderData)
            });
        }
        
        if (response.ok) {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('spiderModal')).hide();
            
            // 重新加载爬虫列表
            loadSpiders();
            
            showAlert(`爬虫${isUpdate ? '更新' : '创建'}成功`, 'success');
        } else {
            const error = await response.json();
            throw new Error(error.detail || '操作失败');
        }
    } catch (error) {
        console.error('保存爬虫失败:', error);
        showAlert(`保存爬虫失败: ${error.message}`, 'danger');
    }
}

// 编辑爬虫
async function editSpider(spiderId) {
    try {
        const response = await fetch(`/api/spiders/${spiderId}`);
        const spider = await response.json();
        
        // 填充表单
        document.getElementById('spiderId').value = spider.id;
        document.getElementById('spiderName').value = spider.name;
        document.getElementById('spiderDescription').value = spider.description || '';
        document.getElementById('spiderScriptPath').value = spider.script_path;
        document.getElementById('spiderIsActive').checked = spider.is_active;
        
        // 更新模态框标题
        document.getElementById('spiderModalTitle').textContent = '编辑爬虫';
        
        // 显示模态框
        const spiderModal = new bootstrap.Modal(document.getElementById('spiderModal'));
        spiderModal.show();
    } catch (error) {
        console.error('获取爬虫详情失败:', error);
        showAlert('获取爬虫详情失败', 'danger');
    }
}

// 删除爬虫
async function deleteSpider(spiderId) {
    if (confirm('确定要删除这个爬虫吗？相关的调度任务和执行日志也将被删除。')) {
        try {
            const response = await fetch(`/api/spiders/${spiderId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // 重新加载爬虫列表
                loadSpiders();
                
                showAlert('爬虫删除成功', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.detail || '删除失败');
            }
        } catch (error) {
            console.error('删除爬虫失败:', error);
            showAlert(`删除爬虫失败: ${error.message}`, 'danger');
        }
    }
}

// 加载调度任务列表
async function loadSchedules(page = 1) {
    try {
        paginationConfig.schedules.currentPage = page;
        const skip = (page - 1) * paginationConfig.schedules.pageSize;
        const searchParams = new URLSearchParams({
            skip: skip.toString(),
            limit: paginationConfig.schedules.pageSize.toString()
        });
        const response = await fetch(`/api/schedules/?${searchParams.toString()}`);
        const schedules = await response.json();
        
        const scheduleListElement = document.getElementById('schedule-list');
        scheduleListElement.innerHTML = '';
        
        // 获取爬虫信息
        const spidersResponse = await fetch('/api/spiders/');
        const spiders = await spidersResponse.json();
        const spiderMap = {};
        spiders.forEach(spider => {
            spiderMap[spider.id] = spider;
        });
        
        for (const schedule of schedules) {
            const spider = spiderMap[schedule.spider_id] || { name: '未知爬虫' };
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${schedule.id}</td>
                <td>${spider.name}</td>
                <td><code>${schedule.cron_expression}</code></td>
                <td>
                    <span class="badge ${schedule.is_active ? 'bg-success' : 'bg-danger'}">
                        ${schedule.is_active ? '激活' : '禁用'}
                    </span>
                </td>
                <td>${formatDateTime(schedule.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-primary edit-schedule" data-id="${schedule.id}">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-danger delete-schedule" data-id="${schedule.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            scheduleListElement.appendChild(row);
        }

        // 更新分页控件
        const paginationElement = document.getElementById('schedule-pagination');
        if (paginationElement) {
            const totalPages = Math.ceil(schedules.length / paginationConfig.schedules.pageSize);
            const currentPage = paginationConfig.schedules.currentPage;
            
            let paginationHtml = `
                <nav aria-label="调度规则分页">
                    <ul class="pagination justify-content-center">
                        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                            <a class="page-link" href="#" data-page="${currentPage - 1}" aria-label="上一页">
                                <span aria-hidden="true">&laquo;</span>
                            </a>
                        </li>`;
            
            for (let i = 1; i <= totalPages; i++) {
                paginationHtml += `
                    <li class="page-item ${i === currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" data-page="${i}">${i}</a>
                    </li>`;
            }
            
            paginationHtml += `
                        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                            <a class="page-link" href="#" data-page="${currentPage + 1}" aria-label="下一页">
                                <span aria-hidden="true">&raquo;</span>
                            </a>
                        </li>
                    </ul>
                </nav>`;
            
            paginationElement.innerHTML = paginationHtml;
            
            // 添加分页事件监听
            paginationElement.querySelectorAll('.page-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const page = parseInt(this.getAttribute('data-page'));
                    if (!isNaN(page) && page > 0) {
                        loadSchedules(page);
                    }
                });
            });
        }

        // 重新绑定调度任务的事件监听器
        setupScheduleEvents();
    } catch (error) {
        console.error('加载调度任务列表失败:', error);
        showAlert('加载调度任务列表失败', 'danger');
    }
}

// 设置调度任务相关事件
function setupScheduleEvents() {
    // 添加调度任务按钮
    const addScheduleBtn = document.getElementById('btn-add-schedule');
    if (addScheduleBtn) {
        addScheduleBtn.addEventListener('click', async function() {
            // 重置表单
            document.getElementById('scheduleForm').reset();
            document.getElementById('scheduleId').value = '';
            document.getElementById('scheduleModalTitle').textContent = '添加调度任务';
            
            // 加载爬虫选项
            await loadSpiderOptions();
            
            // 显示模态框
            const scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));
            scheduleModal.show();
        });
    }
    
    // 保存调度任务按钮
    const saveScheduleBtn = document.getElementById('saveSchedule');
    if (saveScheduleBtn) {
        saveScheduleBtn.addEventListener('click', saveSchedule);
    }
    
    // 编辑调度任务按钮
    document.querySelectorAll('.edit-schedule').forEach(btn => {
        btn.addEventListener('click', function() {
            const scheduleId = this.getAttribute('data-id');
            editSchedule(scheduleId);
        });
    });
    
    // 删除调度任务按钮
    document.querySelectorAll('.delete-schedule').forEach(btn => {
        btn.addEventListener('click', function() {
            const scheduleId = this.getAttribute('data-id');
            deleteSchedule(scheduleId);
        });
    });
}

// 加载爬虫选项
async function loadSpiderOptions() {
    try {
        const response = await fetch('/api/spiders/');
        const spiders = await response.json();
        
        const selectElement = document.getElementById('scheduleSpiderId');
        selectElement.innerHTML = '';
        
        for (const spider of spiders) {
            if (spider.is_active) {
                const option = document.createElement('option');
                option.value = spider.id;
                option.textContent = spider.name;
                selectElement.appendChild(option);
            }
        }
    } catch (error) {
        console.error('加载爬虫选项失败:', error);
        showAlert('加载爬虫选项失败', 'danger');
    }
}

// 保存调度任务
async function saveSchedule() {
    try {
        const scheduleId = document.getElementById('scheduleId').value;
        const isUpdate = scheduleId !== '';
        
        const scheduleData = {
            spider_id: parseInt(document.getElementById('scheduleSpiderId').value),
            cron_expression: document.getElementById('scheduleCronExpression').value,
            is_active: document.getElementById('scheduleIsActive').checked
        };
        
        let response;
        if (isUpdate) {
            // 更新调度任务
            response = await fetch(`/api/schedules/${scheduleId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(scheduleData)
            });
        } else {
            // 创建调度任务
            response = await fetch('/api/schedules/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(scheduleData)
            });
        }
        
        if (response.ok) {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('scheduleModal')).hide();
            
            // 重新加载调度任务列表
            loadSchedules();
            
            showAlert(`调度任务${isUpdate ? '更新' : '创建'}成功`, 'success');
        } else {
            const error = await response.json();
            throw new Error(error.detail || '操作失败');
        }
    } catch (error) {
        console.error('保存调度任务失败:', error);
        showAlert(`保存调度任务失败: ${error.message}`, 'danger');
    }
}

// 编辑调度任务
async function editSchedule(scheduleId) {
    try {
        const response = await fetch(`/api/schedules/${scheduleId}`);
        const schedule = await response.json();
        
        // 加载爬虫选项
        await loadSpiderOptions();
        
        // 填充表单
        document.getElementById('scheduleId').value = schedule.id;
        document.getElementById('scheduleSpiderId').value = schedule.spider_id;
        document.getElementById('scheduleCronExpression').value = schedule.cron_expression;
        document.getElementById('scheduleIsActive').checked = schedule.is_active;
        
        // 更新模态框标题
        document.getElementById('scheduleModalTitle').textContent = '编辑调度任务';
        
        // 显示模态框
        const scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));
        scheduleModal.show();
    } catch (error) {
        console.error('获取调度任务详情失败:', error);
        showAlert('获取调度任务详情失败', 'danger');
    }
}

// 删除调度任务
async function deleteSchedule(scheduleId) {
    if (confirm('确定要删除这个调度任务吗？')) {
        try {
            const response = await fetch(`/api/schedules/${scheduleId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // 重新加载调度任务列表
                loadSchedules();
                
                showAlert('调度任务删除成功', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.detail || '删除失败');
            }
        } catch (error) {
            console.error('删除调度任务失败:', error);
            showAlert(`删除调度任务失败: ${error.message}`, 'danger');
        }
    }
}

// 加载环境列表
async function loadEnvironments(page = 1) {
    try {
        paginationConfig.environments = paginationConfig.environments || {
            currentPage: 1,
            pageSize: 10
        };
        paginationConfig.environments.currentPage = page;
        const skip = (page - 1) * paginationConfig.environments.pageSize;
        const response = await fetch(`/api/environments/?skip=${skip}&limit=${paginationConfig.environments.pageSize}`);
        const environments = await response.json();
        
        const environmentListElement = document.getElementById('environment-list');
        environmentListElement.innerHTML = '';
        
        for (const env of environments) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${env.id}</td>
                <td>${env.name}</td>
                <td>${env.description || '-'}</td>
                <td>${formatDateTime(env.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-info view-variables" data-id="${env.id}" data-name="${env.name}">
                        <i class="bi bi-list"></i> 变量
                    </button>
                    <button class="btn btn-sm btn-primary edit-environment" data-id="${env.id}">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-danger delete-environment" data-id="${env.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            environmentListElement.appendChild(row);
        }

        // 更新分页控件
        updateEnvironmentPagination(environments.length);
        
        // 重新绑定事件
        setupEnvironmentEvents();
    } catch (error) {
        console.error('加载环境列表失败:', error);
        showAlert('加载环境列表失败', 'danger');
    }
}

// 设置环境相关事件
function setupEnvironmentEvents() {
    // 添加环境按钮
    const addEnvironmentBtn = document.getElementById('btn-add-environment');
    if (addEnvironmentBtn) {
        addEnvironmentBtn.addEventListener('click', function() {
            // 重置表单
            document.getElementById('environmentForm').reset();
            document.getElementById('environmentId').value = '';
            document.getElementById('environmentModalTitle').textContent = '添加环境';
            
            // 显示模态框
            const environmentModal = new bootstrap.Modal(document.getElementById('environmentModal'));
            environmentModal.show();
        });
    }
    
    // 保存环境按钮
    const saveEnvironmentBtn = document.getElementById('saveEnvironment');
    if (saveEnvironmentBtn) {
        saveEnvironmentBtn.addEventListener('click', saveEnvironment);
    }
    
    // 编辑环境按钮
    document.querySelectorAll('.edit-environment').forEach(btn => {
        btn.addEventListener('click', function() {
            const environmentId = this.getAttribute('data-id');
            editEnvironment(environmentId);
        });
    });
    
    // 删除环境按钮
    document.querySelectorAll('.delete-environment').forEach(btn => {
        btn.addEventListener('click', function() {
            const environmentId = this.getAttribute('data-id');
            deleteEnvironment(environmentId);
        });
    });
    
    // 查看变量按钮
    document.querySelectorAll('.view-variables').forEach(btn => {
        btn.addEventListener('click', function() {
            const environmentId = this.getAttribute('data-id');
            const environmentName = this.getAttribute('data-name');
            viewEnvironmentVariables(environmentId, environmentName);
        });
    });
}

// 当前日志分页状态
let logPagination = {
    currentPage: 1,
    pageSize: 10,
    totalPages: 1,
    totalRecords: 0
};

// 加载执行日志列表
async function loadLogs(page = 1) {
    try {
        paginationConfig.logs.currentPage = page;
        const pageSize = paginationConfig.logs.pageSize;
        const skip = (page - 1) * pageSize;
        
        // 获取日志数据
        const response = await fetch(`/api/execution-logs/?skip=${skip}&limit=${pageSize}`);
        const logs = await response.json();
        
        // 获取日志总数
        const countResponse = await fetch('/api/execution-logs/count');
        const countData = await countResponse.json();
        paginationConfig.logs.totalRecords = countData.total;
        paginationConfig.logs.totalPages = Math.ceil(countData.total / pageSize);
        
        const logListElement = document.getElementById('log-list');
        logListElement.innerHTML = '';
        
        for (const log of logs) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${log.id}</td>
                <td>${log.spider && log.spider.name ? log.spider.name : '未知爬虫'}</td>
                <td>${formatDateTime(log.start_time)}</td>
                <td>${log.end_time ? formatDateTime(log.end_time) : '-'}</td>
                <td>
                    <span class="badge ${getStatusBadgeClass(log.status)}">
                        ${getStatusText(log.status)}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-info view-log" data-id="${log.id}">
                        <i class="bi bi-file-text"></i> 查看
                    </button>
                </td>
            `;
            logListElement.appendChild(row);
        }
        
        // 设置查看日志按钮事件
        document.querySelectorAll('.view-log').forEach(btn => {
            btn.addEventListener('click', function() {
                const logId = this.getAttribute('data-id');
                viewLogDetail(logId);
            });
        });
        
        // 更新分页控件
        updateLogPagination(paginationConfig.logs.totalRecords);
    } catch (error) {
        console.error('加载执行日志列表失败:', error);
        showAlert('加载执行日志列表失败', 'danger');
    }
}

// 更新日志分页控件
function updateLogPagination(totalItems) {
    const paginationElement = document.getElementById('log-pagination');
    if (!paginationElement) return;

    const totalPages = Math.ceil(totalItems / paginationConfig.logs.pageSize);
    const currentPage = paginationConfig.logs.currentPage;

    let paginationHtml = `
        <nav aria-label="执行日志分页">
            <ul class="pagination justify-content-center">
                <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                    <a class="page-link" href="#" data-page="${currentPage - 1}">
                        <i class="bi bi-chevron-left"></i>
                    </a>
                </li>
    `;

    // 显示页码
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            paginationHtml += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            paginationHtml += `
                <li class="page-item disabled">
                    <span class="page-link">...</span>
                </li>
            `;
        }
    }

    paginationHtml += `
                <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                    <a class="page-link" href="#" data-page="${currentPage + 1}">
                        <i class="bi bi-chevron-right"></i>
                    </a>
                </li>
            </ul>
        </nav>
    `;

    paginationElement.innerHTML = paginationHtml;

    // 添加分页按钮点击事件
    paginationElement.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-page'));
            if (!isNaN(page) && page > 0) {
                loadLogs(page);
            }
        });
    });
}

// 查看日志详情
async function viewLogDetail(logId) {
    try {
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

        console.log(log);
        
        // 清理已存在的模态框
        const existingModal = document.getElementById('logDetailModal');
        if (existingModal) {
            existingModal.parentNode.removeChild(existingModal);
            bootstrap.Modal.getInstance(existingModal)?.dispose();
        }

        // 创建新的模态框容器
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
                                <strong>爬虫名称:</strong> ${log.spider && typeof log.spider === 'object' && log.spider.name ? log.spider.name : '未知爬虫'}
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

        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer);
        
        // 显示模态框
        const logDetailModal = new bootstrap.Modal(document.getElementById('logDetailModal'));
        logDetailModal.show();
    } catch (error) {
        console.error('获取日志详情失败:', error);
        showAlert('获取日志详情失败', 'danger');
    }
}

// 格式化日期时间
function formatDateTime(dateTimeStr) {
    const date = new Date(dateTimeStr);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 获取状态对应的徽章类
function getStatusBadgeClass(status) {
    switch (status) {
        case 'success':
            return 'bg-success';
        case 'failed':
            return 'bg-danger';
        case 'running':
            return 'bg-primary';
        default:
            return 'bg-secondary';
    }
}

// 获取状态文本
function getStatusText(status) {
    switch (status) {
        case 'success':
            return '成功';
        case 'failed':
            return '失败';
        case 'running':
            return '运行中';
        default:
            return '未知';
    }
}

// 显示提示信息
function showAlert(message, type = 'info') {
    // 创建提示元素
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type} alert-dismissible fade show`;
    alertElement.setAttribute('role', 'alert');
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // 添加到页面顶部
    const contentArea = document.getElementById('content-area');
    contentArea.insertBefore(alertElement, contentArea.firstChild);
    
    // 5秒后自动关闭
    setTimeout(() => {
        if (alertElement.parentNode) {
            const bsAlert = new bootstrap.Alert(alertElement);
            bsAlert.close();
        }
    }, 5000);
}

// 更新环境分页控件
function updateEnvironmentPagination(totalItems) {
    const paginationElement = document.getElementById('environment-pagination');
    if (!paginationElement) return;
    
    // 计算总页数
    const totalPages = Math.ceil(totalItems / paginationConfig.environments.pageSize);
    const currentPage = paginationConfig.environments.currentPage;
    
    // 生成分页HTML
    let paginationHtml = '<nav><ul class="pagination justify-content-center">';
    
    // 上一页按钮
    paginationHtml += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${currentPage - 1}" aria-label="上一页">
                <span aria-hidden="true">&laquo;</span>
            </a>
        </li>
    `;
    
    // 页码按钮
    for (let i = 1; i <= totalPages; i++) {
        paginationHtml += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>
        `;
    }
    
    // 下一页按钮
    paginationHtml += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${currentPage + 1}" aria-label="下一页">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>
    `;
    
    paginationHtml += '</ul></nav>';
    paginationElement.innerHTML = paginationHtml;
    
    // 添加分页事件监听
    paginationElement.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-page'));
            if (page && page !== currentPage) {
                loadEnvironments(page);
            }
        });
    });
}

// 保存环境变量
async function saveEnvironment() {
    try {
        const environmentName = document.getElementById('environmentName').value;
        if (!environmentName.trim()) {
            throw new Error('环境名称不能为空');
        }

        const environmentId = document.getElementById('environmentId').value;
        const isUpdate = environmentId !== '';
        
        const environmentData = {
            name: environmentName,
            description: document.getElementById('environmentDescription').value,
            user_id: 1  // 添加必需的user_id字段
        };
        
        let response;
        if (isUpdate) {
            // 更新环境变量
            response = await fetch(`/api/environments/${environmentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(environmentData)
            });
        } else {
            // 创建环境变量
            response = await fetch('/api/environments/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(environmentData)
            });
        }
        
        if (response.ok) {
            // 关闭模态框
            bootstrap.Modal.getInstance(document.getElementById('environmentModal')).hide();
            
            // 重新加载环境变量列表
            loadEnvironments();
            
            showAlert(`环境变量${isUpdate ? '更新' : '创建'}成功`, 'success');
        } else {
            const error = await response.json();
            if (response.status === 422) {
                const validationErrors = error.detail || [];
                const errorMessage = Array.isArray(validationErrors) 
                    ? validationErrors.map(err => err.msg).join('\n')
                    : '数据验证失败';
                throw new Error(errorMessage);
            }
            throw new Error(error.detail || '操作失败');
        }
    } catch (error) {
        console.error('保存环境变量失败:', error);
        showAlert(`保存环境变量失败: ${error.message}`, 'danger');
    }
}

// 编辑环境变量
async function editEnvironment(environmentId) {
    try {
        const response = await fetch(`/api/environments/${environmentId}`);
        const environment = await response.json();
        
        // 填充表单
        document.getElementById('environmentId').value = environment.id;
        document.getElementById('environmentName').value = environment.name;
        document.getElementById('environmentValue').value = environment.value;
        document.getElementById('environmentDescription').value = environment.description || '';
        
        // 更新模态框标题
        document.getElementById('environmentModalTitle').textContent = '编辑环境变量';
        
        // 显示模态框
        const environmentModal = new bootstrap.Modal(document.getElementById('environmentModal'));
        environmentModal.show();
    } catch (error) {
        console.error('获取环境变量详情失败:', error);
        showAlert('获取环境变量详情失败', 'danger');
    }
}

// 删除环境变量
async function deleteEnvironment(environmentId) {
    if (confirm('确定要删除这个环境变量吗？')) {
        try {
            const response = await fetch(`/api/environments/${environmentId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // 重新加载环境变量列表
                loadEnvironments();
                
                showAlert('环境变量删除成功', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.detail || '删除失败');
            }
        } catch (error) {
            console.error('删除环境变量失败:', error);
            showAlert(`删除环境变量失败: ${error.message}`, 'danger');
        }
    }
}

// 查看环境变量详情
async function viewEnvironmentVariables(environmentId, environmentName) {
    try {
        const response = await fetch(`/api/environments/${environmentId}/variables`);
        const variables = await response.json();
        
        // 创建模态框
        const modalHtml = `
            <div class="modal fade" id="variablesModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">环境变量: ${environmentName}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="table-responsive">
                                <table class="table table-striped table-sm">
                                    <thead>
                                        <tr>
                                            <th>名称</th>
                                            <th>值</th>
                                            <th>描述</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${variables.length > 0 ? variables.map(v => `
                                            <tr>
                                                <td>${v.name}</td>
                                                <td>${v.value}</td>
                                                <td>${v.description || '-'}</td>
                                            </tr>
                                        `).join('') : '<tr><td colspan="3" class="text-center">无变量</td></tr>'}
                                    </tbody>
                                </table>
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
        const variablesModal = new bootstrap.Modal(document.getElementById('variablesModal'));
        variablesModal.show();
        
        // 模态框关闭时移除元素
        document.getElementById('variablesModal').addEventListener('hidden.bs.modal', function() {
            document.body.removeChild(modalContainer);
        });
    } catch (error) {
        console.error('获取环境变量详情失败:', error);
        showAlert('获取环境变量详情失败', 'danger');
    }
}

async function pollTaskStatus(taskId) {
    // 轮询间隔和超时设置
    const POLL_INTERVAL = 2000;
    const TIMEOUT = 60000;
    const startTime = Date.now();

    while (Date.now() - startTime < TIMEOUT) {
        const response = await fetch(`/api/spiders/test/status/${taskId}`);
        if (!response.ok) {
            throw new Error('获取任务状态失败');
        }
        
        const status = await response.json();
        
        // 更新进度显示
        updateProgress(status);

        if (status.state === 'SUCCESS') return status;
        if (status.state === 'FAILURE') throw new Error(status.result || '任务执行失败');

        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
    }
    throw new Error('任务执行超时');
}

function updateProgress(status) {
    const progressBar = document.getElementById('testProgressBar');
    const progressLabel = document.getElementById('testProgressLabel');
    
    if (progressBar && progressLabel) {
        progressBar.style.width = `${status.progress || 0}%`;
        progressBar.setAttribute('aria-valuenow', status.progress || 0);
        progressLabel.textContent = status.message || '正在执行...';
    }
}

function handleTestResult(result) {
    const resultContainer = document.getElementById('testResultContainer');
    if (resultContainer) {
        resultContainer.innerHTML = `
            <div class="alert alert-success mt-3">
                <h5>测试成功</h5>
                <p>执行时长: ${result.duration}s</p>
                <p>获取数据量: ${result.count}</p>
                <pre class="bg-dark text-white p-3 mt-2">${JSON.stringify(result.sample_data, null, 2)}</pre>
            </div>
        `;
    }
}