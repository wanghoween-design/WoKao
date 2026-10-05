<script setup>
import { ref, watch, nextTick } from 'vue'
import md from '../md.js'
import { chatWithCoach, updatePlan } from '../api/client.js'

const props = defineProps({
  planId: { type: [Number, String], default: null },
  activeTask: { type: Object, default: null },
  activeTrackName: { type: String, default: '' },
  collapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['update:collapsed', 'clear-task', 'schedule-updated'])

const messages = ref([
  {
    role: 'assistant',
    content: '同学你好！我是你的 **AI 伴学与智能调期导师**。\n\n你可以随时向我提问考点疑难，或者直接对日程提出任何个性化调整（例如：*“周三下午4点插入1小时健身”*、*“每天晚上留出半小时散步”*、*“把周日设为休息日”*），我将实时为你动态重排并自适应更新日历！'
  }
])

const inputMsg = ref('')
const loading = ref(false)
const adjusting = ref(false)
const adjustSuccessMsg = ref('')
const chatContainer = ref(null)

const QUICK_PROMPTS = [
  { label: '🏋️ 插入健身/运动时段', prompt: '我想在每周三和周五下午 16:30-17:30 插入 1 小时健身运动，请帮我调整排期。' },
  { label: '☕ 晚饭后留30m散步', prompt: '请帮我在每天 18:30-19:00 留出 30 分钟散步放松时间，避免学习过度疲劳。' },
  { label: '🏖️ 周日设为完全休息日', prompt: '我希望把周日设定为完全休息日（不安排新任务），将周日内容平摊到周一至周六。' },
  { label: '🔄 均衡周一到周五任务', prompt: '请帮我将各科目的备考任务均匀分散在周一到周五，每天安排 2~4 小时，不要只堆在周一。' },
  { label: '🎯 拆解当前任务考点', prompt: '请帮我深入拆解当前专注任务的核心考点与复习抓手，列出高频重难点。' },
  { label: '🧪 出 3 道真题速测我', prompt: '请针对当前任务的知识点，出 3 道考点速测题考考我，并附带详细解析。' },
]

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// 当用户在日历中点击任务时，自动滚动并准备好上下文
watch(() => props.activeTask, (newT) => {
  if (newT && newT.title) {
    scrollToBottom()
  }
})

// 普通伴学对话
async function send(customText = '') {
  const text = (customText || inputMsg.value).trim()
  if (!text || loading.value || adjusting.value) return

  messages.value.push({ role: 'user', content: text })
  inputMsg.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const historyPayload = messages.value.slice(-8).map(m => ({
      role: m.role,
      content: m.content
    }))

    const res = await chatWithCoach({
      message: text,
      plan_id: props.planId ? Number(props.planId) : null,
      task_context: props.activeTask ? {
        title: props.activeTask.title,
        week: props.activeTask.week,
        weekday: props.activeTask.weekday,
        time_block: props.activeTask.time_block,
        metric: props.activeTask.metric,
        trackName: props.activeTrackName || props.activeTask.trackName || ''
      } : null,
      history: historyPayload
    })

    messages.value.push({
      role: 'assistant',
      content: res.reply || '导师已收到，祝你备考顺利！'
    })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '⚠️ 导师暂时连接受阻：' + ((e.response && e.response.data && e.response.data.detail) || e.message || '请稍后重试')
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

// 直接触发 AI 智能重排日程并更新日历
async function applyScheduleAdjustment(customText = '') {
  const text = (customText || inputMsg.value).trim()
  if (!text || !props.planId || adjusting.value) return

  adjusting.value = true
  adjustSuccessMsg.value = ''
  messages.value.push({ role: 'user', content: `【申请智能重排】${text}` })
  inputMsg.value = ''
  scrollToBottom()

  try {
    const d = await updatePlan(props.planId, {
      user_feedback: text,
      regenerate: true,
    })
    adjustSuccessMsg.value = '✓ AI 已根据您的诉求完成全周期 12 周日程重排！'
    messages.value.push({
      role: 'assistant',
      content: `🎉 **日程已成功重排并更新！**\n\n已根据您的诉求（*“${text}”*）重新计算了 12 周作息排期与时间块分布，左侧日历已实时同步刷新！`
    })
    emit('schedule-updated', d.plan)
  } catch (e) {
    const err = (e.response && e.response.data && e.response.data.detail) || e.message || '调期重排失败'
    messages.value.push({
      role: 'assistant',
      content: `❌ **调期重排失败**：${err}`
    })
  } finally {
    adjusting.value = false
    scrollToBottom()
  }
}
</script>

<template>
  <div class="flex flex-col h-full bg-white border-[3px] border-black shadow-[6px_6px_0px_0px_#000] overflow-hidden select-text">
    <!-- 抽屉顶栏：粗野风格黑色标题栏 -->
    <div class="bg-black text-white px-4 py-3.5 flex items-center justify-between border-b-[3px] border-black">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-[#FFE600] text-black border-2 border-black flex items-center justify-center text-lg font-black shadow-[2px_2px_0px_0px_#fff]">
          🤖
        </div>
        <div>
          <div class="flex items-center gap-1.5">
            <h3 class="text-xs font-black font-neo-title uppercase text-[#FFE600]">AI 伴学导师</h3>
            <span class="neo-badge bg-[#CCFF00] text-black text-[9px] px-1 py-0">
              COPILOT
            </span>
          </div>
          <p class="text-[10px] font-bold text-neutral-300">实时感知任务 · 随时对话 · 智能重排</p>
        </div>
      </div>
      <button 
        @click="emit('update:collapsed', !collapsed)"
        class="neo-btn bg-neutral-800 text-[#FFE600] hover:bg-neutral-700 text-xs px-2.5 py-1 border border-neutral-600 shadow-[1px_1px_0px_0px_#fff]"
        title="收起/展开导师面板"
      >
        {{ collapsed ? '展开 ▶' : '◀ 收起' }}
      </button>
    </div>

    <!-- 当前聚焦任务便签栏 (Context Banner) -->
    <div v-if="activeTask && activeTask.title" class="p-3 bg-[#FFE600] border-b-2 border-black flex items-start justify-between gap-2 text-xs">
      <div class="flex items-start gap-2 overflow-hidden">
        <span class="text-black text-base mt-0.5 shrink-0 font-black">📌</span>
        <div class="overflow-hidden">
          <div class="text-xs font-black text-black truncate">
            当前专注：{{ activeTrackName ? `[${activeTrackName}] ` : '' }}{{ activeTask.title }}
          </div>
          <div class="text-[10px] text-black/80 font-mono font-bold">
            第 {{ activeTask.week || 1 }} 周 · {{ activeTask.weekday }} {{ activeTask.time_block }}
          </div>
        </div>
      </div>
      <button 
        @click="emit('clear-task')" 
        class="neo-badge bg-black text-[#FFE600] cursor-pointer"
        title="清除当前任务聚焦"
      >
        ✕
      </button>
    </div>

    <!-- 消息对话区 -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4 bg-[#FAF7F2]">
      <div 
        v-for="(m, idx) in messages" 
        :key="idx"
        :class="['flex gap-2.5', m.role === 'user' ? 'justify-end' : 'justify-start']"
      >
        <!-- 导师头像 -->
        <div v-if="m.role === 'assistant'" class="w-8 h-8 bg-black text-[#FFE600] border-2 border-black flex items-center justify-center text-xs font-black shadow-[2px_2px_0px_0px_#000] shrink-0 mt-0.5">
          ⚡
        </div>

        <!-- 气泡主体 -->
        <div 
          :class="[
            'max-w-[88%] border-2 border-black p-3.5 text-xs leading-relaxed shadow-[3px_3px_0px_0px_#000]',
            m.role === 'user' 
              ? 'bg-[#FFE600] text-black font-bold' 
              : 'bg-white text-black'
          ]"
        >
          <div v-if="m.role === 'assistant'" class="md-body leading-relaxed space-y-2 text-xs font-medium" v-html="md.render(m.content)"></div>
          <div v-else class="whitespace-pre-wrap font-bold">{{ m.content }}</div>
        </div>
      </div>

      <!-- 加载中与重排中状态 -->
      <div v-if="loading" class="flex items-center gap-2 text-xs font-black text-black bg-[#CCFF00] p-2 border-2 border-black shadow-[2px_2px_0px_0px_#000]">
        <span class="animate-spin text-sm">⏳</span> AI 导师正在思考并剖析考情…
      </div>
      <div v-if="adjusting" class="p-3 bg-[#00F0FF] text-black border-2 border-black text-xs font-black flex items-center gap-2 shadow-[2px_2px_0px_0px_#000]">
        <span class="animate-spin text-base">⚙️</span> 正在结合您的微调意见重排 12 周日程，请稍候…
      </div>
    </div>

    <!-- 快捷常用诉求胶囊 -->
    <div class="px-3.5 py-2.5 bg-white border-t-2 border-black">
      <div class="text-[10px] font-black text-black mb-1.5 uppercase flex items-center gap-1">
        <span>✨ 快捷智能指令 (点击即刻应用/提问)：</span>
      </div>
      <div class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
        <button
          v-for="qp in QUICK_PROMPTS"
          :key="qp.label"
          @click="applyScheduleAdjustment(qp.prompt)"
          :disabled="loading || adjusting"
          class="px-2 py-1 text-[11px] font-black bg-[#FAF7F2] hover:bg-[#FFE600] text-black border-2 border-black transition cursor-pointer shadow-[2px_2px_0px_0px_#000] disabled:opacity-50 flex items-center gap-1 active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
        >
          <span>{{ qp.label }}</span>
        </button>
      </div>
    </div>

    <!-- 底部输入区 -->
    <div class="p-3 bg-white border-t-2 border-black flex flex-col gap-2">
      <div class="flex items-center gap-2">
        <input
          v-model="inputMsg"
          @keydown.enter.prevent="send()"
          :placeholder="activeTask ? `向导师提问关于【${activeTask.title}】或提出调整…` : '输入调整诉求（如：周三加健身 / 考点提问）…'"
          class="neo-input flex-1 text-xs py-2"
        />
        <button
          @click="send()"
          :disabled="loading || adjusting || !inputMsg.trim()"
          class="neo-btn bg-black text-[#FFE600] hover:bg-neutral-800 text-xs px-3.5 py-2 font-black shadow-[2px_2px_0px_0px_#000] shrink-0"
        >
          💬 对话
        </button>
      </div>

      <!-- 醒目的 AI 一键重排按钮 -->
      <button
        @click="applyScheduleAdjustment()"
        :disabled="adjusting || loading || !inputMsg.trim()"
        class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black text-xs font-black py-2 w-full border-2 shadow-[2px_2px_0px_0px_#000]"
      >
        <span>⚡ 应用输入内容并让 AI 重排日程</span>
      </button>
    </div>
  </div>
</template>
