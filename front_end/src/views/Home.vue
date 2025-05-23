<template>
  <div class="home-container">
    <section class="hero-section">
      <div class="hero-content">
        <h1>智能人脸考勤系统</h1>
        <p>基于人脸识别技术的校园考勤管理解决方案</p>
        <!-- <div class="cta-buttons">
          <router-link to="/attendance" class="btn-primary">立即打卡</router-link>
          <router-link to="/register" class="btn-secondary">学生注册</router-link>
        </div> -->
      </div>
      <div class="hero-image">
        <img src="../assets/2.png" alt="人脸识别" />
      </div>
    </section>

    <section class="features-section">
      <h2>系统特点</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">🔐</div>
          <h3>多种活体检测</h3>
          <p>支持三种不同的活体检测方案，有效防止照片、视频攻击</p>
        </div>

        <div class="feature-card">
          <div class="feature-icon">⚡</div>
          <h3>高效便捷</h3>
          <p>快速准确的人脸识别技术，5秒完成签到打卡</p>
        </div>

        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3>数据分析</h3>
          <p>自动统计考勤数据，支持多维度查询与导出</p>
        </div>

        <div class="feature-card">
          <div class="feature-icon">🔄</div>
          <h3>实时同步</h3>
          <p>考勤记录即时上传，管理人员可随时查看</p>
        </div>
      </div>
    </section>

    <section class="stats-section">
      <h2>系统数据</h2>
      <div class="stats-grid">
        <!-- <div class="stat-card">
          <div class="stat-number">93.2%</div>
          <div class="stat-label">识别准确率</div>
        </div> -->

        <div class="stat-card">
          <div class="stat-number">5秒</div>
          <div class="stat-label">平均识别时间</div>
        </div>

        <div class="stat-card">
          <div class="stat-number">3种</div>
          <div class="stat-label">活体检测方案</div>
        </div>

        <div class="stat-card">
          <div class="stat-number">1000+</div>
          <div class="stat-label">日处理考勤量</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
// Home page logic
</script>

<style scoped>
.home-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4rem;
  margin-top: 4%;
  gap: 2rem;
}

.hero-content {
  flex: 1;
  justify-content: center;
  align-items: center;
}

.hero-image {
  border-radius: 2%;
  
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.hero-image img {
  border-radius: 2%;
  border-color: aquamarine;
  border-width: 200px;
  max-width: 65%;
  height: auto;
}

h1 {
  font-size: 4rem;
  margin-bottom: 1rem;
  background: linear-gradient(135deg, var(--primary-color) 0%, #3aa5f1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-content p {
  font-size: 1.5rem;
  margin-bottom: 2rem;
  color: var(--secondary-text);
}

.cta-buttons {
  display: flex;
  gap: 1rem;
}

.btn-primary {
  background-color: var(--primary-color);
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  text-decoration: none;
  font-weight: 600;
  transition: background-color 0.3s ease;
}

.btn-primary:hover {
  background-color: #0051a8;
}

.btn-secondary {
  background-color: white;
  color: var(--primary-color);
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  text-decoration: none;
  font-weight: 600;
  border: 1px solid var(--primary-color);
  transition: background-color 0.3s ease;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
}

/* Features section */
.features-section {
  margin-bottom: 4rem;
}

h2 {
  font-size: 2rem;
  text-align: center;
  margin-bottom: 2rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
}

.feature-card {
  background-color: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
}

.feature-card p {
  color: var(--secondary-text);
}

/* Stats section */
.stats-section {
  margin-bottom: 4rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
}

.stat-card {
  background-color: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 0.5rem;
}

.stat-label {
  color: var(--secondary-text);
  font-size: 1.1rem;
}

/* Responsive */
@media (max-width: 768px) {
  .hero-section {
    flex-direction: column;
  }

  .hero-content {
    text-align: center;
  }

  .cta-buttons {
    justify-content: center;
  }

  h1 {
    font-size: 2rem;
  }

  .hero-content p {
    font-size: 1.1rem;
  }
}
</style>