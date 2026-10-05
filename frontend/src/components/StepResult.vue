<script setup>
import { ref, computed, onMounted } from 'vue'
import { generateFusedPlan, getPlan } from '../api/client.js'
import FusedPlanView from './FusedPlanView.vue'

const props = defineProps({
  identity: { type: String, default: '' },
  nickname: { type: String, default: '' },
  goals: { type: Array, default: () => [] },
  goalTargets: { type: Object, default: () => ({}) },
  dailyHours: { type: Number, default: 4 },
  now: { type: Object, default: null },
  useWebSearch: { type: Boolean, default: true },
})
const emit = defineEmits(['back', 'done'])

const loading = ref(true)
const error = ref('')
const plan = ref(null) // 生成的融合计划对象
const degraded = ref(false) // LLM 内容生成失败、由兜底内容池降级产出
const progressStep = ref(1)

const todayLabel = computed(() => {
  const d = props.now
  return d ? `${d.year} 年 ${d.month} 月 ${d.day} 日` : ''
})

onMounted(async () => {
  loading.value = true
  error.value = ''
  degraded.value = false
  progressStep.value = 1

  const timer1 = setTimeout(() => { if (loading.value) progressStep.value = 2 }, 4000)
  const timer2 = setTimeout(() => { if (loading.value) progressStep.value = 3 }, 12000)

  try {
    const payload = {
      goals: props.goals.map((g) => ({
        exam_name: g.exam_name,
        target_info: props.goalTargets[g.exam_name] || '',
      })),
      daily_hours: props.dailyHours || 4,
      user_feedback: '',
      use_web_search: props.useWebSearch,
    }
    const res = await generateFusedPlan(payload)
    degraded.value = Boolean(res.degraded)
    const full = await getPlan(res.plan_id)
    plan.value = full.plan
  } catch (e) {
    error.value = (e.response && e.response.data && e.response.data.detail) || e.message || '生成失败，请检查模型 API 配置或网络'
  } finally {
    clearTimeout(timer1)
    clearTimeout(timer2)
    loading.value = false
  }
})
</script>

