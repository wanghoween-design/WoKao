<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  task: { type: Object, default: () => ({}) },
  trackName: { type: String, default: '' },
  color: { type: String, default: '#FFE600' },
  isDone: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'toggle-done', 'start-pomodoro', 'ask-coach'])

const NEO_THEMES = {
  yellow: { bg: 'bg-[#FFE600]', text: 'text-black', tape: 'graffiti-tape-lime', badge: 'bg-black text-[#FFE600]' },
  lime: { bg: 'bg-[#CCFF00]', text: 'text-black', tape: 'graffiti-tape-pink', badge: 'bg-black text-[#CCFF00]' },
  cyan: { bg: 'bg-[#00F0FF]', text: 'text-black', tape: 'graffiti-tape-lime', badge: 'bg-black text-[#00F0FF]' },
  purple: { bg: 'bg-[#B388FF]', text: 'text-black', tape: 'graffiti-tape-pink', badge: 'bg-black text-[#B388FF]' },
  pink: { bg: 'bg-[#FF3399]', text: 'text-white', tape: 'graffiti-tape-cyan', badge: 'bg-black text-[#FF3399]' },
}

const theme = computed(() => {
  const hash = Math.abs(String(props.trackName || props.task.title || '').split('').reduce((a, b) => ((a << 5) - a) + b.charCodeAt(0), 0))
  const keys = ['yellow', 'lime', 'cyan', 'purple', 'pink']
  return NEO_THEMES[keys[hash % keys.length]]
})
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
    <!-- 粗野主义任务弹窗主体 -->
    <div 
      class="relative w-full max-w-lg border-[3px] border-black shadow-[8px_8px_0px_0px_#000] p-6 sm:p-8 transform transition-all rotate-[-0.5deg]"
      :class="[theme.bg, theme.text]"
    >
      <!-- 顶部涂鸦胶带标签 -->
      <div :class="['graffiti-tape', theme.tape]">
        ★ TASK FOCUS CARD ★
      </div>

      <!-- 右上角关闭按钮 -->
      <button 
        @click="emit('close')" 
        class="absolute top-4 right-4 neo-badge bg-black text-white cursor-pointer"
      >
        ✕
      </button>

      <!-- 顶部便签标签 -->
      <div class="flex items-center gap-2 mb-3 pt-2">
        <span :class="['neo-badge text-[10px]', theme.badge]">
          🎯 {{ trackName || task.trackName || '备考目标' }}
        </span>
        <span class="text-xs font-black uppercase opacity-90">
          第 {{ task.week || 1 }} 周 · {{ task.weekday || '周一' }}
        </span>
        <span v-if="isDone" class="ml-auto mr-7 neo-badge bg-black text-[#CCFF00] text-[10px]">
          ✓ 已完成
        </span>
      </div>

      <!-- 任务标题 -->
      <h2 class="text-xl font-black font-neo-title leading-snug mb-3">
        {{ task.title || '未命名任务' }}
      </h2>

      <!-- 时间与基础属性条 -->
      <div class="grid grid-cols-2 gap-2 p-3 bg-white text-black border-2 border-black text-xs mb-4 font-bold shadow-[2px_2px_0px_0px_#000]">
        <div>
          <span class="text-neutral-500">⏰ 安排时段：</span>
          <span class="font-mono font-black">{{ task.time_block || '08:30-10:00' }}</span>
        </div>
        <div>
          <span class="text-neutral-500">⏳ 预估用时：</span>
          <span class="font-black">{{ task.duration_hours || 1 }} 小时</span>
        </div>
        <div>
          <span class="text-neutral-500">🏷️ 任务类型：</span>
          <span class="font-black">{{ task.type || '学习' }}</span>
        </div>
        <div>
          <span class="text-neutral-500">📋 进度状态：</span>
          <span :class="isDone ? 'text-emerald-700 font-black' : 'text-neutral-900 font-black'">
            {{ isDone ? '已打卡完成' : '待完成' }}
          </span>
        </div>
      </div>

      <!-- 量化验收指标 (Metric) -->
      <div class="mb-5 p-3.5 bg-white text-black border-2 border-black shadow-[2px_2px_0px_0px_#000]">
        <h4 class="text-xs font-black uppercase mb-1 flex items-center gap-1.5 font-neo-title">
          <span>🎯</span> 量化验收指标与备考要求
        </h4>
        <p class="text-xs leading-relaxed font-bold">
          {{ task.metric || '按质按量完成当日复习任务与笔记梳理。' }}
        </p>
      </div>

      <!-- 底部动作条 -->
      <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t-2 border-black">
        <!-- 打卡状态切换 -->
        <button 
          @click="emit('toggle-done')"
          :class="[
            'neo-btn px-4 py-2 text-xs font-black border-2 shadow-[2px_2px_0px_0px_#000]',
            isDone ? 'bg-neutral-200 text-black' : 'bg-black text-[#CCFF00]'
          ]"
        >
          <span>{{ isDone ? '↩ 设为待办' : '✓ 标记打卡完成' }}</span>
        </button>

        <!-- 专属 AI 伴学提问与番茄钟 -->
        <div class="flex items-center gap-2">
          <button 
            @click="emit('start-pomodoro', task)"
            class="neo-btn bg-white hover:bg-neutral-100 text-black px-3.5 py-2 text-xs font-black border-2 shadow-[2px_2px_0px_0px_#000]"
          >
            <span>⏱️ 番茄钟 (25m)</span>
          </button>

          <button 
            @click="emit('ask-coach', task)"
            class="neo-btn bg-black text-[#FFE600] hover:bg-neutral-800 px-4 py-2 text-xs font-black border-2 shadow-[2px_2px_0px_0px_#000]"
          >
            <span>🤖 让 AI 导师辅导</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
