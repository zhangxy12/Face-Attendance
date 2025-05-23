<template>
  <div class="records-container">
    <h1>考勤记录查询</h1>

    <div class="search-section">
      <div class="search-form">
        <div class="form-group" v-if="isTeacher">
          <label for="studentId">学生学号</label>
          <input 
            type="text" 
            id="studentId" 
            v-model="searchForm.studentId" 
            placeholder="请输入学生学号，不填则查询全部"
          >
        </div>
        <div class="form-group" v-if="isTeacher">
          <label for="className">班级</label>
          <input 
            type="text" 
            id="className" 
            v-model="searchForm.className" 
            placeholder="请输入班级名称,不填则查询全部"
          >
        </div>
        <div class="form-group">
          <label for="startDate">开始日期</label>
          <input 
            type="date" 
            id="startDate" 
            v-model="searchForm.startDate"
          >
        </div>
        <div class="form-group">
          <label for="endDate">结束日期</label>
          <input 
            type="date" 
            id="endDate" 
            v-model="searchForm.endDate"
          >
        </div>
        <button class="search-button" @click="searchRecords" :disabled="isLoading">
          <span v-if="!isLoading">🔍 查询</span>
          <span v-else>⏳ 加载中...</span>
        </button>
      </div>
      <div class="student-notice" v-if="!isTeacher">
        <p>注意：学生只能查看自己的考勤记录</p>
      </div>
    </div>

    <div v-if="isLoading" class="loading-section">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="searchError" class="error-section">
      <div class="error-icon">❌</div>
      <p>{{ searchError }}</p>
    </div>

    <div v-else-if="searchResult" class="records-section">
      <div class="student-info" v-if="!isTeacher || searchForm.studentId">
        <h2>{{ searchResult.student.name }} 的考勤记录</h2>
        <div class="student-details">
          <p><strong>学生学号:</strong> {{ searchResult.student.student_id }}</p>
          <p><strong>班级:</strong> {{ searchResult.student.class_name || '未设置' }}</p>
          <p><strong>记录总数:</strong> {{ searchResult.record_count }}</p>
        </div>
      </div>

      <div class="student-info" v-else>
        <h2>班级考勤记录</h2>
        <div class="student-details">
          <p><strong>班级:</strong> {{ searchForm.className || '全部班级' }}</p>
          <p><strong>时间范围:</strong> {{ searchForm.startDate }} 至 {{ searchForm.endDate }}</p>
          <p><strong>记录总数:</strong> {{ searchResult.record_count }}</p>
        </div>
        <div class="export-section" v-if="isTeacher && searchResult.attendance_records.length > 0">
          <button class="export-button" @click="exportToExcel">
            导出为Excel
          </button>
        </div>
      </div>

      <div class="records-table-container">
        <table class="records-table" v-if="searchResult.attendance_records.length > 0">
          <thead>
            <tr>
              <th v-if="isTeacher && !searchForm.studentId">学号</th>
              <th v-if="isTeacher && !searchForm.studentId">姓名</th>
              <th v-if="isTeacher && !searchForm.studentId">班级</th>
              <th>日期</th>
              <th>时间</th>
              <th>状态</th>
              <th>检测方式</th>
              <th>相似度</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in searchResult.attendance_records" :key="record.id">
              <td v-if="isTeacher && !searchForm.studentId">{{ record.student_id }}</td>
              <td v-if="isTeacher && !searchForm.studentId">{{ record.name }}</td>
              <td v-if="isTeacher && !searchForm.studentId">{{ record.class_name }}</td>
              <td>{{ formatDate(record.check_time) }}</td>
              <td>{{ formatTime(record.check_time) }}</td>
              <td :class="getStatusClass(record.status)">
                {{ translateStatus(record.status) }}
              </td>
              <td>{{ record.detection_method }}</td>
              <td>{{ record.similarity ? (record.similarity * 100).toFixed(2) + '%' : '-' }}</td>
              <td>{{ record.remark || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div class="no-records" v-else>
          <p>该时间段内无考勤记录</p>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">📋</div>
      <p>请输入查询条件并点击查询按钮</p>
    </div>

    <div class="statistics-section" v-if="searchResult && searchResult.attendance_records.length > 0">
      <h2>考勤统计</h2>
      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-title">出勤次数</div>
          <div class="stat-value">{{ statistics.attendanceDays }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">迟到次数</div>
          <div class="stat-value">{{ statistics.lateDays }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">缺勤次数</div>
          <div class="stat-value">{{ statistics.absentDays }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';

// 判断当前用户角色
const userRole = localStorage.getItem('userRole');
const isTeacher = computed(() => userRole === 'teacher');
const userId = localStorage.getItem('userId');
const token = localStorage.getItem('token');
const studentIdFromStorage = localStorage.getItem('student_id');

// 如果是学生，获取学生ID
let studentId = '';
if (!isTeacher.value) {
  // 使用localStorage中的studentId或使用真实姓名来识别
  studentId = studentIdFromStorage || localStorage.getItem('realName');
  
  // 当组件挂载时自动设置
  onMounted(() => {
    if (studentId) {
      searchForm.studentId = studentId;
      // 自动搜索学生的记录
      searchRecords();
    }
  });
}

// 搜索表单
const searchForm = reactive({
  studentId: studentId || '',
  className: '',
  startDate: new Date().toISOString().substr(0, 10),
  endDate: new Date().toISOString().substr(0, 10)
});

// 状态
const isLoading = ref(false);
const searchResult = ref(null);
const searchError = ref(null);
const statisticsData = ref(null);

// 方法
const searchRecords = async () => {
  // 表单验证
  if (!isTeacher.value && !searchForm.studentId) {
    searchError.value = '无法获取学生信息，请登录后再试';
    return;
  }

  // 学生只能查看自己的记录
  if (!isTeacher.value && searchForm.studentId !== studentId) {
    searchError.value = '您只能查看自己的考勤记录';
    return;
  }

  if (!searchForm.startDate) {
    searchError.value = '请选择开始日期';
    return;
  }

  if (!searchForm.endDate) {
    searchError.value = '请选择结束日期';
    return;
  }

  // 日期比较
  if (new Date(searchForm.startDate) > new Date(searchForm.endDate)) {
    searchError.value = '开始日期不能晚于结束日期';
    return;
  }

  searchError.value = null;
  isLoading.value = true;

  try {
    // 构建API URL
    let apiUrl = '/api/attendance?';
    
    // 如果有学生ID，添加到查询参数
    if (searchForm.studentId) {
      apiUrl += `student_id=${searchForm.studentId}&`;
    }
    
    // 如果有班级，添加到查询参数
    if (searchForm.className) {
      apiUrl += `class_name=${searchForm.className}&`;
    }
    
    // 添加日期范围
    apiUrl += `start_date=${searchForm.startDate}&end_date=${searchForm.endDate}`;
    
    // 调用API获取考勤记录
    const response = await fetch(apiUrl);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || '服务器错误');
    }

    const responseData = await response.json();
    
    if (!responseData.success) {
      throw new Error(responseData.message || '获取数据失败');
    }
    console.log(responseData);
    // 如果没有记录
    if (responseData.data.length === 0) {
      searchResult.value = {
        student: {
          student_id: searchForm.studentId || '',
          name: '未知学生',
          class_name: searchForm.className || ''
        },
        record_count: 0,
        attendance_records: []
      };
      return;
    }
    
    // 格式化数据
    if (searchForm.studentId || !isTeacher.value) {
      // 单个学生的记录
      searchResult.value = {
        student: {
          student_id: searchForm.studentId || responseData.data[0].student_id,
          name: responseData.data[0]?.name || '未知学生',
          class_name: responseData.data[0]?.class_name || ''
        },
        record_count: responseData.data.length,
        attendance_records: responseData.data
      };
    } else {
      // 多个学生的记录
      searchResult.value = {
        record_count: responseData.data.length,
        attendance_records: responseData.data
      };
    }

    // 获取考勤统计
    await fetchStatistics();
  } catch (error) {
    console.error('获取考勤记录失败:', error);
    searchError.value = `查询失败: ${error.message || '未知错误'}`;
    searchResult.value = null;
    statisticsData.value = null;
  } finally {
    isLoading.value = false;
  }
};

// 获取考勤统计数据
const fetchStatistics = async () => {
  if (!searchForm.startDate || !searchForm.endDate) {
    return;
  }
  
  try {
    let statsUrl = `/api/attendance/statistics?start_date=${searchForm.startDate}&end_date=${searchForm.endDate}`;
    
    // 学生只能查看自己的统计
    if (!isTeacher.value) {
      statsUrl += `&student_id=${studentId}`;
    } else if (searchForm.studentId) {
      statsUrl += `&student_id=${searchForm.studentId}`;
    }
    
    if (searchForm.className) {
      statsUrl += `&class_name=${searchForm.className}`;
    }
    
    const response = await fetch(statsUrl);
    
    if (!response.ok) {
      console.error('获取统计数据失败');
      return;
    }
    
    const statsData = await response.json();
    
    if (statsData.success && statsData.data) {
      // 找到当前学生的统计数据或者计算总统计
      if (searchForm.studentId) {
        const studentStats = statsData.data.stats.find(
          stat => stat.student_id === searchForm.studentId
        );
        
        if (studentStats) {
          statisticsData.value = {
            attendanceDays: studentStats.present_count || 0,
            lateDays: studentStats.late_count || 0,
            absentDays: studentStats.absent_count || 0
          };
        }
      } else {
        // 计算总统计
        statisticsData.value = {
          attendanceDays: statsData.data.total.total_present || 0,
          lateDays: statsData.data.total.total_late || 0,
          absentDays: statsData.data.total.total_absent || 0
        };
      }
    }
  } catch (error) {
    console.error('获取统计数据异常:', error);
  }
};

// 格式化日期和时间
const formatDate = (dateTimeStr) => {
  const date = new Date(dateTimeStr);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

const formatTime = (dateTimeStr) => {
  const date = new Date(dateTimeStr);
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`;
};

// 获取状态对应的CSS类名
const getStatusClass = (status) => {
  switch (status) {
    case 'early':
      return 'status-present';
    case 'present':
      return 'status-present';
    case 'late':
      return 'status-late';
    case 'absent':
      return 'status-absent';
    default:
      return '';
  }
};

// 翻译状态为中文
const translateStatus = (status) => {
  switch (status) {
    case 'early':
      return '未到打卡时间';
    case 'present':
      return '正常出勤';
    case 'late':
      return '迟到';
    case 'absent':
      return '缺勤';
    default:
      return status;
  }
};

// 考勤统计
const statistics = computed(() => {
  if (statisticsData.value) {
    return statisticsData.value;
  }
  
  if (!searchResult.value || !searchResult.value.attendance_records) {
    return {
      attendanceDays: 0,
      lateDays: 0,
      absentDays: 0
    };
  }

  // 如果没有从API获取到数据，则提供一个基本计算的统计数据
  const records = searchResult.value.attendance_records;
  return {
    attendanceDays: records.filter(r => r.status === 'present').length,
    lateDays: records.filter(r => r.status === 'late').length,
    absentDays: records.filter(r => r.status === 'absent').length
  };
});

// 导出到Excel
const exportToExcel = () => {
  if (!searchResult.value || !searchResult.value.attendance_records || searchResult.value.attendance_records.length === 0) {
    alert('没有可导出的数据');
    return;
  }
  
  // 创建工作表数据
  let csv = '学号,姓名,班级,日期,时间,状态,检测方式,相似度,备注\n';
  
  searchResult.value.attendance_records.forEach(record => {
    const row = [
      record.student_id || '',
      record.name || '',
      record.class_name || '',
      formatDate(record.check_time),
      formatTime(record.check_time),
      translateStatus(record.status),
      record.detection_method || '',
      record.similarity ? (record.similarity * 100).toFixed(2) + '%' : '',
      record.remark || ''
    ];
    
    // 处理可能包含逗号的字段
    const processedRow = row.map(field => {
      // 如果字段包含逗号、双引号或换行符，则用双引号包裹并将内部的双引号替换为两个双引号
      if (typeof field === 'string' && (field.includes(',') || field.includes('"') || field.includes('\n'))) {
        return `"${field.replace(/"/g, '""')}"`;
      }
      return field;
    });
    
    csv += processedRow.join(',') + '\n';
  });
  
  // 创建Blob对象
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  
  // 创建下载链接
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  // 设置文件名
  const fileName = `考勤记录_${searchForm.className || '全部'}_${searchForm.startDate}_${searchForm.endDate}.csv`;
  
  link.href = url;
  link.setAttribute('download', fileName);
  document.body.appendChild(link);
  
  // 触发下载
  link.click();
  
  // 清理
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
</script>

