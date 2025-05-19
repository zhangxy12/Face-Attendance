<template>
  <div class="attendance-rules-container">
    <div class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="goBack">
          <span>←</span> 返回
        </button>
        <h1>{{ className }} - 考勤规则设置</h1>
      </div>
      <button v-if="!hasRule" class="add-btn" @click="showRuleModal = true">创建规则</button>
      <button v-else class="edit-btn" @click="editRule">编辑规则</button>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading">
      <div class="spinner"></div>
      <p>加载考勤规则中...</p>
    </div>

    <!-- 错误信息 -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>

    <!-- 规则已存在 -->
    <div v-if="!isLoading && hasRule" class="rule-card">
      <div class="rule-header">
        <h2>当前考勤规则</h2>
        <span :class="rule.is_active ? 'status-active' : 'status-inactive'">
          {{ rule.is_active ? '已启用' : '已禁用' }}
        </span>
      </div>
      
      <div class="rule-content">
        <div class="rule-item">
          <div class="rule-label">考勤时间</div>
          <div class="rule-value">{{ rule.start_time }} - {{ rule.end_time }}</div>
        </div>
        
        <div class="rule-item">
          <div class="rule-label">迟到阈值</div>
          <div class="rule-value">{{ rule.late_threshold }} 分钟</div>
        </div>
        
        <div class="rule-item">
          <div class="rule-label">适用日期</div>
          <div class="rule-value">{{ formatWeekdays(rule.weekdays) }}</div>
        </div>
        
        <div v-if="rule.remark" class="rule-item">
          <div class="rule-label">备注</div>
          <div class="rule-value">{{ rule.remark }}</div>
        </div>
        
        <div class="rule-item">
          <div class="rule-label">创建时间</div>
          <div class="rule-value">{{ formatDate(rule.create_time) }}</div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!isLoading && !hasRule" class="empty-state">
      <div class="empty-icon">⏰</div>
      <h3>暂无考勤规则</h3>
      <p>该班级尚未设置考勤规则，请点击"创建规则"按钮进行设置</p>
    </div>

    <!-- 规则设置模态框 -->
    <div v-if="showRuleModal" class="modal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ isEditing ? '编辑考勤规则' : '创建考勤规则' }}</h2>
          <button class="close-btn" @click="closeModal">&times;</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitRuleForm">
            <div class="form-row">
              <div class="form-group">
                <label for="start-time">开始时间</label>
                <input 
                  type="time" 
                  id="start-time" 
                  v-model="ruleForm.startTime" 
                  required
                />
              </div>
              <div class="form-group">
                <label for="end-time">结束时间</label>
                <input 
                  type="time" 
                  id="end-time" 
                  v-model="ruleForm.endTime" 
                  required
                />
              </div>
            </div>
            
            <div class="form-group">
              <label for="late-threshold">迟到阈值（分钟）</label>
              <input 
                type="number" 
                id="late-threshold" 
                v-model="ruleForm.lateThreshold" 
                min="1"
                max="120"
                required
              />
            </div>
            
            <div class="form-group">
              <label>适用日期（星期）</label>
              <div class="weekday-selector">
                <label 
                  v-for="day in weekdays" 
                  :key="day.value" 
                  class="weekday-checkbox"
                >
                  <input 
                    type="checkbox" 
                    :value="day.value" 
                    v-model="ruleForm.selectedWeekdays"
                  />
                  <span>{{ day.label }}</span>
                </label>
              </div>
            </div>
            
            <div class="form-group">
              <label for="remark">备注</label>
              <textarea 
                id="remark" 
                v-model="ruleForm.remark" 
                placeholder="请输入规则备注（可选）"
                rows="3"
              ></textarea>
            </div>
            
            <div v-if="isEditing" class="form-group">
              <label for="is-active">规则状态</label>
              <div class="toggle-switch">
                <input 
                  type="checkbox" 
                  id="is-active" 
                  v-model="ruleForm.isActive"
                />
                <label for="is-active"></label>
                <span>{{ ruleForm.isActive ? '已启用' : '已禁用' }}</span>
              </div>
            </div>
            
            <div class="form-actions">
              <button type="button" class="cancel-btn" @click="closeModal">取消</button>
              <button type="submit" class="submit-btn" :disabled="isSubmitting">
                {{ isSubmitting ? '提交中...' : (isEditing ? '保存修改' : '创建规则') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

export default {
  name: 'AttendanceRules',
  setup() {
    const router = useRouter()
    const route = useRoute()
    
    // 路由参数
    const classId = ref(parseInt(route.query.classId) || 0)
    const className = ref(route.query.className || '未知班级')
    
    // 加载状态
    const isLoading = ref(false)
    const errorMessage = ref('')
    
    // 规则数据
    const rule = ref(null)
    const hasRule = computed(() => rule.value !== null)
    
    // 模态框状态
    const showRuleModal = ref(false)
    const isEditing = ref(false)
    const isSubmitting = ref(false)
    
    // 星期几选项
    const weekdays = [
      { label: '周一', value: '1' },
      { label: '周二', value: '2' },
      { label: '周三', value: '3' },
      { label: '周四', value: '4' },
      { label: '周五', value: '5' },
      { label: '周六', value: '6' },
      { label: '周日', value: '7' }
    ]
    
    // 规则表单
    const ruleForm = reactive({
      startTime: '08:00',
      endTime: '17:30',
      lateThreshold: 15,
      selectedWeekdays: ['1', '2', '3', '4', '5'],
      remark: '',
      isActive: true
    })
    
    // 返回班级管理页面
    const goBack = () => {
      router.push('/admin/classes')
    }
    
    // 获取考勤规则
    const fetchRule = async () => {
      if (!classId.value) {
        errorMessage.value = '缺少班级ID参数，无法获取考勤规则'
        return
      }
      
      try {
        isLoading.value = true
        errorMessage.value = ''
        
        const token = localStorage.getItem('token')
        if (!token) {
          router.push('/login')
          return
        }
        
        const response = await fetch(`/api/admin/attendance-rules?class_id=${classId.value}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.message || '获取考勤规则失败')
        }
        
        if (data.data && data.data.length > 0) {
          rule.value = data.data[0]
        } else {
          rule.value = null
        }
      } catch (error) {
        console.error('获取考勤规则错误:', error)
        errorMessage.value = error.message || '获取考勤规则失败，请重试'
      } finally {
        isLoading.value = false
      }
    }
    
    // 编辑规则
    const editRule = () => {
      if (!rule.value) return
      
      // 填充表单数据
      ruleForm.startTime = rule.value.start_time
      ruleForm.endTime = rule.value.end_time
      ruleForm.lateThreshold = rule.value.late_threshold
      ruleForm.selectedWeekdays = rule.value.weekdays.split(',')
      ruleForm.remark = rule.value.remark || ''
      ruleForm.isActive = rule.value.is_active === 1
      
      isEditing.value = true
      showRuleModal.value = true
    }
    
    // 提交规则表单
    const submitRuleForm = async () => {
      try {
        isSubmitting.value = true
        
        const token = localStorage.getItem('token')
        if (!token) {
          router.push('/login')
          return
        }
        
        // 准备请求数据
        const requestData = {
          class_id: classId.value,
          start_time: ruleForm.startTime,
          end_time: ruleForm.endTime,
          late_threshold: parseInt(ruleForm.lateThreshold),
          weekdays: ruleForm.selectedWeekdays.join(','),
          remark: ruleForm.remark || null,
          is_active: ruleForm.isActive ? 1 : 0
        }
        
        if (isEditing.value) {
          // 编辑时添加规则状态
          requestData.is_active = ruleForm.isActive ? 1 : 0
        }
        
        const response = await fetch('/api/admin/attendance-rules', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestData)
        })
        
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error(data.message || '操作失败')
        }
        
        // 成功后刷新规则数据
        await fetchRule()
        closeModal()
        
      } catch (error) {
        console.error('提交规则表单错误:', error)
        errorMessage.value = error.message || '操作失败，请重试'
      } finally {
        isSubmitting.value = false
      }
    }
    
    // 关闭模态框
    const closeModal = () => {
      showRuleModal.value = false
      isEditing.value = false
      
      // 重置表单
      ruleForm.startTime = '08:00'
      ruleForm.endTime = '17:30'
      ruleForm.lateThreshold = 15
      ruleForm.selectedWeekdays = ['1', '2', '3', '4', '5']
      ruleForm.remark = ''
      ruleForm.isActive = true
    }
    
    // 格式化星期几
    const formatWeekdays = (weekdaysStr) => {
      if (!weekdaysStr) return '未知'
      
      const days = weekdaysStr.split(',')
      const dayNames = []
      
      for (const day of days) {
        const weekday = weekdays.find(w => w.value === day)
        if (weekday) {
          dayNames.push(weekday.label)
        }
      }
      
      return dayNames.join('、')
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
      fetchRule()
    })
    
    return {
      classId,
      className,
      isLoading,
      errorMessage,
      rule,
      hasRule,
      showRuleModal,
      isEditing,
      isSubmitting,
      weekdays,
      ruleForm,
      goBack,
      fetchRule,
      editRule,
      submitRuleForm,
      closeModal,
      formatWeekdays,
      formatDate
    }
  }
}
</script>

<style scoped>
.attendance-rules-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.page-header h1 {
  font-size: 1.75rem;
  color: var(--text-color);
  margin: 0;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border: none;
  background-color: #f3f4f6;
  color: #374151;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.back-btn:hover {
  background-color: #e5e7eb;
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

.edit-btn {
  background-color: #f59e0b;
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

.edit-btn:hover {
  background-color: #d97706;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
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

.rule-card {
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.rule-header h2 {
  font-size: 1.25rem;
  color: var(--text-color);
  margin: 0;
}

.status-active, .status-inactive {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-active {
  background-color: #d1fae5;
  color: #065f46;
}

.status-inactive {
  background-color: #fecaca;
  color: #991b1b;
}

.rule-content {
  padding: 1.5rem;
}

.rule-item {
  display: flex;
  margin-bottom: 1rem;
}

.rule-item:last-child {
  margin-bottom: 0;
}

.rule-label {
  width: 120px;
  font-weight: 500;
  color: #4b5563;
}

.rule-value {
  flex: 1;
  color: var(--text-color);
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
  max-width: 600px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
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

.form-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.form-row .form-group {
  flex: 1;
  margin-bottom: 0;
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

.weekday-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.weekday-checkbox {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  user-select: none;
}

.weekday-checkbox input {
  width: auto;
  cursor: pointer;
}

.toggle-switch {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toggle-switch input[type="checkbox"] {
  width: 0;
  height: 0;
  visibility: hidden;
  position: absolute;
}

.toggle-switch label {
  display: block;
  width: 50px;
  height: 26px;
  background: #e5e7eb;
  border-radius: 100px;
  position: relative;
  cursor: pointer;
  transition: 0.3s;
  margin: 0;
}

.toggle-switch label::after {
  content: "";
  width: 22px;
  height: 22px;
  background: #fff;
  position: absolute;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: 0.3s;
}

.toggle-switch input:checked + label {
  background: var(--primary-color);
}

.toggle-switch input:checked + label::after {
  left: calc(100% - 2px);
  transform: translateX(-100%);
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

@media (max-width: 768px) {
  .attendance-rules-container {
    padding: 1rem;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .page-header h1 {
    font-size: 1.5rem;
  }
  
  .form-row {
    flex-direction: column;
    gap: 1.5rem;
  }
  
  .weekday-selector {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
}
</style> 