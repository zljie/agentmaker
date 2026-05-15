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
    const useMock = document.getElementById('use-mock')?.checked ?? true;

    const message = input.value.trim();
    if (!message || isRunning) return;

    addMessage('user', message);
    input.value = '';

    isRunning = true;
    sendBtn.classList.add('hidden');
    abortBtn.classList.remove('hidden');
    input.disabled = true;

    showThinking('正在理解您的问题...');

    const timeline = document.getElementById('execution-timeline');
    if (timeline) {
        timeline.style.display = 'block';
        timeline.classList.remove('hidden');
    }
    const tc = document.getElementById('timeline-content');
    if (tc) tc.innerHTML = '';

    try {
        const { run_id } = await API.run(message, useMock);
        currentRunId = run_id;
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
    }
}

// ==================== LLM Test ====================
async function testLlm() {
    showToast('LLM 连通性测试功能开发中...', 'info');
}

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

// ==================== Init ====================
document.addEventListener('DOMContentLoaded', async () => {
    // Warm up chat with welcome message if container is empty
    const chatContainer = document.getElementById('chat-messages');
    if (chatContainer && chatContainer.children.length === 0) {
        clearChat();
    }

    // Health check
    try {
        await API.healthCheck();
    } catch (_) { /* non-critical */ }
});
