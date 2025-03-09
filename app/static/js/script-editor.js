// 脚本编辑器组件
class ScriptEditor {
    constructor() {
        this.editor = null;
        this.currentPath = null;
        this.modal = null;
        this.saveCallback = null;
        this.monacoLoaded = false;
        this.initialized = false; // 新增初始化状态标识
        this.initPromise = null; // 新增初始化Promise
    }

    // 初始化编辑器
    async init() {
        if (this.initPromise) return this.initPromise;
        
        this.initPromise = new Promise(async (resolve) => {
            // 创建编辑器模态框
            const modalHtml = `
                <div class="modal fade" id="scriptEditorModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">编辑脚本</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body p-0">
                                <div id="monacoEditor" style="height: 500px;"></div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                                <button type="button" class="btn btn-primary" id="saveScript">保存</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // 加载Monaco Editor
            await this.loadMonacoEditor();
            
            // 初始化模态框
            this.modal = new bootstrap.Modal(document.getElementById('scriptEditorModal'));
            
            // 绑定保存按钮事件
            document.getElementById('saveScript').addEventListener('click', () => this.save());
            
            this.initialized = true;
            resolve();
        });
        
        return this.initPromise;
    }

    // 打开编辑器
    async open(path, content = '', onSave = null) {
        await this.init();
        
        if (!this.editor) {
            throw new Error('编辑器尚未初始化完成');
        }

        this.currentPath = path;
        this.saveCallback = onSave;

        // 等待编辑器初始化完成
        if (!this.editor) {
            await this.init();
        }

        // 如果提供了内容，设置到编辑器中
        if (content) {
            this.editor.setValue(content);
        } else {
            // 否则尝试从服务器加载内容
            try {
                // 使用encodeURIComponent对路径进行编码
                const formattedPath = path.split('/').pop();
                const encodedPath = encodeURIComponent(formattedPath);
                const response = await fetch(`/api/spiders/script-content?path=${encodedPath}`);
                const text = await response.text();
                if (response.ok) {
                    this.editor.setValue(text.replace(/\\n/g, '\n'));
                } else {
                    try {
                        const errorData = JSON.parse(text);
                        throw new Error(errorData.detail || '加载失败');
                    } catch (jsonError) {
                        throw new Error(text || '加载失败');
                    }
                }
            } catch (error) {
                console.error('加载脚本内容失败:', error);
                this.editor.setValue('# 加载脚本内容失败\n# ' + error.message);
            }
        }

        // 显示模态框
        this.modal.show();
    }

    // 加载外部脚本
    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // 加载Monaco Editor
    async loadMonacoEditor() {
        if (this.monacoLoaded) return;
        
        await this.loadScript('https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs/loader.min.js');
        
        if (!window.monacoConfig) {
            require.config({
                paths: {
                    'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs'
                }
            });
            window.monacoConfig = true;
        }

        await new Promise((resolve) => {
            require(['vs/editor/editor.main'], () => {
                this.editor = monaco.editor.create(document.getElementById('monacoEditor'), {
                    language: 'python',
                    theme: 'vs-dark',
                    automaticLayout: true,
                    minimap: { enabled: true },
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    wrappingIndent: 'indent',
                    fontSize: 14,
                    tabSize: 4,
                    insertSpaces: true,
                    formatOnPaste: true,
                    formatOnType: true,
                    formatOnSave: true,
                    autoFormat: true
                });
                this.monacoLoaded = true;
                this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF, () => {
                    this.editor.getAction('editor.action.formatDocument').run();
                });
                resolve();
            });
        });
    }

    // 保存内容
    async save() {
        if (!this.currentPath) return;

        const content = this.editor.getValue();
        
        try {
            const response = await fetch('/api/spiders/save-script', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    path: this.currentPath,
                    content: content
                })
            });

            if (response.ok) {
                // 调用保存回调
                if (this.saveCallback) {
                    this.saveCallback(this.currentPath, content);
                }
                
                // 关闭模态框
                this.modal.hide();
                
                // 显示成功提示
                showAlert('脚本保存成功', 'success');
            } else {
                try {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '保存失败');
                } catch (jsonError) {
                    const text = await response.text();
                    throw new Error(text || '保存失败');
                }
            }
        } catch (error) {
            console.error('保存脚本失败:', error);
            showAlert(`保存脚本失败: ${error.message}`, 'danger');
        }
    }

    // 关闭编辑器
    close() {
        if (this.modal) {
            this.modal.hide();
        }
    }
}