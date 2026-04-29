<template>
  <div class="chat-window">
    <!-- 消息列表 -->
    <div class="messages" ref="messagesRef" @click="handleContentClick">
      <div class="messages-inner">
        <div v-if="!messages.length && !sending" class="empty-hint">
          <p>向 {{ model?.display_name || 'AI' }} 发送第一条消息</p>
        </div>
        <div v-for="msg in messages" :key="msg.id" :class="['msg', msg.role]">
          <!-- 用户消息：右侧气泡 -->
          <div v-if="msg.role === 'user'" class="bubble-row user-row">
            <div class="user-msg-wrap">
              <!-- 编辑模式 -->
              <div v-if="editingMsgId === msg.id" class="edit-box">
                <textarea v-model="editText" class="edit-textarea" rows="3"></textarea>
                <div class="edit-btns">
                  <button class="edit-btn cancel" @click="cancelEdit">取消</button>
                  <button class="edit-btn confirm" @click="confirmEdit(msg)">发送</button>
                </div>
              </div>
              <!-- 正常显示 -->
              <div v-else class="bubble bubble-user">
                <span v-html="renderContent(msg.content)"></span>
              </div>
              <!-- 操作按钮 -->
              <div v-if="editingMsgId !== msg.id && !sending" class="user-actions">
                <button class="ua-btn" @click="copyUserMsg(msg)" :title="copiedId === msg.id ? '已复制' : '复制'">
                  {{ copiedId === msg.id ? '✓' : '📋' }}
                </button>
                <button class="ua-btn" @click="startEdit(msg)" title="编辑">✏️</button>
                <button class="ua-btn" @click="undoAndResend(msg)" title="回退到输入框重新编辑">↩️</button>
              </div>
            </div>
          </div>
          <!-- AI 消息：左侧 -->
          <div v-else class="bubble-row ai-row">
            <div class="ai-avatar">✦</div>
            <div class="ai-body">
              <div class="ai-content">
                <ImageGenOverlay
                  v-if="msg.generatingImage || msg.imageUrl"
                  :imageUrl="msg.imageUrl || ''"
                />
                <span v-if="msg.content && !msg.imageUrl" v-html="renderContent(msg.content)"></span>
                <span v-if="sending && msg === messages[messages.length - 1] && msg.role === 'assistant' && !msg.generatingImage" class="stream-cursor">▍</span>
              </div>
              <div class="ai-actions" v-if="!sending || msg !== messages[messages.length - 1]">
                <button class="btn-copy" @click="copyText(msg)">
                  {{ copiedId === msg.id ? '已复制' : '复制' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="input-wrap">
      <!-- 已选附件预览 -->
      <div v-if="attachments.length" class="attach-preview">
        <div v-for="(f, i) in attachments" :key="i" class="attach-item">
          <img v-if="f.thumb" :src="f.thumb" class="attach-thumb" />
          <span v-else class="attach-file-icon">📄</span>
          <span class="attach-name">{{ f.name }}</span>
          <button class="attach-remove" @click="removeAttach(i)">×</button>
        </div>
      </div>
      <div class="input-area">
        <!-- ➕ 按钮 + 弹出菜单 -->
        <div class="attach-wrap">
          <button class="btn-attach" @click="showAttachMenu = !showAttachMenu" title="上传图片或文件" :disabled="sending">
            <span>+</span>
          </button>
          <div v-if="showAttachMenu" class="attach-menu">
            <button class="attach-menu-item" @click="pickImage">🖼️ 选择图片</button>
            <button class="attach-menu-item" @click="pickFile">📄 选择文件</button>
          </div>
        </div>
        <div v-if="showAttachMenu" class="attach-menu-backdrop" @click="showAttachMenu = false"></div>
        <input type="file" ref="imageInputRef" multiple accept="image/*" @change="handleImageSelect" style="display:none" />
        <input type="file" ref="fileInputRef" multiple accept=".pdf,.txt,.md,.json,.csv,.py,.js,.ts,.java,.c,.cpp,.html,.css,.xml,.yml,.yaml,.log,.sql" @change="handleFileSelect" style="display:none" />
        <textarea
          v-model="input"
          :disabled="!model || !conversationId || sending"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行"
          @keydown="handleKeydown"
          rows="1"
          ref="textareaRef"
        ></textarea>
        <button class="btn-send" :disabled="!canSend" @click="send">
          <span v-if="sending" class="spin">●</span>
          <span v-else>↑</span>
        </button>
      </div>
      <p v-if="error" class="error-bar">{{ error }}</p>
    </div>

  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed, defineProps, defineEmits } from 'vue'
import request from '../api/request.js'
import ImageGenOverlay from './ImageGenOverlay.vue'

const props = defineProps({
  conversationId: { type: Number, default: null },
  model: { type: Object, default: null },
})
const emit = defineEmits(['refreshConversations'])

const messages = ref([])
const input = ref('')
const sending = ref(false)
const error = ref('')
const copiedId = ref(null)
const messagesRef = ref(null)
const textareaRef = ref(null)
const fileInputRef = ref(null)
const imageInputRef = ref(null)
const showAttachMenu = ref(false)
const attachments = ref([])   // { name, type, isImage, thumb?, content }
const editingMsgId = ref(null)
const editText = ref('')

const canSend = computed(() => {
  const hasText = input.value.trim()
  const hasFiles = attachments.value.length > 0
  return props.model && props.conversationId && (hasText || hasFiles) && !sending.value
})

function pickImage() {
  showAttachMenu.value = false
  imageInputRef.value?.click()
}
function pickFile() {
  showAttachMenu.value = false
  fileInputRef.value?.click()
}

async function handleImageSelect(e) {
  const files = Array.from(e.target.files || [])
  for (const f of files) {
    if (attachments.value.length >= 5) break
    // 先读 base64 用于本地预览 + 发给 AI
    const base64 = await readFileAsDataURL(f)
    // 上传到服务器获取 URL（用于存储在消息中 + 历史显示）
    let serverUrl = ''
    try {
      const form = new FormData()
      form.append('file', f)
      const res = await request.post('/api/upload', form)
      serverUrl = res.data.url
    } catch { /* 上传失败也允许继续 */ }
    attachments.value.push({
      name: f.name, type: f.type, isImage: true,
      thumb: base64,         // 本地预览
      content: base64,       // base64 发给 AI
      serverUrl,             // 服务器 URL，存入消息文本
    })
  }
  e.target.value = ''
}

function readFileAsDataURL(file) {
  return new Promise(resolve => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.readAsDataURL(file)
  })
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files || [])
  for (const f of files) {
    if (attachments.value.length >= 5) break
    const reader = new FileReader()
    reader.onload = () => {
      attachments.value.push({ name: f.name, type: f.type, isImage: false, thumb: null, content: reader.result })
    }
    reader.readAsText(f)
  }
  e.target.value = ''
}

