<template>
  <div class="chat-page">
    <!-- 左侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <ConversationList
        v-if="!sidebarCollapsed"
        :conversations="convList"
        v-model="currentConv"
        @refresh="loadConversations"
      />
      <div class="sidebar-footer" v-if="!sidebarCollapsed">
        <button class="footer-btn" @click="showKeyModal = true" title="API Key 配置">
          <span class="footer-icon">🔑</span>
          <span>API Key</span>
        </button>
        <button class="footer-btn" @click="toggleTheme" :title="isDark ? '切换日间' : '切换夜间'">
          <span class="footer-icon">{{ isDark ? '☀️' : '🌙' }}</span>
        </button>
        <button class="footer-btn" @click="logout" title="退出登录">
          <span class="footer-icon">退出</span>
        </button>
      </div>
    </aside>

    <!-- 主聊天区 -->
    <main class="main">
      <header class="main-header">
        <div class="header-left">
          <button class="btn-icon" @click="sidebarCollapsed = !sidebarCollapsed" title="收起/展开侧边栏">
            <span v-if="sidebarCollapsed">☰</span>
            <span v-else>◧</span>
          </button>
        </div>
        <ModelSelector
          :models="availableModels"
          v-model="currentModel"
          @openKeys="showKeyModal = true"
        />
        <div class="header-right">
          <button v-if="currentConv" class="btn-header-text" @click="handleShare" title="分享">↗ 分享</button>
          <div v-if="currentConv" class="hm-wrap">
            <button class="btn-icon" @click="headerMenuOpen = !headerMenuOpen" title="更多">⋯</button>
            <div v-if="headerMenuOpen" class="hm-dropdown">
              <button class="hm-item" @click="headerExportMd">导出 Markdown</button>
              <button class="hm-item" @click="headerExportPdf">导出 PDF</button>
              <button class="hm-item" @click="headerExportJson">导出 JSON</button>
              <button class="hm-item hm-danger" @click="headerDeleteConv">删除对话</button>
            </div>
          </div>
        </div>
      </header>

      <div v-if="headerMenuOpen" class="hm-backdrop" @click="headerMenuOpen = false"></div>
      <div v-if="shareToast" class="share-toast">{{ shareToast }}</div>

      <div class="main-chat">
        <ChatWindow
          v-if="currentModel && currentConv"
          :conversationId="currentConv?.id"
          :model="currentModel"
          @refreshConversations="loadConversations"
        />
        <div v-else class="main-empty">
          <div class="empty-card" v-if="!availableModels.length">
            <p class="empty-title">暂无可用模型</p>
            <p class="empty-sub">请先配置 API Key 以使用聊天功能</p>
            <button class="btn-accent" @click="showKeyModal = true">配置 API Key</button>
          </div>
          <div class="empty-card" v-else-if="!currentConv">
            <p class="empty-title">Chat Lite</p>
            <p class="empty-sub">新建一个对话开始聊天</p>
          </div>
        </div>
      </div>
    </main>

    <KeyConfigModal v-if="showKeyModal" @close="showKeyModal = false" @saved="onKeySaved" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request.js'
import KeyConfigModal from '../components/KeyConfigModal.vue'
import ModelSelector from '../components/ModelSelector.vue'
import ConversationList from '../components/ConversationList.vue'
import ChatWindow from '../components/ChatWindow.vue'

const router = useRouter()
const showKeyModal = ref(false)
const availableModels = ref([])
const currentModel = ref(null)
const convList = ref([])
const currentConv = ref(null)
const checkedKeys = ref(false)
const isDark = ref(localStorage.getItem('theme') === 'dark')
const sidebarCollapsed = ref(false)
const headerMenuOpen = ref(false)

function applyTheme() {
  document.documentElement.classList.toggle('dark', isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}
function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme()
}

async function loadModels() {
  try {
    const res = await request.get('/api/models/available')
    availableModels.value = res.data
    // 恢复上次选中的模型
    const savedModelName = localStorage.getItem('chat_model')
    const savedModel = savedModelName && res.data.find(m => m.model_name === savedModelName)
    if (savedModel) {
      currentModel.value = savedModel
    } else if (res.data.length && (!currentModel.value || !res.data.find(m => m.id === currentModel.value.id))) {
      currentModel.value = res.data[0]
    }
    if (!res.data.length) {
      currentModel.value = null
    }
    if (!checkedKeys.value) {
      checkedKeys.value = true
      if (!res.data.length) showKeyModal.value = true
    }
  } catch {}
}

async function loadConversations() {
  try {
    const res = await request.get('/api/conversations')
    convList.value = res.data
    // 恢复上次选中的对话
    if (!currentConv.value) {
      const savedId = parseInt(localStorage.getItem('chat_conv_id'))
      const saved = savedId && res.data.find(c => c.id === savedId)
      if (saved) {
        currentConv.value = saved
        return
      }
    }
    if (currentConv.value && !res.data.find(c => c.id === currentConv.value.id)) {
      currentConv.value = res.data.length ? res.data[0] : null
    }
  } catch {}
}

const shareToast = ref('')

