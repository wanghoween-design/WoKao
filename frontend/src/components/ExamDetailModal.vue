<script setup>
import { computed } from 'vue'

const props = defineProps({
  exam: { type: Object, default: null },
})
const emit = defineEmits(['close'])

function websiteUrl(text) {
  if (!text) return ''
  const m = text.match(/https?:\/\/[^\s]+/)
  return m ? m[0] : ''
}
const siteUrl = computed(() => (props.exam ? websiteUrl(props.exam.official_website) : ''))
const siteLabel = computed(() => {
  if (!props.exam) return ''
  const url = siteUrl.value
  return (props.exam.official_website || '').replace(url, '').trim() || '官方网站'
})

function isTbd(text) {
  if (!text) return false
  return /待定|待公布|以官方|以公告|具体以|实时获取|为准/.test(text)
}
</script>

<template>
  <div v-if="exam" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" @click.self="emit('close')">
    <div class="bg-white border-[3px] border-black shadow-[8px_8px_0px_0px_#000] w-full max-w-2xl max-h-[88vh] overflow-auto relative">
      <!-- 模态框头部 -->
      <div class="sticky top-0 bg-black text-white px-6 py-4 flex items-center justify-between border-b-[3px] border-black z-10">
        <div class="flex items-center gap-2.5">
          <span class="text-2xl font-black">🏛️</span>
          <div>
            <h3 class="text-base font-black font-neo-title uppercase text-[#FFE600]">{{ exam.exam_name }} · 国家大纲明细</h3>
            <span class="neo-badge bg-[#CCFF00] text-black text-[9px] px-1 py-0">{{ exam.category }}</span>
          </div>
        </div>
        <button @click="emit('close')" class="neo-badge bg-[#FF3399] text-white cursor-pointer">✕</button>
      </div>

      <div class="p-6 text-xs space-y-4 text-black font-bold leading-relaxed bg-[#FAF7F2]">
        <p class="bg-white p-3.5 border-2 border-black shadow-[2px_2px_0px_0px_#000] leading-normal font-bold">{{ exam.description }}</p>

        <!-- 每年大致时段 -->
        <div class="bg-[#FFE600] border-2 border-black p-3.5 shadow-[2px_2px_0px_0px_#000]">
          <div class="text-xs font-black uppercase mb-1 flex items-center gap-1.5 font-neo-title">
            <span>📅 每年常规考期规律</span>
          </div>
          <div class="font-bold">{{ exam.annual_period || '以官方公告为准' }}</div>
        </div>

        <!-- 今年具体考期与报名 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="bg-white p-3 border-2 border-black shadow-[2px_2px_0px_0px_#000]">
            <div class="flex items-center justify-between mb-1">
              <div class="text-neutral-500 font-black">今年考试时间</div>
              <span v-if="isTbd(exam.exam_time)" class="neo-badge bg-[#FFE600] text-black text-[9px]">
                待官方公布
              </span>
            </div>
            <div class="font-black font-mono text-sm">{{ exam.exam_time }}</div>
          </div>
          <div class="bg-white p-3 border-2 border-black shadow-[2px_2px_0px_0px_#000]">
            <div class="flex items-center justify-between mb-1">
              <div class="text-neutral-500 font-black">今年报名时间</div>
              <span v-if="isTbd(exam.registration_time)" class="neo-badge bg-[#FFE600] text-black text-[9px]">
                待官方公布
              </span>
            </div>
            <div class="font-black text-sm">{{ exam.registration_time || '以官方公告为准' }}</div>
          </div>
        </div>

        <div v-if="siteUrl" class="bg-white p-3 border-2 border-black flex items-center justify-between shadow-[2px_2px_0px_0px_#000]">
          <div>
            <div class="text-neutral-500 text-[10px] font-black uppercase">权威官方网站与招考系统</div>
            <div class="font-black text-sm mt-0.5">{{ siteLabel }}</div>
          </div>
          <a :href="siteUrl" target="_blank" rel="noopener" class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black text-xs px-3.5 py-1.5 font-black shadow-[2px_2px_0px_0px_#000]">
            访问官网 ↗
          </a>
        </div>

        <!-- 核心科目明细表 -->
        <div v-if="exam.subjects_detail && exam.subjects_detail.length">
          <div class="font-black uppercase mb-1.5 flex items-center gap-1.5 font-neo-title text-sm">
            <span class="w-2.5 h-2.5 bg-black inline-block"></span>
            <span>科目明细与分值拆解</span>
          </div>
          <div class="border-2 border-black overflow-hidden shadow-[3px_3px_0px_0px_#000]">
            <table class="w-full text-xs border-collapse">
              <thead>
                <tr class="bg-[#FFE600] text-black font-black border-b-2 border-black">
                  <th class="p-2.5 text-left border-r-2 border-black">科目名称</th>
                  <th class="p-2.5 text-left border-r-2 border-black">类型</th>
                  <th class="p-2.5 text-left border-r-2 border-black">分值/时长</th>
                  <th class="p-2.5 text-left">考察范围与特点</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in exam.subjects_detail" :key="d.name" class="border-b-2 border-black last:border-0 bg-white">
                  <td class="p-2.5 font-black border-r-2 border-black">{{ d.name }}</td>
                  <td class="p-2.5 font-bold border-r-2 border-black">{{ d.type }}</td>
                  <td class="p-2.5 font-mono font-black border-r-2 border-black">{{ d.score }}分 / {{ d.duration }}</td>
                  <td class="p-2.5 leading-tight font-medium">{{ d.desc }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="exam.exam_format && exam.exam_format.length" class="space-y-1 bg-white p-3 border-2 border-black shadow-[2px_2px_0px_0px_#000]">
          <div class="font-black uppercase font-neo-title">考试形式与阶段：</div>
          <ul class="list-disc list-inside space-y-0.5 font-bold">
            <li v-for="(f, i) in exam.exam_format" :key="i">{{ f }}</li>
          </ul>
        </div>

        <div v-if="exam.tips && exam.tips.length" class="space-y-1 bg-[#CCFF00] p-3 border-2 border-black shadow-[2px_2px_0px_0px_#000]">
          <div class="font-black uppercase font-neo-title text-black">💡 官方备考指南与贴士：</div>
          <ul class="list-disc list-inside space-y-0.5 font-bold text-black">
            <li v-for="(t, i) in exam.tips" :key="i">{{ t }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
