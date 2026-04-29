<template>
  <div class="share-page">
    <header class="share-header">
      <h1 class="share-title">{{ conversation.title || '分享对话' }}</h1>
      <p class="share-meta" v-if="conversation.model_name">模型: {{ conversation.model_name }}</p>
    </header>

    <div class="share-messages" v-if="conversation.messages?.length" @click="handleContentClick">
      <div class="messages-inner">
        <div v-for="msg in conversation.messages" :key="msg.id" :class="['msg', msg.role]">
          <div v-if="msg.role === 'user'" class="bubble-row user-row">
            <div class="bubble bubble-user">
              <span v-html="renderContent(msg.content)"></span>
            </div>
          </div>
          <div v-else class="bubble-row ai-row">
            <div class="ai-avatar">✦</div>
            <div class="ai-body">
              <div class="ai-content" v-html="renderContent(msg.content)"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!loading && !error" class="share-empty">
      <p>暂无消息</p>
    </div>

    <div v-if="error" class="share-error">
      <p>{{ error }}</p>
    </div>

    <!-- 底部提示 -->
    <footer class="share-footer">
      <p>此对话为只读模式。如需继续对话，请访问 <a :href="chatUrl">Chat Lite</a> 并配置 API Key。</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import request from '../api/request.js'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const route = useRoute()
const conversation = ref({})
const loading = ref(true)
const error = ref('')
const chatUrl = window.location.origin + '/chat'

async function loadShare() {
  try {
    const res = await request.get(`/api/share/${route.params.shareId}`)
    conversation.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || '分享链接无效或已过期'
  } finally {
    loading.value = false
  }
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function renderKatex(latex, displayMode) {
  try {
    return katex.renderToString(latex, { displayMode, throwOnError: false })
  } catch { return escapeHtml(latex) }
}

function renderContent(text) {
  // 0. 提取 LaTeX 公式
  const mathBlocks = []
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => {
    const idx = mathBlocks.length
    mathBlocks.push(renderKatex(tex.trim(), true))
    return `__MATH_${idx}__`
  })
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, tex) => {
    const idx = mathBlocks.length
    mathBlocks.push(renderKatex(tex.trim(), true))
    return `__MATH_${idx}__`
  })
  text = text.replace(/\\\((.+?)\\\)/g, (_, tex) => {
    const idx = mathBlocks.length
    mathBlocks.push(renderKatex(tex.trim(), false))
    return `__MATH_${idx}__`
  })
  text = text.replace(/(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)/g, (_, tex) => {
    const idx = mathBlocks.length
    mathBlocks.push(renderKatex(tex.trim(), false))
    return `__MATH_${idx}__`
  })

  // 1. 提取 ![img](url)
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

  // 3. 提取 inline code
  const inlineCodes = []
  text = text.replace(/`([^`\n]+)`/g, (_, code) => {
    const idx = inlineCodes.length
    inlineCodes.push(code)
    return `__INLINE_${idx}__`
  })

  // 4. HTML 转义
  let html = escapeHtml(text)

  // 5. Markdown 格式化
  html = html
    .replace(/^#{6}\s*(.*\S.*)$/gm, '<h6 class="md-h">$1</h6>')
    .replace(/^#{5}\s*(.*\S.*)$/gm, '<h5 class="md-h">$1</h5>')
    .replace(/^#{4}\s*(.*\S.*)$/gm, '<h4 class="md-h">$1</h4>')
    .replace(/^#{3}\s*(.*\S.*)$/gm, '<h3 class="md-h">$1</h3>')
    .replace(/^#{2}\s*(.*\S.*)$/gm, '<h2 class="md-h">$1</h2>')
    .replace(/^#{1}\s*(.*\S.*)$/gm, '<h1 class="md-h">$1</h1>')
    .replace(/^#{1,6}\s*$/gm, '')
    .replace(/^[-*_]{3,}\s*$/gm, '<hr class="md-hr">')
    .replace(/^&gt;\s?(.+)$/gm, '<blockquote class="md-bq">$1</blockquote>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/~~(.+?)~~/g, '<del>$1</del>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="md-link">$1</a>')
    .replace(/^(\d+)\.\s+(.+)$/gm, '<li class="md-oli" value="$1">$2</li>')
    .replace(/^[-*+]\s+(.+)$/gm, '<li class="md-uli">$1</li>')

  // 6. 换行 + 清理
  html = html.replace(/\n/g, '<br>')
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
    .replace(/<\/blockquote>\s*<blockquote class="md-bq">/g, '<br>')

  // 6b. 用 <ol>/<ul> 包裹连续的 <li>
  html = html.replace(/((?:<li class="md-oli"[^>]*>[\s\S]*?<\/li>\s*)+)/g, '<ol class="md-ol">$1</ol>')
  html = html.replace(/((?:<li class="md-uli">[\s\S]*?<\/li>\s*)+)/g, '<ul class="md-ul">$1</ul>')

  // 7. 还原 inline code
  for (let i = 0; i < inlineCodes.length; i++) {
    html = html.replace(`__INLINE_${i}__`, `<code class="inline-code">${escapeHtml(inlineCodes[i])}</code>`)
  }

  // 8. 还原 code blocks
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

  // 9. 还原图片
  for (let i = 0; i < imgMap.length; i++) {
    html = html.replace(`__IMG_${i}__`, `<img src="${imgMap[i]}" class="msg-img" alt="图片" />`)
  }

  // 10. 清理残留
  html = html.replace(/<br>```\w*<br>/g, '<br>')
  html = html.replace(/^```\w*<br>/g, '')
  html = html.replace(/<br>```\w*$/g, '')

  // 11. 还原 LaTeX 公式
  for (let i = 0; i < mathBlocks.length; i++) {
    html = html.replace(`__MATH_${i}__`, mathBlocks[i])
  }

  return html
}

