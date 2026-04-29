import axios from 'axios'

const request = axios.create({
  baseURL: '',
  timeout: 120000,
})

// admin 页面用 admin_token
request.interceptors.request.use((config) => {
  const adminToken = localStorage.getItem('admin_token')
  if (adminToken && config.url?.startsWith('/api/admin')) {
    config.headers.Authorization = `Bearer ${adminToken}`
  }
  return config
})

export default request
