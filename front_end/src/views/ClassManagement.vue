<template>
  <div class="class-management-container">
    <div class="page-header">
      <h1>班级管理</h1>
      <button class="add-btn" @click="showAddModal = true">添加班级</button>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading">
      <div class="spinner"></div>
      <p>加载班级数据中...</p>
    </div>

    <!-- 错误信息 -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>

    <!-- 班级列表 -->
    <div v-if="!isLoading && classes.length > 0" class="class-list">
      <div class="class-list-header">
        <div class="col-id">ID</div>
        <div class="col-name">班级名称</div>
        <div class="col-description">描述</div>
        <div class="col-teacher">班主任</div>
        <div class="col-date">创建时间</div>
        <div class="col-actions">操作</div>
      </div>
      
      <div v-for="classItem in classes" :key="classItem.id" class="class-item">
        <div class="col-id">{{ classItem.id }}</div>
        <div class="col-name">{{ classItem.class_name }}</div>
        <div class="col-description">{{ classItem.description || '无' }}</div>
        <div class="col-teacher">{{ classItem.teacher_name || '未分配' }}</div>
        <div class="col-date">{{ formatDate(classItem.create_time) }}</div>
        <div class="col-actions">
          <button class="edit-btn" @click="editClass(classItem)">编辑</button>
          <button class="view-btn" @click="viewClassDetails(classItem)">查看学生</button>
          <button class="rule-btn" @click="manageRules(classItem)">考勤规则</button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!isLoading && classes.length === 0" class="empty-state">
      <div class="empty-icon">📚</div>
      <h3>暂无班级</h3>
      <p>您可以点击上方的"添加班级"按钮创建新班级</p>
    </div>

    <!-- 添加班级模态框 -->
    <div v-if="showAddModal" class="modal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ isEditing ? '编辑班级' : '添加班级' }}</h2>
          <button class="close-btn" @click="closeModal">&times;</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitClassForm">
            <div class="form-group">
              <label for="class-name">班级名称</label>
              <input 
                type="text" 
                id="class-name" 
                v-model="classForm.className" 
                placeholder="请输入班级名称"
                required
              />
            </div>
            <div class="form-group">
              <label for="class-description">班级描述</label>
              <textarea 
                id="class-description" 
                v-model="classForm.description" 
                placeholder="请输入班级描述（可选）"
                rows="3"
              ></textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="cancel-btn" @click="closeModal">取消</button>
              <button type="submit" class="submit-btn" :disabled="isSubmitting">
                {{ isSubmitting ? '提交中...' : (isEditing ? '保存修改' : '创建班级') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 班级详情模态框 -->
    <div v-if="showDetailsModal" class="modal">
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h2>{{ selectedClass?.class_name }} - 学生列表</h2>
          <button class="close-btn" @click="closeDetailsModal">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="isLoadingStudents" class="loading centered">
            <div class="spinner"></div>
            <p>加载学生数据中...</p>
          </div>
          
          <div v-else-if="classStudents.length === 0" class="empty-state small">
            <h3>暂无学生</h3>
            <p>该班级目前没有学生</p>
          </div>
          
          <div v-else class="student-list">
            <div class="student-list-header">
              <div class="col-s-id">学号</div>
              <div class="col-s-name">姓名</div>
              <div class="col-s-register">注册时间</div>
              <div class="col-s-face">人脸注册</div>
            </div>
            
            <div v-for="student in classStudents" :key="student.student_id" class="student-item">
              <div class="col-s-id">{{ student.student_id }}</div>
              <div class="col-s-name">{{ student.name }}</div>
              <div class="col-s-register">{{ formatDate(student.register_time) }}</div>
              <div class="col-s-face">
                <span :class="student.has_face_feature ? 'status-yes' : 'status-no'">
                  {{ student.has_face_feature ? '已注册' : '未注册' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'ClassManagement',
  setup() {
    const router = useRouter()
    const classes = ref([])
    const isLoading = ref(false)
    const errorMessage = ref('')
    
    // 班级表单
    const classForm = reactive({
      className: '',
      description: ''
    })
    
    // 模态框状态
    const showAddModal = ref(false)
    const showDetailsModal = ref(false)
    const isEditing = ref(false)
    const isSubmitting = ref(false)
    const selectedClass = ref(null)
    const classStudents = ref([])
    const isLoadingStudents = ref(false)
    
    // 获取所有班级
    const fetchClasses = async () => {
      try {
        isLoading.value = true
        errorMessage.value = ''
        
        const token = localStorage.getItem('token')
        if (!token) {
          router.push('/login')
          return
        }
        
        const response = await fetch('/api/admin/classes', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.message || '获取班级列表失败')
        }
        
        classes.value = data.data || []
      } catch (error) {
        console.error('获取班级列表错误:', error)
        errorMessage.value = error.message || '获取班级列表失败，请重试'
      } finally {
        isLoading.value = false
      }
    }
    
    // 提交班级表单
    const submitClassForm = async () => {
      try {
        isSubmitting.value = true
        
        const token = localStorage.getItem('token')
        if (!token) {
          router.push('/login')
          return
        }
        
        const formData = new FormData()
        formData.append('class_name', classForm.className)
        formData.append('description', classForm.description || '')
        
        let url = '/api/admin/classes'
        let method = 'POST'
        
        if (isEditing.value && selectedClass.value) {
          url = `/admin/classes/${selectedClass.value.id}`
          method = 'PUT'
        }
        
        const response = await fetch(url, {
          method,
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.message || '操作失败')
        }
        
        // 成功后刷新班级列表
        await fetchClasses()
        closeModal()
        
      } catch (error) {
        console.error('提交班级表单错误:', error)
        errorMessage.value = error.message || '操作失败，请重试'
      } finally {
        isSubmitting.value = false
      }
    }
    
    // 编辑班级
    const editClass = (classItem) => {
      selectedClass.value = classItem
      classForm.className = classItem.class_name
      classForm.description = classItem.description || ''
      isEditing.value = true
      showAddModal.value = true
    }
    
    // 查看班级详情
    const viewClassDetails = async (classItem) => {
      selectedClass.value = classItem
      showDetailsModal.value = true
      
      try {
        isLoadingStudents.value = true
        
        const token = localStorage.getItem('token')
        if (!token) {
          router.push('/login')
          return
        }
        
        const response = await fetch(`http://localhost:8000/api/admin/students?class_name=${encodeURIComponent(classItem.class_name)}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.message || '获取学生列表失败')
        }
        
        classStudents.value = data.data || []
      } catch (error) {
        console.error('获取学生列表错误:', error)
        errorMessage.value = error.message || '获取学生列表失败，请重试'
      } finally {
        isLoadingStudents.value = false
      }
    }
    
    // 管理考勤规则
    const manageRules = (classItem) => {
      router.push({
        name: 'AttendanceRules',
        query: { classId: classItem.id, className: classItem.class_name }
      })
    }
    
    // 关闭模态框
    const closeModal = () => {
      showAddModal.value = false
      isEditing.value = false
      selectedClass.value = null
      classForm.className = ''
      classForm.description = ''
    }
    
    // 关闭详情模态框
    const closeDetailsModal = () => {
      showDetailsModal.value = false
      selectedClass.value = null
      classStudents.value = []
    }
    
    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '未知'
      
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
    
    onMounted(() => {
      fetchClasses()
    })
    
    return {
      classes,
      isLoading,
      errorMessage,
      classForm,
      showAddModal,
      showDetailsModal,
      isEditing,
      isSubmitting,
      selectedClass,
      classStudents,
      isLoadingStudents,
      fetchClasses,
      submitClassForm,
      editClass,
      viewClassDetails,
      manageRules,
      closeModal,
      closeDetailsModal,
      formatDate
    }
  }
}
</script>

<style scoped>
.class-management-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  color: var(--text-color);
  margin: 0;
}

.add-btn {
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: background-color 0.2s;
}

.add-btn:hover {
  background-color: #005bbf;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.loading.centered {
  min-height: 200px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(0, 113, 227, 0.1);
  border-left-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  background-color: #fef1f2;
  color: #e11d48;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.class-list {
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.class-list-header {
  display: flex;
  background-color: #f9fafb;
  padding: 1rem;
  font-weight: 600;
  border-bottom: 1px solid #e5e7eb;
}

.class-item {
  display: flex;
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
  transition: background-color 0.2s;
}

.class-item:last-child {
  border-bottom: none;
}

.class-item:hover {
  background-color: #f9fafb;
}

.col-id {
  width: 10%;
}

.col-name {
  width: 20%;
  font-weight: 500;
}

.col-description {
  width: 25%;
  color: #4b5563;
}

.col-teacher {
  width: 15%;
}

.col-date {
  width: 15%;
  font-size: 0.9rem;
  color: #6b7280;
}

.col-actions {
  width: 15%;
  display: flex;
  gap: 0.5rem;
}

.edit-btn, .view-btn, .rule-btn {
  padding: 0.4rem 0.75rem;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.edit-btn {
  background-color: #e5e7eb;
  color: #1f2937;
}

.edit-btn:hover {
  background-color: #d1d5db;
}

.view-btn {
  background-color: #dbeafe;
  color: #1e40af;
}

.view-btn:hover {
  background-color: #bfdbfe;
}

.rule-btn {
  background-color: #ffedd5;
  color: #c2410c;
}

.rule-btn:hover {
  background-color: #fed7aa;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  text-align: center;
}

.empty-state.small {
  padding: 2rem;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  font-size: 1.5rem;
  color: var(--text-color);
  margin-bottom: 0.5rem;
}

.empty-state p {
  color: #6b7280;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-content.modal-large {
  max-width: 800px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  font-size: 1.5rem;
  color: var(--text-color);
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.form-group input, .form-group textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus, .form-group textarea:focus {
  border-color: var(--primary-color);
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.2);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
}

.cancel-btn {
  background-color: #e5e7eb;
  color: #1f2937;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.cancel-btn:hover {
  background-color: #d1d5db;
}

.submit-btn {
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.submit-btn:hover {
  background-color: #005bbf;
}

.submit-btn:disabled {
  background-color: #93c5fd;
  cursor: not-allowed;
}

.student-list {
  width: 100%;
}

.student-list-header {
  display: flex;
  background-color: #f9fafb;
  padding: 0.75rem 1rem;
  font-weight: 600;
  border-bottom: 1px solid #e5e7eb;
}

.student-item {
  display: flex;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.student-item:last-child {
  border-bottom: none;
}

.col-s-id {
  width: 25%;
}

.col-s-name {
  width: 25%;
  font-weight: 500;
}

.col-s-register {
  width: 30%;
  font-size: 0.9rem;
  color: #6b7280;
}

.col-s-face {
  width: 20%;
}

.status-yes {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background-color: #d1fae5;
  color: #065f46;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 500;
}

.status-no {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background-color: #fecaca;
  color: #991b1b;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 500;
}

@media (max-width: 768px) {
  .class-management-container {
    padding: 1rem;
  }

  .class-list-header, .class-item {
    font-size: 0.85rem;
  }

  .col-id {
    width: 15%;
  }

  .col-description {
    display: none;
  }

  .col-teacher {
    width: 25%;
  }

  .col-date {
    display: none;
  }

  .col-actions {
    width: 35%;
  }

  .edit-btn, .view-btn, .rule-btn {
    padding: 0.3rem 0.5rem;
    font-size: 0.75rem;
  }
}
</style> 