<script setup>
import { ref, reactive, computed, watch } from 'vue'
import md from '../md.js'
import ScheduleEditor from './ScheduleEditor.vue'
import AppleCalendarWeekView from './AppleCalendarWeekView.vue'
import TaskDetailModal from './TaskDetailModal.vue'
import AICoachDrawer from './AICoachDrawer.vue'
import DeleteConfirmModal from './DeleteConfirmModal.vue'
import { updatePlan, deletePlan, downloadPlanIcs, downloadPlanMd } from '../api/client.js'

const props = defineProps({
  plan: { type: Object, required: true },
  me: { type: Object, default: null },
})
const emit = defineEmits(['back', 'deleted', 'updated'])

const TRACK_COLORS = ['#FFE600', '#CCFF00', '#00F0FF', '#FF3399', '#B388FF', '#FFA34D']
const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const localPlan = ref(props.plan)
const fused = ref(null)
const activeView = ref('week') // week (Apple Calendar) | timeline | list | md
const selectedTrackFilter = ref('all')
const checked = ref({}) // taskId -> bool
const saving = ref(false)
const deleting = ref(false)
const showDeleteModal = ref(false)
const msg = ref('')
const error = ref('')
const feedback = ref('')
const regen = ref(false)
const showFeedbackDrawer = ref(false)
const copySuccess = ref(false)
const showScheduleEditor = ref(false)

// 任务详情弹窗状态与 AI 导师状态
const activeTaskModal = reactive({
  show: false,
  task: null,
  trackName: '',
  color: '',
  isDone: false
})
const focusedCoachTask = ref(null)
const focusedCoachTrackName = ref('')
const coachCollapsed = ref(false)

function onSelectTask(evt) {
  activeTaskModal.show = true
  activeTaskModal.task = evt.task
  activeTaskModal.trackName = evt.trackName
  activeTaskModal.color = evt.color
  activeTaskModal.isDone = evt.isDone
  focusedCoachTask.value = evt.task
  focusedCoachTrackName.value = evt.trackName
}

function onToggleDoneFromModal() {
  if (activeTaskModal.task) {
    toggle(activeTaskModal.task._id)
    activeTaskModal.isDone = isChecked(activeTaskModal.task._id)
  }
}

function onAskCoachFromModal(task) {
  activeTaskModal.show = false
  focusedCoachTask.value = task
  coachCollapsed.value = false
}

function onStartPomodoro(task) {
  activeTaskModal.show = false
  startTaskTimer(task.title)
}

function onScheduleSaved() {
  showScheduleEditor.value = false
  emit('updated')
}

function parsePlanDate(str) {
  if (!str) return new Date()
  const parts = str.match(/(\d{4})-(\d{2})-(\d{2})/)
  if (parts) {
    return new Date(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3]))
  }
  return new Date(str)
}

function getWeekDateRange(w) {
  const base = parsePlanDate(localPlan.value?.created_at)
  const currentDay = base.getDay()
  const distToMonday = (currentDay === 0 ? -6 : 1 - currentDay)
  const mondayOfWeek1 = new Date(base)
  mondayOfWeek1.setDate(base.getDate() + distToMonday)
  mondayOfWeek1.setHours(0, 0, 0, 0)

  const monday = new Date(mondayOfWeek1)
  monday.setDate(mondayOfWeek1.getDate() + (Number(w) - 1) * 7)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)

  const fmt = (d) => `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`
  return `${fmt(monday)}~${fmt(sunday)}`
}

function onScheduleUpdatedFromCoach(updatedPlan) {
  if (updatedPlan) {
    syncFromPlan(updatedPlan)
  }
  emit('updated')
}

// 番茄钟状态
const showTimer = ref(false)
const timerSeconds = ref(25 * 60)
const timerRunning = ref(false)
let timerInterval = null

function parseFused(p) {
  if (!p || !p.fused_plan) return null
  try {
    const obj = JSON.parse(p.fused_plan)
    ;(obj.tracks || []).forEach((t, ti) => {
      t._color = TRACK_COLORS[ti % TRACK_COLORS.length]
      ;(t.tasks || []).forEach((task, ki) => {
        task._id = `${ti}-${ki}`
      })
    })
    return obj
  } catch (e) {
    return null
  }
}

