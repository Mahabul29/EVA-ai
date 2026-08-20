/* =========================================================
   EvaAI — app.js
   Full chat UI logic: conversations, streaming render,
   markdown + code highlighting, settings, PWA install.
   ========================================================= */

/* ---------- Global state ---------- */
const messageInput   = document.getElementById('messageInput');
const sendBtn        = document.getElementById('sendBtn');
const messagesArea   = document.getElementById('messagesArea');
const welcomeScreen  = document.getElementById('welcomeScreen');
const chatListEl     = document.getElementById('chatList');
const sidebar        = document.getElementById('sidebar');
const installBanner  = document.getElementById('installBanner');
const offlineBar     = document.getElementById('offlineBar');
const settingsModal  = document.getElementById('settingsModal');
const themeSelect    = document.getElementById('themeSelect');
const fontSizeSelect = document.getElementById('fontSizeSelect');
const toastContainer = document.getElementById('toastContainer');
const apiKeyInput     = document.getElementById('apiKeyInput');
const apiKeyToggle    = document.getElementById('apiKeyToggle');
const apiKeyStatus    = document.getElementById('apiKeyStatus');

let conversations = {};          // { id: { id, title, messages: [{role, content}] } }
let currentConversationId = null;
let isTyping = false;
let deferredInstallPrompt = null;

const STORAGE_KEY  = 'evaai_conversations';
const THEME_KEY    = 'evaai_theme';
const FONT_KEY     = 'evaai_font_size';
const INSTALL_KEY  = 'evaai_install_dismissed';
const API_KEY_KEY  = 'evaai_api_key';

/* ---------- Init ---------- */
document.addEventListener('DOMContentLoaded', init);

function init() {
    loadConversations();
    renderChatList();
    loadSettings();
    loadApiKey();
    setupInstallPrompt();
    setupOfflineDetection();

    if (window.marked) {
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: function (code, lang) {
                if (window.hljs && lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return window.hljs ? hljs.highlightAuto(code).value : code;
            }
        });
    }

    messageInput?.addEventListener('input', () => {
        sendBtn.disabled = messageInput.value.trim().length === 0 || isTyping;
    });
    sendBtn.disabled = true;
}

/* ---------- Conversation persistence ---------- */
function loadConversations() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        conversations = raw ? JSON.parse(raw) : {};
    } catch (e) {
        conversations = {};
    }
}

function saveConversations() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (e) {
        console.error('Failed to save conversations', e);
    }
}

function renderChatList() {
    chatListEl.innerHTML = '';
    const ids = Object.keys(conversations).sort((a, b) =>
        (conversations[b].updatedAt || 0) - (conversations[a].updatedAt || 0)
    );

    if (ids.length === 0) {
        chatListEl.innerHTML = '<div class="chat-list-empty">No conversations yet</div>';
        return;
    }

    ids.forEach(id => {
        const convo = conversations[id];
        const item = document.createElement('div');
        item.className = 'chat-item' + (id === currentConversationId ? ' active' : '');
        item.dataset.id = id;

        const title = document.createElement('span');
        title.className = 'chat-item-title';
        title.textContent = convo.title || 'New chat';
        item.appendChild(title);

        const delBtn = document.createElement('button');
        delBtn.className = 'chat-item-delete';
        delBtn.setAttribute('aria-label', 'Delete chat');
        delBtn.innerHTML = '&times;';
        delBtn.onclick = (e) => {
            e.stopPropagation();
            deleteConversation(id);
        };
        item.appendChild(delBtn);

        item.onclick = () => loadConversation(id);
        chatListEl.appendChild(item);
    });
}

function deleteConversation(id) {
    delete conversations[id];
    saveConversations();
    if (id === currentConversationId) {
        startNewChat();
    } else {
        renderChatList();
    }
}

/* ---------- Chat lifecycle ---------- */
function startNewChat() {
    currentConversationId = null;
    messagesArea.innerHTML = '';
    messagesArea.appendChild(welcomeScreen);
    welcomeScreen.style.display = 'flex';
    messageInput.value = '';
    autoResize(messageInput);
    renderChatList();
    closeSidebarOnMobile();
}

