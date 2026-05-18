// NextStudio Frontend JavaScript

// ==================== State ====================
let currentRunId = null;
let eventSource = null;
let isRunning = false;

// Streaming buffer: accumulates raw markdown tokens before flush
let _bufText = '';        // raw text waiting to be flushed
let _bufTimer = null;
let _bufFlushMs = 150;    // flush interval (ms)

// ==================== Navigation ====================
function toggleGroup(groupId) {
    const group = document.getElementById(`group-${groupId}`);
    const chevron = document.getElementById(`chevron-${groupId}`);

    if (group.style.display === 'none') {
        group.style.display = 'block';
        chevron.style.transform = 'rotate(0deg)';
    } else {
        group.style.display = 'none';
        chevron.style.transform = 'rotate(-90deg)';
    }
}

function filterResources() {
    const search = document.getElementById('resource-search')?.value.toLowerCase() || '';
    const items = document.querySelectorAll('.resource-item');

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(search)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// ==================== Toast ====================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== API ====================
const API = {
    baseUrl: '/api',

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            method: options.method || 'GET',
            headers: { 'Content-Type': 'application/json' },
            ...options,
        };

        if (options.body) {
            config.body = JSON.stringify(options.body);
        }

        const response = await fetch(url, config);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        return data;
    },

    async healthCheck() { return this.request('/health'); },
    async run(message, useMock = true) {
        return this.request('/runs', {
            method: 'POST',
            body: { message, use_mock: useMock },
        });
    },
    streamEvents(runId) {
        return new EventSource(`${this.baseUrl}/runs/${runId}/events`);
    },
    async abortRun(runId) {
        return this.request(`/runs/${runId}/abort`, { method: 'POST' });
    },
    async getBundle() { return this.request('/bundle'); },
    async getStats() { return this.request('/stats'); },
    async uploadOntology(formData) {
        const response = await fetch(`${this.baseUrl}/ontologies/upload`, {
            method: 'POST',
            body: formData,
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }
        return data;
    },
};

// ==================== Markdown ====================
/** Parse markdown text to HTML using marked (if loaded) or plain text fallback. */
function renderMarkdown(text) {
    if (!text) return '';
    if (typeof window.marked !== 'undefined') {
        return window.marked.parse(text);
    }
    // Fallback: escape HTML and render basic markdown with regex
    let html = String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Code blocks
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.+?)_/g, '<em>$1</em>');
    // Strikethrough
    html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    // Horizontal rule
    html = html.replace(/^---$/gm, '<hr>');
    // Unordered lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)+/g, '<ul>$&</ul>');
    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    // Paragraphs
    const paras = html.split(/\n{2,}/);
    html = paras.map(p => {
        p = p.trim();
        if (!p) return '';
        if (/<(h[1-6]|ul|ol|pre|hr|blockquote)/.test(p)) return p;
        return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    }).join('');

    // Clean up wrappers
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>(<h[1-3]>)/g, '$1');
    html = html.replace(/(<\/h[1-3]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<(?:ul|ol|pre|blockquote)>)/gi, '$1');
    html = html.replace(/(<\/(?:ul|ol|pre|blockquote)>)<\/p>/gi, '$1');
    html = html.replace(/<p>(<hr>)<\/p>/g, '$1');
    return html;
}

// ==================== Streaming Buffer ====================

/** Append raw markdown delta to the flush buffer. */
function appendToLastAssistant(newContent) {
    _bufText += newContent;
    if (!_bufTimer) {
        _bufTimer = setInterval(_flushBuffer, _bufFlushMs);
    }
}

/** Flush accumulated text to the live assistant bubble. */
function _flushBuffer() {
    const raw = _bufText;
    if (!raw) return;

    const container = document.getElementById('chat-messages');
    if (!container) { _bufText = ''; return; }

    let bubble = container.querySelector('.assistant-bubble');
    if (!bubble) {
        bubble = _createAssistantBubble(container);
    }

    bubble.innerHTML = renderMarkdown(raw) +
        '<span class="typewriter-cursor" aria-hidden="true">▋</span>';
    container.scrollTop = container.scrollHeight;
}

/** Final flush: render complete markdown, remove cursor. */
function _flushBufferFinal() {
    clearInterval(_bufTimer);
    _bufTimer = null;

    const raw = _bufText;
    _bufText = '';

    const container = document.getElementById('chat-messages');
    if (!container || !raw) return;

    let bubble = container.querySelector('.assistant-bubble');
    if (!bubble) {
        bubble = _createAssistantBubble(container);
    }

    bubble.innerHTML = renderMarkdown(raw);
    container.scrollTop = container.scrollHeight;
}

function _createAssistantBubble(container) {
    const div = document.createElement('div');
    div.className = 'flex items-start gap-3 chat-message';
    div.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
            <i class="fas fa-robot text-blue-600 text-sm"></i>
        </div>
        <div class="flex-1">
            <div class="font-medium text-sm text-slate-700 mb-1.5">采购助手</div>
            <div class="p-4 bg-slate-50 rounded-2xl rounded-tl-none assistant-bubble message-content"></div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div.querySelector('.assistant-bubble');
}

