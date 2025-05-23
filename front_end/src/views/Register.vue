<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1>用户注册</h1>
        <h2>请选择您的角色并完成注册</h2>
      </div>
      
      <!-- 角色选择 -->
      <div v-if="!selectedRole" class="role-selection">
        <h3>请选择您的角色</h3>
        <div class="role-buttons">
          <button 
            class="role-btn student-btn" 
            @click="selectRole('student')"
          >
            <div class="icon">👨‍🎓</div>
            <div class="label">学生</div>
          </button>
          <button 
            class="role-btn teacher-btn" 
            @click="selectRole('teacher')"
          >
            <div class="icon">👨‍🏫</div>
            <div class="label">教师</div>
          </button>
        </div>
      </div>
      
      <!-- 错误信息显示 -->
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
      
      <!-- 成功信息显示 -->
      <div v-if="successMessage" class="success-message">
        {{ successMessage }}
        <div class="redirect-info">
          <span>{{ countdown }} 秒后跳转到登录页面</span>
          <button class="redirect-btn" @click="goToLogin">立即登录</button>
        </div>
      </div>
      
      <!-- 学生注册表单 -->
      <form 
        v-if="selectedRole === 'student' && !successMessage" 
        @submit.prevent="handleStudentRegister" 
        class="register-form"
      >
        <h3>学生注册</h3>
        
        <div class="form-group">
          <label for="student-real-name">姓名</label>
          <input 
            type="text" 
            id="student-real-name" 
            v-model="studentForm.realName" 
            placeholder="请输入姓名"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="student-password">密码</label>
          <input 
            type="password" 
            id="student-password" 
            v-model="studentForm.password" 
            placeholder="请输入密码"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="student-confirm-password">确认密码</label>
          <input 
            type="password" 
            id="student-confirm-password" 
            v-model="studentForm.confirmPassword" 
            placeholder="请再次输入密码"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="student-id">学号</label>
          <input 
            type="text" 
            id="student-id" 
            v-model="studentForm.studentId" 
            placeholder="请输入学号"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="student-phone">手机号</label>
          <input 
            type="tel" 
            id="student-phone" 
            v-model="studentForm.phone" 
            placeholder="请输入手机号"
          />
        </div>
        
        <div class="form-actions">
          <button 
            type="button" 
            class="btn-back" 
            @click="resetForm"
          >
            返回
          </button>
          <button 
            type="submit" 
            class="btn-register" 
            :disabled="isLoading"
          >
            {{ isLoading ? '注册中...' : '注册' }}
          </button>
        </div>
      </form>
      
      <!-- 教师注册表单 -->
      <form 
        v-if="selectedRole === 'teacher' && !successMessage" 
        @submit.prevent="handleTeacherRegister" 
        class="register-form"
      >
        <h3>教师注册</h3>
        
        <div class="form-group">
          <label for="teacher-real-name">姓名</label>
          <input 
            type="text" 
            id="teacher-real-name" 
            v-model="teacherForm.realName" 
            placeholder="请输入姓名"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="teacher-password">密码</label>
          <input 
            type="password" 
            id="teacher-password" 
            v-model="teacherForm.password" 
            placeholder="请输入密码"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="teacher-confirm-password">确认密码</label>
          <input 
            type="password" 
            id="teacher-confirm-password" 
            v-model="teacherForm.confirmPassword" 
            placeholder="请再次输入密码"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="teacher-id">教师工号</label>
          <input 
            type="text" 
            id="teacher-id" 
            v-model="teacherForm.teacherId" 
            placeholder="请输入教师工号"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="teacher-phone">手机号</label>
          <input 
            type="tel" 
            id="teacher-phone" 
            v-model="teacherForm.phone" 
            placeholder="请输入手机号"
          />
        </div>
        
        <div class="form-actions">
          <button 
            type="button" 
            class="btn-back" 
            @click="resetForm"
          >
            返回
          </button>
          <button 
            type="submit" 
            class="btn-register" 
            :disabled="isLoading"
          >
            {{ isLoading ? '注册中...' : '注册' }}
          </button>
        </div>
      </form>
      
      <!-- 返回登录链接 -->
      <div v-if="!successMessage" class="login-link">
        <p>已有账号？ <router-link to="/login">返回登录</router-link></p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'RegisterView',
  setup() {
    const router = useRouter()
    const selectedRole = ref(null)
    const errorMessage = ref('')
    const successMessage = ref('')
    const isLoading = ref(false)
    const countdown = ref(5)
    let redirectTimer = null
    
    // 学生注册表单
    const studentForm = reactive({
      realName: '',
      password: '',
      confirmPassword: '',
      studentId: '',
      phone: ''
    })
    
    // 教师注册表单
    const teacherForm = reactive({
      realName: '',
      password: '',
      confirmPassword: '',
      teacherId: '',
      phone: ''
    })
    
    // 选择角色
    const selectRole = (role) => {
      selectedRole.value = role
      errorMessage.value = ''
    }
    
    // 重置表单
    const resetForm = () => {
      selectedRole.value = null
      errorMessage.value = ''
    }
    
    // 开始倒计时
    const startCountdown = () => {
      redirectTimer = setInterval(() => {
        countdown.value -= 1
        if (countdown.value <= 0) {
          clearInterval(redirectTimer)
          goToLogin()
        }
      }, 1000)
    }
    
    // 跳转到登录页
    const goToLogin = () => {
      if (redirectTimer) clearInterval(redirectTimer)
      router.push('/login')
    }
    
    // 学生注册处理
    const handleStudentRegister = async () => {
      // 验证密码是否一致
      if (studentForm.password !== studentForm.confirmPassword) {
        errorMessage.value = '两次输入的密码不一致'
        return
      }
      
      try {
        isLoading.value = true
        errorMessage.value = ''
        
        // 准备请求数据
        const requestData = {
          real_name: studentForm.realName,
          password: studentForm.password,
          student_id: studentForm.studentId,
          phone: studentForm.phone || null
        }
        
        // 调用注册API
        const response = await fetch('/api/auth/register/student', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestData)
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.message || '注册失败，请重试')
        }
        
        // 注册成功
        successMessage.value = data.message || '学生注册成功！'
        startCountdown()
      } catch (error) {
        console.error('注册错误:', error)
        errorMessage.value = error.message || '注册失败，请重试'
      } finally {
        isLoading.value = false
      }
    }
    
    // 教师注册处理
    const handleTeacherRegister = async () => {
      // 验证密码是否一致
      if (teacherForm.password !== teacherForm.confirmPassword) {
        errorMessage.value = '两次输入的密码不一致'
        return
      }
      
      try {
        isLoading.value = true
        errorMessage.value = ''
        
        // 准备请求数据
        const requestData = {
          real_name: teacherForm.realName,
          password: teacherForm.password,
          teacher_id: teacherForm.teacherId,
          phone: teacherForm.phone || null
        }
        
        // 调用注册API
        const response = await fetch('/api/auth/register/teacher', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestData)
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.message || '注册失败，请重试')
        }
        
        // 注册成功
        successMessage.value = data.message || '教师注册成功！'
        startCountdown()
      } catch (error) {
        console.error('注册错误:', error)
        errorMessage.value = error.message || '注册失败，请重试'
      } finally {
        isLoading.value = false
      }
    }
    
    return {
      selectedRole,
      studentForm,
      teacherForm,
      errorMessage,
      successMessage,
      isLoading,
      countdown,
      selectRole,
      resetForm,
      handleStudentRegister,
      handleTeacherRegister,
      goToLogin
    }
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - var(--nav-height));
  /* background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); */
  padding: 20px;
}

