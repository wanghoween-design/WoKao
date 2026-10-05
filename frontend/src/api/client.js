import axios from 'axios'

const TOKEN_KEY = 'wokao_token'

const http = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

// 请求拦截：自动附带 Bearer 令牌
http.interceptors.request.use((config) => {
  const t = localStorage.getItem(TOKEN_KEY)
  if (t) config.headers.Authorization = `Bearer ${t}`
  return config
})

// 响应拦截：401 统一清空令牌并通知应用跳转登录
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      window.dispatchEvent(new Event('wokao:unauthorized'))
    }
    return Promise.reject(err)
  }
)

// ---- 令牌管理 ----
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

// ---- 通用 ----
export const getExams = () => http.get('/exams').then((r) => r.data)
export const getNow = () => http.get('/now').then((r) => r.data)

// ---- 账号 ----
export const registerUser = (payload) => http.post('/auth/register', payload).then((r) => r.data)
export const loginUser = (payload) => http.post('/auth/login', payload).then((r) => r.data)
export const logoutUser = () => http.post('/auth/logout').then((r) => r.data).catch(() => ({}))
export const getMe = () => http.get('/me').then((r) => r.data)

// ---- 计划（需登录）----
export const generateFusedPlan = (payload) => http.post('/generate_fused_plan', payload).then((r) => r.data)
export const listPlans = () => http.get('/plans').then((r) => r.data)
export const getPlan = (id) => http.get(`/plans/${id}`).then((r) => r.data)
export const updatePlan = (id, payload) => http.put(`/plans/${id}`, payload).then((r) => r.data)
export const deletePlan = (id) => http.delete(`/plans/${id}`).then((r) => r.data)

// ---- 导出与下载 ----
export async function downloadPlanIcs(id, filename = '备考计划.ics') {
  const res = await http.get(`/plans/${id}/export.ics`, { responseType: 'blob' })
  const blob = new Blob([res.data], { type: 'text/calendar;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.ics') ? filename : `${filename}.ics`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export async function downloadPlanMd(id, filename = '备考计划.md') {
  const res = await http.get(`/plans/${id}/export.md`, { responseType: 'blob' })
  const blob = new Blob([res.data], { type: 'text/markdown;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.md') ? filename : `${filename}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

/** 保存用户简历文本 */
export function saveResume(payload) {
  return http.post('/profile/resume', payload).then(r => r.data)
}

/** 获取用户画像（含简历） */
export function getProfile() {
  return http.get('/profile').then(r => r.data)
}

/** 全量更新用户画像与档案 */
export function updateProfile(payload) {
  return http.put('/profile', payload).then(r => r.data)
}

/** 搜索考试信息（带来源验证） */
export function searchExamInfo(payload) {
  return http.post('/search_exam_info', payload).then(r => r.data)
}

/** 更新计划日程编排 */
export function updateSchedule(planId, payload) {
  return http.put(`/plans/${planId}/schedule`, payload).then(r => r.data)
}

/** 获取当前用户自定义 LLM 配置 */
export function getUserLLMConfig() {
  return http.get('/user/llm_config').then((r) => r.data)
}

/** 保存或更新用户自定义 LLM 配置（同名覆盖，带 name 支持多套配置） */
export function saveUserLLMConfig(payload) {
  return http.post('/user/llm_config', payload).then((r) => r.data)
}

/** 切换激活的模型配置（额度用完换另一套） */
export function activateUserLLMConfig(name) {
  return http.post('/user/llm_config/activate', { name }).then((r) => r.data)
}

/** 删除用户自定义 LLM 配置：带 name 删单套，不带 name 清空全部（恢复默认） */
export function deleteUserLLMConfig(name) {
  return http.delete('/user/llm_config', { params: name ? { name } : {} }).then((r) => r.data)
}

/** 测试 LLM 模型连接 */
export function testUserLLMConfig(payload) {
  return http.post('/user/llm_config/test', payload).then((r) => r.data)
}

/** 与伴学 AI 导师对话 */
export function chatWithCoach(payload) {
  return http.post('/agent/chat', payload).then((r) => r.data)
}

export default http

