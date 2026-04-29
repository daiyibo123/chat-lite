<template>
  <div class="admin-page">
    <!-- 未登录：账号+密码 -->
    <div v-if="!adminToken" class="admin-login">
      <div class="login-card">
        <h1>管理后台</h1>
        <form @submit.prevent="handleAdminLogin">
          <div class="field">
            <label>管理员账号</label>
            <input v-model="username" placeholder="请输入管理员账号" />
          </div>
          <div class="field">
            <label>管理员密码</label>
            <input v-model="password" type="password" placeholder="请输入管理员密码" />
          </div>
          <p v-if="loginError" class="error">{{ loginError }}</p>
          <button type="submit">进入后台</button>
        </form>
      </div>
    </div>

    <!-- 已登录：模型管理 -->
    <div v-else class="admin-main">
      <header class="admin-header">
        <h2>模型管理</h2>
        <div class="header-actions">
          <button class="btn-primary" @click="openAdd">+ 新增模型</button>
          <button class="btn-logout" @click="adminLogout">退出后台</button>
        </div>
      </header>

      <section class="key-control-panel">
        <div class="panel-title">API Key 输入框控制</div>
        <div class="key-switches">
          <div class="key-switch-card" v-for="item in keyControlItems" :key="item.type">
            <div>
              <div class="key-switch-title">{{ item.label }}</div>
              <div class="key-switch-desc">{{ keySettings[item.type]?.enabled === false ? keySettings[item.type]?.message : '用户可以填写该公司 API Key' }}</div>
            </div>
            <button
              :class="keySettings[item.type]?.enabled === false ? 'switch-btn off' : 'switch-btn on'"
              @click="toggleKeyInput(item.type)"
            >
              {{ keySettings[item.type]?.enabled === false ? '已关闭 · 点击开启' : '已开启 · 点击关闭' }}
            </button>
          </div>
        </div>
      </section>

      <!-- 模型表格 -->
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>排序</th>
              <th>显示名</th>
              <th>模型名</th>
              <th>公司</th>
              <th>接口类型</th>
              <th>Key 类型</th>
              <th>上下文</th>
              <th>生图</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in models" :key="m.id">
              <td>{{ m.sort_order }}</td>
              <td>{{ m.display_name }}</td>
              <td><code>{{ m.model_name }}</code></td>
              <td>{{ m.company_type }}</td>
              <td>{{ m.endpoint_type }}</td>
              <td>{{ m.required_key_type }}</td>
              <td>{{ (m.context_limit / 1000).toFixed(0) }}K</td>
              <td>{{ m.support_image ? '是' : '否' }}</td>
              <td>
                <span :class="m.enabled ? 'tag-on' : 'tag-off'" @click="toggleEnabled(m)">
                  {{ m.enabled ? '启用中 · 点击关闭' : '维护中 · 点击开启' }}
                </span>
              </td>
              <td class="actions">
                <button class="btn-sm" @click="openEdit(m)">编辑</button>
                <button class="btn-sm btn-danger" @click="handleDelete(m)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 弹窗：新增 / 编辑 -->
      <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
        <div class="modal">
          <h3>{{ isEdit ? '编辑模型' : '新增模型' }}</h3>
          <form @submit.prevent="handleSave">
            <div class="form-grid">
              <div class="field">
                <label>显示名</label>
                <input v-model="form.display_name" required />
              </div>
              <div class="field">
                <label>模型名（请求用）</label>
                <input v-model="form.model_name" required />
              </div>
              <div class="field">
                <label>公司类型</label>
                <select v-model="form.company_type">
                  <option value="openai">openai</option>
                  <option value="claude">claude</option>
                  <option value="gemini">gemini</option>
                </select>
              </div>
              <div class="field">
                <label>接口类型</label>
                <select v-model="form.endpoint_type">
                  <option value="openai_chat">openai_chat</option>
                  <option value="anthropic">anthropic</option>
                  <option value="gemini">gemini</option>
                  <option value="openai_image">openai_image</option>
                </select>
              </div>
              <div class="field full">
                <label>接口地址</label>
                <input v-model="form.endpoint_url" />
              </div>
              <div class="field">
                <label>所需 Key</label>
                <select v-model="form.required_key_type">
                  <option value="openai_key">openai_key</option>
                  <option value="claude_key">claude_key</option>
                  <option value="gemini_key">gemini_key</option>
                </select>
              </div>
              <div class="field">
                <label>上下文限制</label>
                <input v-model.number="form.context_limit" type="number" />
              </div>
              <div class="field">
                <label>排序</label>
                <input v-model.number="form.sort_order" type="number" />
              </div>
              <div class="field row-check">
                <label><input type="checkbox" v-model="form.enabled" /> 启用</label>
                <label><input type="checkbox" v-model="form.support_image" /> 支持生图</label>
              </div>
            </div>
            <p v-if="formError" class="error">{{ formError }}</p>
            <div class="modal-actions">
              <button type="button" class="btn-cancel" @click="showModal = false">取消</button>
              <button type="submit" class="btn-primary">保存</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request.js'