function loadConversation(id) {
    const convo = conversations[id];
    if (!convo) return;

    currentConversationId = id;
    welcomeScreen.style.display = 'none';
    messagesArea.innerHTML = '';
    messagesArea.appendChild(welcomeScreen);

    convo.messages.forEach(m => appendMessage(m.role, m.content, false));
    renderChatList();
    scrollToBottom();
    closeSidebarOnMobile();
}

function ensureConversation() {
    if (currentConversationId && conversations[currentConversationId]) return;
    const id = 'chat_' + Date.now();
    conversations[id] = { id, title: 'New chat', messages: [], updatedAt: Date.now() };
    currentConversationId = id;
}

function closeSidebarOnMobile() {
    if (window.innerWidth <= 768) sidebar.classList.remove('open');
}

/* ---------- Sending messages ---------- */
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

function sendSuggestion(text) {
    messageInput.value = text;
    autoResize(messageInput);
    sendMessage();
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isTyping) return;

    welcomeScreen.style.display = 'none';
    ensureConversation();

    appendMessage('user', message);
    conversations[currentConversationId].messages.push({ role: 'user', content: message });
    if (conversations[currentConversationId].messages.length === 1) {
        conversations[currentConversationId].title = message.slice(0, 40);
    }
    conversations[currentConversationId].updatedAt = Date.now();
    saveConversations();
    renderChatList();

    messageInput.value = '';
    autoResize(messageInput);
    sendBtn.disabled = true;

    isTyping = true;
    showTypingIndicator();

    try {
        const headers = { 'Content-Type': 'application/json' };
        const apiKey = localStorage.getItem(API_KEY_KEY);
        if (apiKey) headers['X-API-Key'] = apiKey;

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                message: message,
                conversation_id: currentConversationId
            })
        });

        if (!response.ok) throw new Error('Request failed: ' + response.status);

        const data = await response.json();
        removeTypingIndicator();

        const reply = data.response || data.message || '(No response)';
        appendMessage('assistant', reply);
        conversations[currentConversationId].messages.push({ role: 'assistant', content: reply });
        conversations[currentConversationId].updatedAt = Date.now();
        saveConversations();
    } catch (err) {
        console.error(err);
        removeTypingIndicator();
        appendMessage('assistant', '⚠️ Something went wrong. Please try again.');
        showToast('Failed to get a response', 'error');
    } finally {
        isTyping = false;
        sendBtn.disabled = messageInput.value.trim().length === 0;
    }
}

/* ---------- Rendering messages ---------- */
function appendMessage(role, content, scroll = true) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message message-' + role;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'U' : '⚡';

    const bubble = document.createElement('div');
    bubble.className = 'message-content';

    if (role === 'assistant' && window.marked) {
        bubble.innerHTML = marked.parse(content);
    } else {
        bubble.textContent = content;
    }

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesArea.appendChild(wrapper);

    if (role === 'assistant' && window.hljs) {
        bubble.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
    }

    if (scroll) scrollToBottom();
}

function showTypingIndicator() {
    const wrapper = document.createElement('div');
    wrapper.className = 'message message-assistant';
    wrapper.id = 'typingIndicator';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '⚡';

    const bubble = document.createElement('div');
    bubble.className = 'message-content typing-dots';
    bubble.innerHTML = '<span></span><span></span><span></span>';

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesArea.appendChild(wrapper);
    scrollToBottom();
}

function removeTypingIndicator() {
    document.getElementById('typingIndicator')?.remove();
}