.register-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 600px;
  padding: 40px;
  margin: 40px 0;
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
}

.register-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 8px;
}

.register-header h2 {
  font-size: 18px;
  font-weight: 400;
  color: var(--secondary-text);
}

.role-selection {
  text-align: center;
  margin-bottom: 30px;
}

.role-selection h3 {
  font-size: 20px;
  font-weight: 500;
  margin-bottom: 20px;
  color: var(--text-color);
}

.role-buttons {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 20px;
}

.role-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px solid #eaeaea;
  border-radius: 12px;
  padding: 30px;
  width: 150px;
  background-color: white;
  cursor: pointer;
  transition: all 0.25s ease;
}

.role-btn:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.role-btn .icon {
  font-size: 48px;
  margin-bottom: 15px;
}

.role-btn .label {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
}

.student-btn:hover {
  border-color: #4caf50;
}

.teacher-btn:hover {
  border-color: #2196f3;
}

.error-message {
  background-color: #fef1f2;
  color: #e11d48;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
  text-align: center;
}

.success-message {
  background-color: #ecfdf5;
  color: #047857;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  text-align: center;
  font-weight: 500;
}

.redirect-info {
  margin-top: 15px;
  font-size: 14px;
  color: #6b7280;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.redirect-btn {
  background-color: #047857;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
}

.register-form {
  margin-bottom: 30px;
}

.register-form h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--text-color);
  text-align: center;
}

.teacher-notice {
  color: #f59e0b;
  text-align: center;
  font-size: 14px;
  margin-bottom: 20px;
  padding: 8px;
  background-color: #fffbeb;
  border-radius: 6px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 15px;
}

.form-group label {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.form-group input {
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 15px;
  transition: border-color 0.15s ease;
}

.form-group input:focus {
  border-color: var(--primary-color);
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.2);
}

.form-actions {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  margin-top: 25px;
}

.btn-back {
  padding: 12px 20px;
  background-color: #e5e7eb;
  color: #374151;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease;
  flex: 1;
}

.btn-back:hover {
  background-color: #d1d5db;
}

.btn-register {
  padding: 12px 20px;
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease;
  flex: 2;
}

.btn-register:hover {
  background-color: #005bbf;
}

.btn-register:disabled {
  background-color: #88b8e9;
  cursor: not-allowed;
}

.login-link {
  text-align: center;
  margin-top: 20px;
  color: var(--secondary-text);
}

.login-link a {
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 500;
}

.login-link a:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .role-buttons {
    flex-direction: column;
    align-items: center;
  }
  
  .register-card {
    padding: 25px;
  }
}
</style> 