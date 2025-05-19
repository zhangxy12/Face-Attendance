<template>
  <div id="app">
    <header class="main-header">
      <nav class="main-nav">
        <router-link to="/" class="logo">
          <span class="logo-text">Face Attendance</span>
        </router-link>
        
        <!-- 未登录状态的导航 -->
        <div v-if="!isLoggedIn" class="btn-group">
          <router-link to="/" class="btn left">首页</router-link>
          <router-link to="/login" class="btn middle">登录</router-link>
          <router-link to="/register" class="btn right">注册</router-link>
        </div>
        
        <!-- 学生导航 -->
        <div v-else-if="userRole === 'student'" class="btn-group">
          <router-link to="/" class="btn left">首页</router-link>
          <router-link to="/attendance" class="btn middle">考勤打卡</router-link>
          <router-link to="/records" class="btn middle">考勤记录</router-link>
          <router-link to="/student-register" class="btn right">人脸注册</router-link>
        </div>
        
        <!-- 教师导航 -->
        <div v-else-if="userRole === 'teacher'" class="btn-group">
          <router-link to="/" class="btn left">首页</router-link>
          <!-- <router-link to="/admin/students" class="btn middle">学生管理</router-link> -->
          <router-link to="/admin/classes" class="btn middle">班级管理</router-link>
          <router-link to="/admin/attendance-records" class="btn middle">考勤记录</router-link>
          <!-- <router-link to="/admin/attendance-rules" class="btn middle">考勤规则</router-link> -->
      
        </div>
        
        <!-- 用户信息和登出 -->
        <div v-if="isLoggedIn" class="user-info">
          <span class="user-name">{{ realName }}</span>
          <span class="user-role">{{ userRoleText }}</span>
          <button class="logout-btn" @click="logout">退出登录</button>
        </div>
      </nav>
    </header>
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

export default {
  setup() {
    const router = useRouter()
    const token = ref(localStorage.getItem('token') || '')
    const userRole = ref(localStorage.getItem('userRole') || '')
    const userId = ref(localStorage.getItem('userId') || '')
    const realName = ref(localStorage.getItem('realName') || '')
    
    const isLoggedIn = computed(() => !!token.value)
    
    const userRoleText = computed(() => {
      if (userRole.value === 'teacher') return '教师'
      if (userRole.value === 'student') return '学生'
      return ''
    })
    
    // 检查令牌有效性
    const checkToken = () => {
      // 获取localStorage中的token
      const currentToken = localStorage.getItem('token')
      
      // 如果没有token，无需进一步验证
      if (!currentToken) {
        return
      }
      
      try {
        // 解析JWT令牌（不验证签名）
        const tokenParts = currentToken.split('.')
        if (tokenParts.length !== 3) {
          // 令牌格式无效，直接登出
          console.error('无效的令牌格式')
          logout()
          return
        }
        
        // 解码令牌载荷部分
        const payload = JSON.parse(atob(tokenParts[1]))
        
        // 检查令牌是否过期
        if (payload.exp) {
          const expirationTime = payload.exp * 1000 // 转换为毫秒
          const currentTime = Date.now()
          
          if (currentTime >= expirationTime) {
            // 令牌已过期，执行登出
            console.error('令牌已过期')
            logout()
            return
          }
          
          // 如果令牌快过期（比如30分钟内），可以在这里添加刷新令牌的逻辑
          const thirtyMinutes = 30 * 60 * 1000
          if (expirationTime - currentTime < thirtyMinutes) {
            console.log('令牌即将过期，应考虑刷新')
            // 这里可以调用刷新令牌的API
            // refreshToken()
          }
        }
      } catch (error) {
        // 解析过程中出现错误，说明令牌无效
        console.error('令牌解析错误:', error)
        logout()
      }
    }
    
    // 登出
    const logout = () => {
      localStorage.removeItem('token')
      localStorage.removeItem('userRole')
      localStorage.removeItem('userId')
      localStorage.removeItem('realName')
      
      token.value = ''
      userRole.value = ''
      userId.value = ''
      realName.value = ''
      
      // 跳转到登录页
      router.push('/login')
    }
    
    onMounted(() => {
      checkToken()
    })
    
    return {
      isLoggedIn,
      userRole,
      realName,
      userRoleText,
      logout
    }
  }
}
</script>

<style>
/* Reset CSS */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* Hide scrollbar for Chrome, Safari and Opera */
::-webkit-scrollbar {
  display: none;
}

/* Hide scrollbar for IE, Edge and Firefox */
* {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}

/* Global styles */
:root {
  --primary-color: #0071e3;
  --text-color: #1d1d1f;
  --secondary-text: #86868b;
  --background-light: #f5f5f7;
  --nav-height: 60px;
  --nav-background: rgba(255, 255, 255, 0.9);
  --section-padding: 4rem 2rem;
  --content-max-width: 1400px;
}