<style scoped>
.records-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: var(--text-color);
}

.search-section {
  background-color: white;
  border-radius: 1rem;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-end;
}

.form-group {
  flex: 1;
  min-width: 200px;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--text-color);
}

input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.search-button {
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.search-button:hover {
  background-color: #0060c7;
}

.search-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.loading-section,
.empty-state,
.error-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  background-color: white;
  border-radius: 1rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 5px solid rgba(0, 113, 227, 0.3);
  border-radius: 50%;
  border-top-color: var(--primary-color);
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 1rem;
}

.empty-icon,
.error-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.error-icon {
  color: #f44336;
}

.records-section {
  margin-top: 2rem;
}

.student-info {
  background-color: white;
  border-radius: 1rem;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  position: relative;
}

.student-info h2 {
  margin-bottom: 1rem;
  font-size: 1.5rem;
}

.student-details {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.student-details p {
  margin: 0;
  flex: 1;
  min-width: 200px;
}

.export-section {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
}

.export-button {
  background-color: #4caf50;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.export-button:hover {
  background-color: #3d8b40;
}

.records-table-container {
  background-color: white;
  border-radius: 1rem;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow-x: auto;
}

.records-table {
  width: 100%;
  border-collapse: collapse;
}

.records-table th,
.records-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #eee;
  text-align: left;
}

.records-table th {
  background-color: #f5f5f7;
  font-weight: 600;
}

.records-table tbody tr:hover {
  background-color: #f9f9f9;
}

.status-present {
  color: #4caf50;
}

.status-late {
  color: #ff9800;
}

.status-absent {
  color: #f44336;
}

.no-records {
  text-align: center;
  padding: 2rem;
  color: var(--secondary-text);
}

.statistics-section {
  background-color: white;
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.statistics-section h2 {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  text-align: center;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background-color: #f5f5f7;
  border-radius: 0.75rem;
  padding: 1.5rem;
  text-align: center;
}

.stat-title {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--secondary-text);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--primary-color);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .search-form {
    flex-direction: column;
  }
  
  .form-group {
    width: 100%;
  }
  
  .search-button {
    width: 100%;
  }
  
  .student-details {
    flex-direction: column;
  }
  
  .export-section {
    position: static;
    margin-top: 1rem;
    text-align: center;
  }
}

.student-notice {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background-color: #fff9c4;
  border-radius: 0.5rem;
  border-left: 4px solid #ffc107;
}

.student-notice p {
  margin: 0;
  color: #856404;
  font-weight: 500;
}
</style> 