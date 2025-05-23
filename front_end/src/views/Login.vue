<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>学生校园人脸考勤系统</h1>
        <h2>用户登录</h2>
      </div>
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">姓名</label>
          <input 
            type="text" 
            id="username" 
            v-model="username" 
            placeholder="请输入姓名"
            required
          />
        </div>
        <div class="form-group">
          <label for="password">密码</label>
          <input 
            type="password" 
            id="password" 
            v-model="password" 
            placeholder="请输入密码"
            required
          />
        </div>
        <div class="form-actions">
          <button 
            type="submit" 
            class="btn-login" 
            :disabled="isLoading"
          >
            {{ isLoading ? '登录中...' : '登录' }}
          </button>
        </div>
      </form>
      <div class="register-link">
        <p>还没有账号？ <router-link to="/register">立即注册</router-link></p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'LoginView',
  emits: ['login-success'],
  setup(props, { emit }) {
    const router = useRouter()
    const username = ref('')
    const password = ref('')
    const errorMessage = ref('')
    const isLoading = ref(false)

    const handleLogin = async () => {
      if (!username.value || !password.value) {
        errorMessage.value = '请输入用户名和密码'
        return
      }

      try {
        isLoading.value = true
        errorMessage.value = ''
        
        // 创建表单数据
        const formData = new FormData()
        formData.append('username', username.value)
        formData.append('password', password.value)
        
        // 调用登录API
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          body: formData
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.detail || '登录失败，请检查用户名和密码')
        }
        
        // 保存登录信息到 localStorage
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('userRole', data.user_role)
        localStorage.setItem('userId', data.user_id)
        localStorage.setItem('realName', data.real_name)
        
        // 如果是学生，保存学生ID
        if (data.student_id) {
          localStorage.setItem('student_id', data.student_id)
        }
        
        // 如果是教师，保存教师ID
        if (data.teacher_id) {
          localStorage.setItem('teacher_id', data.teacher_id)
        }
        
        // 登录成功回调
        emit('login-success')
        
        // 登录成功，跳转到首页并刷新页面
        router.push('/').then(() => {
          window.location.reload();
        })
      } catch (error) {
        console.error('登录错误:', error)
        errorMessage.value = error.message || '登录失败，请重试'
      } finally {
        isLoading.value = false
      }
    }

    return {
      username,
      password,
      errorMessage,
      isLoading,
      handleLogin
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - var(--nav-height));
  /* background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); */
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 480px;
  padding: 40px;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 8px;
}

.login-header h2 {
  font-size: 20px;
  font-weight: 500;
  color: var(--text-color);
}

.error-message {
  background-color: #fef1f2;
  color: #e11d48;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
  text-align: center;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-color);
}

.form-group input {
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.15s ease;
}

.form-group input:focus {
  border-color: var(--primary-color);
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.2);
}

.form-actions {
  margin-top: 10px;
}

.btn-login {
  width: 100%;
  padding: 14px;
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.btn-login:hover {
  background-color: #005bbf;
}

.btn-login:disabled {
  background-color: #88b8e9;
  cursor: not-allowed;
}

.register-link {
  text-align: center;
  margin-top: 20px;
  color: var(--secondary-text);
}

.register-link a {
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 500;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>