import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import "./styles.css";

// 前端入口：创建应用、注册路由、挂载到页面。
createApp(App).use(router).mount("#app");