// ==================== Messages ====================
function addMessage(role, content) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    // Stop any active stream
    clearInterval(_bufTimer);
    _bufTimer = null;
    _bufText = '';

    const div = document.createElement('div');
    div.className = 'flex items-start gap-3 chat-message';

    if (role === 'user') {
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0 ml-auto">
                <i class="fas fa-user text-white text-xs"></i>
            </div>
            <div class="flex-1">
                <div class="font-medium text-sm text-slate-700 mb-1.5 text-right">你</div>
                <div class="p-4 bg-blue-500 text-white rounded-2xl rounded-tr-none message-content ml-auto" style="max-width: 80%;">
                    ${renderMarkdown(content)}
                </div>
            </div>
        `;
    } else {
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <i class="fas fa-robot text-blue-600 text-sm"></i>
            </div>
            <div class="flex-1">
                <div class="font-medium text-sm text-slate-700 mb-1.5">采购助手</div>
                <div class="p-4 bg-slate-50 rounded-2xl rounded-tl-none message-content" style="max-width: 80%;">
                    ${renderMarkdown(content)}
                </div>
            </div>
        `;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function clearChat() {
    clearInterval(_bufTimer);
    _bufTimer = null;
    _bufText = '';

    const container = document.getElementById('chat-messages');
    if (container) container.innerHTML = '';

    addMessage('assistant', `您好！我是**采购助手**，可以帮您：

- **查询物料** — 物料主数据和库存
- **查询供应商** — 供应商信息
- **查询订单** — 采购订单状态
- **数据分析** — 需求排名、供应商绩效

请问有什么可以帮您？`);
}

function exportChat() {
    const messages = document.querySelectorAll('#chat-messages .chat-message');
    const content = Array.from(messages).map(msg => {
        const roleEl = msg.querySelector('.fa-user');
        const role = roleEl ? 'User' : 'Assistant';
        const text = msg.querySelector('.message-content')?.textContent || '';
        return `[${role}]\n${text}`;
    }).join('\n\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('对话已导出', 'success');
}

// ==================== Chat ====================
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const abortBtn = document.getElementById('abort-btn');
    const useMockCheckbox = document.getElementById('use-mock');

    const message = input.value.trim();
    if (!message || isRunning) return;

    addMessage('user', message);
    input.value = '';

    isRunning = true;
    sendBtn.classList.add('hidden');
    abortBtn.classList.remove('hidden');
    input.disabled = true;

    // Auto-detect mock vs real LLM
    const useMock = useMockCheckbox ? useMockCheckbox.checked : true;

    if (!useMock) {
        // Check if LLM is configured
        try {
            const health = await API.healthCheck();
            if (!health.llm_configured) {
                showToast('LLM 未配置。使用 Mock 模式。', 'info');
                useMockCheckbox.checked = true;
            }
        } catch (_) {}
    }

    showThinking('正在理解您的问题...');

    const timeline = document.getElementById('execution-timeline');
    if (timeline) {
        timeline.style.display = 'block';
        timeline.classList.remove('hidden');
    }
    const tc = document.getElementById('timeline-content');
    if (tc) tc.innerHTML = '';

    try {
        const { run_id, use_mock } = await API.run(message, useMock);
        currentRunId = run_id;

        // Update status indicator
        const statusEl = document.getElementById('llm-status');
        if (statusEl) {
            if (use_mock) {
                statusEl.innerHTML = `
                    <span class="w-2 h-2 rounded-full bg-amber-500"></span>
                    <span class="text-xs text-amber-600">Mock 模式</span>
                `;
            } else {
                statusEl.innerHTML = `
                    <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    <span class="text-xs text-green-600">LLM 运行中</span>
                `;
            }
        }

        streamEvents(run_id);
    } catch (error) {
        showToast('发送失败: ' + error.message, 'error');
        isRunning = false;
        sendBtn.classList.remove('hidden');
        abortBtn.classList.add('hidden');
        input.disabled = false;
        hideThinking();
    }
}

function sendExample(message) {
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = message;
        sendMessage();
    }
}

function abortMessage() {
    if (currentRunId && isRunning) {
        API.abortRun(currentRunId);
        showToast('正在中止...', 'info');
        const input = document.getElementById('chat-input');
        if (input) input.disabled = false;
    }
}

function streamEvents(runId) {
    if (eventSource) eventSource.close();

    eventSource = API.streamEvents(runId);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleEvent(data);
    };

    eventSource.onerror = () => {
        isRunning = false;
        _flushBufferFinal();
        const sendBtn = document.getElementById('send-btn');
        const abortBtn = document.getElementById('abort-btn');
        const input = document.getElementById('chat-input');
        if (sendBtn) sendBtn.classList.remove('hidden');
        if (abortBtn) abortBtn.classList.add('hidden');
        if (input) input.disabled = false;
        hideThinking();
        showToast('连接中断，请重试', 'error');
    };
}

function handleEvent(event) {
    switch (event.type) {
        case 'run_started':
            updateTimeline('start', { message: event.data.message });
            break;

        case 'intent':
            updateThinkingText('识别意图: ' + event.data.type);
            updateTimeline('intent', { type: event.data.type, confidence: event.data.confidence });
            break;

        case 'prelude_delta':
            hideThinking();
            if (event.data.content) appendToLastAssistant(event.data.content);
            break;

        case 'thinking':
            hideThinking();
            updateThinkingText(event.data.thought || '正在思考...');
            break;

        case 'step_start':
            hideThinking();
            updateThinkingText('执行: ' + (event.data.tool || event.data.action || '...'));
            updateTimeline('step_start', event.data);
            break;

        case 'step_end':
            updateTimeline('step_end', event.data);
            break;

        case 'hitl_pending':
            updateTimeline('hitl_pending', event.data);
            addHITLPending(event.data);
            break;

        case 'auto_approved':
            updateTimeline('auto_approved', event.data);
            break;

        case 'analysis':
            updateTimeline('analysis', event.data);
            break;

        case 'plan':
            updateTimeline('plan', event.data);
            break;

        case 'skill_call':
            updateTimeline('skill_call', event.data);
            break;

        case 'skill_result':
            updateTimeline('skill_result', event.data);
            break;

        case 'final_delta':
            hideThinking();
            appendToLastAssistant(event.data.content);
            break;

        case 'done':
        case 'completed':
            isRunning = false;
            hideThinking();
            _flushBufferFinal();
            {
                const sendBtn = document.getElementById('send-btn');
                const abortBtn = document.getElementById('abort-btn');
                const input = document.getElementById('chat-input');
                if (sendBtn) sendBtn.classList.remove('hidden');
                if (abortBtn) abortBtn.classList.add('hidden');
                if (input) input.disabled = false;
            }
            showToast('运行完成', 'success');
            break;

        case 'error':
            hideThinking();
            _flushBufferFinal();
            isRunning = false;
            {
                const sb = document.getElementById('send-btn');
                const ab = document.getElementById('abort-btn');
                const inp = document.getElementById('chat-input');
                if (sb) sb.classList.remove('hidden');
                if (ab) ab.classList.add('hidden');
                if (inp) inp.disabled = false;
            }
            showToast('错误: ' + (event.data.error || 'Unknown error'), 'error');
            break;

        case 'aborted':
            hideThinking();
            _flushBufferFinal();
            isRunning = false;
            showToast('运行已中止', 'info');
            break;

        case 'stream_end':
            if (eventSource) eventSource.close();
            break;
    }
}

function showThinking(text) {
    const indicator = document.getElementById('thinking-indicator');
    const textEl = document.getElementById('thinking-text');
    if (indicator) {
        indicator.style.display = 'flex';
        indicator.classList.remove('hidden');
    }
    if (textEl) textEl.textContent = text;
}