function handleContentClick(e) {
  const btn = e.target.closest('.code-copy-btn')
  if (!btn) return
  const code = btn.getAttribute('data-code')
  const txt = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
  navigator.clipboard.writeText(txt).catch(() => {})
  btn.textContent = '已复制'
  setTimeout(() => { btn.textContent = '复制' }, 1500)
}

onMounted(loadShare)
</script>

<style scoped>
.share-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.share-header {
  text-align: center;
  padding: 32px 20px 16px;
  border-bottom: 1px solid var(--border);
}
.share-title {
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 4px;
}
.share-meta {
  color: var(--text-muted);
  font-size: .8rem;
}

.share-messages {
  flex: 1;
  overflow-y: auto;
}
.messages-inner {
  max-width: 768px;
  margin: 0 auto;
  padding: 24px 20px;
}

.msg { margin-bottom: 20px; }
.bubble-row { display: flex; }

.user-row { justify-content: flex-end; }
.bubble {
  max-width: 75%;
  padding: 10px 16px;
  border-radius: 20px;
  font-size: .9rem;
  line-height: 1.6;
  word-break: break-word;
}
.bubble-user {
  background: var(--bg-bubble-user);
  color: var(--text-bubble-user);
  border-bottom-right-radius: 4px;
}

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
  font-size: .9rem;
  line-height: 1.7;
  color: var(--text-bubble-ai);
  word-break: break-word;
}

.share-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.share-error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--danger);
  font-size: .95rem;
}

.share-footer {
  text-align: center;
  padding: 16px 20px;
  border-top: 1px solid var(--border);
  color: var(--text-muted);
  font-size: .8rem;
}
.share-footer a {
  color: var(--accent);
  text-decoration: underline;
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
:deep(.code-pre code) { font-family: inherit; }

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
:deep(.md-h) { margin: 16px 0 8px; line-height: 1.35; color: var(--text-primary); }
:deep(h1.md-h) { font-size: 1.5rem; font-weight: 700; }
:deep(h2.md-h) { font-size: 1.3rem; font-weight: 700; }
:deep(h3.md-h) { font-size: 1.15rem; font-weight: 600; }
:deep(h4.md-h) { font-size: 1.05rem; font-weight: 600; }
:deep(h5.md-h) { font-size: 1rem; font-weight: 600; }
:deep(h6.md-h) { font-size: .9rem; font-weight: 600; color: var(--text-secondary); }

/* ─── 引用块 ─── */
:deep(.md-bq) {
  margin: 8px 0;
  padding: 8px 14px;
  border-left: 3px solid var(--accent);
  background: var(--bg-hover, rgba(0,0,0,.03));
  color: var(--text-secondary);
  border-radius: 0 8px 8px 0;
  font-size: .95em;
}

/* ─── 分割线 ─── */
:deep(.md-hr) { border: none; border-top: 1px solid var(--border); margin: 14px 0; }

/* ─── 链接 ─── */
:deep(.md-link) { color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; transition: border-color .15s; }
:deep(.md-link:hover) { border-bottom-color: var(--accent); }

/* ─── 列表 ─── */
:deep(.md-ol) { list-style-type: decimal; margin: 8px 0; padding-left: 1.8em; }
:deep(.md-ul) { list-style-type: disc; margin: 8px 0; padding-left: 1.8em; }
:deep(.md-oli), :deep(.md-uli) { padding: 2px 0; line-height: 1.6; }

/* ─── 图片 ─── */
:deep(.msg-img) {
  display: block;
  max-width: 320px;
  max-height: 320px;
  border-radius: 12px;
  margin: 8px 0 4px;
  object-fit: contain;
  border: 1px solid var(--border);
}

/* ─── KaTeX 公式 ─── */
:deep(.katex-display) {
  margin: 12px 0;
  overflow-x: auto;
  overflow-y: hidden;
}
:deep(.katex) {
  font-size: 1.05em;
}
</style>
