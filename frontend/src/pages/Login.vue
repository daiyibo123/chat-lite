<template>
  <div class="login-page">
    <div class="login-card">
      <h1>Chat Lite</h1>
      <div class="tabs">
        <button type="button" class="active">sub2api 登录</button>
      </div>

      <button type="button" class="sso-btn" :disabled="ssoLoading" @click="handleSsoLogin">
        <span v-if="ssoLoading" class="spinner"></span>
        {{ ssoLoading ? '正在通过 sub2api 登录…' : '🔐 用 sub2api 一键登录' }}
      </button>
      <div class="divider"><span>或使用账号密码</span></div>

      <form @submit.prevent="handleSubmit">
        <div class="field">
          <label>邮箱</label>
          <input v-model="form.email" type="email" placeholder="请输入 sub2api 邮箱" autocomplete="email" />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request.js'

const router = useRouter()
const loading = ref(false)
const ssoLoading = ref(false)
const error = ref('')
const form = reactive({ email: '', password: '' })

// sub2api 桥接页地址（部署后可根据需要修改）
const SUB2API_BRIDGE_URL = 'https://www.dai1bo.tech/sso-bridge.html'

let ssoPopup = null
let ssoTimer = null
let messageHandler = null

function cleanupSso() {
  if (ssoTimer) { clearInterval(ssoTimer); ssoTimer = null }
  if (messageHandler) { window.removeEventListener('message', messageHandler); messageHandler = null }
  ssoPopup = null
}

async function exchangeToken(subToken) {
  ssoLoading.value = true
  try {
    const res = await request.post('/api/auth/sub2api-sso', { access_token: subToken })
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('username', res.data.user.username)
    router.push('/chat')
  } catch (e) {
    error.value = e.response?.data?.detail || 'sub2api 登录态验证失败'
  } finally {
    ssoLoading.value = false
  }
}

async function handleSsoLogin() {
  error.value = ''
  cleanupSso()
  ssoLoading.value = true

  const origin = window.location.origin
  const url = `${SUB2API_BRIDGE_URL}?origin=${encodeURIComponent(origin)}`
  ssoPopup = window.open(url, 'sub2api_sso', 'width=440,height=480,menubar=no,toolbar=no')
  if (!ssoPopup) {
    ssoLoading.value = false
    error.value = '弹窗被浏览器拦截，请允许本站弹窗后重试'
    return
  }

  // 监听 postMessage
  messageHandler = (e) => {
    try {
      const bridgeOrigin = new URL(SUB2API_BRIDGE_URL).origin
      if (e.origin !== bridgeOrigin) return
    } catch { return }
    if (!e.data || e.data.type !== 'sub2api_token') return
    const token = e.data.token
    cleanupSso()
    if (token) {
      exchangeToken(token)
    } else {
      ssoLoading.value = false
      error.value = '未获取到 sub2api 登录态'
    }
  }
  window.addEventListener('message', messageHandler)

  // 检测用户手动关闭弹窗
  ssoTimer = setInterval(() => {
    if (ssoPopup && ssoPopup.closed) {
      cleanupSso()
      if (ssoLoading.value) {
        ssoLoading.value = false
        if (!error.value) error.value = '已取消 sub2api 登录'
      }
    }
  }, 600)
}

onUnmounted(() => { cleanupSso() })

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    const res = await request.post('/api/auth/login', form)
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('username', res.data.user.username)
    router.push('/chat')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #1a1a2e;
}
.login-card {
  width: 360px;
  padding: 40px 32px;
  background: #16213e;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}
.login-card h1 {
  text-align: center;
  font-size: 1.8rem;
  margin-bottom: 22px;
  color: #e0e0e0;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.sso-btn {
  width: 100%;
  padding: 12px;
  background: #0f3460;
  color: #fff;
  border: 1px solid #1f4d8e;
  border-radius: 6px;
  font-size: 0.95rem;
  cursor: pointer;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background 0.2s;
}
.sso-btn:hover:not(:disabled) { background: #1f4d8e; }
.sso-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner {
  width: 14px; height: 14px;
  border: 2px solid #aaa;
  border-top-color: #e94560;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.divider {
  text-align: center;
  font-size: 0.75rem;
  color: #777;
  margin: 14px 0 18px;
  position: relative;
}
.divider::before, .divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 30%;
  height: 1px;
  background: #2a3a5e;
}
.divider::before { left: 0; }
.divider::after { right: 0; }
.divider span { background: #16213e; padding: 0 8px; }
.tabs button {
  background: #0f3460;
  color: #aaa;
}
.tabs button.active {
  background: #e94560;
  color: #fff;
}
.field {
  margin-bottom: 20px;
}
.field label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.9rem;
  color: #aaa;
}
.field input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #0f3460;
  color: #e0e0e0;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}
.field input:focus {
  border-color: #e94560;
}
.error {
  color: #e94560;
  font-size: 0.85rem;
  margin-bottom: 12px;
}
form > button {
  width: 100%;
  padding: 12px;
  background: #e94560;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}
form > button:hover:not(:disabled) {
  background: #c73650;
}
form > button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