function scrollToBottom() {
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

/* ---------- Sidebar ---------- */
function toggleSidebar() {
    sidebar.classList.toggle('open');
}

/* ---------- Topbar actions ---------- */
function shareChat() {
    if (!currentConversationId || !conversations[currentConversationId]) {
        showToast('Nothing to share yet', 'info');
        return;
    }
    const convo = conversations[currentConversationId];
    const text = convo.messages.map(m => (m.role === 'user' ? 'You: ' : 'EvaAI: ') + m.content).join('\n\n');

    if (navigator.share) {
        navigator.share({ title: convo.title, text }).catch(() => {});
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(text);
        showToast('Chat copied to clipboard', 'success');
    } else {
        showToast('Sharing not supported on this device', 'error');
    }
}

function clearCurrentChat() {
    if (!currentConversationId) return;
    if (!confirm('Clear this conversation?')) return;
    conversations[currentConversationId].messages = [];
    messagesArea.innerHTML = '';
    messagesArea.appendChild(welcomeScreen);
    welcomeScreen.style.display = 'flex';
    saveConversations();
    renderChatList();
}

/* ---------- Settings modal ---------- */
function showSettings() {
    settingsModal.classList.add('open');
}

function hideSettings() {
    settingsModal.classList.remove('open');
}

function closeSettings(event) {
    if (event.target === settingsModal) hideSettings();
}

function loadSettings() {
    const theme = localStorage.getItem(THEME_KEY) || 'dark';
    const fontSize = localStorage.getItem(FONT_KEY) || 'medium';
    themeSelect.value = theme;
    fontSizeSelect.value = fontSize;
    applyTheme(theme);
    applyFontSize(fontSize);
}

function changeTheme(value) {
    localStorage.setItem(THEME_KEY, value);
    applyTheme(value);
}

function applyTheme(value) {
    let resolved = value;
    if (value === 'system') {
        resolved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', resolved);
}

function changeFontSize(value) {
    localStorage.setItem(FONT_KEY, value);
    applyFontSize(value);
}

function applyFontSize(value) {
    document.documentElement.setAttribute('data-font-size', value);
}

/* ---------- API key ---------- */
function loadApiKey() {
    if (!apiKeyInput) return;
    const saved = localStorage.getItem(API_KEY_KEY);
    if (saved) {
        apiKeyInput.value = saved;
        apiKeyStatus.textContent = 'Set on this device';
        apiKeyStatus.classList.add('set');
    } else {
        apiKeyStatus.textContent = 'Not set';
        apiKeyStatus.classList.remove('set');
    }
}

function saveApiKey() {
    const value = apiKeyInput.value.trim();
    if (!value) {
        localStorage.removeItem(API_KEY_KEY);
        apiKeyStatus.textContent = 'Not set';
        apiKeyStatus.classList.remove('set');
        showToast('API key cleared', 'info');
        return;
    }
    localStorage.setItem(API_KEY_KEY, value);
    apiKeyStatus.textContent = 'Set on this device';
    apiKeyStatus.classList.add('set');
    showToast('API key saved', 'success');
}

function toggleApiKeyVisibility() {
    if (!apiKeyInput) return;
    apiKeyInput.type = apiKeyInput.type === 'password' ? 'text' : 'password';
}

function clearAllData() {
    if (!confirm('Delete all chats? This cannot be undone.')) return;
    conversations = {};
    saveConversations();
    startNewChat();
    hideSettings();
    showToast('All chats deleted', 'success');
}

/* ---------- Toasts ---------- */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/* ---------- PWA install ---------- */
function setupInstallPrompt() {
    if (localStorage.getItem(INSTALL_KEY) === 'true') {
        installBanner.style.display = 'none';
        return;
    }
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredInstallPrompt = e;
        installBanner.classList.add('show');
    });
    window.addEventListener('appinstalled', () => {
        installBanner.classList.remove('show');
        showToast('EvaAI installed', 'success');
    });
}

function installApp() {
    if (!deferredInstallPrompt) {
        installBanner.classList.remove('show');
        return;
    }
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.finally(() => {
        deferredInstallPrompt = null;
        installBanner.classList.remove('show');
    });
}

function dismissInstall() {
    installBanner.classList.remove('show');
    localStorage.setItem(INSTALL_KEY, 'true');
}

/* ---------- Offline detection ---------- */
function setupOfflineDetection() {
    const update = () => {
        offlineBar.classList.toggle('show', !navigator.onLine);
    };
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    update();
}