function updateThinkingText(text) {
    const textEl = document.getElementById('thinking-text');
    if (textEl) textEl.textContent = text;
}

function hideThinking() {
    const indicator = document.getElementById('thinking-indicator');
    if (indicator) {
        indicator.style.display = 'none';
        indicator.classList.add('hidden');
    }
}

// ==================== Timeline ====================
function updateTimeline(type, data) {
    const container = document.getElementById('timeline-content');
    if (!container) return;

    switch (type) {
        case 'start':
            container.innerHTML = `
                <div class="flex items-center gap-2 text-xs text-slate-600">
                    <i class="fas fa-play-circle text-green-500"></i>
                    <span>开始处理: ${data.message}</span>
                </div>`;
            break;

        case 'intent':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs text-slate-600">
                    <i class="fas fa-bullseye text-purple-500"></i>
                    <span>意图识别: ${data.type}</span>
                    <span class="text-slate-400">(置信度: ${(data.confidence * 100).toFixed(0)}%)</span>
                </div>`;
            break;

        case 'step_start':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs text-slate-600 step-running" id="step-running">
                    <i class="fas fa-spinner fa-spin text-amber-500"></i>
                    <span>执行: ${data.tool || data.action}</span>
                    ${data.args ? `<span class="text-slate-400">${JSON.stringify(data.args)}</span>` : ''}
                </div>`;
            break;

        case 'step_end': {
            const runningEl = document.getElementById('step-running');
            if (runningEl) {
                const ok = data.status === 'ok';
                runningEl.innerHTML = `
                    <i class="fas fa-${ok ? 'check-circle text-green-500' : 'times-circle text-red-500'}"></i>
                    <span>${data.tool || data.action}:</span>
                    <span class="${ok ? 'text-green-600' : 'text-red-600'}">${data.status}</span>
                    ${data.output ? `<span class="text-slate-400 ml-2">[已返回数据]</span>` : ''}`;
                runningEl.id = '';
                runningEl.className = 'flex items-center gap-2 text-xs text-slate-600';
            }
            break;
        }

        case 'analysis':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs text-slate-600">
                    <i class="fas fa-chart-pie text-blue-500"></i>
                    <span>分析结果:</span>
                    <span class="text-green-600">自动审批 ${data.summary?.auto_count || 0} 单</span>
                    <span class="text-amber-600">待人工审批 ${data.summary?.hitl_count || 0} 单</span>
                    <span class="text-slate-400">阈值: ¥${data.summary?.threshold || 1000}</span>
                </div>`;
            break;

        case 'hitl_pending':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs text-amber-600">
                    <i class="fas fa-user-clock text-amber-500"></i>
                    <span>待人工审批: ${data.request_no}</span>
                    <span class="font-medium">¥${(data.amount || 0).toLocaleString()}</span>
                </div>`;
            break;

        case 'auto_approved':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs text-green-600">
                    <i class="fas fa-check-circle text-green-500"></i>
                    <span>自动通过: ${data.request_no}</span>
                </div>`;
            break;

        case 'plan':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs text-purple-600">
                    <i class="fas fa-tasks text-purple-500"></i>
                    <span>执行计划: ${data.tasks?.length || 0} 个任务</span>
                    <span class="text-slate-400">自动审批阈值: ¥${data.auto_approve_threshold}</span>
                </div>`;
            break;

        case 'skill_call':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs text-slate-500">
                    <i class="fas fa-cog text-slate-400"></i>
                    <span>内部函数: ${data.skill_name || data.skill}</span>
                    ${data.internal ? '<span class="badge badge-slate text-xs ml-1">内部</span>' : ''}
                </div>`;
            break;

        case 'skill_result':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs text-slate-500">
                    <i class="fas fa-check text-slate-400"></i>
                    <span>日期解析: ${data.result?.date_from} 至 ${data.result?.date_to}</span>
                    ${data.result?.is_today ? '<span class="badge badge-green text-xs ml-1">今日</span>' : ''}
                </div>`;
            break;

        case 'approval_completed':
            container.innerHTML += `
                <div class="flex items-center gap-2 text-xs ${data.action === 'approved' ? 'text-green-600' : 'text-red-600'}">
                    <i class="fas fa-${data.action === 'approved' ? 'check-circle' : 'times-circle'} text-${data.action === 'approved' ? 'green' : 'red'}-500"></i>
                    <span>人工审批完成: ${data.request_no || ''} → ${data.action}</span>
                </div>`;
            break;
    }
}

// ==================== LLM Test ====================
async function testLlm() {
    const health = await API.healthCheck();
    if (health.llm_configured) {
        showToast(`LLM 已配置: ${health.llm_model || 'deepseek-chat'}`, 'success');
    } else {
        showToast('LLM 未配置。请设置 LLM_API_KEY 环境变量。', 'error');
    }
}

// ==================== LLM Status ====================
function updateLlmStatus(health) {
    const statusEl = document.getElementById('llm-status');
    if (!statusEl) return;

    if (health.llm_configured) {
        statusEl.innerHTML = `
            <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span class="text-xs text-green-600">${health.llm_model || 'LLM'} 已连接</span>
        `;
    } else {
        statusEl.innerHTML = `
            <span class="w-2 h-2 rounded-full bg-amber-500"></span>
            <span class="text-xs text-amber-600">Mock 模式</span>
        `;
    }
}

// ==================== Ontology Upload ====================
let _selectedFile = null;

function showUploadModal() {
    document.getElementById('upload-modal').classList.remove('hidden');
}

function closeUploadModal() {
    document.getElementById('upload-modal').classList.add('hidden');
    clearFile();
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        _selectedFile = file;
        const preview = document.getElementById('file-preview');
        const dropZone = document.getElementById('drop-zone');
        const fileName = document.getElementById('file-name');
        const fileSize = document.getElementById('file-size');
        const uploadBtn = document.getElementById('upload-btn');

        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);

        dropZone.classList.add('hidden');
        preview.classList.remove('hidden');
        uploadBtn.disabled = false;
    }
}

