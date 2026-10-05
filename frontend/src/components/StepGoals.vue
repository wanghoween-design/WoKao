<script setup>
import { ref, computed } from 'vue'
import ExamSearchView from './ExamSearchView.vue'
import ExamDetailModal from './ExamDetailModal.vue'

const props = defineProps({
  exams: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  selected: { type: Array, default: () => [] },
  now: { type: Object, default: null },
  useWebSearch: { type: Boolean, default: true },
})
const emit = defineEmits(['next', 'back', 'update:useWebSearch'])

const localWeb = computed({
  get: () => props.useWebSearch,
  set: (v) => emit('update:useWebSearch', v),
})

const activeCategory = ref(props.categories[0] || '高校/大学生')
const selectedKeys = ref(new Set(props.selected.map((e) => e.exam_name)))
const detailExam = ref(null)

const searchSchool = ref('')
const searchMajor = ref('')
const searching = ref(false)
const searchResult = ref(null)
const searchExamType = ref('')

const filteredExams = computed(() =>
  props.exams.filter((e) => e.category === activeCategory.value)
)

const needsSearch = computed(() => {
  const searchableExams = ['考研', '申博', '考博']
  return [...selectedKeys.value].some(name => 
    searchableExams.some(keyword => name.includes(keyword))
  )
})

const NEO_CARD_COLORS = [
  { bg: 'bg-[#FFE600]', text: 'text-black', tape: 'graffiti-tape-lime' },
  { bg: 'bg-[#CCFF00]', text: 'text-black', tape: 'graffiti-tape-pink' },
  { bg: 'bg-[#00F0FF]', text: 'text-black', tape: 'graffiti-tape-lime' },
  { bg: 'bg-[#FF3399]', text: 'text-white', tape: 'graffiti-tape-cyan' },
  { bg: 'bg-[#B388FF]', text: 'text-black', tape: 'graffiti-tape-pink' },
]

async function triggerSearch() {
  if (!searchSchool.value) return
  searching.value = true
  searchExamType.value = [...selectedKeys.value].find(name => 
    ['考研','申博','考博'].some(k => name.includes(k))
  ) || '考研'
  searchResult.value = true
  searching.value = false
}

function isTbd(text) {
  if (!text) return false
  return /待定|待公布|以官方|以公告|具体以|实时获取|为准/.test(text)
}
function isSelected(name) {
  return selectedKeys.value.has(name)
}
function toggle(exam) {
  if (selectedKeys.value.has(exam.exam_name)) {
    selectedKeys.value.delete(exam.exam_name)
  } else {
    selectedKeys.value.add(exam.exam_name)
  }
  selectedKeys.value = new Set(selectedKeys.value)
}
function openDetail(exam, e) {
  e.stopPropagation()
  detailExam.value = exam
}
function next() {
  const goals = props.exams.filter((e) => selectedKeys.value.has(e.exam_name))
  emit('next', goals)
}
</script>