async function handleShare() {
  if (!currentConv.value) return
  try {
    const res = await request.post(`/api/conversations/${currentConv.value.id}/share`)
    const shareUrl = `${window.location.origin}/share/${res.data.share_id}`
    await navigator.clipboard.writeText(shareUrl)
    shareToast.value = '分享链接已复制到剪贴板'
    setTimeout(() => { shareToast.value = '' }, 2500)
  } catch {
    shareToast.value = '分享失败'
    setTimeout(() => { shareToast.value = '' }, 2500)
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click()
  document.body.removeChild(a); URL.revokeObjectURL(url)
}

async function headerExportMd() {
  headerMenuOpen.value = false
  if (!currentConv.value) return
  try {
    const res = await request.get(`/api/conversations/${currentConv.value.id}/export/md`, { responseType: 'blob' })
    downloadBlob(res.data, `conversation-${currentConv.value.id}.md`)
  } catch {}
}

async function headerExportPdf() {
  headerMenuOpen.value = false
  if (!currentConv.value) return
  try {
    const res = await request.get(`/api/conversations/${currentConv.value.id}/export/pdf`, { responseType: 'blob' })
    downloadBlob(res.data, `conversation-${currentConv.value.id}.pdf`)
  } catch {}
}

async function headerExportJson() {
  headerMenuOpen.value = false
  if (!currentConv.value) return
  try {
    const res = await request.get(`/api/conversations/${currentConv.value.id}/export/json`, { responseType: 'blob' })
    downloadBlob(res.data, `conversation-${currentConv.value.id}.json`)
  } catch {}
}

async function headerDeleteConv() {
  headerMenuOpen.value = false
  if (!currentConv.value) return
  if (!confirm(`确定删除对话「${currentConv.value.title}」？`)) return
  try {
    await request.delete(`/api/conversations/${currentConv.value.id}`)
    currentConv.value = null
    await loadConversations()
  } catch {}
}

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('chat_conv_id')
  localStorage.removeItem('chat_model')
  router.push('/login')
}

function onKeySaved() {
  loadModels()
}

// 持久化选中状态
watch(currentConv, (v) => {
  if (v) localStorage.setItem('chat_conv_id', v.id)
  else localStorage.removeItem('chat_conv_id')
})
watch(currentModel, (v) => {
  if (v) localStorage.setItem('chat_model', v.model_name)
})

onMounted(() => {
  applyTheme()
  loadModels()
  loadConversations()
})
</script>

<style scoped>
.chat-page {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

/* ─── 左侧边栏 ─── */
.sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  transition: width .2s ease;
  overflow: hidden;
}
.sidebar.collapsed {
  width: 0;
  border-right: none;
}
.sidebar-footer {
  flex-shrink: 0;
  padding: 10px 12px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 6px;
}
.footer-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: .85rem;
  transition: background .15s;
}
.footer-btn:hover { background: var(--bg-hover); }
.footer-icon { font-size: 1rem; }

/* ─── 主区域 ─── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}
.main-header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
}
.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 120px;
}
.header-right { justify-content: flex-end; }

/* 通用 icon 按钮 */
.btn-icon {
  width: 34px; height: 34px;
  display: flex; align-items: center; justify-content: center;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 1.05rem;
  transition: background .15s, color .15s;
}
.btn-icon:hover { background: var(--bg-hover); color: var(--text-primary); }

/* 文字按钮 */
.btn-header-text {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: .85rem;
  transition: background .15s;
  white-space: nowrap;
}
.btn-header-text:hover { background: var(--bg-hover); color: var(--text-primary); }

/* 顶部 ⋯ 下拉菜单 */
.hm-wrap { position: relative; }
.hm-dropdown {
  position: absolute;
  right: 0; top: calc(100% + 6px);
  min-width: 150px;
  background: var(--bg-modal);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  z-index: 90;
  padding: 4px 0;
}
.hm-item {
  display: block; width: 100%;
  padding: 10px 16px;
  background: transparent; border: none;
  color: var(--text-primary);
  font-size: .85rem;
  cursor: pointer; text-align: left;
  transition: background .1s;
}
.hm-item:hover { background: var(--bg-hover); }
.hm-danger { color: var(--danger); }
.hm-danger:hover { background: rgba(239,68,68,.08); }
.hm-backdrop { position: fixed; inset: 0; z-index: 80; }

/* toast */
.share-toast {
  position: absolute;
  top: 56px; left: 50%;
  transform: translateX(-50%);
  padding: 8px 20px;
  background: var(--accent); color: #fff;
  border-radius: 20px; font-size: .85rem;
  z-index: 95; white-space: nowrap;
  box-shadow: var(--shadow);
  animation: toastIn .3s ease;
}
@keyframes toastIn { from { opacity: 0; transform: translateX(-50%) translateY(-8px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }

.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.main-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-card { text-align: center; padding: 40px; }
.empty-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.empty-sub {
  color: var(--text-secondary);
  font-size: .95rem;
  margin-bottom: 20px;
}
.btn-accent {
  padding: 10px 24px;
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: .9rem;
  font-weight: 600;
}
.btn-accent:hover { background: var(--accent-hover); }
</style>
