import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import AttendancePage from '../views/AttendancePage.vue'
import AttendanceRecords from '../views/AttendanceRecords.vue'
import StudentRegister from '../views/StudentRegister.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import ClassManagement from '../views/ClassManagement.vue'
import AttendanceRules from '../views/AttendanceRules.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresGuest: true }
  },
  {
    path: '/attendance',
    name: 'Attendance',
    component: AttendancePage,
    meta: { requiresAuth: true }
  },
  {
    path: '/records',
    name: 'Records',
    component: AttendanceRecords,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/attendance-records',
    name: 'TeacherAttendanceRecords',
    component: AttendanceRecords,
    meta: { requiresAuth: true, role: 'teacher' }
  },
  {
    path: '/student-register',
    name: 'StudentRegister',
    component: StudentRegister,
    meta: { requiresAuth: true, role: 'student' }
  },
  {
    path: '/admin/classes',
    name: 'ClassManagement',
    component: ClassManagement,
    meta: { requiresAuth: true, role: 'teacher' }
  },
  {
    path: '/admin/attendance-rules',
    name: 'AttendanceRules',
    component: AttendanceRules,
    meta: { requiresAuth: true, role: 'teacher' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL || '/'),
  routes
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const userRole = localStorage.getItem('userRole')
  const isAuthenticated = !!token

  // 需要认证的路由，但用户未登录
  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
    return
  }

  // 需要游客身份的路由（如登录页），但用户已登录
  if (to.meta.requiresGuest && isAuthenticated) {
    next('/')
    return
  }

  // 需要特定角色的路由
  if (to.meta.role && to.meta.role !== userRole) {
    next('/')
    return
  }

  next()
})

export default router 