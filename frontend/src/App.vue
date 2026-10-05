<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import {
  getExams,
  getNow,
  getToken,
  getMe,
  setToken,
  clearToken,
  logoutUser,
  listPlans,
  getUserLLMConfig,
  getProfile,
} from './api/client.js'
import StepIdentity from './components/StepIdentity.vue'
import StepGoals from './components/StepGoals.vue'
import StepProfile from './components/StepProfile.vue'
import StepResult from './components/StepResult.vue'
import AuthView from './components/AuthView.vue'
import DashboardView from './components/DashboardView.vue'
import PlanDetailView from './components/PlanDetailView.vue'
import LLMConfigModal from './components/LLMConfigModal.vue'
import UserProfileModal from './components/UserProfileModal.vue'

const STEP_LABELS = ['身份设定', '备考目标', '画像配置', '极速生成']

// 顶层视图：auth(登录/注册) | dashboard(我的计划) | wizard(向导) | plan(计划详情)
const view = ref('auth')
const me = ref(null)
const plans = ref([])
const selectedPlanId = ref(null)
const status = ref('')
const error = ref('')
const showLLMModal = ref(false)
const showProfileModal = ref(false)
const userLLMConfig = ref(null)

// 向导状态
const step = ref(1)
const now = ref(null)
const identity = ref('')
const nickname = ref('')
const selectedGoals = ref([])
const goalTargets = reactive({})
const dailyHours = ref(4)
const resumeText = ref('')
const useWebSearch = ref(true) // 联网检索真实招生政策（申博/考研）
const exams = ref([])
const categories = ref([])