function syncFromPlan(p) {
  localPlan.value = p
  fused.value = parseFused(p)
  const c = {}
  ;(fused.value?.tracks || []).forEach((t) =>
    (t.tasks || []).forEach((task) => {
      if (task.status === 'done') c[task._id] = true
    })
  )
  checked.value = c
  msg.value = ''
}
syncFromPlan(props.plan)

watch(
  () => props.plan,
  (p) => syncFromPlan(p)
)

const isFused = computed(() => !!fused.value && Array.isArray(fused.value.tracks) && fused.value.tracks.length > 0)
const horizon = computed(() => Math.max(1, Number(fused.value?.horizon_weeks) || 12))
const weekCols = computed(() => Array.from({ length: horizon.value }, (_, i) => i + 1))

const selectedWeekFilter = ref(1) // 默认聚焦第 1 周

const trackProgress = computed(() => {
  const map = {}
  ;(fused.value?.tracks || []).forEach((t) => {
    const total = (t.tasks || []).length
    const done = (t.tasks || []).filter((k) => !!checked.value[k._id]).length
    const pct = total ? Math.round((done / total) * 100) : 0
    map[t.exam_name] = { total, done, pct }
  })
  return map
})

const totalStats = computed(() => {
  let total = 0
  let done = 0
  Object.values(trackProgress.value).forEach((p) => {
    total += p.total
    done += p.done
  })
  const pct = total ? Math.round((done / total) * 100) : 0
  return { total, done, pct }
})

function isChecked(id) {
  return !!checked.value[id]
}

function toggle(id) {
  checked.value[id] = !checked.value[id]
  checked.value = { ...checked.value }
}

async function saveProgress() {
  if (!isFused.value) return
  saving.value = true
  msg.value = ''
  error.value = ''
  try {
    const clone = JSON.parse(JSON.stringify(fused.value))
    ;(clone.tracks || []).forEach((t) =>
      (t.tasks || []).forEach((k) => {
        k.status = checked.value[k._id] ? 'done' : 'todo'
        delete k._id
      })
    )
    const newJson = JSON.stringify(clone)
    const d = await updatePlan(localPlan.value.id, { fused_plan: newJson })
    syncFromPlan(d.plan)
    msg.value = '✓ 打卡进度已保存至档案库'
    emit('updated')
  } catch (e) {
    error.value = '保存打卡进度失败：' + e.message
  } finally {
    saving.value = false
  }
}

async function regenerate() {
  if (!feedback.value.trim()) return
  regen.value = true
  msg.value = ''
  error.value = ''
  try {
    const payload = {
      title: localPlan.value.title,
      daily_hours: localPlan.value.daily_hours,
      user_feedback: feedback.value,
    }
    const d = await updatePlan(localPlan.value.id, payload)
    syncFromPlan(d.plan)
    msg.value = '✓ AI 规划师已按意见重构周作息与排期'
    feedback.value = ''
    showFeedbackDrawer.value = false
    emit('updated')
  } catch (e) {
    error.value = '微调重构失败：' + e.message
  } finally {
    regen.value = false
  }
}

function remove() {
  showDeleteModal.value = true
}

async function onConfirmDelete(reason) {
  deleting.value = true
  try {
    await deletePlan(localPlan.value.id)
    showDeleteModal.value = false
    emit('deleted')
  } catch (e) {
    alert('删除失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    deleting.value = false
  }
}

async function exportIcs() {
  try {
    await downloadPlanIcs(localPlan.value.id, `${localPlan.value.title || localPlan.value.exam_name}_日历`)
  } catch (e) {
    alert('日历导出失败：' + e.message)
  }
}

async function exportMd() {
  try {
    await downloadPlanMd(localPlan.value.id, `${localPlan.value.title || localPlan.value.exam_name}_规划`)
  } catch (e) {
    alert('导出 Markdown 失败：' + e.message)
  }
}

async function copyMarkdownText() {
  const text = localPlan.value.generated_plan || ''
  try {
    await navigator.clipboard.writeText(text)
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 2000)
  } catch (e) {
    alert('复制到剪贴板失败，请手动导出 .md 文件')
  }
}

function printPlan() {
  window.print()
}

function startTaskTimer(taskName) {
  showTimer.value = true
  resetTimer(25)
  toggleTimer()
}