function removeAttach(i) {
  attachments.value.splice(i, 1)
}

function buildPayload(text) {
  const imageAttach = attachments.value.filter(a => a.isImage)
  const fileAttach = attachments.value.filter(a => !a.isImage)

  // 文本文件内容拼入消息（截断节省 token）
  let msgText = text
  if (fileAttach.length) {
    let parts = []
    for (const a of fileAttach) {
      let content = a.content || ''
      if (content.length > 4000) {
        content = content.slice(0, 4000) + '\n...(内容过长已截断)'
      }
      parts.push(`--- ${a.name} ---\n${content}\n--- end ---`)
    }
    msgText = msgText ? `${msgText}\n\n${parts.join('\n\n')}` : parts.join('\n\n')
  }

  // 图片：消息里只存 ![img](serverUrl) 格式（极小 token 占用）
  // base64 走 images 字段仅当前这一次发给 AI
  if (imageAttach.length) {
    const imgTags = imageAttach
      .map(a => a.serverUrl ? `![img](${a.serverUrl})` : `[图片: ${a.name}]`)
      .join('\n')
    msgText = msgText ? `${msgText}\n\n${imgTags}` : imgTags
  }

  return {
    message: msgText,
    images: imageAttach.length ? imageAttach.map(a => a.content) : undefined,
  }
}