function clearFile() {
    _selectedFile = null;
    const preview = document.getElementById('file-preview');
    const dropZone = document.getElementById('drop-zone');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('ontology-file-input');
    const nameInput = document.getElementById('ontology-name-input');

    if (preview) preview.classList.add('hidden');
    if (dropZone) dropZone.classList.remove('hidden');
    if (uploadBtn) uploadBtn.disabled = true;
    if (fileInput) fileInput.value = '';
    if (nameInput) nameInput.value = '';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function uploadOntology() {
    if (!_selectedFile) return;

    const uploadBtn = document.getElementById('upload-btn');
    const nameInput = document.getElementById('ontology-name-input');

    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>上传中...';

    try {
        const formData = new FormData();
        formData.append('file', _selectedFile);
        if (nameInput.value.trim()) {
            formData.append('name', nameInput.value.trim());
        }

        const response = await fetch('/api/ontologies/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.error) {
            throw new Error(result.error);
        }

        let message = `本体 "${result.name || result.domain}" 上传成功！`;
        if (result.is_osi_format) {
            message = `OSI 本体 "${result.name || result.domain}" 上传成功！已转换 ${result.entity_count} 个数据集。`;
        }
        if (result.warning) {
            message += ' (' + result.warning + ')';
        }

        showToast(message, 'success');
        closeUploadModal();

        // Show OSI summary if applicable
        if (result.is_osi_format && result.osi_summary) {
            showOSISummary(result.osi_summary);
        }

    } catch (error) {
        showToast('上传失败: ' + error.message, 'error');
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fas fa-upload mr-1"></i>上传';
    }
}

function showOSISummary(summary) {
    // Create a simple info modal for OSI summary
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[70vh] overflow-hidden flex flex-col">
            <div class="flex items-center justify-between p-4 border-b">
                <h3 class="font-semibold text-slate-800">OSI 本体摘要</h3>
                <button onclick="this.closest('.fixed').remove()" class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors">✕</button>
            </div>
            <div class="flex-1 overflow-y-auto p-4">
                <pre class="text-sm text-slate-600 whitespace-pre-wrap font-mono">${escapeHtml(summary)}</pre>
            </div>
            <div class="flex justify-end p-4 border-t bg-slate-50">
                <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">确定</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

// Drag and drop support
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-blue-400', 'bg-blue-50');
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('border-blue-400', 'bg-blue-50');
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-400', 'bg-blue-50');
            const file = e.dataTransfer.files[0];
            if (file && (file.name.endsWith('.yaml') || file.name.endsWith('.yml') || file.name.endsWith('.json'))) {
                const dt = new DataTransfer();
                dt.items.add(file);
                document.getElementById('ontology-file-input').files = dt.files;
                handleFileSelect({ target: { files: [file] } });
            } else {
                showToast('请上传 .yaml, .yml 或 .json 文件', 'error');
            }
        });
    }
});

// ==================== Ontology Modal ====================
async function loadOntologyRaw() {
    try {
        const response = await API.request('/ontologies/raw');
        document.getElementById('ontology-yaml-content').textContent = response.yaml;
        document.getElementById('ontology-raw-modal').classList.remove('hidden');
    } catch (error) {
        showToast('加载失败: ' + error.message, 'error');
    }
}

function closeOntologyRawModal() {
    document.getElementById('ontology-raw-modal').classList.add('hidden');
}

// ==================== Intent Management ====================
let _currentIntents = [];
let _editingIntentType = null;

async function loadIntents() {
    try {
        const response = await API.request('/intents');
        _currentIntents = response.intents || [];
        renderIntentList(_currentIntents);
    } catch (error) {
        showToast('加载意图失败: ' + error.message, 'error');
    }
}