function formatLocalDate(d) {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const todayLabel = computed(() => {
  const d = now.value
  if (!d) return ''
  return `${d.year} 年 ${d.month} 月 ${d.day} 日 · ${d.weekday || ''}`
})

async function loadExams() {
  status.value = '加载国家大纲库中…'
  try {
    const data = await getExams()
    exams.value = data.exams || []
    categories.value = data.categories || []
  } catch (e) {
    error.value = '加载考试大纲库失败：' + ((e.response && e.response.data && e.response.data.detail) || e.message)
  } finally {
    status.value = ''
  }
}

async function loadNow() {
  try {
    now.value = await getNow()
  } catch (e) {
    const t = new Date()
    const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
    now.value = {
      iso: formatLocalDate(t),
      date: formatLocalDate(t),
      year: t.getFullYear(),
      month: t.getMonth() + 1,
      day: t.getDate(),
      weekday: weekdays[t.getDay()],
      quarter: Math.floor(t.getMonth() / 3) + 1,
    }
  }
}

async function loadPlans() {
  try {
    const d = await listPlans()
    plans.value = d.plans || []
  } catch (e) {
    plans.value = []
  }
}

async function loadUserLLMConfig() {
  try {
    const res = await getUserLLMConfig()
    if (res && res.configured && res.config) {
      userLLMConfig.value = res.config
    } else {
      userLLMConfig.value = null
    }
  } catch (e) {
    userLLMConfig.value = null
  }
}

async function loadUserProfile() {
  try {
    const p = await getProfile()
    if (p && me.value) {
      me.value.nickname = p.nickname
      if (p.nickname && !nickname.value) {
        nickname.value = p.nickname
      }
      if (p.resume_text && !resumeText.value) {
        resumeText.value = p.resume_text
      }
    }
  } catch (e) {
    // ignore
  }
}

function onLLMConfigSaved(evt) {
  if (evt && evt.configured) {
    userLLMConfig.value = {
      provider: evt.provider,
      model_name: evt.model_name
    }
  } else {
    userLLMConfig.value = null
  }
}

function onProfileSaved(profile) {
  if (profile && me.value) {
    me.value.nickname = profile.nickname || me.value.username
    if (profile.nickname) nickname.value = profile.nickname
    if (profile.resume_text) resumeText.value = profile.resume_text
  }
}

// ---- 会话与路由自愈 ----
async function boot() {
  await loadExams()
  await loadNow()
  if (getToken()) {
    try {
      me.value = await getMe()
      loadUserLLMConfig()
      loadUserProfile()
      // 检查 hash 路由恢复
      const hash = window.location.hash
      if (hash.startsWith('#plan/')) {
        const pid = parseInt(hash.replace('#plan/', ''), 10)
        if (pid) {
          selectedPlanId.value = pid
          view.value = 'plan'
          await loadPlans()
          return
        }
      }
      view.value = 'dashboard'
      await loadPlans()
      return
    } catch (e) {
      clearToken()
    }
  }
  view.value = 'auth'
}

function onAuthed(payload) {
  setToken(payload.token)
  me.value = { user_id: payload.user_id, username: payload.username }
  view.value = 'dashboard'
  window.location.hash = '#dashboard'
  loadPlans()
  loadUserLLMConfig()
  loadUserProfile()
}

function logout() {
  // 通知后端吊销会话；即使请求失败也照常清理本地登录态
  logoutUser().catch(() => {})
  clearToken()
  me.value = null
  view.value = 'auth'
  window.location.hash = '#auth'
}

// ---- 向导流转 ----
function startWizard() {
  step.value = 1
  identity.value = ''
  selectedGoals.value = []
  for (const k in goalTargets) delete goalTargets[k]
  dailyHours.value = 4
  view.value = 'wizard'
  window.location.hash = '#wizard'
}

function goGoals(data) {
  identity.value = data.identity
  nickname.value = data.nickname
  step.value = 2
}

function goProfile(goals) {
  selectedGoals.value = goals
  step.value = 3
}

function goResult(data) {
  dailyHours.value = data.dailyHours
  Object.assign(goalTargets, data.goalTargets)
  if (data.resumeText) resumeText.value = data.resumeText
  step.value = 4
}

function onWizardDone() {
  loadPlans()
  view.value = 'dashboard'
  window.location.hash = '#dashboard'
}

function openPlan(id) {
  selectedPlanId.value = id
  view.value = 'plan'
  window.location.hash = `#plan/${id}`
}

function gotoDashboard() {
  selectedPlanId.value = null
  view.value = 'dashboard'
  window.location.hash = '#dashboard'
  loadPlans()
}

// 全局 401 监听
onMounted(() => {
  window.addEventListener('wokao:unauthorized', () => {
    me.value = null
    view.value = 'auth'
    window.location.hash = '#auth'
  })
  boot()
})
</script>

<template>
  <div class="min-h-screen bg-[#FAF7F2] text-black font-sans flex flex-col antialiased selection:bg-[#FFE600] selection:text-black">
    <!-- 顶栏：新粗野主义与涂鸦街头海报设计 -->
    <header class="bg-[#FFE600] border-b-[3px] border-black px-4 sm:px-8 py-3.5 sticky top-0 z-40 shadow-[0_4px_0px_0px_#000000]">
      <div class="max-w-6xl mx-auto flex items-center justify-between gap-4">
        <!-- 品牌 LOGO -->
        <div class="flex items-center gap-3 cursor-pointer select-none" @click="gotoDashboard">
          <div class="w-10 h-10 bg-black text-[#FFE600] border-2 border-black flex items-center justify-center font-black font-mono text-xl shadow-[3px_3px_0px_0px_#ffffff] rotate-[-2deg]">
            考
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-xl sm:text-2xl font-black font-neo-title tracking-tight text-black">
                我考 WO KAO
              </h1>
              <span class="neo-badge bg-black text-[#CCFF00] text-[10px] hidden sm:inline-block">
                v2.0 PRO
              </span>
            </div>
            <p class="text-[11px] font-bold text-neutral-800 tracking-wide uppercase">
              国家考试多目标融合备考规划院
            </p>
          </div>
        </div>

        <!-- 当前日期与状态 -->
        <div class="hidden md:flex items-center gap-2">
          <div class="neo-badge bg-white text-black text-xs font-mono shadow-[2px_2px_0px_0px_#000000]">
            📅 {{ todayLabel }}
          </div>
        </div>

        <!-- 登录状态 / 操作区 -->
        <div v-if="view !== 'auth'" class="flex items-center gap-2.5">
          <!-- 个人档案入口 -->
          <button
            @click="showProfileModal = true"
            class="neo-btn bg-white hover:bg-neutral-100 text-black text-xs px-3 py-1.5 font-black flex items-center gap-1.5 shadow-[2px_2px_0px_0px_#000]"
            title="查看与完善考生个人档案"
          >
            <span>👤 个人档案</span>
          </button>

          <!-- 自定义大模型配置入口 (BYOK) -->
          <button
            @click="showLLMModal = true"
            class="neo-btn bg-white hover:bg-neutral-100 text-black text-xs px-3 py-1.5 font-black flex items-center gap-1.5 shadow-[2px_2px_0px_0px_#000]"
            title="自定义大模型 API 密钥与 Provider 设置"
          >
            <span>⚙️ 模型配置</span>
            <span v-if="userLLMConfig" class="text-[10px] px-1.5 py-0.5 bg-[#CCFF00] text-black border border-black font-black max-w-[90px] truncate">
              {{ userLLMConfig.model_name || userLLMConfig.provider }}
            </span>
            <span v-else class="text-[10px] px-1.5 py-0.5 bg-[#E5E7EB] text-black border border-black font-bold">
              默认
            </span>
          </button>

          <div class="text-right hidden sm:block">
            <div class="text-xs font-black flex items-center gap-1.5 bg-white px-2.5 py-1 border-2 border-black shadow-[2px_2px_0px_0px_#000000]">
              <span class="w-2.5 h-2.5 rounded-full bg-[#CCFF00] border border-black inline-block animate-pulse"></span>
              {{ me ? (me.nickname || me.username) : '考生' }}
            </div>
          </div>
          <button
            class="neo-btn bg-black text-white hover:bg-neutral-800 text-xs px-3 py-1.5"
            @click="logout"
          >
            退出
          </button>
        </div>
      </div>
    </header>

    <!-- 视图主区域 -->
    <main class="flex-1 max-w-6xl mx-auto w-full px-4 py-6">
      <!-- 登录 / 注册视图 -->
      <AuthView v-if="view === 'auth'" @authed="onAuthed" />

      <!-- 我的计划（仪表盘） -->
      <DashboardView
        v-else-if="view === 'dashboard'"
        :plans="plans"
        :me="me"
        :now-label="todayLabel"
        @new="startWizard"
        @open="openPlan"
        @refresh="loadPlans"
        @open-profile="showProfileModal = true"
      />

      <!-- 备考规划向导涂鸦海报盒 -->
      <div
        v-else-if="view === 'wizard'"
        class="bg-white border-[3px] border-black shadow-[8px_8px_0px_0px_#000000] p-6 sm:p-9 min-h-[65vh] relative"
      >
        <!-- 顶部街头涂鸦胶带标签 -->
        <div class="graffiti-tape graffiti-tape-lime">
          ★ WO KAO PLANNER WIZARD ★
        </div>

        <!-- 步骤指示器（粗野风格） -->
        <div class="mb-8 border-b-[3px] border-black pb-6 pt-2">
          <ol class="flex items-center justify-between max-w-3xl mx-auto">
            <li v-for="(label, i) in STEP_LABELS" :key="label" class="flex-1 flex items-center">
              <div class="flex flex-col sm:flex-row items-center gap-2">
                <div
                  :class="[
                    'w-9 h-9 flex items-center justify-center text-sm font-black border-2 border-black transition-all shadow-[2px_2px_0px_0px_#000000]',
                    step > i + 1
                      ? 'bg-[#CCFF00] text-black'
                      : step === i + 1
                      ? 'bg-[#FFE600] text-black scale-110 shadow-[3px_3px_0px_0px_#000000]'
                      : 'bg-[#F4F0EA] text-neutral-400',
                  ]"
                >
                  <span v-if="step > i + 1">✓</span>
                  <span v-else>{{ i + 1 }}</span>
                </div>
                <span
                  :class="[
                    'text-xs font-black text-center sm:text-left tracking-wide',
                    step === i + 1 ? 'text-black bg-[#FFE600] px-1.5 py-0.5 border border-black shadow-[1px_1px_0px_0px_#000]' : 'text-neutral-500',
                  ]"
                >
                  {{ label }}
                </span>
              </div>
              <div
                v-if="i < STEP_LABELS.length - 1"
                :class="[
                  'flex-1 h-1.5 mx-2 border border-black transition-all',
                  step > i + 1 ? 'bg-black' : 'bg-[#E5E7EB]',
                ]"
              ></div>
            </li>
          </ol>
        </div>

        <!-- 动态步骤组件 -->
        <StepIdentity
          v-if="step === 1"
          :identity="identity"
          :nickname="nickname"
          @next="goGoals"
        />

        <StepGoals
          v-else-if="step === 2"
          :exams="exams"
          :categories="categories"
          :selected="selectedGoals"
          :now="now"
          v-model:use-web-search="useWebSearch"
          @next="goProfile"
          @back="step = 1"
        />

        <StepProfile
          v-else-if="step === 3"
          :identity="identity"
          :nickname="nickname"
          :goals="selectedGoals"
          :goal-targets="goalTargets"
          :daily-hours="dailyHours"
          @next="goResult"
          @back="step = 2"
        />

        <StepResult
          v-else-if="step === 4"
          :identity="identity"
          :nickname="nickname"
          :goals="selectedGoals"
          :goal-targets="goalTargets"
          :daily-hours="dailyHours"
          :now="now"
          :use-web-search="useWebSearch"
          @back="step = 3"
          @done="onWizardDone"
        />
      </div>

      <!-- 计划详情与交互看板 -->
      <PlanDetailView
        v-else-if="view === 'plan'"
        :plan-id="selectedPlanId"
        :me="me"
        @back="gotoDashboard"
        @deleted="gotoDashboard"
      />
    </main>

    <footer v-if="view !== 'auth'" class="text-center text-xs font-bold text-black py-4 no-print border-t-[3px] border-black bg-[#FAF7F2]">
      ⚡ 我考 WoKao-ExamAgent · 依据国家招考大纲与确定性约束求解排程引擎 · 时间以官方实时公告为准 💥
    </footer>

    <div v-if="status" class="fixed bottom-6 left-1/2 -translate-x-1/2 bg-[#FFE600] text-black border-[3px] border-black text-xs font-black px-5 py-2.5 shadow-[4px_4px_0px_0px_#000000] z-50 flex items-center gap-2">
      <span class="animate-spin text-sm">⏳</span> {{ status }}
    </div>
    <div v-if="error" class="fixed bottom-6 left-1/2 -translate-x-1/2 bg-[#FF3399] text-white border-[3px] border-black text-xs font-black px-5 py-2.5 shadow-[4px_4px_0px_0px_#000000] max-w-md text-center z-50">
      {{ error }}
      <button @click="error = ''" class="ml-3 underline bg-black text-white px-2 py-0.5 text-[10px] border border-white">关闭</button>
    </div>

    <!-- 用户自定义 LLM 模型配置弹窗 -->
    <LLMConfigModal
      :show="showLLMModal"
      @close="showLLMModal = false"
      @saved="onLLMConfigSaved"
    />

    <!-- 考生个人档案中心弹窗 -->
    <UserProfileModal
      :show="showProfileModal"
      @close="showProfileModal = false"
      @saved="onProfileSaved"
    />
  </div>
</template>
