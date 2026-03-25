import axios from "axios";

// 统一的 HTTP 客户端，避免每个页面重复配置 baseURL。
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  timeout: 10000,
});

export default apiClient;
