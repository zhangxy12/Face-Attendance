<template>
  <div class="attendance-container wide-layout">
    <!-- <h1>学生考勤打卡</h1> -->
    <div class="detection-options">
      <h2>活体检测方案</h2>
      <div class="option-buttons" style="align-items: center;">
        <button 
          class="option-btn" 
          :class="{ active: currentMethod === 'api' }" 
          @click="currentMethod = 'api'"
        >
          <span class="option-icon">🔌</span>
          <span>API方案</span>
        </button>
        <button 
          class="option-btn" 
          :class="{ active: currentMethod === 'model' }" 
          @click="currentMethod = 'model'"
        >
          <span class="option-icon">🧠</span>
          <span>基于InsightFace的方案</span>
        </button>
        <button 
          class="option-btn" 
          :class="{ active: currentMethod === 'custom' }" 
          @click="currentMethod = 'custom'"
        >
          <span class="option-icon">⚙️</span>
          <span>Silent-Face-Anti-Spoofing</span>
        </button>
      </div>
      <p class="method-description">{{ methodDescriptions[currentMethod] }}</p>
    </div>

    <div class="main-flex-row">
      <!-- API实时识别panel -->
      <div class="liveness-steps-panel" v-if="currentMethod === 'api'">
        <h3 class="liveness-title">实时识别结果</h3>
        <div v-if="lastFaceRecognizeResult">
          <div v-if="lastFaceRecognizeResult.success" class="api-result-success">
            <div class="api-result-row">
              <span class="api-result-label">识别状态：</span>
              <span class="api-result-value success">✅ 识别成功</span>
            </div>
            <div class="api-result-row">
              <span class="api-result-label">姓名：</span>
              <span class="api-result-value">{{ lastFaceRecognizeResult.name || '未知' }}</span>
            </div>
            <div class="api-result-row">
              <span class="api-result-label">学号：</span>
              <span class="api-result-value">{{ lastFaceRecognizeResult.student_id || '-' }}</span>
            </div>
            <div class="api-result-row">
              <span class="api-result-label">活体检测：</span>
              <span class="api-result-value">
                {{ lastFaceRecognizeResult.liveness_score === true ? '真人' : (lastFaceRecognizeResult.liveness_score === false ? '非真人' : '-') }}
              </span>
            </div>
            <div class="api-result-row">
              <span class="api-result-label">相似度：</span>
              <span class="api-result-value">{{ (lastFaceRecognizeResult.similarity * 100).toFixed(2) }}%</span>
            </div>
          </div>
          <div v-else class="api-result-fail">
            <div class="api-result-row">
              <span class="api-result-label">识别状态：</span>
              <span class="api-result-value fail">❌ 识别失败</span>
            </div>
            <div class="api-result-row">
              <span class="api-result-label">原因：</span>
              <span class="api-result-value">{{ lastFaceRecognizeResult.message || '未识别到人脸' }}</span>
            </div>
            <div class="api-result-row">
              <span class="api-result-label">活体检测：</span>
              <span class="api-result-value">
                {{ lastFaceRecognizeResult.liveness_score === true ? '真人' : (lastFaceRecognizeResult.liveness_score === false ? '非真人' : '-') }}
              </span>
            </div>
            <div v-if="lastFaceRecognizeResult.similarity !== undefined" class="api-result-row">
              <span class="api-result-label">相似度：</span>
              <span class="api-result-value">{{ (lastFaceRecognizeResult.similarity * 100).toFixed(2) }}%</span>
            </div>
          </div>
        </div>
        <div v-else class="liveness-current-tip">
          <span>请正对摄像头，系统将自动识别</span>
        </div>
      </div>
      <!-- 步骤与提示区 -->
      <div class="liveness-steps-panel" v-if="currentMethod === 'model'">
        <h3 class="liveness-title">活体检测进度</h3>
        <ul class="liveness-steps-list">
          <li v-for="(step, idx) in livenessSteps" :key="step.name" class="liveness-step-item">
            <span
              class="liveness-step-status"
              :class="{
                passed: step.done,
                current: idx === livenessCurrentIdx && !livenessAllPassed,
                failed: !step.done && idx < livenessCurrentIdx
              }"
            >
              <template v-if="step.done">🟩</template>
              <template v-else-if="idx === livenessCurrentIdx && !livenessAllPassed">🟦</template>
              <template v-else>🟥</template>
            </span>
            <span class="liveness-step-text-label">{{ step.text }}</span>
            <span v-if="step.done" class="liveness-step-passed">（已通过）</span>
          </li>
        </ul>
        <div v-if="livenessAllPassed" class="liveness-all-passed">
          <span class="liveness-yellow-block">🟨 活体检测全部通过，正在打卡... 🟨</span>
        </div>
        <div v-else class="liveness-current-tip">
          <span v-if="livenessStepText">{{ livenessStepText }}</span>
        </div>
        <div v-if="livenessError" class="liveness-error-tip">❌ {{ livenessError }}</div>
      </div>

      <!-- 自定义方案 -->
      <div class="liveness-steps-panel" v-if="currentMethod === 'custom'">
        <h3 class="liveness-title">静默活体检测</h3>
        <span>无需任何操作</span>
        <span>点击打卡即可执行</span>
        
      </div>
      <!-- 摄像头区 -->
      <div class="camera-section">
        <div class="camera-container">
          <video ref="video" class="camera-feed" autoplay playsinline></video>
          <canvas ref="canvas" class="face-canvas"></canvas>
          <div v-if="processingAttendance" class="processing-overlay">
            <div class="spinner"></div>
            <p>处理中...</p>
          </div>
        </div>
        <div class="camera-controls">
          <button class="control-btn start-btn" @click="startCamera" v-if="!cameraActive">
            <span class="btn-icon">📷</span>
            <span>开启摄像头</span>
          </button>
          <button class="control-btn stop-btn" @click="stopCamera" v-if="cameraActive && !processingAttendance">
            <span class="btn-icon">⏹️</span>
            <span>关闭摄像头</span>
          </button>
          <button class="control-btn attendance-btn" @click="takeAttendance" v-if="cameraActive && !processingAttendance" :disabled="processingAttendance || livenessActive">
            <span class="btn-icon">✅</span>
            <span>打卡</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="attendanceResult" class="result-section">
      <div class="result-card" :class="{ success: attendanceResult.success, error: !attendanceResult.success }">
        <div class="result-icon">{{ attendanceResult.success ? '✅' : '❌' }}</div>
        <div class="result-content">
          <h3>{{ attendanceResult.success ? '打卡成功' : '打卡失败' }}</h3>
          <p>{{ attendanceResult.message }}</p>
          <div v-if="attendanceResult.success" class="result-details">
            <p><strong>学生姓名:</strong> {{ attendanceResult.student?.name }}</p>
            <p><strong>打卡时间:</strong> {{ attendanceResult.check_time }}</p>
            <p><strong>签到类型:</strong> {{ attendanceResult.check_type === 'in' ? '上课签到' : '下课签退' }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue';

// 活体检测方法切换
const currentMethod = ref('api');
const methodDescriptions = {
  api: '通过调用人脸识别API实现活体检测，高精度识别真假人脸，可抵御照片和视频攻击。',
  model: '基于dlib的交互式活体检测（眨眼、张嘴、点头、摇头），全部通过后自动打卡。',
  custom: 'Silent-Face-Anti-Spoofing，实现活体识别，特征抽取，特征对比，有效防止欺骗。'
};

// 摄像头相关
const cameraActive = ref(false);
const processingAttendance = ref(false);
const video = ref(null);
const canvas = ref(null);
const stream = ref(null);
const attendanceResult = ref(null);

// API实时识别相关
const faceRecognizeResult = ref(null);
const lastFaceRecognizeResult = ref(null);
const faceRecognizeLoading = ref(false);
let faceRecognizeTimer = null;
const FACE_RECOGNIZE_INTERVAL = 500; // ms

// 定时采集帧并调用/api/face-recognize
const startFaceRecognize = () => {
  if (faceRecognizeTimer) clearInterval(faceRecognizeTimer);
  faceRecognizeLoading.value = false;
  // 不清空lastFaceRecognizeResult
  faceRecognizeTimer = setInterval(async () => {
    if (!cameraActive.value || currentMethod.value !== 'api') return;
    try {
      faceRecognizeLoading.value = true;
      // 采集当前帧
      const ctx = canvas.value.getContext('2d');
      canvas.value.width = video.value.videoWidth;
      canvas.value.height = video.value.videoHeight;
      ctx.drawImage(video.value, 0, 0, canvas.value.width, canvas.value.height);
      const imageData = canvas.value.toDataURL('image/jpeg');
      // base64转blob
      const base64Response = await fetch(imageData);
      const blob = await base64Response.blob();
      const formData = new FormData();
      formData.append('image', blob, 'image.jpg');
      const studentId = localStorage.getItem('student_id');
      if (studentId) formData.append('student_id', studentId);
      const response = await fetch('/api/face-recognize', {
        method: 'POST',
        body: formData
      });
      const result = await response.json();
      faceRecognizeResult.value = result;
      lastFaceRecognizeResult.value = result; // 只在有新结果时更新
    } catch (e) {
      faceRecognizeResult.value = { success: false, message: '识别异常' };
    } finally {
      faceRecognizeLoading.value = false;
    }
  }, FACE_RECOGNIZE_INTERVAL);
};

const stopFaceRecognize = () => {
  if (faceRecognizeTimer) {
    clearInterval(faceRecognizeTimer);
    faceRecognizeTimer = null;
  }
  faceRecognizeResult.value = null;
  faceRecognizeLoading.value = false;
};

// 交互式活体检测相关
const livenessActive = ref(false);
const livenessStepText = ref('');
const livenessPassed = ref(false);
const livenessError = ref('');
const livenessSessionId = ref('');
const livenessFrame = ref(null); // 最后一帧
const livenessSteps = ref([]); // 步骤列表
const livenessCurrentIdx = ref(0);
const livenessAllPassed = ref(false);

// 开启摄像头
const startCamera = async () => {
  try {
    const constraints = {
      video: {
        width: 640,
        height: 480,
        facingMode: 'user'
      }
    };
    stream.value = await navigator.mediaDevices.getUserMedia(constraints);
    video.value.srcObject = stream.value;
    cameraActive.value = true;
    await nextTick();
    video.value.onloadedmetadata = () => {
      canvas.value.width = video.value.videoWidth;
      canvas.value.height = video.value.videoHeight;
      canvas.value.style.width = '100%';
      canvas.value.style.height = '100%';
      video.value.style.width = '100%';
      video.value.style.height = '100%';
    };
    // API实时识别：摄像头一打开就自动识别
    if (currentMethod.value === 'api') {
      startFaceRecognize();
    }
  } catch (error) {
    console.error('无法访问摄像头:', error);
    alert('无法访问摄像头，请确保已授予摄像头访问权限。');
  }
};

// 停止摄像头
const stopCamera = () => {
  if (stream.value) {
    stream.value.getTracks().forEach(track => track.stop());
    video.value.srcObject = null;
    cameraActive.value = false;
    // 清除画布
    const ctx = canvas.value.getContext('2d');
    ctx.clearRect(0, 0, canvas.value.width, canvas.value.height);
  }
  stopFaceRecognize();
};


// 执行考勤打卡
const takeAttendance = async () => {
  if (!cameraActive.value) return;
  processingAttendance.value = true;
  try {
    // 捕获当前画面
    const ctx = canvas.value.getContext('2d');
    canvas.value.width = video.value.videoWidth;
    canvas.value.height = video.value.videoHeight;
    ctx.drawImage(video.value, 0, 0, canvas.value.width, canvas.value.height);
    // 转换为base64
    const imageData = canvas.value.toDataURL('image/jpeg');
    let result;
    switch (currentMethod.value) {
      case 'api':
        result = await apiAttendance(imageData);
        break;
      case 'model':
        result = await interactiveLivenessAttendance();
        break;
      case 'custom':
        result = await customAttendance(imageData);
        break;
    }
    attendanceResult.value = result;
    if (attendanceResult.value) {
      setTimeout(() => {
        attendanceResult.value = null;
      }, 5000000000);
    }
  } catch (error) {
    console.error('考勤打卡失败:', error);
    attendanceResult.value = {
      success: false,
      message: `打卡失败: ${error.message || '未知错误'}`
    };
  } finally {
    processingAttendance.value = false;
  }
};

// API方案 - 调用后端接口
const apiAttendance = async (imageData) => {
  const apiUrl = '/api/attendance';
  try {
    const formData = new FormData();
    const base64Response = await fetch(imageData);
    const blob = await base64Response.blob();
    formData.append('image', blob, 'image.jpg');
    formData.append('method', 'arcsoft');
    const studentId = localStorage.getItem('student_id');
    if (studentId) {
      formData.append('student_id', studentId);
    }
    const response = await fetch(apiUrl, {
      method: 'POST',
      body: formData
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || '服务器错误');
    }
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.message || '考勤失败');
    }
    return {
      success: true,
      message: '打卡成功',
      student: {
        student_id: result.student_id,
        name: result.student?.name || '未知学生'
      },
      check_time: result.check_time || new Date().toLocaleString(),
      check_type: 'in'
    };
  } catch (error) {
    console.error('API调用失败:', error);
    throw error;
  }
};

