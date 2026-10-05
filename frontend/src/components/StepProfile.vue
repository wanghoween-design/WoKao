<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getProfile, saveResume } from '../api/client.js'

const props = defineProps({
  identity: { type: String, default: '' },
  nickname: { type: String, default: '' },
  goals: { type: Array, default: () => [] },
  goalTargets: { type: Object, default: () => ({}) },
  dailyHours: { type: Number, default: 4 },
})
const emit = defineEmits(['next', 'back'])

const targets = reactive({})
props.goals.forEach((g) => {
  targets[g.exam_name] = props.goalTargets[g.exam_name] || ''
})
const hours = ref(props.dailyHours || 4)
const resumeText = ref('')

onMounted(async () => {
  try {
    const profile = await getProfile()
    if (profile.resume_text) resumeText.value = profile.resume_text
  } catch (e) { /* ignore if no profile yet */ }
})

async function submit() {
  if (resumeText.value.trim()) {
    // 简历保存失败不阻塞向导流转，生成计划后仍可在个人档案中补填
    try { await saveResume({ resume_text: resumeText.value }) } catch (e) { /* ignore */ }
  }
  emit('next', { dailyHours: Number(hours.value) || 4, goalTargets: { ...targets }, resumeText: resumeText.value })
}
</script>

<template>
  <div>
    <div class="border-b-[3px] border-black pb-4 mb-5">
      <div class="flex items-center gap-2">
        <span class="neo-badge bg-[#00F0FF] text-black">STEP 03</span>
        <h2 class="text-xl font-black font-neo-title text-black">
          确认考生画像与目标定位
        </h2>
      </div>
      <p class="text-xs font-bold text-neutral-600 mt-1">
        为每一项考试写下具体期望（如目标院校层次、意向专业、报考省份或分数线要求），以便大模型输出精准抓手。
      </p>
    </div>

    <!-- 档案概览卡片 -->
    <div class="bg-black text-white border-[3px] border-black p-5 mb-6 shadow-[6px_6px_0px_0px_#FFE600] relative">
      <div class="flex flex-wrap items-center gap-2 text-xs font-bold">
        <span class="text-neutral-400">考生背景：</span>
        <span class="neo-badge bg-[#FFE600] text-black">
          {{ identity || '考生' }}
        </span>
        <span class="text-neutral-500">·</span>
        <span class="text-neutral-400">称呼：</span>
        <span class="neo-badge bg-[#CCFF00] text-black">
          {{ nickname || '同学' }}
        </span>
      </div>
      <div class="flex flex-wrap items-center gap-2 text-xs mt-3 font-bold">
        <span class="text-neutral-400">已选并行轨道：</span>
        <span
          v-for="g in goals"
          :key="g.exam_name"
          class="neo-badge bg-[#00F0FF] text-black"
        >
          🎯 {{ g.exam_name }}
        </span>
      </div>
    </div>

    <!-- 各目标详细期望输入 -->
    <div class="space-y-4">
      <div
        v-for="g in goals"
        :key="g.exam_name"
        class="bg-white border-[3px] border-black p-5 shadow-[4px_4px_0px_0px_#000] relative"
      >
        <div class="graffiti-tape graffiti-tape-lime">
          TARGET SPECS
        </div>
        <div class="flex items-center justify-between mb-2">
          <label class="text-xs font-black text-black flex items-center gap-1.5 uppercase font-neo-title text-sm">
            <span class="w-2.5 h-2.5 bg-[#FFE600] border border-black inline-block"></span>
            <span>{{ g.exam_name }} · 具体目标定位与期望</span>
          </label>
          <span class="text-[11px] font-mono font-bold bg-black/10 px-2 py-0.5 border border-black/20">{{ g.annual_period }}</span>
        </div>
        <input
          v-model="targets[g.exam_name]"
          :placeholder="`如：吉林大学 计算机 408 / 国考省直综合管理岗 / 专硕全日制`"
          class="neo-input text-sm"
        />
        <div class="text-[11px] text-black font-bold mt-2 flex items-center gap-1">
          <span>💡 核心科目：</span>
          <span class="underline">{{ (g.exam_subjects || []).join('、') }}</span>
        </div>
      </div>
    </div>

    <!-- 每日精力分配 -->
    <div class="mt-6 bg-[#FFFDE6] border-[3px] border-black p-5 max-w-md shadow-[4px_4px_0px_0px_#000] relative">
      <div class="graffiti-tape graffiti-tape-pink">
        DAILY CAPACITY
      </div>
      <label class="block text-xs font-black text-black mb-1 uppercase">
        ⏱️ 每日可用学习总时长（小时）
      </label>
      <p class="text-[11px] font-bold text-neutral-600 mb-3">
        多目标将在此总时长下错峰排布（建议在职 2~4h，在校全职 6~8h）
      </p>
      <div class="flex items-center gap-4">
        <input
          type="range"
          min="1"
          max="12"
          step="0.5"
          v-model.number="hours"
          class="flex-1 accent-black cursor-pointer"
        />
        <span class="text-base font-black font-mono text-black bg-white px-3 py-1 border-2 border-black shadow-[2px_2px_0px_0px_#000]">
          {{ hours }} <span class="text-xs font-normal">h / 天</span>
        </span>
      </div>
    </div>

    <!-- 个人简历/背景 -->
    <div class="mt-6 p-5 border-[3px] border-black bg-white shadow-[4px_4px_0px_0px_#000] relative">
      <div class="graffiti-tape graffiti-tape-cyan">
        RESUME & PROFILE
      </div>
      <h3 class="text-sm font-black text-black mb-1 font-neo-title flex items-center gap-1.5">
        <span>📋 个人简历概况 / 备考背景（可选）</span>
      </h3>
      <p class="text-xs font-bold text-neutral-600 mb-3">
        粘贴您的简历纯文本（专业背景、工作经历、科研论文等），AI 导师将据此给出极具针对性的背景匹配与定制规划。
      </p>
      <textarea 
        v-model="resumeText" 
        rows="5" 
        placeholder="粘贴您的简历内容或科研/工作背景（选填）..."
        class="neo-input text-xs leading-relaxed"
      ></textarea>
      <p class="text-[11px] font-mono font-bold text-neutral-500 mt-1.5 text-right">{{ resumeText.length }} 字</p>
    </div>

    <div class="mt-8 pt-4 border-t-[3px] border-black flex justify-between">
      <button @click="emit('back')" class="neo-btn bg-white hover:bg-neutral-100 text-black px-6 py-3 text-xs font-black">
        ← 上一步
      </button>
      <button
        @click="submit"
        class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black px-8 py-3.5 text-xs font-black border-[3px] shadow-[4px_4px_0px_0px_#000]"
      >
        <span>下一步：生成 24H 周作息全景方案 ➔</span>
      </button>
    </div>
  </div>
</template>
