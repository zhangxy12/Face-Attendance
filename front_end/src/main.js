import { createApp } from 'vue';
import './style.css'; // 引入样式文件
import App from './App.vue'; // 引入根组件
// import DataVVue3 from '@kjgl77/datav-vue3'
import router from './router/index.js'

// import VueVideoPlayer from  '@videojs-player/vue'; // 引入 Video.js 的样式
// 创建 Vue 应用
const app = createApp(App);

// app.use(DataVVue3);
app.use(router);
// app.use(VueVideoPlayer);
app.mount('#app');

