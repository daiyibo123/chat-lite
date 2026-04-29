import { createRouter, createWebHistory } from 'vue-router'
import Chat from './pages/Chat.vue'
import Admin from './pages/Admin.vue'
import ShareView from './pages/ShareView.vue'
import Login from './pages/Login.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/chat', name: 'Chat', component: Chat, meta: { requiresAuth: true } },
  { path: '/share/:shareId', name: 'Share', component: ShareView },
  { path: '/admin', name: 'Admin', component: Admin },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !localStorage.getItem('token')) {
    return '/login'
  }
  if (to.path === '/login' && localStorage.getItem('token')) {
    return '/chat'
  }
})

export default router
