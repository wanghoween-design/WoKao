<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  plan: { type: Object, default: () => ({}) },
  deleting: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'confirm'])

const selectedReason = ref('已有其他备考计划，重新规划')
const showReasonDropdown = ref(false)

const REASONS = [
  '📝 已有其他备考计划，重新规划',
  '⏳ 工作/学业变动导致时间冲突，暂缓备考',
  '🎯 目标院校/岗位发生调整',
  '🧪 测试生成方案 / 清理不再需要',
  '💨 节奏太紧，需要重新制定更轻松的计划',
]

// 提取方案中的所有目标名称
const targetNames = computed(() => {
  if (!props.plan) return []
  if (props.plan.exam_name) {
    return props.plan.exam_name.split('+').map(s => s.trim())
  }
  return [props.plan.title || '当前考试目标']
})

// 估算倒计时天数
const daysLeftEstimate = computed(() => {
  // 基础估算 90~120 天
  return 98
})
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
    <div class="bg-white border-[3px] border-black shadow-[8px_8px_0px_0px_#000] w-full max-w-lg overflow-hidden relative rotate-[-0.3deg]">
      <!-- 顶部涂鸦胶带 -->
      <div class="graffiti-tape graffiti-tape-pink">
        ★ RETENTION & CARE ★
      </div>

      <!-- 弹窗顶栏 -->
      <div class="bg-black text-white px-6 py-4 flex items-center justify-between border-b-[3px] border-black">
        <div class="flex items-center gap-2.5">
          <span class="text-2xl font-black">🚨</span>
          <div>
            <h3 class="text-base font-black font-neo-title uppercase text-[#FFE600]">确定要放弃当前的备考计划吗？</h3>
            <p class="text-xs font-bold text-neutral-400">每一份坚持都在闪闪发光 · 请慎重决定</p>
          </div>
        </div>
        <button @click="emit('close')" class="neo-badge bg-neutral-800 text-white cursor-pointer">✕</button>
      </div>

      <!-- 内容主体 -->
      <div class="p-6 space-y-5 bg-[#FAF7F2]">
        <!-- 温情挽留与目标卡片 -->
        <div class="bg-[#FFFDE6] border-2 border-black p-4 shadow-[4px_4px_0px_0px_#000]">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-2xl">⏳</span>
            <div class="font-black text-sm font-neo-title text-black">
              距离目标考期仅剩约 <span class="bg-[#FFE600] px-2 py-0.5 border border-black font-mono text-base">{{ daysLeftEstimate }}</span> 天！
            </div>
          </div>

          <div class="text-xs text-black font-bold leading-relaxed">
            你已经为这份方案规划了：
            <span class="inline-flex gap-1.5 flex-wrap my-1.5">
              <span v-for="t in targetNames" :key="t" class="neo-badge bg-black text-[#CCFF00] text-[11px]">
                🎯 {{ t }}
              </span>
            </span>
          </div>

          <p class="text-xs font-bold text-neutral-700 mt-2 bg-white p-2.5 border border-black leading-relaxed">
            💬 <strong>AI 导师悄悄话：</strong>“备考的过程就像在黑夜中默默扎根，万物皆有回响。每一个早起的晨读、每一道啃下的真题都不会白费，真的不再努力尝试一下吗？💪”
          </p>
        </div>

        <!-- 放弃原因选择区 -->
        <div class="bg-white border-2 border-black p-3.5 shadow-[2px_2px_0px_0px_#000]">
          <label class="block text-xs font-black uppercase text-neutral-600 mb-1.5">
            若确实需要删除，请选择原因（帮助我们优化生成策略）：
          </label>
          <select v-model="selectedReason" class="neo-input text-xs font-bold cursor-pointer">
            <option v-for="r in REASONS" :key="r" :value="r">
              {{ r }}
            </option>
          </select>
        </div>

        <!-- 操作按钮组 -->
        <div class="pt-3 border-t-2 border-black space-y-2.5">
          <!-- 主操作：强烈挽留，继续努力 -->
          <button
            @click="emit('close')"
            class="neo-btn bg-[#CCFF00] hover:bg-[#B8FF00] text-black w-full py-3 text-xs font-black border-[3px] shadow-[4px_4px_0px_0px_#000] flex items-center justify-center gap-2"
          >
            <span class="text-base">💪</span>
            <span>我想再尝试一下，继续坚持！</span>
          </button>

          <!-- 次操作：确定删除 -->
          <button
            @click="emit('confirm', selectedReason)"
            :disabled="deleting"
            class="neo-btn bg-white hover:bg-[#FF3399] hover:text-white text-neutral-700 w-full py-2.5 text-xs font-black border-2 shadow-[2px_2px_0px_0px_#000] transition-colors flex items-center justify-center gap-1.5"
          >
            <span v-if="deleting" class="animate-spin">⏳</span>
            <span>{{ deleting ? '删除中…' : '💔 确定放弃并删除此计划' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