function renderIntentList(intents) {
    const container = document.getElementById('intent-list');
    if (!container) return;

    if (intents.length === 0) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-bullseye"></i><p>暂无意图定义</p></div>';
        return;
    }

    container.innerHTML = intents.map(i => `
        <div class="p-4 border border-slate-200 rounded-lg border-l-4 border-l-purple-500 hover:border-purple-300 hover:shadow-sm transition-all intent-item" data-type="${i.type}">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div>
                        <div class="font-medium text-slate-800">${escapeHtml(i.name || i.type)}</div>
                        <div class="text-xs text-slate-500 mt-1">${escapeHtml(i.description || '')}</div>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <span class="badge badge-purple">${i.priority || 50} 分</span>
                    <span class="badge badge-${i.enabled ? 'green' : 'red'}">${i.enabled ? '已启用' : '已禁用'}</span>
                    <button onclick="editIntent('${i.type}')" class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors" title="编辑">
                        <i class="fas fa-pen text-xs"></i>
                    </button>
                    <button onclick="deleteIntent('${i.type}')" class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors" title="删除">
                        <i class="fas fa-trash text-xs"></i>
                    </button>
                </div>
            </div>
            <div class="mt-3 flex flex-wrap gap-1 items-center">
                <span class="text-xs text-slate-400">关键词:</span>
                ${i.keywords && i.keywords.length > 0
                    ? i.keywords.map(kw => `<span class="badge badge-slate">${escapeHtml(kw)}</span>`).join('')
                    : '<span class="text-xs text-slate-400">无</span>'}
            </div>
            <div class="mt-2 flex flex-wrap gap-1 items-center">
                <span class="text-xs text-slate-400">操作:</span>
                ${i.actions && i.actions.length > 0
                    ? i.actions.map(a => `<span class="font-mono text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">${escapeHtml(a)}</span>`).join('')
                    : '<span class="text-xs text-slate-400">无</span>'}
            </div>
            ${i.examples && i.examples.length > 0 ? `
            <div class="mt-2 flex flex-wrap gap-1 items-center">
                <span class="text-xs text-slate-400">示例:</span>
                ${i.examples.slice(0, 3).map(ex => `<span class="text-xs text-slate-600 bg-slate-50 px-2 py-0.5 rounded italic">"${escapeHtml(ex)}"</span>`).join('')}
                ${i.examples.length > 3 ? `<span class="text-xs text-slate-400">+${i.examples.length - 3}...</span>` : ''}
            </div>
            ` : ''}
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showCreateIntentModal() {
    _editingIntentType = null;
    document.getElementById('intent-modal-title').textContent = '新建意图';
    document.getElementById('intent-original-type').value = '';
    document.getElementById('intent-type').value = '';
    document.getElementById('intent-type').disabled = false;
    document.getElementById('intent-name').value = '';
    document.getElementById('intent-description').value = '';
    document.getElementById('intent-keywords').value = '';
    document.getElementById('intent-actions').value = '';
    document.getElementById('intent-priority').value = '50';
    document.getElementById('intent-enabled').checked = true;
    document.getElementById('intent-examples').value = '';
    document.getElementById('intent-modal').classList.remove('hidden');
}

function editIntent(type) {
    const intent = _currentIntents.find(i => i.type === type);
    if (!intent) {
        showToast('意图不存在', 'error');
        return;
    }

    _editingIntentType = type;
    document.getElementById('intent-modal-title').textContent = '编辑意图';
    document.getElementById('intent-original-type').value = type;
    document.getElementById('intent-type').value = intent.type;
    document.getElementById('intent-type').disabled = false; // Allow editing type
    document.getElementById('intent-name').value = intent.name || '';
    document.getElementById('intent-description').value = intent.description || '';
    document.getElementById('intent-keywords').value = (intent.keywords || []).join(', ');
    document.getElementById('intent-actions').value = (intent.actions || []).join(', ');
    document.getElementById('intent-priority').value = intent.priority || 50;
    document.getElementById('intent-enabled').checked = intent.enabled !== false;
    document.getElementById('intent-examples').value = (intent.examples || []).join('\n');
    document.getElementById('intent-modal').classList.remove('hidden');
}

function closeIntentModal() {
    document.getElementById('intent-modal').classList.add('hidden');
    _editingIntentType = null;
}

async function saveIntent() {
    const type = document.getElementById('intent-type').value.trim();
    const name = document.getElementById('intent-name').value.trim();
    const description = document.getElementById('intent-description').value.trim();
    const keywordsStr = document.getElementById('intent-keywords').value.trim();
    const actionsStr = document.getElementById('intent-actions').value.trim();
    const priority = parseInt(document.getElementById('intent-priority').value) || 50;
    const enabled = document.getElementById('intent-enabled').checked;
    const examplesStr = document.getElementById('intent-examples').value.trim();

    if (!type) {
        showToast('请输入意图类型', 'warning');
        return;
    }
    if (!name) {
        showToast('请输入意图名称', 'warning');
        return;
    }

    const keywords = keywordsStr ? keywordsStr.split(',').map(k => k.trim()).filter(k => k) : [];
    const actions = actionsStr ? actionsStr.split(',').map(a => a.trim()).filter(a => a) : [];
    const examples = examplesStr ? examplesStr.split('\n').map(e => e.trim()).filter(e => e) : [];

    const intent = {
        type,
        name,
        description,
        keywords,
        actions,
        priority,
        enabled,
        examples,
    };

    try {
        const isNew = !_editingIntentType;
        const method = isNew ? 'POST' : 'PUT';
        const url = isNew ? '/api/intents' : `/api/intents/${_editingIntentType}`;

        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(intent)
        });

        const result = await response.json();

        if (result.error) {
            throw new Error(result.error);
        }

        closeIntentModal();
        showToast(isNew ? '意图创建成功' : '意图更新成功', 'success');

        // Reload intents
        await loadIntents();

    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

async function deleteIntent(type) {
    if (!confirm(`确定要删除意图 "${type}" 吗？`)) {
        return;
    }

    try {
        const response = await fetch(`/api/intents/${type}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.error) {
            throw new Error(result.error);
        }

        showToast('意图已删除', 'success');
        await loadIntents();

    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// ==================== Ontology Parse ====================
let _parsedIntents = [];

async function parseOntology() {
    const modal = document.getElementById('parse-modal');
    const content = document.getElementById('parse-content');
    const summary = document.getElementById('parse-summary');
    const kgStats = document.getElementById('parse-kg-stats');

    modal.classList.remove('hidden');
    content.innerHTML = `
        <div class="text-center py-8">
            <div class="animate-spin w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p class="text-slate-500">正在解析本体，提取意图...</p>
        </div>
    `;
    summary.textContent = '';
    kgStats.textContent = '';

    try {
        // Get the ontology YAML
        const rawResponse = await API.request('/ontologies/raw');
        const yamlContent = rawResponse.yaml;

        // Call parse API
        const response = await fetch('/api/ontologies/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ yaml_content: yamlContent, ontology_id: 'current' })
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Store parsed intents
        _parsedIntents = data.intents || [];

        // Update summary
        summary.textContent = data.summary || `提取了 ${_parsedIntents.length} 个意图`;

        // Update KG stats
        if (data.kg_stats) {
            kgStats.textContent = `知识图谱: ${data.kg_stats.entity_count || 0} 实体, ${data.kg_stats.action_count || 0} 操作, ${data.kg_stats.edge_count || 0} 关系`;
        }

        // Render intents
        if (_parsedIntents.length === 0) {
            content.innerHTML = `
                <div class="text-center py-8">
                    <i class="fas fa-inbox text-4xl text-slate-300 mb-4"></i>
                    <p class="text-slate-500">未能从本体中提取意图</p>
                    <p class="text-xs text-slate-400 mt-2">${data.summary || ''}</p>
                </div>
            `;
        } else {
            content.innerHTML = _parsedIntents.map((intent, idx) => `
                <div class="p-4 border border-slate-200 rounded-lg hover:border-purple-300 hover:shadow-sm transition-all mb-3">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="font-mono text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded">${intent.type}</span>
                                <span class="text-sm font-medium text-slate-800">${intent.name}</span>
                            </div>
                            <p class="text-xs text-slate-500 mb-2">${intent.description || '无描述'}</p>

                            <div class="mb-2">
                                <span class="text-xs text-slate-400">关键词: </span>
                                <div class="flex flex-wrap gap-1 mt-1">
                                    ${(intent.keywords || []).map(kw => `<span class="badge badge-slate text-xs">${kw}</span>`).join('')}
                                </div>
                            </div>

                            <div>
                                <span class="text-xs text-slate-400">关联操作: </span>
                                <div class="flex flex-wrap gap-1 mt-1">
                                    ${(intent.actions || []).map(a => `<span class="font-mono text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">${a}</span>`).join('')}
                                </div>
                            </div>

                            ${intent.examples && intent.examples.length > 0 ? `
                            <div class="mt-2">
                                <span class="text-xs text-slate-400">示例问法: </span>
                                <div class="flex flex-wrap gap-1 mt-1">
                                    ${intent.examples.map(ex => `<span class="text-xs text-slate-600 bg-slate-50 px-2 py-0.5 rounded italic">"${ex}"</span>`).join('')}
                                </div>
                            </div>
                            ` : ''}
                        </div>
                        <label class="flex items-center gap-2">
                            <input type="checkbox" id="intent-${idx}" checked
                                   class="w-4 h-4 text-purple-600 rounded border-slate-300 focus:ring-purple-500">
                            <span class="text-xs text-slate-500">启用</span>
                        </label>
                    </div>
                </div>
            `).join('');
        }

    } catch (error) {
        content.innerHTML = `
            <div class="text-center py-8">
                <i class="fas fa-exclamation-triangle text-4xl text-red-300 mb-4"></i>
                <p class="text-red-500">解析失败</p>
                <p class="text-xs text-slate-400 mt-2">${error.message}</p>
            </div>
        `;
    }
}

function closeParseModal() {
    document.getElementById('parse-modal').classList.add('hidden');
}

async function applyParsedIntents() {
    if (_parsedIntents.length === 0) {
        showToast('没有可应用的意图', 'warning');
        return;
    }

    // Collect selected intents
    const selectedIntents = _parsedIntents.filter((_, idx) => {
        const checkbox = document.getElementById(`intent-${idx}`);
        return checkbox && checkbox.checked;
    });

    if (selectedIntents.length === 0) {
        showToast('请至少选择一个意图', 'warning');
        return;
    }

    try {
        showToast('正在应用意图...', 'info');

        let successCount = 0;
        let errorCount = 0;

        for (const intent of selectedIntents) {
            const response = await fetch('/api/intents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: intent.type,
                    name: intent.name,
                    description: intent.description,
                    keywords: intent.keywords || [],
                    actions: intent.actions || [],
                    examples: intent.examples || [],
                    priority: 50,
                    enabled: true,
                })
            });

            if (response.ok) {
                successCount++;
            } else {
                const result = await response.json();
                if (result.error && result.error.includes('already exists')) {
                    // Skip if already exists
                } else {
                    errorCount++;
                }
            }
        }

        closeParseModal();

        if (errorCount > 0) {
            showToast(`已添加 ${successCount} 个意图，${errorCount} 个失败`, 'warning');
        } else {
            showToast(`已应用 ${successCount} 个意图`, 'success');
        }

        // Reload intents
        await loadIntents();

    } catch (error) {
        showToast('应用失败: ' + error.message, 'error');
    }
}