html, body {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Icons', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 16px;
  line-height: 1.5;
  color: var(--text-color);
  overflow-x: hidden; /* 防止水平滚动 */
}

body {
  background-color: var(--background-light);
}

#app {
  width: 100vw; /* 确保宽度为视口宽度 */
  height: 100%;
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  overflow-x: hidden; /* 防止右侧留白 */
}

/* Header styles */
.main-header {
  width: 100%;
  position: fixed;
  height: var(--nav-height);
  background: var(--nav-background);
  z-index: 999;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  top: 0;
  left: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.main-nav {
  width: 100%;
  height: 100%;
  max-width: 100%; /* 防止超出屏幕宽度 */
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  text-decoration: none;
  color: var(--text-color);
  font-weight: 600;
  font-size: 1.8rem;
  letter-spacing: -0.5px;
}

.logo-text {
  background: linear-gradient(135deg, var(--text-color) 0%, #666 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* User info styles */
.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 20px;
}

.user-name {
  font-weight: 600;
  color: var(--text-color);
}

.user-role {
  font-size: 0.85rem;
  color: var(--secondary-text);
  background-color: #f0f0f0;
  padding: 2px 8px;
  border-radius: 12px;
}

.logout-btn {
  background-color: #f0f0f0;
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 14px;
  color: #e11d48;
  cursor: pointer;
  transition: all 0.2s ease;
}

.logout-btn:hover {
  background-color: #fee2e2;
}

/* Button group styles */
.btn-group {
  display: flex;
  gap: 0;
  text-align: center;
}

.btn {
  font: inherit;
  background-color: #f0f0f0;
  border: 0;
  color: #242424;
  font-size: 1.15rem;
  padding: 0.375em 1em;
  text-shadow: 0 0.0625em 0 #fff;
  box-shadow: inset 0 0.0625em 0 0 #f4f4f4, 0 0.0625em 0 0 #efefef,
    0 0.125em 0 0 #f4f3f3, 0 0.25em 0 0 #f0eeee, 0 0.3125em 0 0 #e8e7e7,
    0 0.375em 0 0 #dcdcdc, 0 0.425em 0 0 #cacaca, 0 0.425em 0.5em 0 #cecece;
  transition: 0.23s ease;
  cursor: pointer;
  font-weight: bold;
  text-align: center;
  
  text-decoration: none;
  display: inline-block;
}

.middle {
  border-radius: 0px;
}

.right {
  border-top-right-radius: 0.5em;
  border-bottom-right-radius: 0.5em;
}

.left {
  border-top-left-radius: 0.5em;
  border-bottom-left-radius: 0.5em;
}

.btn:active {
  translate: 0 0.225em;
  box-shadow: inset 0 0.03em 0 0 #f4f4f4, 0 0.03em 0 0 #efefef,
    0 0.0625em 0 0 #ececec, 0 0.125em 0 0 #e0e0e0, 0 0.125em 0 0 #dedede,
    0 0.2em 0 0 #dcdcdc, 0 0.225em 0 0 #cacaca, 0 0.225em 0.375em 0 #cecece;
  letter-spacing: 0.1em;
  color: var(--primary-color);
}

.btn:focus {
  color: var(--primary-color);
}

.btn.router-link-active {
  color: var(--primary-color);
}

.btn:hover {
  color: var(--primary-color);
  text-decoration: none;
}

/* Main content styles */
.main-content {
  width: 100%;
  height: 100%;
  position: relative;
  margin: 0;
  overflow-x: hidden;
  max-width: 100%; /* 防止内容超出屏幕宽度 */
  padding-top: var(--nav-height);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive design */
@media (max-width: 768px) {
  .main-nav {
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .btn-group {
    flex-direction: column;
    gap: 0.5rem;
  }

  .btn {
    font-size: 1rem;
    padding: 0.5rem 1rem;
  }
  
  .user-info {
    margin-top: 10px;
    margin-left: 0;
  }
}

@media (max-width: 480px) {
  .logo-text {
    font-size: 1.5rem;
  }

  .btn {
    font-size: 0.9rem;
    padding: 0.4rem 0.8rem;
  }
}

/* 针对超高分辨率设备的媒体查询 */
@media (min-width: 2560px) {
  html {
    font-size: 18px; /* 增大基础字体大小 */
  }

  .main-nav {
    padding: 0 3rem; /* 增加导航栏的内边距 */
  }
}

/* Global utility classes */
.container {
  width: 100%;
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: 0 var(--section-padding);
}

/* Ensure all router views take full width */
.router-view {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  position: relative;
  z-index: 2;
  background: transparent;
}
</style>