<template>
  <div class="login-page">
    <div class="login-card">
      <h1>Chat Lite</h1>

      <button type="button" class="sso-btn" disabled title="sub2api 登录服务暂时不可用">
        🔐 sub2api 一键登录（暂不可用）
      </button>
      <div class="divider"><span>使用账号密码登录</span></div>

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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request.js'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const form = reactive({ email: '', password: '' })

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
.sso-btn {
  width: 100%;
  padding: 12px;
  background: #1a2a4a;
  color: #fff;
  border: 1px solid #2a3a5e;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: not-allowed;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  opacity: 0.4;
}
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
