<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h3>API Key 配置</h3>
      <p class="hint">填写 Key 后点击「测试并保存」，留空的 Key 不会被覆盖。有效期 7 天。</p>

      <div class="key-section" v-for="item in keyItems" :key="item.type">
        <div class="key-header">
          <span class="key-label">{{ item.label }}</span>
          <span v-if="availability[item.type]?.available === false" class="key-status maintenance">
            {{ availability[item.type]?.message || '该模型正在修复中.....' }}
          </span>
          <span v-if="status[item.type]?.configured" class="key-status ok">
            已配置 · {{ status[item.type].masked }} · 到期 {{ status[item.type].expires_at }}
          </span>
          <span v-else-if="availability[item.type]?.available !== false" class="key-status off">未配置</span>
        </div>
        <input
          v-model="form[item.type]"
          :placeholder="item.placeholder"
          type="password"
          :disabled="availability[item.type]?.available === false"
        />
        <p v-if="results[item.type]" :class="results[item.type].success ? 'msg ok' : 'msg fail'">
          {{ results[item.type].message }}
        </p>
      </div>

      <div class="modal-actions">
        <button class="btn-cancel" @click="$emit('close')">关闭</button>
        <button class="btn-primary" :disabled="saving" @click="handleSave">
          {{ saving ? '测试中…' : '测试并保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, defineEmits } from 'vue'
import request from '../api/request.js'

const emit = defineEmits(['close', 'saved'])

const keyItems = [
  { type: 'openai_key', label: 'OpenAI Key', placeholder: 'sk-...' },
  { type: 'claude_key', label: 'Claude Key', placeholder: 'sk-ant-...' },
  { type: 'gemini_key', label: 'Gemini Key', placeholder: 'AIza...' },
]

const form = reactive({ openai_key: '', claude_key: '', gemini_key: '' })
const status = ref({})
const availability = ref({})
const results = ref({})
const saving = ref(false)

async function loadStatus() {
  try {
    const [statusRes, availabilityRes] = await Promise.all([
      request.get('/api/keys/status'),
      request.get('/api/models/key-availability'),
    ])
    status.value = statusRes.data
    availability.value = availabilityRes.data
  } catch {}
}

async function handleSave() {
  saving.value = true
  results.value = {}
  try {
    const payload = {}
    for (const item of keyItems) {
      if (availability.value[item.type]?.available !== false) {
        payload[item.type] = form[item.type]
      }
    }
    const res = await request.post('/api/keys/save', payload)
    results.value = res.data
    // 清空已成功的输入框
    for (const k of Object.keys(res.data)) {
      if (res.data[k]?.success) form[k] = ''
    }
    await loadStatus()
    emit('saved')
  } catch (e) {
    results.value = { openai_key: { success: false, message: e.response?.data?.detail || '请求失败' } }
  } finally {
    saving.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: var(--bg-overlay);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  width: 520px; max-height: 85vh; overflow-y: auto; background: var(--bg-modal);
  border: 1px solid var(--border); border-radius: 16px; padding: 28px 32px;
  box-shadow: var(--shadow-lg);
}
.modal h3 { margin-bottom: 8px; color: var(--text-primary); }
.hint { color: var(--text-secondary); font-size: .85rem; margin-bottom: 20px; }

.key-section { margin-bottom: 18px; }
.key-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.key-label { font-size: .95rem; color: var(--text-primary); font-weight: 600; }
.key-status { font-size: .8rem; }
.key-status.ok { color: var(--accent); }
.key-status.off { color: var(--text-muted); }
.key-status.maintenance { color: var(--danger); font-weight: 600; }

.key-section input {
  width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px;
  background: var(--bg-input); color: var(--text-primary); font-size: .9rem; outline: none;
}
.key-section input:focus { border-color: var(--accent); }
.key-section input:disabled {
  opacity: .55;
  cursor: not-allowed;
  background: var(--bg-hover);
}

.msg { font-size: .8rem; margin-top: 4px; }
.msg.ok { color: var(--accent); }
.msg.fail { color: var(--danger); }

.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.btn-primary {
  padding: 10px 22px; background: var(--accent); color: #fff; border: none;
  border-radius: 20px; cursor: pointer; font-size: .9rem;
}
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.btn-cancel {
  padding: 10px 22px; background: transparent; color: var(--text-secondary); border: 1px solid var(--border);
  border-radius: 20px; cursor: pointer;
}
.btn-cancel:hover { background: var(--bg-hover); }
</style>
