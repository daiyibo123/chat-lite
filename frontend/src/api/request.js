import axios from 'axios'

const request = axios.create({
  baseURL: '',
  timeout: 120000,
})

request.interceptors.request.use((config) => {
  const adminToken = localStorage.getItem('admin_token')
  const token = localStorage.getItem('token')
  if (adminToken && config.url?.startsWith('/api/admin')) {
    config.headers.Authorization = `Bearer ${adminToken}`
  } else if (token && config.url?.startsWith('/api') && !config.url?.startsWith('/api/auth')) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.startsWith('/api/admin')) {
      localStorage.removeItem('token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default request
