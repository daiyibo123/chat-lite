<template>
  <div class="login-page">
    <div class="login-card">
      <h1>Chat Lite</h1>
      <div class="tabs">
        <button type="button" class="active">sub2api 登录</button>
      </div>
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
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}
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
button {
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
button:hover:not(:disabled) {
  background: #c73650;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