// 交互式活体检测+打卡
const interactiveLivenessAttendance = async () => {
  livenessActive.value = true;
  livenessPassed.value = false;
  livenessError.value = '';
  livenessStepText.value = '正在初始化活体检测...';
  livenessSessionId.value = Math.random().toString(36).slice(2) + Date.now();
  livenessSteps.value = [];
  livenessCurrentIdx.value = 0;
  livenessAllPassed.value = false;
  let finished = false;
  let lastFrame = null;
  try {
    while (!finished) {
      // 抓取当前帧
      const ctx = canvas.value.getContext('2d');
      canvas.value.width = video.value.videoWidth;
      canvas.value.height = video.value.videoHeight;
      ctx.drawImage(video.value, 0, 0, canvas.value.width, canvas.value.height);
      const imageData = canvas.value.toDataURL('image/jpeg');
      // 发送到后端
      const formData = new FormData();
      const base64Response = await fetch(imageData);
      const blob = await base64Response.blob();
      formData.append('image', blob, 'image.jpg');
      formData.append('session_id', livenessSessionId.value);
      const response = await fetch('/api/interactive-liveness', {
        method: 'POST',
        body: formData
      });
      const result = await response.json();
      if (!result.success) {
        livenessError.value = result.message || '活体检测失败';
        livenessStepText.value = '';
        livenessActive.value = false;
        return {
          success: false,
          message: livenessError.value
        };
      }
      // 步骤进度
      if (Array.isArray(result.steps)) {
        livenessSteps.value = result.steps;
        livenessCurrentIdx.value = result.steps.findIndex(s => !s.done);
        if (livenessCurrentIdx.value === -1) livenessCurrentIdx.value = result.steps.length - 1;
      }
      livenessAllPassed.value = !!result.all_passed;
      // 优先显示msg（如未检测到单个人脸）
      if (result.msg && result.msg !== '') {
        livenessStepText.value = result.msg;
      } else if (result.current_text) {
        livenessStepText.value = result.current_text;
      } else {
        livenessStepText.value = '请根据提示完成动作';
      }
      if (result.all_passed) {
        livenessStepText.value = '活体检测通过，正在打卡...';
        finished = true;
        lastFrame = result.last_frame;
        break;
      }
      // 等待用户完成动作
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    // 活体检测通过，上传最后一帧打卡
    if (lastFrame) {
      const formData = new FormData();
      // base64转blob
      const res = await fetch('data:image/jpeg;base64,' + lastFrame);
      const blob = await res.blob();
      formData.append('image', blob, 'image.jpg');
      const studentId = localStorage.getItem('student_id');
      if (studentId) formData.append('student_id', studentId);
      const response = await fetch('/api/attendance/deepface', {
        method: 'POST',
        body: formData
      });
      const result = await response.json();
      livenessActive.value = false;
      if (!result.success) {
        return {
          success: false,
          message: result.message || '打卡失败'
        };
      }
      return {
        success: true,
        message: result.message || '打卡成功',
        student: {
          student_id: result.student?.student_id || studentId,
          name: result.student?.name || '未知学生'
        },
        check_time: new Date().toLocaleString(),
        check_type: 'in'
      };
    } else {
      livenessActive.value = false;
      return {
        success: false,
        message: '未获取到有效打卡帧'
      };
    }
  } catch (error) {
    livenessActive.value = false;
    livenessError.value = error.message || '活体检测异常';
    return {
      success: false,
      message: livenessError.value
    };
  }
};

// 自定义方案 - 调用静默活体检测考勤API
const customAttendance = async (imageData) => {
  const apiUrl = '/api/attendance/silence';
  try {
    const formData = new FormData();
    const base64Response = await fetch(imageData);
    const blob = await base64Response.blob();
    formData.append('image', blob, 'image.jpg');
    const studentId = localStorage.getItem('student_id');
    if (studentId) {
      formData.append('student_id', studentId);
    }
    const response = await fetch(apiUrl, {
      method: 'POST',
      body: formData
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || '服务器错误');
    }
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.message || '考勤失败');
    }
    return {
      success: true,
      message: result.message || '打卡成功',
      student: {
        student_id: result.student?.student_id || studentId,
        name: result.student?.name || '未知学生'
      },
      check_time: new Date().toLocaleString(),
      check_type: 'in'
    };
  } catch (error) {
    return {
      success: false,
      message: error.message || '静默活体考勤失败'
    };
  }
};