<template>
  <div>
    <div class="border-b-[3px] border-black pb-4 mb-5 flex items-baseline justify-between">
      <div class="flex items-center gap-2">
        <span class="neo-badge bg-[#FF3399] text-white">STEP 04</span>
        <h2 class="text-xl font-black font-neo-title text-black">
          备考方案与执行看板
        </h2>
      </div>
      <span v-if="!loading && plan" class="neo-badge bg-[#CCFF00] text-black">
        ✓ 方案编排就绪
      </span>
    </div>

    <!-- 考生档案凭证卡片 -->
    <div class="bg-black text-white border-[3px] border-black p-5 shadow-[6px_6px_0px_0px_#FFE600] mb-6">
      <div class="flex flex-wrap items-center gap-2 text-xs font-bold">
        <span class="text-neutral-400">考生档案：</span>
        <span class="neo-badge bg-[#FFE600] text-black">{{ identity }}</span>
        <span class="text-neutral-500">·</span>
        <span class="neo-badge bg-[#CCFF00] text-black">{{ nickname }}</span>
        <span class="text-neutral-500">·</span>
        <span class="text-neutral-400">基准日期：</span>
        <span class="neo-badge bg-[#00F0FF] text-black">{{ todayLabel }}</span>
        <span class="text-neutral-500">·</span>
        <span class="text-neutral-400">每日时长：</span>
        <span class="neo-badge bg-[#FF3399] text-white">{{ dailyHours }}h / 天</span>
      </div>

      <div class="flex flex-wrap items-center gap-2 text-xs mt-3 pt-2.5 border-t border-neutral-800 font-bold">
        <span class="text-neutral-400">协同多轨目标：</span>
        <span v-for="g in goals" :key="g.exam_name" class="neo-badge bg-[#FFE600] text-black">
          🎯 {{ g.exam_name }}
          <span class="opacity-70 text-[10px]">（{{ g.annual_period }}）</span>
        </span>
      </div>
    </div>

    <!-- 生成中动态阶段动画 -->
    <div v-if="loading" class="bg-white border-[3px] border-black p-10 text-center space-y-6 shadow-[6px_6px_0px_0px_#000]">
      <div class="w-16 h-16 mx-auto bg-[#FFE600] border-2 border-black text-black flex items-center justify-center text-3xl font-black animate-bounce shadow-[3px_3px_0px_0px_#000]">
        ⚡
      </div>

      <div>
        <h3 class="font-neo-title text-xl font-black text-black">
          AI 规划师正在编排多目标融合方案…
        </h3>
        <p class="text-xs font-bold text-neutral-600 mt-1 max-w-md mx-auto">
          系统正在综合国家大纲库、消解多科目冲突，并编排未来 12 周 24H 空间解耦作息表。
        </p>
      </div>

      <!-- 阶段进度列表 -->
      <div class="max-w-xs mx-auto text-left space-y-2.5 text-xs bg-[#FAF7F2] p-5 border-2 border-black shadow-[3px_3px_0px_0px_#000]">
        <div class="flex items-center gap-2" :class="progressStep >= 1 ? 'text-black font-black' : 'text-neutral-400'">
          <span>{{ progressStep > 1 ? '✅' : '⏳' }}</span>
          <span>1. 调取权威大纲与历年考期标准库</span>
        </div>
        <div class="flex items-center gap-2" :class="progressStep >= 2 ? 'text-black font-black' : 'text-neutral-400'">
          <span>{{ progressStep > 2 ? '✅' : (progressStep === 2 ? '⏳' : '⚪') }}</span>
          <span>2. {{ useWebSearch ? '联网检索并比对官方招生政策' : '消解多科目时间与精力冲突' }}</span>
        </div>
        <div class="flex items-center gap-2" :class="progressStep >= 3 ? 'text-black font-black' : 'text-neutral-400'">
          <span>{{ progressStep === 3 ? '⏳' : '⚪' }}</span>
          <span>3. 编排 12 周梯度周日程与生活作息</span>
        </div>
      </div>
    </div>

    <div v-else-if="error" class="text-xs font-black text-white bg-[#FF3399] border-[3px] border-black p-5 my-4 shadow-[4px_4px_0px_0px_#000] leading-relaxed">
      <div class="font-black text-sm mb-1">💥 方案生成遇到问题：</div>
      <div>{{ error }}</div>
      <div class="mt-2 text-white/80 font-bold">建议返回上一步重试，或检查服务端的 OPENAI_API_KEY 与模型网络连接。</div>
    </div>

    <!-- 方案展示与看板 -->
    <div v-else-if="plan" class="mt-4">
      <div v-if="degraded" class="text-xs font-black text-black bg-[#FFE600] border-[3px] border-black p-4 mb-4 shadow-[4px_4px_0px_0px_#000] leading-relaxed">
        ⚠️ 本次方案由系统内置排程引擎直接产出（AI 内容生成暂不可用）。日程结构仍然有效，可在「设置」中检查模型 API Key 后重新生成以获得个性化任务内容。
      </div>
      <FusedPlanView :plan="plan" :me="null" @back="emit('back')" @deleted="emit('done')" />
    </div>

    <div class="mt-8 pt-4 border-t-[3px] border-black flex justify-between">
      <button @click="emit('back')" :disabled="loading" class="neo-btn bg-white hover:bg-neutral-100 text-black px-6 py-3 text-xs font-black">
        ← 返回调整画像
      </button>
      <button @click="emit('done')" :disabled="loading" class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black px-8 py-3.5 text-xs font-black border-[3px] shadow-[4px_4px_0px_0px_#000]">
        进入我的档案库 ➔
      </button>
    </div>
  </div>
</template>
