<template>
  <div class="register-container">
    <h1>人脸注册</h1>

    <div class="register-content">
      <div class="register-form-container">
        <h2>学生信息</h2>
        <form class="register-form" @submit.prevent="submitForm">
          <div class="form-group">
            <label for="studentId">学生学号 <span class="required">*</span></label>
            <input 
              type="text" 
              id="studentId" 
              v-model.trim="formData.studentId" 
              required
              placeholder="请输入学生学号"
            >
          </div>

          <div class="form-group">
            <label for="name">姓名 <span class="required">*</span></label>
            <input 
              type="text" 
              id="name" 
              v-model.trim="formData.name" 
              required
              placeholder="请输入学生姓名"
            >
          </div>

          <div class="form-group">
            <label for="className">班级 <span class="required">*</span></label>
            <input 
              type="text" 
              id="className" 
              v-model.trim="formData.className" 
              placeholder="请输入所属班级"
            >
          </div>

          <div class="form-actions">
            <button 
              type="submit" 
              class="submit-btn" 
              :disabled="isSubmitting || !isFormValid || !hasFace"
            >
              {{ isSubmitting ? '提交中...' : '提交注册' }}
            </button>
            <button 
              type="button" 
              class="reset-btn" 
              @click="resetForm"
              :disabled="isSubmitting"
            >
              重置
            </button>
          </div>
        </form>
      </div>

      <div class="register-face-container">
        <h2>人脸上传</h2>
        <div class="face-capture-area">
          <img v-if="facePreview" :src="facePreview" alt="上传的人脸照片" class="face-preview" />
          
          <div class="face-placeholder" v-if="!facePreview">
            <span class="face-icon">👤</span>
            <p>请上传人脸照片</p>
          </div>

          <div class="upload-controls" v-if="!isSubmitting">
            <label class="upload-btn">
              <span class="btn-icon">📁</span>
              <span>{{ facePreview ? '重新上传' : '选择照片' }}</span>
              <input 
                type="file"
                accept="image/*"
                @change="handleFileUpload"
                ref="fileInput"
                class="hidden-input"
              />
            </label>
            <button 
              v-if="facePreview" 
              class="control-btn remove-btn" 
              @click="removeFace"
            >
              <span class="btn-icon">🗑️</span>
              <span>删除照片</span>
            </button>
          </div>
        </div>

        <div class="face-guidelines">
          <h3>照片上传指南</h3>
          <ul>
            <li>上传清晰的正面照片，面部居中</li>
            <li>确保光线充足，面部清晰可见</li>
            <li>不要佩戴墨镜或遮挡面部</li>
            <li>保持自然表情</li>
            <li>支持JPG、PNG等常见图片格式</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="result-message" v-if="resultMessage">
      <div class="result-card" :class="{ success: isSuccess, error: !isSuccess }">
        <div class="result-icon">{{ isSuccess ? '✅' : '❌' }}</div>
        <div class="result-content">
          <h3>{{ isSuccess ? '注册成功' : '注册失败' }}</h3>
          <p>{{ resultMessage }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';

// 表单数据
const formData = reactive({
  studentId: '',
  name: '',
  className: ''
});

// 照片相关
const facePreview = ref(null);
const hasFace = ref(false);
const isSubmitting = ref(false);
const fileInput = ref(null);

// 结果消息
const resultMessage = ref('');
const isSuccess = ref(false);

// 表单验证
const isFormValid = computed(() => {
  return formData.studentId.trim() !== '' && formData.name.trim() !== '';
});

// 处理文件上传
const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  // 验证文件类型
  if (!file.type.match('image.*')) {
    alert('请上传图片文件！');
    return;
  }
  
  // 预览文件
  const reader = new FileReader();
  reader.onload = (e) => {
    facePreview.value = e.target.result;
    hasFace.value = true;
  };
  
  reader.readAsDataURL(file);
};

// 删除照片
const removeFace = () => {
  facePreview.value = null;
  hasFace.value = false;
  if (fileInput.value) {
    fileInput.value.value = null;
  }
};