// 监听方案切换，切换时重置活体检测状态和API识别
watch(currentMethod, (val, oldVal) => {
  livenessActive.value = false;
  livenessStepText.value = '';
  livenessError.value = '';
  stopFaceRecognize();
  if (cameraActive.value && val === 'api') {
    startFaceRecognize();
  }
});

onMounted(() => {
  // 组件挂载时自动初始化
});

onUnmounted(() => {
  stopCamera();
  stopFaceRecognize();
});
</script>

<style scoped>
.attendance-container {
  width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}
.wide-layout {
  max-width: 1400px;
}
.main-flex-row {
  margin-top: 2%;
  height: 90%;
  display: flex;
  flex-direction: row;
  gap: 2.5rem;
}
.liveness-steps-panel {
  width: 320px;
  background: #f8fafb;
  border-radius: 1rem;
  padding: 2rem 1.5rem 1.5rem 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-height: 420px;
  margin-top: 0.5rem;
}
.liveness-title {
  font-size: 1.2rem;
  font-weight: bold;
  margin-bottom: 1.2rem;
  color: #005fa3;
}
.liveness-steps-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1.2rem 0;
  width: 100%;
}
.liveness-step-item {
  display: flex;
  align-items: center;
  margin-bottom: 0.7rem;
  font-size: 1.08rem;
}
.liveness-step-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: 1.3rem;
  margin-right: 0.7rem;
  background: #e9f5e1;
  color: #3bb273;
  border: 1.5px solid #b6e2b3;
}
.liveness-step-status.passed {
  background: #e9f5e1;
  color: #3bb273;
  border-color: #b6e2b3;
}
.liveness-step-status.current {
  background: #e3f0fa;
  color: #0071e3;
  border-color: #b3d8f6;
}
.liveness-step-status.failed {
  background: #ffeaea;
  color: #f44336;
  border-color: #fbb6b6;
}
.liveness-step-text-label {
  flex: 1;
  font-size: 1.08rem;
  color: #333;
}
.liveness-step-passed {
  color: #3bb273;
  font-size: 0.98rem;
  margin-left: 0.3rem;
}
.liveness-all-passed {
  margin: 1.2rem 0 0.5rem 0;
  width: 100%;
  display: flex;
  justify-content: center;
}
.liveness-yellow-block {
  background: #fffbe6;
  color: #bfa100;
  border-radius: 0.7rem;
  padding: 0.7rem 1.2rem;
  font-size: 1.15rem;
  font-weight: bold;
  box-shadow: 0 2px 8px rgba(255, 215, 0, 0.08);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.liveness-current-tip {
  margin-top: 1.2rem;
  color: #0071e3;
  font-size: 1.2rem;
  min-height: 1.5rem;
}
.liveness-error-tip {
  margin-top: 0.7rem;
  color: #f44336;
  font-size: 1.05rem;
  background: #fff0f0;
  border-radius: 0.5rem;
  padding: 0.5rem 1rem;
}
.detection-options {
  align-items: center;
  background-color: white;
  border-radius: 1rem;
  padding: 1.5rem;
  margin-bottom: 0rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

h2 {
  margin-bottom: 1rem;
  font-size: 1.5rem;
}

.option-buttons {
  
  align-items: center;
  display: flex;
  gap: 6rem;
  margin-bottom: 1rem;
}

.option-btn {
  align-items: center;
  display: flex;
  align-items: center;
  gap: 1rem;
  background-color: #f5f5f7;
  border: 2px solid transparent;
  border-radius: 0.5rem;
  padding: 0.75rem 3rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #888;
}

.option-btn.active {
  background-color: rgba(0, 113, 227, 0.1);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.option-icon {
  font-size: 1.25rem;
}

.method-description {
  background-color: #f5f5f7;
  padding: 1rem;
  border-radius: 0.5rem;
  color: var(--secondary-text);
}

.camera-section {
  justify-content: center;
  align-items: center;
  margin-bottom: 0rem;
}

.camera-container {
  align-items: center;
  position: relative;
  width: 100%;
  height: 480px;
  background-color: #f0f0f0;
  border-radius: 1rem;
  overflow: hidden;
  margin-bottom: 1rem;
  display: flex;
  justify-content: center;
  align-items: center;
}

.camera-feed {
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  /* object-fit: cover; */
}

.face-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.camera-controls {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.control-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease;
  border: none;
}

.start-btn {
  background-color: var(--primary-color);
  color: white;
}

.start-btn:hover {
  background-color: #0060c7;
}

.stop-btn {
  background-color: #f44336;
  color: white;
}

.stop-btn:hover {
  background-color: #d32f2f;
}

.attendance-btn {
  background-color: #4caf50;
  color: white;
}

.attendance-btn:hover {
  background-color: #388e3c;
}

.btn-icon {
  font-size: 1.25rem;
}

.processing-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: white;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 5px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.result-section {
  margin-top: 2rem;
}

.result-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  background-color: white;
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.result-card.success {
  border-left: 5px solid #4caf50;
}

.result-card.error {
  border-left: 5px solid #f44336;
}

.result-icon {
  font-size: 2rem;
}

.result-content {
  flex: 1;
}

.result-content h3 {
  margin-bottom: 0.5rem;
  font-size: 1.25rem;
}

.result-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.result-details p {
  margin-bottom: 0.5rem;
}

.api-result-success .api-result-row {
  color: #2e7d32;
  font-weight: 500;
  margin-bottom: 0.5rem;
}
.api-result-fail .api-result-row {
  color: #c62828;
  font-weight: 500;
  margin-bottom: 0.5rem;
}
.api-result-label {
  display: inline-block;
  min-width: 80px;
  color: #555;
}
.api-result-value.success {
  color: #2e7d32;
  font-weight: bold;
}
.api-result-value.fail {
  color: #c62828;
  font-weight: bold;
}
.api-result-value {
  margin-left: 0.5rem;
}

@media (max-width: 768px) {
  .option-buttons {
    flex-direction: column;
  }
  
  .camera-container {
    height: 350px;
  }
  
  .camera-controls {
    flex-direction: column;
  }
}
</style>