const router = useRouter()

const adminToken = ref(localStorage.getItem('admin_token') || '')
const username = ref('')
const password = ref('')
const loginError = ref('')

const models = ref([])
const keySettings = ref({})
const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formError = ref('')

const emptyForm = () => ({
  display_name: '',
  model_name: '',
  company_type: 'openai',
  endpoint_type: 'openai_chat',
  endpoint_url: '',
  required_key_type: 'openai_key',
  enabled: true,
  context_limit: 200000,
  support_image: false,
  sort_order: 0,
})
const form = reactive(emptyForm())
const keyControlItems = [
  { type: 'openai_key', label: 'OpenAI Key 输入框' },
  { type: 'claude_key', label: 'Claude Key 输入框' },
  { type: 'gemini_key', label: 'Gemini Key 输入框' },
]

function adminHeaders() {
  return { Authorization: `Bearer ${adminToken.value}` }
}

async function handleAdminLogin() {
  loginError.value = ''
  try {
    const res = await request.post('/api/admin/login', { username: username.value, password: password.value })
    adminToken.value = res.data.admin_token
    localStorage.setItem('admin_token', adminToken.value)
    await loadModels()
    await loadKeySettings()
    router.push('/admin')
  } catch (e) {
    loginError.value = e.response?.data?.detail || '登录失败'
  }
}

function adminLogout() {
  adminToken.value = ''
  localStorage.removeItem('admin_token')
  router.push('/chat')
}

async function loadModels() {
  try {
    const res = await request.get('/api/admin/models', { headers: adminHeaders() })
    models.value = res.data
  } catch (e) {
    if (e.response?.status === 401) { adminLogout() }
  }
}

async function loadKeySettings() {
  try {
    const res = await request.get('/api/admin/key-input-settings', { headers: adminHeaders() })
    keySettings.value = res.data
  } catch (e) {
    if (e.response?.status === 401) { adminLogout() }
  }
}

async function toggleKeyInput(keyType) {
  const current = keySettings.value[keyType]?.enabled !== false
  await request.put(
    `/api/admin/key-input-settings/${keyType}`,
    { enabled: !current, message: '该模型正在修复中.....' },
    { headers: adminHeaders() }
  )
  await loadKeySettings()
  await loadModels()
}

function openAdd() {
  Object.assign(form, emptyForm())
  isEdit.value = false
  editId.value = null
  formError.value = ''
  showModal.value = true
}

function openEdit(m) {
  Object.assign(form, {
    display_name: m.display_name,
    model_name: m.model_name,
    company_type: m.company_type,
    endpoint_type: m.endpoint_type,
    endpoint_url: m.endpoint_url || '',
    required_key_type: m.required_key_type,
    enabled: m.enabled,
    context_limit: m.context_limit,
    support_image: m.support_image,
    sort_order: m.sort_order,
  })
  isEdit.value = true
  editId.value = m.id
  formError.value = ''
  showModal.value = true
}

async function handleSave() {
  formError.value = ''
  try {
    if (isEdit.value) {
      await request.put(`/api/admin/models/${editId.value}`, form, { headers: adminHeaders() })
    } else {
      await request.post('/api/admin/models', form, { headers: adminHeaders() })
    }
    showModal.value = false
    await loadModels()
  } catch (e) {
    formError.value = e.response?.data?.detail || '保存失败'
  }
}

async function toggleEnabled(m) {
  await request.put(`/api/admin/models/${m.id}`, { enabled: !m.enabled }, { headers: adminHeaders() })
  await loadModels()
}

async function handleDelete(m) {
  if (!confirm(`确定删除模型「${m.display_name}」？`)) return
  await request.delete(`/api/admin/models/${m.id}`, { headers: adminHeaders() })
  await loadModels()
}

