import { createRouter, createWebHistory } from 'vue-router'
import Chat from './pages/Chat.vue'
import Admin from './pages/Admin.vue'
import ShareView from './pages/ShareView.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', name: 'Chat', component: Chat },
  { path: '/share/:shareId', name: 'Share', component: ShareView },
  { path: '/admin', name: 'Admin', component: Admin },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