// 提交表单
const submitForm = async () => {
  if (!isFormValid.value || !hasFace.value) return;
  
  isSubmitting.value = true;
  
  try {
    // 从预览图像中获取Blob数据
    const response = await fetch(facePreview.value);
    const blob = await response.blob();
    
    // 创建FormData对象
    const formDataObj = new FormData();
    formDataObj.append('student_id', formData.studentId);
    formDataObj.append('name', formData.name);
    formDataObj.append('class_name', formData.className || '');
    formDataObj.append('face_image', blob, 'face.jpg');
    
    // 调用API
    const apiUrl = '/api/register-student';
    const apiResponse = await fetch(apiUrl, {
      method: 'POST',
      body: formDataObj
    });
    
    const result = await apiResponse.json();
    
    if (!apiResponse.ok || !result.success) {
      throw new Error(result.message || '注册失败');
    }
    
    // 注册成功
    isSuccess.value = true;
    resultMessage.value = `学生 ${formData.name} (${formData.studentId}) 注册成功`;
    
    // 重置表单
    resetForm();
    
  } catch (error) {
    console.error('注册失败:', error);
    isSuccess.value = false;
    resultMessage.value = `注册失败: ${error.message || '未知错误'}`;
  } finally {
    isSubmitting.value = false;
  }
};

// 重置表单
const resetForm = () => {
  formData.studentId = '';
  formData.name = '';
  formData.className = '';
  
  facePreview.value = null;
  hasFace.value = false;
  
  if (fileInput.value) {
    fileInput.value.value = null;
  }
};
</script>

<style scoped>
.register-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: var(--text-color);
}

.register-content {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  margin-bottom: 2rem;
}

.register-form-container, 
.register-face-container {
  flex: 1;
  min-width: 300px;
  background-color: white;
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--primary-color);
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

label {
  font-weight: 500;
}

.required {
  color: red;
}

input {
  padding: 0.75rem;
  border: 1px solid #ccc;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

button {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn {
  background-color: var(--primary-color);
  color: white;
  flex: 2;
}

.submit-btn:hover {
  background-color: var(--primary-color);
}

.submit-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.reset-btn {
  background-color: #f8f9fa;
  color: var(--text-color);
  border: 1px solid #dee2e6;
  flex: 1;
}

.reset-btn:hover {
  background-color: #e9ecef;
}

.face-capture-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  border: 2px dashed #ccc;
  border-radius: 0.5rem;
  padding: 1.5rem;
  min-height: 300px;
  position: relative;
}

.face-preview {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
}

.face-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #6c757d;
  height: 100%;
  width: 100%;
}

.face-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.upload-controls {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.upload-btn, .control-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background-color: var(--primary-color);
  color: white;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.3s;
}

.upload-btn:hover, .control-btn:hover {
  background-color:  var(--primary-color);
}

.remove-btn {
  background-color: #dc3545;
}

.remove-btn:hover {
  background-color: #c82333;
}

.hidden-input {
  display: none;
}

.btn-icon {
  font-size: 1.25rem;
}

.face-guidelines {
  background-color: #f8f9fa;
  border-radius: 0.5rem;
  padding: 1rem;
}

.face-guidelines h3 {
  margin-top: 0;
  font-size: 1rem;
  color: var(--text-color);
}

.face-guidelines ul {
  margin: 0;
  padding-left: 1.5rem;
}

.face-guidelines li {
  margin-bottom: 0.5rem;
}

.result-message {
  margin-top: 2rem;
}

.result-card {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 0.5rem;
  background-color: white;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.result-card.success {
  border-left: 5px solid #28a745;
}

.result-card.error {
  border-left: 5px solid #dc3545;
}

.result-icon {
  font-size: 2rem;
}

.result-content {
  flex: 1;
}

.result-content h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
}

.result-content p {
  margin: 0;
  color: #6c757d;
}

@media (max-width: 768px) {
  .register-content {
    flex-direction: column;
  }
}
</style> 