<template>
  <div>
    <div class="border-b-[3px] border-black pb-4 mb-5 flex items-baseline justify-between flex-wrap gap-2">
      <div>
        <div class="flex items-center gap-2">
          <span class="neo-badge bg-[#CCFF00] text-black">STEP 02</span>
          <h2 class="text-xl font-black font-neo-title text-black">
            挑选备考目标大纲
          </h2>
          <span class="neo-badge bg-[#FFE600] text-black text-[10px]">
            ⚡ 支持多目标并行融合（如 考研 + 国考）
          </span>
        </div>
        <p class="text-xs font-bold text-neutral-600 mt-1">
          勾选您今年计划参加的考试。系统将自动消除时间冲突，为您编排在同一张 24H 空间周作息表中。
        </p>
      </div>
      <div class="text-xs font-black bg-white border-2 border-black px-3.5 py-1.5 shadow-[2px_2px_0px_0px_#000]">
        已选目标：<span class="bg-[#FFE600] px-2 py-0.5 border border-black font-mono font-black text-sm">{{ selectedKeys.size }}</span> 项
      </div>
    </div>

    <!-- 联网检索开关 -->
    <div class="bg-white border-2 border-black p-3.5 mb-5 flex items-center justify-between text-xs shadow-[3px_3px_0px_0px_#000] relative">
      <div class="graffiti-tape graffiti-tape-lime">
        WEB SEARCH AGENT
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xl font-black">🌐</span>
        <div>
          <span class="font-black text-black">官方招生简章实时联网核验</span>
          <span class="text-neutral-500 ml-1 font-bold">（针对申博/考研等目标，自动联网调取最新简章与时间节点）</span>
        </div>
      </div>
      <label class="flex items-center gap-2 cursor-pointer select-none bg-[#FFE600] px-3 py-1 border-2 border-black font-black shadow-[2px_2px_0px_0px_#000]">
        <input type="checkbox" v-model="localWeb" class="w-4 h-4 text-black rounded-none cursor-pointer accent-black" />
        <span>启用联网检索</span>
      </label>
    </div>

    <!-- 分类标签栏 -->
    <div class="flex flex-wrap gap-2 mb-5">
      <button
        v-for="cat in categories"
        :key="cat"
        @click="activeCategory = cat"
        :class="[
          'neo-btn px-4 py-2 text-xs',
          activeCategory === cat
            ? 'bg-[#FFE600] text-black shadow-[3px_3px_0px_0px_#000]'
            : 'bg-white text-black hover:bg-[#FFFDE6] shadow-[2px_2px_0px_0px_#000]',
        ]"
      >
        📑 {{ cat }}
      </button>
    </div>

    <!-- 考试卡片矩阵 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
      <div
        v-for="(exam, eIdx) in filteredExams"
        :key="exam.exam_name"
        @click="toggle(exam)"
        :class="[
          'border-[3px] border-black p-4.5 cursor-pointer flex flex-col justify-between select-none transition-all relative',
          NEO_CARD_COLORS[eIdx % NEO_CARD_COLORS.length].bg,
          NEO_CARD_COLORS[eIdx % NEO_CARD_COLORS.length].text,
          isSelected(exam.exam_name)
            ? 'shadow-[6px_6px_0px_0px_#000000] translate-x-[-2px] translate-y-[-2px] ring-4 ring-black'
            : 'shadow-[4px_4px_0px_0px_#000000] hover:shadow-[6px_6px_0px_0px_#000000] hover:translate-x-[-1px] hover:translate-y-[-1px]',
        ]"
      >
        <div :class="['graffiti-tape', NEO_CARD_COLORS[eIdx % NEO_CARD_COLORS.length].tape]">
          EXAM TRACK
        </div>

        <div>
          <div class="flex items-start justify-between gap-2 pt-1">
            <div class="flex items-center gap-2">
              <span
                :class="[
                  'w-6 h-6 border-2 border-black flex items-center justify-center text-xs font-black transition shrink-0',
                  isSelected(exam.exam_name)
                    ? 'bg-black text-[#FFE600] shadow-[1px_1px_0px_0px_#fff]'
                    : 'bg-white text-transparent',
                ]"
              >
                ✓
              </span>
              <span class="font-black text-base leading-snug">
                {{ exam.exam_name }}
              </span>
            </div>

            <button
              @click="openDetail(exam, $event)"
              class="neo-btn bg-white hover:bg-neutral-100 text-black text-[11px] px-2 py-0.5 border-2 shadow-[2px_2px_0px_0px_#000]"
            >
              大纲明细 📖
            </button>
          </div>

          <div class="text-xs mt-2 font-mono font-bold bg-black/10 p-1 border border-black/20">
            📅 {{ exam.annual_period }}
          </div>
        </div>

        <div class="mt-4 pt-2.5 border-t-2 border-black/20 flex items-center justify-between text-xs">
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="subj in (exam.exam_subjects || []).slice(0, 2)"
              :key="subj"
              class="text-[10px] font-black px-2 py-0.5 bg-white text-black border border-black shadow-[1px_1px_0px_0px_#000]"
            >
              {{ subj }}
            </span>
            <span v-if="(exam.exam_subjects || []).length > 2" class="text-[10px] font-black opacity-80 self-center">...</span>
          </div>

          <span v-if="isTbd(exam.exam_time)" class="neo-badge bg-black text-[#FFE600] text-[10px]">
            待定 · 实时获取
          </span>
        </div>
      </div>
    </div>

    <!-- 院校搜索卡片 -->
    <div v-if="needsSearch" class="mt-7 p-6 border-[3px] border-black bg-white shadow-[6px_6px_0px_0px_#000] relative">
      <div class="graffiti-tape graffiti-tape-pink">
        DEEP SEARCH PIPELINE
      </div>
      <h3 class="text-sm font-black text-black mb-3 font-neo-title flex items-center gap-1.5">
        <span>🔍 搜索目标院校/专业的详细考情与招生信息</span>
      </h3>
      <div class="flex flex-col sm:flex-row gap-2 mb-3">
        <input v-model="searchSchool" placeholder="目标学校（如：吉林大学 / 东北师范大学）" 
               class="neo-input flex-1 text-sm" />
        <input v-model="searchMajor" placeholder="目标专业（如：计算机科学与技术）" 
               class="neo-input flex-1 text-sm" />
        <button @click="triggerSearch" :disabled="searching" 
                class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black px-6 py-2.5 text-xs font-black shrink-0 border-[3px] shadow-[3px_3px_0px_0px_#000]">
          {{ searching ? '检索中…' : '🔍 检索招生简章' }}
        </button>
      </div>
      <ExamSearchView v-if="searchResult" :exam-type="searchExamType" :school="searchSchool" :major="searchMajor" 
                      @close="searchResult = null" />
    </div>

    <div class="mt-8 pt-4 border-t-[3px] border-black flex justify-between">
      <button @click="emit('back')" class="neo-btn bg-white hover:bg-neutral-100 text-black px-6 py-3 text-xs font-black">
        ← 上一步
      </button>
      <button
        @click="next"
        :disabled="selectedKeys.size === 0"
        :class="[
          'neo-btn px-8 py-3.5 text-xs font-black border-[3px]',
          selectedKeys.size > 0
            ? 'bg-[#FFE600] text-black hover:bg-[#FFF066] shadow-[4px_4px_0px_0px_#000]'
            : 'bg-neutral-200 text-neutral-400 border-neutral-400 cursor-not-allowed shadow-none',
        ]"
      >
        <span>下一步：确认画像与期望 ➔</span>
      </button>
    </div>

    <ExamDetailModal :exam="detailExam" @close="detailExam = null" />
  </div>
</template>