async function loadIntents() {
    try {
        const response = await API.request('/intents');
        // You could update the intent list UI here
        console.log('Intents loaded:', response.intents);
    } catch (error) {
        console.error('Failed to load intents:', error);
    }
}

// ==================== Init ====================
document.addEventListener('DOMContentLoaded', async () => {
    // Warm up chat with welcome message if container is empty
    const chatContainer = document.getElementById('chat-messages');
    if (chatContainer && chatContainer.children.length === 0) {
        clearChat();
    }

    // Health check and update LLM status
    try {
        const health = await API.healthCheck();
        updateLlmStatus(health);
    } catch (_) {
        const statusEl = document.getElementById('llm-status');
        if (statusEl) {
            statusEl.innerHTML = `
                <span class="w-2 h-2 rounded-full bg-red-400"></span>
                <span class="text-xs text-slate-400">连接异常</span>
            `;
        }
    }
});

// ==================== HITL 审批 ====================

// 存储待审批的申请
let _pendingApprovals = [];

function addHITLPending(data) {
    // 确保每个申请单只添加一次
    const exists = _pendingApprovals.find(p => p.request_no === data.request_no);
    if (!exists) {
        _pendingApprovals.push(data);
    }
    renderPendingApprovals();
}

function renderPendingApprovals() {
    // 创建或更新 HITL 面板
    let panel = document.getElementById('hitl-panel');
    if (!panel) {
        panel = createHITLPanel();
        document.body.appendChild(panel);
    }

    const container = document.getElementById('hitl-pending-list');
    if (!container) return;

    if (_pendingApprovals.length === 0) {
        panel.classList.add('hidden');
        return;
    }

    panel.classList.remove('hidden');

    // 按申请单号分组，渲染每个申请单
    container.innerHTML = _pendingApprovals.map((req, reqIdx) => `
        <div class="request-card" data-request-no="${req.request_no}">
            <!-- 申请单头部 -->
            <div class="request-header">
                <div class="request-info">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="badge badge-amber">待审批</span>
                        <span class="font-mono text-sm font-medium text-slate-800">${req.request_no}</span>
                        <span class="text-xs text-slate-400">${req.request_date || ''}</span>
                    </div>
                    <div class="text-sm text-slate-600">
                        <i class="fas fa-user mr-1"></i>${req.requester?.name || '-'}
                        <span class="mx-2">|</span>
                        <i class="fas fa-building mr-1"></i>${req.requester?.department || '-'}
                    </div>
                </div>
                <div class="request-amount">
                    <div class="text-xs text-slate-400 mb-1">申请总额</div>
                    <div class="text-xl font-bold text-amber-600">¥${(req.amount || 0).toLocaleString('zh-CN', {minimumFractionDigits: 2})}</div>
                </div>
            </div>

            <!-- 申请标题 -->
            <div class="request-title">
                <i class="fas fa-clipboard-list text-slate-400 mr-2"></i>
                ${req.title || '未命名申请'}
            </div>

            ${req.description ? `
            <div class="request-description">
                ${req.description}
            </div>
            ` : ''}

            <!-- 明细行列表 -->
            <div class="line-items">
                <div class="line-items-header">
                    <span class="text-xs font-medium text-slate-500">采购明细（${req.line_items?.length || 0} 项）</span>
                </div>
                ${(req.line_items || []).map((line, lineIdx) => `
                    <div class="line-item ${line.status === 'approved' ? 'line-approved' : ''} ${line.status === 'rejected' ? 'line-rejected' : ''}"
                         data-line-id="${line.item_id}" data-request-no="${req.request_no}">
                        <div class="line-item-header">
                            <div class="flex items-center gap-2">
                                <span class="line-no">${line.line_no}</span>
                                ${line.status === 'pending' ? '<span class="badge badge-amber badge-xs">待审</span>' : ''}
                                ${line.status === 'approved' ? '<span class="badge badge-green badge-xs">已通过</span>' : ''}
                                ${line.status === 'rejected' ? '<span class="badge badge-red badge-xs">已拒绝</span>' : ''}
                            </div>
                            <span class="line-amount">¥${(line.line_amount || 0).toLocaleString('zh-CN', {minimumFractionDigits: 2})}</span>
                        </div>
                        <div class="line-item-body">
                            <div class="line-name">${line.item_name}</div>
                            <div class="line-detail">
                                ${line.quantity} ${line.unit || '项'} × ¥${(line.unit_price || 0).toLocaleString('zh-CN', {minimumFractionDigits: 2})}
                            </div>
                        </div>
                        ${line.status === 'pending' ? `
                        <div class="line-item-actions">
                            <input type="text" class="line-comment-input"
                                   id="comment-${line.item_id}"
                                   placeholder="审批意见（可选）" />
                            <div class="line-btn-group">
                                <button onclick="handleLineApprove('${req.request_no}', '${line.item_id}')"
                                        class="btn-line-approve">
                                    <i class="fas fa-check"></i> 通过
                                </button>
                                <button onclick="handleLineReject('${req.request_no}', '${line.item_id}')"
                                        class="btn-line-reject">
                                    <i class="fas fa-times"></i> 拒绝
                                </button>
                            </div>
                        </div>
                        ` : `
                        <div class="line-item-footer">
                            <span class="text-xs ${line.status === 'approved' ? 'text-green-600' : 'text-red-600'}">
                                ${line.status === 'approved' ? '✓ 已通过' : '✗ 已拒绝'}
                            </span>
                        </div>
                        `}
                    </div>
                `).join('')}
            </div>

            <!-- 申请单操作栏 -->
            <div class="request-footer">
                <div class="request-progress">
                    <span class="text-xs text-slate-500">
                        进度: ${(req.line_items || []).filter(l => l.status !== 'pending').length}/${(req.line_items || []).length} 项已审批
                    </span>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${((req.line_items || []).filter(l => l.status !== 'pending').length / Math.max((req.line_items || []).length, 1) * 100)}%"></div>
                    </div>
                </div>
                <div class="request-actions">
                    <button onclick="handleRequestApproveAll('${req.request_no}')"
                            class="btn-request-approve ${(req.line_items || []).every(l => l.status === 'pending') ? '' : 'hidden'}">
                        <i class="fas fa-check-double mr-1"></i>全部通过
                    </button>
                    <button onclick="handleRequestRejectAll('${req.request_no}')"
                            class="btn-request-reject ${(req.line_items || []).some(l => l.status === 'pending') ? '' : 'hidden'}">
                        <i class="fas fa-ban mr-1"></i>全部拒绝
                    </button>
                </div>
            </div>

            <!-- 提示信息 -->
            <div class="request-note">
                <i class="fas fa-info-circle text-amber-400 mr-1"></i>
                ${req.threshold_note || '金额超过阈值，需要人工审批'}
            </div>
        </div>
    `).join('');

    // 更新计数
    document.getElementById('hitl-count').textContent = _pendingApprovals.length;
}