async function loadMessages() {
  if (!props.conversationId) { messages.value = []; return }
  try {
    const res = await request.get(`/api/conversations/${props.conversationId}/messages`)
    messages.value = res.data
    await nextTick()
    scrollBottom()
  } catch (e) { console.error('[loadMessages]', e) }
}

async function send() {
  if (!canSend.value) return
  const text = input.value.trim()
  const payload = buildPayload(text)
  input.value = ''
  attachments.value = []
  error.value = ''

  // 添加用户消息
  const tempUserMsg = { id: Date.now(), role: 'user', content: payload.message }
  messages.value.push(tempUserMsg)
  // 添加空的 AI 消息占位（用于流式填充）
  const aiMsg = { id: Date.now() + 1, role: 'assistant', content: '', generatingImage: !!props.model?.support_image, imageUrl: '' }
  messages.value.push(aiMsg)
  await nextTick()
  scrollBottom()

  sending.value = true
  try {
    const token = localStorage.getItem('token')
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers.Authorization = `Bearer ${token}`
    const resp = await fetch('/api/chat/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        conversation_id: props.conversationId,
        model_name: props.model.model_name,
        message: payload.message,
        images: payload.images,
      }),
    })

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}))
      throw new Error(errData.detail || `HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // 按行解析 SSE
      const lines = buffer.split('\n')
      buffer = lines.pop() // 保留最后一行（可能不完整）

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') continue
        try {
          const obj = JSON.parse(data)
          if (obj.t) {
            aiMsg.content += obj.t
            messages.value = [...messages.value]
            scrollBottomLazy()
          }
          if (obj.image_url) {
            aiMsg.imageUrl = obj.image_url
            aiMsg.content = `![img](${obj.image_url})`
            aiMsg.generatingImage = false
            messages.value = [...messages.value]
          }
          if (obj.done && obj.message_id) {
            aiMsg.id = obj.message_id
          }
          if (obj.error) {
            aiMsg.generatingImage = false
            error.value = obj.error
            messages.value = [...messages.value]
          }
        } catch {}
      }
    }

    emit('refreshConversations')
  } catch (e) {
    // 流式失败但 AI 已有部分内容 → 保留显示
    if (aiMsg.content) {
      emit('refreshConversations')
    } else {
      // 完全失败 → 从数据库重新加载（用户消息已存）
      error.value = e.message || '连接中断，请重试'
      await loadMessages()
      emit('refreshConversations')
    }
  } finally {
    sending.value = false
    aiMsg.generatingImage = false
    messages.value = [...messages.value]
    await nextTick()
    scrollBottom()
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function scrollBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

let _scrollTimer = null
function scrollBottomLazy() {
  if (_scrollTimer) return
  _scrollTimer = setTimeout(() => {
    _scrollTimer = null
    scrollBottom()
  }, 50)
}

function copyText(msg) {
  navigator.clipboard.writeText(msg.content).catch(() => {})
  copiedId.value = msg.id
  setTimeout(() => { copiedId.value = null }, 1500)
}

// ─── 用户消息操作 ───
function copyUserMsg(msg) {
  navigator.clipboard.writeText(msg.content).catch(() => {})
  copiedId.value = msg.id
  setTimeout(() => { copiedId.value = null }, 1500)
}

function startEdit(msg) {
  editingMsgId.value = msg.id
  editText.value = msg.content
}

function cancelEdit() {
  editingMsgId.value = null
  editText.value = ''
}

async function confirmEdit(msg) {
  const newContent = editText.value.trim()
  if (!newContent) return
  editingMsgId.value = null
  editText.value = ''
  // 删除该条及之后的消息，然后重新发送编辑后的内容
  try {
    await request.delete(`/api/conversations/${props.conversationId}/messages/${msg.id}/and-after`)
    await loadMessages()
  } catch {}
  // 将编辑后的内容填入输入框并自动发送
  input.value = newContent
  await nextTick()
  send()
}

async function undoAndResend(msg) {
  // 把消息内容回退到输入框，删除该消息及之后的所有消息
  const content = msg.content
  try {
    await request.delete(`/api/conversations/${props.conversationId}/messages/${msg.id}/and-after`)
    input.value = content
    await loadMessages()
    emit('refreshConversations')
    await nextTick()
    textareaRef.value?.focus()
  } catch {}
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function renderContent(text) {
  // 1. 提取 ![img](url) 占位
  const imgMap = []
  text = text.replace(/!\[img\]\(([^)]+)\)/g, (_, url) => {
    const idx = imgMap.length
    imgMap.push(url)
    return `__IMG_${idx}__`
  })

  // 2. 提取已完成的 fenced code blocks
  const codeBlocks = []
  text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length
    codeBlocks.push({ lang, code })
    return `__CODEBLOCK_${idx}__`
  })
  text = text.replace(/```(\w*)([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length
    codeBlocks.push({ lang, code })
    return `__CODEBLOCK_${idx}__`
  })

  // 2b. 流式输出时处理未闭合的 ``` 代码块
  const unclosedMatch = text.match(/```(\w*)\n([\s\S]*)$/)
  let unclosedBlock = null
  if (unclosedMatch) {
    unclosedBlock = { lang: unclosedMatch[1], code: unclosedMatch[2] }
    text = text.replace(/```(\w*)\n([\s\S]*)$/, '__UNCLOSED_CODE__')
  }

  // 3. 提取 inline code `code`
  const inlineCodes = []
  text = text.replace(/`([^`\n]+)`/g, (_, code) => {
    const idx = inlineCodes.length
    inlineCodes.push(code)
    return `__INLINE_${idx}__`
  })

  // 4. HTML 转义正文
  let html = escapeHtml(text)

  // 5. Markdown 格式化
  html = html
    // 标题（支持有无空格：### Title 或 ###Title）
    .replace(/^#{6}\s*(.*\S.*)$/gm, '<h6 class="md-h">$1</h6>')
    .replace(/^#{5}\s*(.*\S.*)$/gm, '<h5 class="md-h">$1</h5>')
    .replace(/^#{4}\s*(.*\S.*)$/gm, '<h4 class="md-h">$1</h4>')
    .replace(/^#{3}\s*(.*\S.*)$/gm, '<h3 class="md-h">$1</h3>')
    .replace(/^#{2}\s*(.*\S.*)$/gm, '<h2 class="md-h">$1</h2>')
    .replace(/^#{1}\s*(.*\S.*)$/gm, '<h1 class="md-h">$1</h1>')
    // 单独一行只有 # 号的（流式残留），直接隐藏
    .replace(/^#{1,6}\s*$/gm, '')
    // 分割线
    .replace(/^[-*_]{3,}\s*$/gm, '<hr class="md-hr">')
    // 引用块 > text
    .replace(/^&gt;\s?(.+)$/gm, '<blockquote class="md-bq">$1</blockquote>')
    // 粗体 / 斜体
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 删除线
    .replace(/~~(.+?)~~/g, '<del>$1</del>')
    // 链接 [text](url)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="md-link">$1</a>')
    // 有序列表
    .replace(/^(\d+)\.\s+(.+)$/gm, '<li class="md-oli" value="$1">$2</li>')
    // 无序列表
    .replace(/^[-*+]\s+(.+)$/gm, '<li class="md-uli">$1</li>')

  // 6. 换行
  html = html.replace(/\n/g, '<br>')
  // 清理块级元素前后多余的 <br>
  html = html
    .replace(/<br>\s*(<h[1-6])/g, '$1')
    .replace(/(<\/h[1-6]>)\s*<br>/g, '$1')
    .replace(/<br>\s*(<hr)/g, '$1')
    .replace(/(<hr[^>]*>)\s*<br>/g, '$1')
    .replace(/<br>\s*(<blockquote)/g, '$1')
    .replace(/(<\/blockquote>)\s*<br>/g, '$1')
    .replace(/<br>\s*(<div class="code-block")/g, '$1')
    .replace(/(<\/div>)\s*<br>/g, '$1')
    .replace(/<br>\s*(<li )/g, '$1')
    .replace(/(<\/li>)\s*<br>/g, '$1')
    // 合并连续的 blockquote
    .replace(/<\/blockquote>\s*<blockquote class="md-bq">/g, '<br>')

  // 6b. 用 <ol>/<ul> 包裹连续的 <li>
  html = html.replace(/((?:<li class="md-oli"[^>]*>[\s\S]*?<\/li>\s*)+)/g, '<ol class="md-ol">$1</ol>')
  html = html.replace(/((?:<li class="md-uli">[\s\S]*?<\/li>\s*)+)/g, '<ul class="md-ul">$1</ul>')

  // 7. 还原 inline code
  for (let i = 0; i < inlineCodes.length; i++) {
    html = html.replace(`__INLINE_${i}__`, `<code class="inline-code">${escapeHtml(inlineCodes[i])}</code>`)
  }

  // 8. 还原完整的 code blocks
  for (let i = 0; i < codeBlocks.length; i++) {
    const { lang, code } = codeBlocks[i]
    const langLabel = lang || 'code'
    const escaped = escapeHtml(code.trim())
    html = html.replace(
      `__CODEBLOCK_${i}__`,
      `<div class="code-block">` +
        `<div class="code-header"><span class="code-lang">${escapeHtml(langLabel)}</span>` +
        `<button class="code-copy-btn" data-code="${escaped.replace(/"/g, '&quot;')}">复制</button></div>` +
        `<pre class="code-pre"><code>${escaped}</code></pre>` +
      `</div>`
    )
  }

  // 8b. 还原未闭合的代码块（流式输出中）
  if (unclosedBlock) {
    const langLabel = unclosedBlock.lang || 'code'
    const escaped = escapeHtml(unclosedBlock.code)
    html = html.replace(
      '__UNCLOSED_CODE__',
      `<div class="code-block">` +
        `<div class="code-header"><span class="code-lang">${escapeHtml(langLabel)}</span></div>` +
        `<pre class="code-pre"><code>${escaped}</code></pre>` +
      `</div>`
    )
  }

  // 9. 还原图片
  for (let i = 0; i < imgMap.length; i++) {
    html = html.replace(`__IMG_${i}__`, `<img src="${imgMap[i]}" class="msg-img" alt="图片" />`)
  }

  // 10. 清理残留的原始 Markdown 符号
  // 去掉流式输出中可能残留的单独 ``` 行
  html = html.replace(/<br>```\w*<br>/g, '<br>')
  html = html.replace(/^```\w*<br>/g, '')
  html = html.replace(/<br>```\w*$/g, '')

  return html
}

// 事件委托：代码块复制按钮
function handleContentClick(e) {
  const btn = e.target.closest('.code-copy-btn')
  if (!btn) return
  const code = btn.getAttribute('data-code')
  // 把 HTML entities 还原回纯文本
  const txt = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
  navigator.clipboard.writeText(txt).catch(() => {})
  btn.textContent = '已复制'
  setTimeout(() => { btn.textContent = '复制' }, 1500)
}

watch(() => props.conversationId, () => { loadMessages() }, { immediate: true })
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 消息列表 */
.messages {
  flex: 1;
  overflow-y: auto;
}
.messages-inner {
  max-width: 768px;
  margin: 0 auto;
  padding: 24px 20px;
}
.empty-hint {
  text-align: center;
  color: var(--text-muted);
  padding-top: 30vh;
  font-size: 1.1rem;
}

/* 消息行 */
.msg { margin-bottom: 20px; }
.bubble-row { display: flex; }

/* ─── 用户消息：右侧气泡 ─── */
.user-row {
  justify-content: flex-end;
}
.bubble {
  max-width: 75%;
  padding: 12px 18px;
  border-radius: 20px;
  font-size: 1rem;
  line-height: 1.7;
  word-break: break-word;
}
.bubble-user {
  background: var(--bg-bubble-user);
  color: var(--text-bubble-user);
  border-bottom-right-radius: 4px;
}

/* ─── 用户消息操作 ─── */
.user-msg-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  max-width: 75%;
}
.user-msg-wrap .bubble { max-width: 100%; }
.user-actions {
  display: flex;
  gap: 2px;
  margin-top: 4px;
  opacity: 0.55;
  transition: opacity .15s;
}
.msg:hover .user-actions { opacity: 1; }
.ua-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: .8rem;
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--text-muted);
  transition: all .12s;
}
.ua-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* 编辑模式 */
.edit-box {
  width: 100%;
  min-width: 280px;
}
.edit-textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--accent);
  border-radius: 14px;
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: .95rem;
  line-height: 1.6;
  font-family: inherit;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}
.edit-btns {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  margin-top: 6px;
}
.edit-btn {
  font-size: .8rem;
  padding: 4px 14px;
  border-radius: 6px;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all .12s;
}
.edit-btn.cancel {
  background: transparent;
  color: var(--text-muted);
}
.edit-btn.cancel:hover {
  background: var(--bg-hover);
}
.edit-btn.confirm {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.edit-btn.confirm:hover {
  opacity: .85;
}

/* ─── AI 消息：左侧 ─── */
.ai-row {
  justify-content: flex-start;
  gap: 10px;
  align-items: flex-start;
}
.ai-avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent); color: #fff;
  font-size: .85rem; flex-shrink: 0;
  margin-top: 2px;
}
.ai-body {
  flex: 1;
  min-width: 0;
  max-width: 80%;
}
.ai-content {
  font-size: 1rem;
  line-height: 1.75;
  color: var(--text-bubble-ai);
  word-break: break-word;
}
.ai-actions {
  margin-top: 4px;
  display: flex;
  gap: 6px;
  opacity: 0.55;
  transition: opacity .15s;
}
.msg:hover .ai-actions { opacity: 1; }

.btn-copy {
  font-size: .75rem; color: var(--text-muted);
  background: transparent; border: 1px solid var(--border);
  border-radius: 4px; padding: 3px 10px; cursor: pointer;
}
.btn-copy:hover { color: var(--text-primary); border-color: var(--text-muted); }

/* 流式光标 */
.stream-cursor {
  display: inline;
  color: var(--accent);
  font-weight: 400;
  animation: blink 1s steps(2) infinite;
}
@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
}

/* ─── 附件预览 ─── */
.attach-preview {
  max-width: 768px;
  margin: 0 auto 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.attach-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 8px;
  background: var(--bg-hover);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: .9rem;
  color: var(--text-secondary);
  max-width: 220px;
}
.attach-thumb {
  width: 36px; height: 36px;
  object-fit: cover;
  border-radius: 6px;
}
.attach-file-icon { font-size: 1.1rem; }
.attach-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attach-remove {
  background: none; border: none;
  color: var(--text-muted); cursor: pointer;
  font-size: 1rem; padding: 0 4px;
}
.attach-remove:hover { color: var(--danger); }

/* ─── 输入区 ─── */
.input-wrap {
  flex-shrink: 0;
  padding: 0 20px 16px;
}
.input-area {
  max-width: 768px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 26px;
  padding: 10px 12px 10px 10px;
  box-shadow: var(--shadow);
}
/* ➕ 弹出菜单包装 */
.attach-wrap {
  position: relative;
  flex-shrink: 0;
}
.btn-attach {
  width: 38px; height: 38px;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.4rem;
  font-weight: 300;
  flex-shrink: 0;
  transition: all .15s;
}
.btn-attach:hover { color: var(--text-primary); background: var(--bg-active); border-color: var(--text-muted); }
.btn-attach:disabled { opacity: .3; cursor: not-allowed; }
.attach-menu {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  min-width: 160px;
  background: var(--bg-modal);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  z-index: 100;
  padding: 4px 0;
}
.attach-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 11px 16px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: .95rem;
  cursor: pointer;
  text-align: left;
  transition: background .1s;
}
.attach-menu-item:hover { background: var(--bg-hover); }
.attach-menu-backdrop { position: fixed; inset: 0; z-index: 90; }
.input-area textarea {
  flex: 1;
  min-height: 28px;
  max-height: 160px;
  padding: 8px 0;
  background: transparent;
  color: var(--text-primary);
  border: none;
  resize: none;
  font-size: 1rem;
  outline: none;
  font-family: inherit;
  line-height: 1.6;
}
.input-area textarea::placeholder { color: var(--text-muted); font-size: .95rem; }
.btn-send {
  width: 38px; height: 38px;
  display: flex; align-items: center; justify-content: center;
  background: var(--text-primary); color: var(--bg-primary);
  border: none; border-radius: 50%;
  cursor: pointer; font-size: 1.1rem; flex-shrink: 0;
  transition: opacity .15s;
}
.btn-send:disabled { opacity: .3; cursor: not-allowed; }
.btn-send:hover:not(:disabled) { opacity: .8; }
.spin {
  animation: spin 1s linear infinite;
  display: inline-block;
  font-size: .7rem;
}
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.error-bar {
  max-width: 768px;
  margin: 6px auto 0;
  text-align: center; color: var(--danger);
  font-size: .8rem;
}

/* 消息中的内联图片 */
:deep(.msg-img) {
  display: block;
  max-width: 320px;
  max-height: 320px;
  border-radius: 12px;
  margin: 8px 0 4px;
  object-fit: contain;
  cursor: pointer;
  border: 1px solid var(--border);
}
:deep(.msg-img:hover) {
  opacity: .9;
}

/* ─── 代码块 ─── */
:deep(.code-block) {
  margin: 10px 0;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--border);
  background: #1e1e2e;
  font-size: .88rem;
}
:deep(.code-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 14px;
  background: #2b2b3d;
  border-bottom: 1px solid rgba(255,255,255,.06);
}
:deep(.code-lang) {
  font-size: .75rem;
  color: #a0a0b8;
  text-transform: uppercase;
  letter-spacing: .5px;
}
:deep(.code-copy-btn) {
  font-size: .75rem;
  color: #c0c0d0;
  background: transparent;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 4px;
  padding: 2px 10px;
  cursor: pointer;
  transition: all .15s;
}
:deep(.code-copy-btn:hover) {
  background: rgba(255,255,255,.08);
  color: #fff;
}
:deep(.code-pre) {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
  color: #e0e0ee;
  font-family: 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
  font-size: .85rem;
  line-height: 1.65;
  white-space: pre;
  tab-size: 2;
}
:deep(.code-pre code) {
  font-family: inherit;
}

/* ─── 行内代码 ─── */
:deep(.inline-code) {
  background: var(--bg-hover, rgba(0,0,0,.06));
  color: var(--accent, #e06c75);
  padding: 1px 6px;
  border-radius: 4px;
  font-family: 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
  font-size: .88em;
}

/* ─── Markdown 标题 ─── */
:deep(.md-h) {
  margin: 16px 0 8px;
  line-height: 1.35;
  color: var(--text-primary);
}
:deep(h1.md-h) { font-size: 1.5rem; font-weight: 700; }
:deep(h2.md-h) { font-size: 1.3rem; font-weight: 700; }
:deep(h3.md-h) { font-size: 1.15rem; font-weight: 600; }
:deep(h4.md-h) { font-size: 1.05rem; font-weight: 600; }
:deep(h5.md-h) { font-size: 1rem; font-weight: 600; }
:deep(h6.md-h) { font-size: .9rem; font-weight: 600; color: var(--text-secondary); }

/* ─── Markdown 引用块 ─── */
:deep(.md-bq) {
  margin: 8px 0;
  padding: 8px 14px;
  border-left: 3px solid var(--accent);
  background: var(--bg-hover, rgba(0,0,0,.03));
  color: var(--text-secondary);
  border-radius: 0 8px 8px 0;
  font-size: .95em;
}

/* ─── Markdown 分割线 ─── */
:deep(.md-hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 14px 0;
}

/* ─── Markdown 链接 ─── */
:deep(.md-link) {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color .15s;
}
:deep(.md-link:hover) {
  border-bottom-color: var(--accent);
}

/* ─── Markdown 列表 ─── */
:deep(.md-ol) {
  list-style-type: decimal;
  margin: 8px 0;
  padding-left: 1.8em;
}
:deep(.md-ul) {
  list-style-type: disc;
  margin: 8px 0;
  padding-left: 1.8em;
}
:deep(.md-oli), :deep(.md-uli) {
  padding: 2px 0;
  line-height: 1.6;
}
</style>