onMounted(() => {
  if (adminToken.value) {
    loadModels()
    loadKeySettings()
  }
})
</script>

<style scoped>
.admin-page { min-height: 100vh; background: #1a1a2e; }

/* ---- 登录 ---- */
.admin-login {
  display: flex; align-items: center; justify-content: center; min-height: 100vh;
}
.login-card {
  width: 360px; padding: 40px 32px; background: #16213e;
  border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,.4);
}
.login-card h1 { text-align: center; margin-bottom: 24px; color: #e0e0e0; }

/* ---- 主体 ---- */
.admin-main { padding: 24px 32px; }
.admin-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
}
.admin-header h2 { color: #e0e0e0; }
.header-actions { display: flex; gap: 10px; }

/* ---- Key 输入框控制 ---- */
.key-control-panel {
  background: #16213e;
  border: 1px solid #1e2a4a;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 18px;
}
.panel-title {
  color: #e0e0e0;
  font-weight: 700;
  margin-bottom: 12px;
}
.key-switches {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.key-switch-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  background: #0f3460;
  border: 1px solid #22345f;
  border-radius: 10px;
  padding: 12px;
}
.key-switch-title {
  color: #e0e0e0;
  font-weight: 600;
  font-size: .9rem;
}
.key-switch-desc {
  color: #aaa;
  font-size: .78rem;
  margin-top: 4px;
}
.switch-btn {
  flex-shrink: 0;
  border: none;
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: .78rem;
  white-space: nowrap;
}
.switch-btn.on {
  color: #4ade80;
  background: rgba(74,222,128,.12);
}
.switch-btn.off {
  color: #f87171;
  background: rgba(248,113,113,.12);
}

/* ---- 表格 ---- */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td {
  padding: 10px 12px; text-align: left; border-bottom: 1px solid #1e2a4a;
}
th { background: #16213e; color: #aaa; font-weight: 600; }
td { color: #ddd; }
code { background: #0f3460; padding: 2px 6px; border-radius: 4px; font-size: .85rem; }
.tag-on {
  color: #4ade80; cursor: pointer; background: rgba(74,222,128,.12);
  padding: 2px 10px; border-radius: 10px; font-size: .8rem;
}
.tag-off {
  color: #f87171; cursor: pointer; background: rgba(248,113,113,.12);
  padding: 2px 10px; border-radius: 10px; font-size: .8rem;
}
.actions { display: flex; gap: 6px; }

/* ---- 按钮 ---- */
.btn-primary {
  padding: 8px 18px; background: #e94560; color: #fff; border: none;
  border-radius: 6px; cursor: pointer; font-size: .9rem;
}
.btn-primary:hover { background: #c73650; }
.btn-logout {
  padding: 8px 18px; background: transparent; color: #aaa; border: 1px solid #333;
  border-radius: 6px; cursor: pointer; font-size: .9rem;
}
.btn-sm {
  padding: 4px 12px; background: #0f3460; color: #ddd; border: 1px solid #333;
  border-radius: 4px; cursor: pointer; font-size: .8rem;
}
.btn-sm:hover { background: #16213e; }
.btn-danger { color: #f87171; border-color: #f87171; }
.btn-danger:hover { background: rgba(248,113,113,.15); }
.btn-cancel {
  padding: 8px 18px; background: transparent; color: #aaa; border: 1px solid #444;
  border-radius: 6px; cursor: pointer;
}

/* ---- 弹窗 ---- */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.6);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  width: 560px; max-height: 85vh; overflow-y: auto; background: #16213e;
  border-radius: 12px; padding: 28px 32px;
}
.modal h3 { margin-bottom: 20px; color: #e0e0e0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.full { grid-column: 1 / -1; }
.row-check { grid-column: 1 / -1; display: flex; gap: 24px; align-items: center; }
.row-check label { display: flex; align-items: center; gap: 6px; color: #ccc; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }

/* ---- 表单通用 ---- */
.field { display: flex; flex-direction: column; }
.field label { margin-bottom: 4px; font-size: .85rem; color: #aaa; }
.field input, .field select {
  padding: 8px 10px; border: 1px solid #333; border-radius: 6px;
  background: #0f3460; color: #e0e0e0; font-size: .9rem; outline: none;
}
.field input:focus, .field select:focus { border-color: #e94560; }
.error { color: #e94560; font-size: .85rem; margin: 8px 0; }
</style>