function createHITLPanel() {
    const panel = document.createElement('div');
    panel.id = 'hitl-panel';
    panel.className = 'fixed right-4 top-20 w-[420px] max-h-[calc(100vh-8rem)] bg-white rounded-xl shadow-2xl border border-slate-200 z-40 hidden flex flex-col';
    panel.innerHTML = `
        <div class="flex items-center justify-between p-4 border-b border-slate-200 bg-gradient-to-r from-amber-50 to-white">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                    <i class="fas fa-clipboard-check text-amber-600"></i>
                </div>
                <div>
                    <h3 class="font-semibold text-slate-800">待审批采购申请</h3>
                    <span id="hitl-count" class="text-sm text-amber-600 font-medium">0 单</span>
                </div>
            </div>
            <button onclick="hideHITLPanel()" class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div id="hitl-pending-list" class="flex-1 overflow-y-auto p-4 space-y-4">
        </div>
        <div class="p-4 border-t border-slate-200 bg-slate-50 rounded-b-xl">
            <div class="flex items-center justify-between text-sm text-slate-500 mb-3">
                <span><i class="fas fa-info-circle mr-1"></i>审批规则：金额 ≤ ¥1,000 自动通过</span>
                <span class="font-medium text-amber-600">金额 > ¥1,000 需人工审批</span>
            </div>
            <div class="flex gap-3">
                <button onclick="handleApproveAll()" class="flex-1 py-3 px-6 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white rounded-xl font-semibold transition-all shadow-lg shadow-green-500/30 flex items-center justify-center gap-2">
                    <i class="fas fa-check-double"></i>
                    一键通过全部
                </button>
                <button onclick="hideHITLPanel()" class="py-3 px-6 bg-white hover:bg-slate-100 text-slate-600 border border-slate-200 rounded-xl font-medium transition-colors">
                    稍后处理
                </button>
            </div>
        </div>
    `;
    return panel;
}

function showHITLPanel() {
    const panel = document.getElementById('hitl-panel');
    if (panel) {
        panel.classList.remove('hidden');
        document.getElementById('hitl-count').textContent = _pendingApprovals.length;
    }
}

function hideHITLPanel() {
    const panel = document.getElementById('hitl-panel');
    if (panel) {
        panel.classList.add('hidden');
    }
}

async function handleHITLApprove(requestNo) {
    // 对整个申请单进行审批（批准所有行）
    const req = _pendingApprovals.find(p => p.request_no === requestNo);
    if (!req) return;

    try {
        const response = await fetch('/api/approvals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_no: requestNo,
                action: 'approve',
                comment: '整单审批通过',
            }),
        });

        const result = await response.json();

        if (result.success) {
            showToast(`已批准 ${requestNo}`, 'success');
            _pendingApprovals = _pendingApprovals.filter(p => p.request_no !== requestNo);
            renderPendingApprovals();

            addMessage('assistant', `✅ **审批通过**\n\n申请单 **${requestNo}** 已批准。`);

            updateTimeline('approval_completed', { request_no: requestNo, action: 'approved' });
        } else {
            showToast(result.error || '审批失败', 'error');
        }
    } catch (error) {
        showToast('审批请求失败: ' + error.message, 'error');
    }
}

async function handleHITLReject(requestNo) {
    const req = _pendingApprovals.find(p => p.request_no === requestNo);
    if (!req) return;

    const commentInput = document.getElementById(`comment-${requestNo}`);
    const comment = commentInput ? commentInput.value : '';

    if (!comment) {
        showToast('请输入拒绝理由', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/approvals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_no: requestNo,
                action: 'reject',
                comment: comment,
            }),
        });

        const result = await response.json();

        if (result.success) {
            showToast(`已拒绝 ${requestNo}`, 'success');
            _pendingApprovals = _pendingApprovals.filter(p => p.request_no !== requestNo);
            renderPendingApprovals();

            addMessage('assistant', `❌ **审批拒绝**\n\n申请单 **${requestNo}** 已拒绝。\n\n**拒绝理由**: ${comment}`);

            updateTimeline('approval_completed', { request_no: requestNo, action: 'rejected' });
        } else {
            showToast(result.error || '审批失败', 'error');
        }
    } catch (error) {
        showToast('审批请求失败: ' + error.message, 'error');
    }
}

