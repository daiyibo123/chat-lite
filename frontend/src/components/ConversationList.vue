<template>
  <div class="conv-list">
    <button class="btn-new" @click="handleNew">
      <span class="btn-new-icon">+</span>
      <span>新对话</span>
    </button>

    <div class="list">
      <div
        v-for="c in conversations"
        :key="c.id"
        class="conv-item"
        :class="{ active: modelValue?.id === c.id }"
        @click="$emit('update:modelValue', c)"
      >
        <span class="conv-title">{{ c.title }}</span>
        <div class="conv-more-wrap" :class="{ 'menu-open': openMenuId === c.id }">
          <button class="btn-more" @click.stop="toggleMenu($event, c.id)" title="更多">⋯</button>
        </div>
      </div>
    </div>

    <p v-if="!conversations.length" class="empty">新建一个对话开始聊天</p>

    <!-- 菜单背景遮罩 + 固定菜单 -->
    <div v-if="openMenuId !== null" class="menu-backdrop" @click="closeMenu"></div>
    <div v-if="openMenuId !== null" class="conv-menu" :style="menuStyle">
      <button class="menu-item" @click.stop="doExportMd">导出 Markdown</button>
      <button class="menu-item" @click.stop="doExportPdf">导出 PDF</button>
      <button class="menu-item" @click.stop="doExportJson">导出 JSON</button>
      <button class="menu-item menu-danger" @click.stop="doDelete">删除</button>
    </div>

    <!-- 对话数量上限弹窗 -->
    <div v-if="showLimitModal" class="limit-overlay" @click.self="showLimitModal = false">
      <div class="limit-modal">
        <h3>对话数量已满</h3>
        <p class="limit-hint">最多保留 10 个对话，请选择一个删除后再新建：</p>
        <div class="limit-list">
          <div
            v-for="c in conversations"
            :key="c.id"
            class="limit-item"
            @click="deleteFromLimit(c)"
          >
            <span class="limit-title">{{ c.title }}</span>
            <span class="limit-del">删除</span>
          </div>
        </div>
        <button class="limit-cancel" @click="showLimitModal = false">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import request from '../api/request.js'

const props = defineProps({
  conversations: { type: Array, default: () => [] },
  modelValue: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'refresh'])
const showLimitModal = ref(false)
const openMenuId = ref(null)
const menuStyle = ref({})

function toggleMenu(event, id) {
  if (openMenuId.value === id) {
    openMenuId.value = null
    return
  }
  const btn = event.currentTarget
  const rect = btn.getBoundingClientRect()
  menuStyle.value = {
    top: rect.bottom + 4 + 'px',
    left: Math.min(rect.left, window.innerWidth - 170) + 'px',
  }
  openMenuId.value = id
}
function closeMenu() {
  openMenuId.value = null
}
function getOpenConv() {
  return props.conversations.find(c => c.id === openMenuId.value)
}
function doExportMd() { const c = getOpenConv(); closeMenu(); if (c) exportMd(c) }
function doExportPdf() { const c = getOpenConv(); closeMenu(); if (c) exportPdf(c) }
function doExportJson() { const c = getOpenConv(); closeMenu(); if (c) exportJson(c) }
function doDelete() { const c = getOpenConv(); if (c) handleDelete(c) }

async function handleNew() {
  try {
    const res = await request.post('/api/conversations')
    emit('refresh')
    emit('update:modelValue', res.data)
  } catch (e) {
    if (e.response?.status === 409) {
      showLimitModal.value = true
    }
  }
}

async function deleteFromLimit(c) {
  try {
    await request.delete(`/api/conversations/${c.id}`)
    if (props.modelValue?.id === c.id) {
      emit('update:modelValue', null)
    }
    emit('refresh')
    showLimitModal.value = false
    await handleNew()
  } catch {}
}

async function handleDelete(c) {
  closeMenu()
  if (!confirm(`确定删除对话「${c.title}」？`)) return
  try {
    await request.delete(`/api/conversations/${c.id}`)
    emit('refresh')
    if (props.modelValue?.id === c.id) {
      emit('update:modelValue', null)
    }
  } catch {}
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function exportMd(c) {
  try {
    const res = await request.get(`/api/conversations/${c.id}/export/md`, { responseType: 'blob' })
    downloadBlob(res.data, `conversation-${c.id}.md`)
  } catch {}
}

async function exportJson(c) {
  try {
    const res = await request.get(`/api/conversations/${c.id}/export/json`, { responseType: 'blob' })
    downloadBlob(res.data, `conversation-${c.id}.json`)
  } catch {}
}

async function exportPdf(c) {
  try {
    const res = await request.get(`/api/conversations/${c.id}/export/pdf`, { responseType: 'blob' })
    downloadBlob(res.data, `conversation-${c.id}.pdf`)
  } catch {}
}
</script>

<style scoped>
.conv-list {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.btn-new {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px;
  padding: 12px 14px;
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  font-size: .9rem;
  transition: background .15s;
}
.btn-new:hover { background: var(--bg-hover); }
.btn-new-icon { font-size: 1.1rem; font-weight: 300; }

.list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.conv-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 2px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .15s;
}
.conv-item:hover { background: var(--bg-hover); }
.conv-item.active { background: var(--bg-active); }

.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-size: .875rem;
}

/* ⋯ 按钮 */
.conv-more-wrap {
  position: relative;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity .15s;
}
.conv-item:hover .conv-more-wrap,
.conv-more-wrap.menu-open { opacity: 1; }

.btn-more {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1.1rem;
  font-weight: 700;
}
.btn-more:hover { color: var(--text-primary); background: var(--bg-active); }

/* 下拉菜单 */
.conv-menu {
  position: fixed;
  min-width: 150px;
  background: var(--bg-modal);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  z-index: 200;
  padding: 4px 0;
}
.menu-item {
  display: block;
  width: 100%;
  padding: 10px 16px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: .85rem;
  cursor: pointer;
  text-align: left;
  transition: background .1s;
}
.menu-item:hover { background: var(--bg-hover); }
.menu-danger { color: var(--danger); }
.menu-danger:hover { background: rgba(239,68,68,.08); }

.menu-backdrop {
  position: fixed; inset: 0; z-index: 150;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 20px;
  font-size: .85rem;
}

/* ─── 上限弹窗 ─── */
.limit-overlay {
  position: fixed; inset: 0;
  background: var(--bg-overlay);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.limit-modal {
  width: 400px;
  background: var(--bg-modal);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: var(--shadow-lg);
}
.limit-modal h3 {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--text-primary);
}
.limit-hint {
  color: var(--text-secondary);
  font-size: .85rem;
  margin-bottom: 16px;
}
.limit-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 240px;
  overflow-y: auto;
}
.limit-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .15s;
}
.limit-item:hover { background: var(--bg-hover); }
.limit-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-size: .9rem;
}
.limit-del {
  color: var(--danger);
  font-size: .8rem;
  font-weight: 600;
  flex-shrink: 0;
  margin-left: 12px;
}
.limit-cancel {
  display: block;
  width: 100%;
  margin-top: 12px;
  padding: 10px;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font-size: .9rem;
}
.limit-cancel:hover { background: var(--bg-hover); }
</style>