function toggleTimer() {
  if (timerRunning.value) {
    clearInterval(timerInterval)
    timerRunning.value = false
  } else {
    timerRunning.value = true
    timerInterval = setInterval(() => {
      if (timerSeconds.value > 0) {
        timerSeconds.value--
      } else {
        clearInterval(timerInterval)
        timerRunning.value = false
        alert('🔔 番茄专注时间结束！请休息 5 分钟后继续下一轮复习。')
      }
    }, 1000)
  }
}

function resetTimer(mins = 25) {
  clearInterval(timerInterval)
  timerRunning.value = false
  timerSeconds.value = mins * 60
}

const timerDisplay = computed(() => {
  const m = Math.floor(timerSeconds.value / 60).toString().padStart(2, '0')
  const s = (timerSeconds.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

const renderedMarkdown = computed(() => (localPlan.value ? md.render(localPlan.value.generated_plan || '') : ''))
</script>

<template>
  <div class="space-y-6 print-area">
    <!-- 方案顶栏粗野卡片 -->
    <div class="bg-white border-[3px] border-black p-6 shadow-[6px_6px_0px_0px_#000] relative">
      <div class="graffiti-tape graffiti-tape-lime">
        MASTER PLAN BOARD
      </div>

      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-1">
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <span class="neo-badge bg-[#FFE600] text-black">
              EXAM SCHEDULE
            </span>
            <h2 class="text-xl md:text-2xl font-black font-neo-title text-black">
              {{ localPlan.title || localPlan.exam_name }}
            </h2>
          </div>
          <p class="text-xs font-bold text-neutral-600 mt-2 flex items-center gap-3 flex-wrap">
            <span>🎯 目标：<strong class="text-black underline">{{ localPlan.target_info || localPlan.exam_name }}</strong></span>
            <span>·</span>
            <span>⏱️ 每日可用：<strong class="bg-[#CCFF00] text-black px-1 border border-black">{{ localPlan.daily_hours }}h</strong></span>
            <span>·</span>
            <span>📅 创建：{{ localPlan.created_at ? localPlan.created_at.slice(0, 10) : '' }}</span>
          </p>
        </div>

        <!-- 总体完成进度指标 -->
        <div class="flex items-center gap-4 bg-[#FAF7F2] border-2 border-black p-3 shadow-[3px_3px_0px_0px_#000] shrink-0">
          <div class="text-right">
            <div class="text-[11px] font-black uppercase text-neutral-500">总打卡进度</div>
            <div class="text-xl font-black text-black font-mono">
              {{ totalStats.pct }}%
              <span class="text-xs font-bold text-neutral-400">({{ totalStats.done }}/{{ totalStats.total }})</span>
            </div>
          </div>
          <div class="w-12 h-12 bg-[#FFE600] border-2 border-black flex items-center justify-center text-black font-black text-xs shadow-[2px_2px_0px_0px_#000]">
            {{ totalStats.pct }}%
          </div>
        </div>
      </div>

      <!-- 快速工具与导出操作栏 -->
      <div class="mt-5 pt-4 border-t-2 border-black flex flex-wrap items-center justify-between gap-3 no-print">
        <div class="flex flex-wrap items-center gap-2">
          <!-- 导出手机日历 (.ics) -->
          <button
            @click="exportIcs"
            class="neo-btn bg-[#FFE600] text-black hover:bg-[#FFF066] text-xs px-3.5 py-1.5 shadow-[2px_2px_0px_0px_#000]"
            title="导出为标准日历文件，支持一键导入 iPhone/Android/Mac/Outlook 日历"
          >
            <span>📅 导出手机日历 (.ics)</span>
          </button>

          <!-- 复制 Markdown -->
          <button
            @click="copyMarkdownText"
            class="neo-btn bg-white hover:bg-neutral-100 text-black text-xs px-3 py-1.5 shadow-[2px_2px_0px_0px_#000]"
          >
            <span>{{ copySuccess ? '✓ 已复制全文' : '📋 复制 Markdown' }}</span>
          </button>

          <!-- 导出 .md 文件 -->
          <button
            @click="exportMd"
            class="neo-btn bg-white hover:bg-neutral-100 text-black text-xs px-3 py-1.5 shadow-[2px_2px_0px_0px_#000]"
          >
            ⬇️ 导出 .md
          </button>

          <!-- 打印 / PDF -->
          <button
            @click="printPlan"
            class="neo-btn bg-white hover:bg-neutral-100 text-black text-xs px-3 py-1.5 shadow-[2px_2px_0px_0px_#000]"
          >
            🖨️ 打印 / PDF
          </button>

          <!-- 专注番茄钟触发 -->
          <button
            @click="showTimer = !showTimer"
            class="neo-btn bg-[#CCFF00] hover:bg-[#B8FF00] text-black text-xs px-3 py-1.5 shadow-[2px_2px_0px_0px_#000]"
          >
            <span>⏱️ 专注时钟</span>
            <span v-if="timerRunning" class="w-2.5 h-2.5 rounded-full bg-[#FF3399] border border-black animate-ping"></span>
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="showFeedbackDrawer = !showFeedbackDrawer"
            class="neo-btn bg-[#00F0FF] hover:bg-[#80F8FF] text-black text-xs px-3 py-1.5 shadow-[2px_2px_0px_0px_#000]"
          >
            ✍️ 反馈微调排期
          </button>
          <button
            @click="remove"
            class="neo-btn bg-[#FF3399] hover:bg-[#F43F5E] text-white text-xs px-3 py-1.5 shadow-[2px_2px_0px_0px_#000]"
          >
            删除方案
          </button>
        </div>
      </div>

      <!-- 悬浮番茄钟组件 -->
      <div v-if="showTimer" class="mt-5 p-4 bg-black text-white border-2 border-black flex items-center justify-between flex-wrap gap-3 shadow-[4px_4px_0px_0px_#FFE600]">
        <div class="flex items-center gap-3">
          <span class="text-3xl">⏳</span>
          <div>
            <div class="text-xs text-[#FFE600] font-black uppercase font-neo-title">POMODORO FOCUS TIMER</div>
            <div class="text-3xl font-black font-mono tracking-widest text-white">{{ timerDisplay }}</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="toggleTimer"
            :class="[
              'neo-btn px-4 py-2 text-xs font-black shadow-[2px_2px_0px_0px_#fff]',
              timerRunning ? 'bg-[#FF3399] text-white' : 'bg-[#CCFF00] text-black',
            ]"
          >
            {{ timerRunning ? '暂停计时' : '开始专注' }}
          </button>
          <button @click="resetTimer(25)" class="neo-btn bg-neutral-800 text-white px-3 py-2 text-xs font-black border-white shadow-[2px_2px_0px_0px_#fff]">
            25m
          </button>
          <button @click="resetTimer(45)" class="neo-btn bg-neutral-800 text-white px-3 py-2 text-xs font-black border-white shadow-[2px_2px_0px_0px_#fff]">
            45m
          </button>
        </div>
      </div>

      <!-- 微调反馈抽屉面板 -->
      <div v-if="showFeedbackDrawer" class="mt-5 p-5 bg-[#FFFDE6] border-2 border-black shadow-[4px_4px_0px_0px_#000]">
        <div class="flex items-center justify-between mb-2">
          <label class="text-xs font-black text-black">
            ✍️ 告诉规划师你的调整要求（如："在职加班，周中只学2小时，周末补齐" / "重点突击行测数量关系"）：
          </label>
          <button @click="showFeedbackDrawer = false" class="neo-badge bg-black text-white cursor-pointer">✕ 收起</button>
        </div>
        <textarea
          v-model="feedback"
          rows="2"
          placeholder="输入您的微调诉求，系统将重新平衡任务排期…"
          class="neo-input text-xs"
        ></textarea>
        <div class="mt-3 flex items-center justify-between">
          <span class="text-[11px] font-bold text-neutral-600">重生成将保留您的既有目标，并自适应重排 12 周作息。</span>
          <button
            @click="regenerate"
            :disabled="regen"
            class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black px-5 py-2 text-xs font-black shadow-[3px_3px_0px_0px_#000]"
          >
            {{ regen ? 'AI 正在重构排期…' : '应用意见并重生成 ➔' }}
          </button>
        </div>
      </div>

      <div v-if="msg" class="mt-3 text-xs font-black text-black bg-[#CCFF00] border-2 border-black p-3 shadow-[2px_2px_0px_0px_#000]">
        {{ msg }}
      </div>
      <div v-if="error" class="mt-3 text-xs font-black text-white bg-[#FF3399] border-2 border-black p-3 shadow-[2px_2px_0px_0px_#000]">
        {{ error }}
      </div>
    </div>

    <!-- 视图切换选项卡 -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 no-print">
      <div class="flex flex-wrap gap-2 text-xs font-black">
        <button
          @click="activeView = 'week'"
          :class="['neo-btn px-4 py-2 text-xs', activeView === 'week' ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]' : 'bg-white text-black hover:bg-[#FFFDE6]']"
        >
          🌟 ⏱️ 24H 周作息
        </button>
        <button
          @click="activeView = 'timeline'"
          :class="['neo-btn px-4 py-2 text-xs', activeView === 'timeline' ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]' : 'bg-white text-black hover:bg-[#FFFDE6]']"
        >
          📊 甘特时间线
        </button>
        <button
          @click="activeView = 'list'"
          :class="['neo-btn px-4 py-2 text-xs', activeView === 'list' ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]' : 'bg-white text-black hover:bg-[#FFFDE6]']"
        >
          ✅ 任务打卡清单
        </button>
        <button
          @click="activeView = 'md'"
          :class="['neo-btn px-4 py-2 text-xs', activeView === 'md' ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]' : 'bg-white text-black hover:bg-[#FFFDE6]']"
        >
          📜 规划大纲 (Markdown)
        </button>
        <button @click="showScheduleEditor = true" 
                class="neo-btn bg-[#00F0FF] hover:bg-[#80F8FF] text-black px-3.5 py-2 text-xs">
          ✏️ 编辑日程
        </button>
      </div>

      <!-- 目标轨道筛选器 -->
      <div v-if="isFused && (fused?.tracks || []).length > 1" class="flex items-center gap-1.5 text-xs font-black">
        <span class="text-neutral-500 uppercase">轨道过滤：</span>
        <button
          @click="selectedTrackFilter = 'all'"
          :class="[
            'neo-badge cursor-pointer',
            selectedTrackFilter === 'all' ? 'bg-black text-[#FFE600]' : 'bg-white text-black',
          ]"
        >
          全部
        </button>
        <button
          v-for="t in fused.tracks"
          :key="t.exam_name"
          @click="selectedTrackFilter = t.exam_name"
          :class="[
            'neo-badge cursor-pointer',
            selectedTrackFilter === t.exam_name ? 'bg-[#FFE600] text-black' : 'bg-white text-black',
          ]"
        >
          {{ t.exam_name }}
        </button>
      </div>
    </div>

    <!-- 视图 1：时间线甘特图 (Timeline) -->
    <div v-if="activeView === 'timeline'" class="space-y-4">
      <div v-if="isFused" class="bg-white border-[3px] border-black p-6 shadow-[6px_6px_0px_0px_#000] overflow-x-auto">
        <div class="min-w-[780px]">
          <!-- 周头部标尺 -->
          <div class="grid grid-cols-12 gap-1.5 mb-4 text-center border-b-2 border-black pb-3">
            <div
              v-for="w in weekCols"
              :key="w"
              class="text-[11px] font-black bg-[#FFE600] text-black py-1.5 border border-black shadow-[1px_1px_0px_0px_#000]"
            >
              W{{ w }}
            </div>
          </div>

          <!-- 各 Track 时间线 -->
          <div class="space-y-5">
            <div
              v-for="t in fused.tracks"
              :key="t.exam_name"
              v-show="selectedTrackFilter === 'all' || selectedTrackFilter === t.exam_name"
              class="border-2 border-black p-4 bg-[#FAF7F2] shadow-[3px_3px_0px_0px_#000]"
            >
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                  <span class="w-3.5 h-3.5 border border-black" :style="{ backgroundColor: t._color }"></span>
                  <span class="font-black text-base font-neo-title text-black">{{ t.exam_name }}</span>
                  <span class="text-xs text-neutral-500 font-bold truncate max-w-xs">{{ t.key_dates }}</span>
                </div>
                <span class="neo-badge bg-black text-[#FFE600] text-xs">
                  {{ trackProgress[t.exam_name]?.done }}/{{ trackProgress[t.exam_name]?.total }} 任务
                </span>
              </div>

              <!-- 任务按周网格分布 -->
              <div class="grid grid-cols-12 gap-1.5">
                <div
                  v-for="w in weekCols"
                  :key="w"
                  class="min-h-[55px] bg-white border border-black p-1 flex flex-col gap-1 text-[10px]"
                >
                  <template v-for="task in (t.tasks || []).filter((k) => Number(k.week) === w)" :key="task._id">
                    <div
                      @click="toggle(task._id)"
                      :class="[
                        'p-1 border border-black text-left cursor-pointer transition select-none font-bold',
                        isChecked(task._id) ? 'bg-neutral-200 text-neutral-400 line-through' : 'bg-[#FFFDE6] text-black hover:bg-[#FFE600] shadow-[1px_1px_0px_0px_#000]',
                      ]"
                      :title="`${task.title}（${task.weekday} ${task.time_block}，${task.duration_hours}h）`"
                    >
                      <div class="truncate leading-tight font-black">{{ task.title }}</div>
                      <div class="text-[9px] text-neutral-500 mt-0.5">{{ task.weekday }} {{ task.duration_hours }}h</div>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-5 pt-3 border-t-2 border-black flex items-center justify-between text-xs font-bold text-neutral-500">
            <span>💡 提示：点击任务卡片可直接打卡标记完成</span>
            <button @click="saveProgress" :disabled="saving" class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black text-xs px-5 py-2 font-black shadow-[3px_3px_0px_0px_#000]">
              {{ saving ? '保存中…' : '保存打卡状态' }}
            </button>
          </div>
        </div>
      </div>
      <div v-else class="bg-white border-[3px] border-black p-8 text-center text-xs font-bold text-neutral-500 shadow-[4px_4px_0px_0px_#000]">
        该计划采用经典文本大纲结构，请切换至「规划大纲」选项卡查看完整备考方案。
      </div>
    </div>

    <!-- 视图 2：24H 周视图 + 伴学 AI 导师 (Week Schedule & AI Coach) -->
    <div v-else-if="activeView === 'week'" class="space-y-4">
      <div v-if="isFused" class="flex flex-col lg:flex-row gap-5 items-start">
        <!-- 左侧 / 中部：24H 周视图 -->
        <div class="flex-1 w-full space-y-4 min-w-0">
          <!-- 醒目的 AI 智能调期快速交互横幅 -->
          <div class="bg-[#00F0FF] text-black border-[3px] border-black p-4 shadow-[4px_4px_0px_0px_#000] flex flex-wrap items-center justify-between gap-3 relative">
            <div class="flex items-center gap-3">
              <span class="text-2xl font-black">⚡</span>
              <div>
                <h4 class="text-sm font-black font-neo-title uppercase flex items-center gap-2">
                  <span>AI 智能调期助手</span>
                  <span class="neo-badge bg-black text-[#00F0FF] text-[10px]">DYNAMIC REPLAN</span>
                </h4>
                <p class="text-xs font-bold mt-0.5">
                  想加健身、留散步时间或调整强度？点击右侧或在导师面板提出即可自动重构日程！
                </p>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <button
                @click="coachCollapsed = false"
                class="neo-btn bg-black text-[#00F0FF] hover:bg-neutral-900 text-xs px-4 py-2 font-black shadow-[2px_2px_0px_0px_#fff]"
              >
                <span>🤖 打开 AI 调期对话框</span>
              </button>
            </div>
          </div>

          <!-- 周次切换 Tab 栏 (带真实公历日期范围) -->
          <div class="bg-white border-[3px] border-black p-4 shadow-[4px_4px_0px_0px_#000] flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-2 overflow-x-auto max-w-full pb-1">
              <span class="text-xs font-black uppercase mr-1 shrink-0">选择周次:</span>
              <button
                v-for="w in weekCols"
                :key="w"
                @click="selectedWeekFilter = w"
                :class="[
                  'neo-btn px-3.5 py-1.5 text-xs font-black shrink-0 flex flex-col items-center',
                  selectedWeekFilter === w
                    ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]'
                    : 'bg-white text-black hover:bg-[#FFFDE6]'
                ]"
              >
                <span>第 {{ w }} 周</span>
                <span class="text-[9px] font-mono opacity-80">{{ getWeekDateRange(w) }}</span>
              </button>
              <button
                @click="selectedWeekFilter = 'all'"
                :class="[
                  'neo-btn px-3.5 py-1.5 text-xs font-black shrink-0 ml-1',
                  selectedWeekFilter === 'all'
                    ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]'
                    : 'bg-white text-black hover:bg-[#FFFDE6]'
                ]"
              >
                全部周总览
              </button>
            </div>

            <div class="flex items-center gap-2">
              <button
                @click="coachCollapsed = !coachCollapsed"
                class="neo-btn bg-[#CCFF00] hover:bg-[#B8FF00] text-black text-xs px-3.5 py-2 font-black shadow-[2px_2px_0px_0px_#000]"
              >
                <span>🤖 {{ coachCollapsed ? '展开 AI 导师' : '收起 AI 导师' }}</span>
              </button>
            </div>
          </div>

          <!-- 24h 时间轴粗野周视图 -->
          <AppleCalendarWeekView
            :fused="fused"
            :selected-week="selectedWeekFilter"
            :selected-track="selectedTrackFilter"
            :checked-map="checked"
            :plan-created-at="localPlan.created_at"
            @select-task="onSelectTask"
            @toggle-check="toggle"
          />

          <div class="flex items-center justify-between text-xs font-bold text-neutral-600 px-2 pt-1">
            <span>📌 单击卡片可查看详细任务指标、番茄钟打卡与 AI 导师出题辅导</span>
            <button @click="saveProgress" :disabled="saving" class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black text-xs px-5 py-2 font-black shadow-[3px_3px_0px_0px_#000]">
              {{ saving ? '保存中…' : '💾 保存打卡状态' }}
            </button>
          </div>
        </div>

        <!-- 右侧：常驻 / 可收折伴学 AI 导师抽屉 -->
        <div v-show="!coachCollapsed" class="w-full lg:w-[390px] h-[660px] shrink-0 lg:sticky lg:top-4">
          <AICoachDrawer
            :plan-id="localPlan.id"
            :active-task="focusedCoachTask"
            :active-track-name="focusedCoachTrackName"
            v-model:collapsed="coachCollapsed"
            @clear-task="focusedCoachTask = null"
            @schedule-updated="onScheduleUpdatedFromCoach"
          />
        </div>
      </div>
      <div v-else class="bg-white border-[3px] border-black p-8 text-center text-xs font-bold text-neutral-500 shadow-[4px_4px_0px_0px_#000]">
        该计划采用经典文本大纲结构，请切换至「规划大纲」选项卡查看完整备考方案。
      </div>
    </div>

    <!-- 视图 3：任务打卡清单 (Checklist - 按周分页展示) -->
    <div v-else-if="activeView === 'list'" class="bg-white border-[3px] border-black p-6 shadow-[6px_6px_0px_0px_#000] space-y-5">
      <div v-if="isFused">
        <!-- 周次切换 Tab 栏 -->
        <div class="flex flex-wrap items-center justify-between gap-3 mb-5 pb-3 border-b-2 border-black">
          <div class="flex items-center gap-2 overflow-x-auto max-w-full pb-1">
            <span class="text-xs font-black uppercase mr-1 shrink-0">选择周次:</span>
            <button
              v-for="w in weekCols"
              :key="w"
              @click="selectedWeekFilter = w"
              :class="[
                'neo-btn px-3.5 py-1.5 text-xs font-black shrink-0 flex flex-col items-center',
                selectedWeekFilter === w
                  ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]'
                  : 'bg-white text-black hover:bg-[#FFFDE6]'
              ]"
            >
              <span>第 {{ w }} 周</span>
              <span class="text-[9px] font-mono opacity-80">{{ getWeekDateRange(w) }}</span>
            </button>
            <button
              @click="selectedWeekFilter = 'all'"
              :class="[
                'neo-btn px-3.5 py-1.5 text-xs font-black shrink-0 ml-1',
                selectedWeekFilter === 'all'
                  ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]'
                  : 'bg-white text-black hover:bg-[#FFFDE6]'
              ]"
            >
              全部周总览
            </button>
          </div>
        </div>

        <div v-for="t in fused.tracks" :key="t.exam_name" v-show="selectedTrackFilter === 'all' || selectedTrackFilter === t.exam_name" class="space-y-3 mb-6">
          <div class="flex items-center gap-2 border-b-2 border-black pb-2">
            <span class="w-4 h-4 border border-black" :style="{ backgroundColor: t._color }"></span>
            <h4 class="font-black font-neo-title text-base text-black">
              {{ t.exam_name }} · {{ selectedWeekFilter === 'all' ? '全部任务清单' : `第 ${selectedWeekFilter} 周任务清单` }}
            </h4>
            <span class="text-xs text-neutral-500 font-bold">（{{ t.key_dates }}）</span>
          </div>

          <div class="grid sm:grid-cols-2 gap-3">
            <div
              v-for="task in (t.tasks || []).filter((k) => selectedWeekFilter === 'all' || Number(k.week) === Number(selectedWeekFilter))"
              :key="task._id"
              @click="toggle(task._id)"
              :class="[
                'p-3.5 border-2 border-black flex items-start gap-3 cursor-pointer transition-all shadow-[3px_3px_0px_0px_#000] hover:shadow-[4px_4px_0px_0px_#000]',
                isChecked(task._id) ? 'bg-neutral-200 text-neutral-400' : 'bg-white text-black',
              ]"
            >
              <input
                type="checkbox"
                :checked="isChecked(task._id)"
                class="mt-1 w-4 h-4 text-black rounded-none cursor-pointer accent-black"
                @click.stop="toggle(task._id)"
              />
              <div class="flex-1 text-xs">
                <div :class="['font-black', isChecked(task._id) ? 'line-through text-neutral-400' : 'text-black']">
                  第{{ task.week }}周 · {{ task.weekday }} {{ task.time_block }} ｜ {{ task.title }}
                </div>
                <div class="text-neutral-600 mt-1 font-bold">🎯 指标：{{ task.metric }}</div>
                <div class="text-[10px] font-mono text-neutral-500 mt-0.5">时长：{{ task.duration_hours }}h · 属性：{{ task.type }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="pt-4 border-t-2 border-black flex justify-end">
          <button @click="saveProgress" :disabled="saving" class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black px-6 py-2.5 text-xs font-black shadow-[3px_3px_0px_0px_#000]">
            {{ saving ? '保存中…' : '保存打卡状态' }}
          </button>
        </div>
      </div>
      <div v-else class="text-center py-8 text-xs font-bold text-neutral-400">
        该计划无独立任务清单，请切换至「规划大纲」查看。
      </div>
    </div>

    <!-- 视图 4：规划大纲 (Markdown) -->
    <div v-else-if="activeView === 'md'" class="bg-white border-[3px] border-black p-6 md:p-8 shadow-[6px_6px_0px_0px_#000]">
      <div class="flex items-center justify-between mb-4 pb-3 border-b-2 border-black no-print">
        <span class="text-xs font-black uppercase">📜 完整备考规划方案全文</span>
        <button @click="copyMarkdownText" class="neo-badge bg-[#FFE600] text-black cursor-pointer">
          {{ copySuccess ? '✓ 已复制' : '复制全文' }}
        </button>
      </div>
      <div class="md-body" v-html="renderedMarkdown"></div>
    </div>

    <!-- 日程编辑器 -->
    <div v-if="showScheduleEditor" class="fixed inset-0 z-50 bg-black/60 flex items-start justify-center pt-8 overflow-y-auto">
      <div class="bg-white border-[3px] border-black shadow-[8px_8px_0px_0px_#000] w-full max-w-5xl mx-4 mb-8">
        <ScheduleEditor 
          :plan="localPlan" 
          :plan-id="localPlan.id" 
          @saved="onScheduleSaved"
          @close="showScheduleEditor = false" 
        />
      </div>
    </div>

    <!-- 任务详情弹窗 -->
    <TaskDetailModal
      :show="activeTaskModal.show"
      :task="activeTaskModal.task || {}"
      :track-name="activeTaskModal.trackName"
      :color="activeTaskModal.color"
      :is-done="activeTaskModal.isDone"
      @close="activeTaskModal.show = false"
      @toggle-done="onToggleDoneFromModal"
      @start-pomodoro="onStartPomodoro"
      @ask-coach="onAskCoachFromModal"
    />

    <!-- 温情挽留删除确认弹窗 -->
    <DeleteConfirmModal
      :show="showDeleteModal"
      :plan="localPlan"
      :deleting="deleting"
      @close="showDeleteModal = false"
      @confirm="onConfirmDelete"
    />
  </div>
</template>