// ========== 明细行级别审批 ==========

async function handleLineApprove(requestNo, lineId) {
    const commentInput = document.getElementById(`comment-${lineId}`);
    const comment = commentInput ? commentInput.value : '';

    try {
        const response = await fetch('/api/approvals/line', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_no: requestNo,
                line_id: lineId,
                action: 'approve',
                comment: comment,
            }),
        });

        const result = await response.json();

        if (result.success) {
            showToast(`已通过第 ${lineId.split('-').pop()} 行`, 'success');

            // 更新本地状态
            updateLineStatus(requestNo, lineId, 'approved', comment);

            addMessage('assistant', `✅ **明细行审批通过**\n\n申请单 **${requestNo}** 第 ${lineId.split('-').pop()} 行已批准${comment ? `（意见：${comment}）` : ''}。`);
        } else {
            showToast(result.error || '审批失败', 'error');
        }
    } catch (error) {
        showToast('审批请求失败: ' + error.message, 'error');
    }
}

async function handleLineReject(requestNo, lineId) {
    const commentInput = document.getElementById(`comment-${lineId}`);
    const comment = commentInput ? commentInput.value : '';

    if (!comment) {
        showToast('请输入拒绝理由', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/approvals/line', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_no: requestNo,
                line_id: lineId,
                action: 'reject',
                comment: comment,
            }),
        });

        const result = await response.json();

        if (result.success) {
            showToast(`已拒绝第 ${lineId.split('-').pop()} 行`, 'success');

            // 更新本地状态
            updateLineStatus(requestNo, lineId, 'rejected', comment);

            addMessage('assistant', `❌ **明细行审批拒绝**\n\n申请单 **${requestNo}** 第 ${lineId.split('-').pop()} 行已拒绝。\n\n**拒绝理由**: ${comment}`);
        } else {
            showToast(result.error || '审批失败', 'error');
        }
    } catch (error) {
        showToast('审批请求失败: ' + error.message, 'error');
    }
}

function updateLineStatus(requestNo, lineId, status, comment = '') {
    const req = _pendingApprovals.find(p => p.request_no === requestNo);
    if (!req || !req.line_items) return;

    const line = req.line_items.find(l => l.item_id === lineId);
    if (line) {
        line.status = status;
        line.comment = comment;
    }

    // 重新渲染
    renderPendingApprovals();
}

async function handleRequestApproveAll(requestNo) {
    const req = _pendingApprovals.find(p => p.request_no === requestNo);
    if (!req) return;

    // 逐行批准
    const pendingLines = (req.line_items || []).filter(l => l.status === 'pending');
    let successCount = 0;

    for (const line of pendingLines) {
        try {
            const response = await fetch('/api/approvals/line', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    request_no: requestNo,
                    line_id: line.item_id,
                    action: 'approve',
                    comment: '批量审批通过',
                }),
            });

            const result = await response.json();
            if (result.success) {
                successCount++;
                updateLineStatus(requestNo, line.item_id, 'approved', '批量审批通过');
            }
        } catch (e) {
            console.error(`Failed to approve line ${line.item_id}:`, e);
        }
    }

    if (successCount === pendingLines.length) {
        showToast(`已全部通过 ${successCount} 项`, 'success');
        addMessage('assistant', `✅ **批量审批完成**\n\n申请单 **${requestNo}** 的 ${successCount} 项明细已全部批准。`);
    }
}

async function handleRequestRejectAll(requestNo) {
    const req = _pendingApprovals.find(p => p.request_no === requestNo);
    if (!req) return;

    const comment = '整单拒绝';

    // 逐行拒绝
    const pendingLines = (req.line_items || []).filter(l => l.status === 'pending');
    let successCount = 0;

    for (const line of pendingLines) {
        try {
            const response = await fetch('/api/approvals/line', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    request_no: requestNo,
                    line_id: line.item_id,
                    action: 'reject',
                    comment: comment,
                }),
            });

            const result = await response.json();
            if (result.success) {
                successCount++;
                updateLineStatus(requestNo, line.item_id, 'rejected', comment);
            }
        } catch (e) {
            console.error(`Failed to reject line ${line.item_id}:`, e);
        }
    }

    if (successCount > 0) {
        showToast(`已拒绝全部 ${successCount} 项`, 'success');
        addMessage('assistant', `❌ **批量拒绝完成**\n\n申请单 **${requestNo}** 的 ${successCount} 项明细已全部拒绝。`);
    }
}

async function handleApproveAll() {
    if (_pendingApprovals.length === 0) {
        showToast('没有待审批的申请', 'info');
        return;
    }

    const results = [];

    // 遍历所有申请单
    for (const req of _pendingApprovals) {
        // 遍历所有待审批的明细行
        const pendingLines = (req.line_items || []).filter(l => l.status === 'pending');

        for (const line of pendingLines) {
            try {
                const response = await fetch('/api/approvals/line', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        request_no: req.request_no,
                        line_id: line.item_id,
                        action: 'approve',
                        comment: '批量审批通过',
                    }),
                });

                const result = await response.json();
                if (result.success) {
                    results.push({ request_no: req.request_no, line_id: line.item_id });
                    updateLineStatus(req.request_no, line.item_id, 'approved', '批量审批通过');
                }
            } catch (e) {
                console.error(`Failed to approve ${req.request_no}/${line.item_id}:`, e);
            }
        }
    }

    if (results.length > 0) {
        showToast(`已批准 ${results.length} 个明细项`, 'success');

        addMessage('assistant', `✅ **批量审批完成**\n\n已批准 ${results.length} 个明细项：\n${
            results.map(r => `- ${r.request_no} / ${r.line_id.split('-').pop()}行`).join('\n')
        }`);

        updateTimeline('approval_completed', { count: results.length, action: 'approved' });

        // 如果所有申请的所有行都已审批，从列表中移除
        _pendingApprovals = _pendingApprovals.filter(req => {
            return (req.line_items || []).some(l => l.status === 'pending');
        });
        renderPendingApprovals();
    }
}
