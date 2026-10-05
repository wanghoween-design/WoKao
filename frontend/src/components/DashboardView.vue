<script setup>
import { ref, computed } from 'vue'
import { downloadPlanIcs, deletePlan } from '../api/client.js'
import DeleteConfirmModal from './DeleteConfirmModal.vue'

const props = defineProps({
  plans: { type: Array, default: () => [] },
  me: { type: Object, default: null },
  nowLabel: { type: String, default: '' },
})
const emit = defineEmits(['new', 'open', 'refresh', 'open-profile'])

const sorted = computed(() => props.plans)

// 粗野主义与涂鸦配色主题
const NEO_THEMES = [
  { bg: 'bg-[#FFE600]', tape: 'graffiti-tape-lime', text: 'text-black', tag: 'bg-black text-[#FFE600]', rot: 'sticker-rot-1' },
  { bg: 'bg-[#CCFF00]', tape: 'graffiti-tape-pink', text: 'text-black', tag: 'bg-black text-[#CCFF00]', rot: 'sticker-rot-2' },
  { bg: 'bg-[#00F0FF]', tape: 'graffiti-tape-lime', text: 'text-black', tag: 'bg-black text-[#00F0FF]', rot: 'sticker-rot-3' },
  { bg: 'bg-[#FF3399]', tape: 'graffiti-tape-cyan', text: 'text-white', tag: 'bg-black text-[#FF3399]', rot: 'sticker-rot-1' },
  { bg: 'bg-[#B388FF]', tape: 'graffiti-tape-lime', text: 'text-black', tag: 'bg-black text-[#B388FF]', rot: 'sticker-rot-2' },
]

// 删除弹窗状态
const showDeleteModal = ref(false)
const selectedPlanToDelete = ref(null)
const deleting = ref(false)

function askDelete(p, e) {
  e.stopPropagation()
  selectedPlanToDelete.value = p
  showDeleteModal.value = true
}

async function onConfirmDelete(reason) {
  if (!selectedPlanToDelete.value) return
  deleting.value = true
  try {
    await deletePlan(selectedPlanToDelete.value.id)
    showDeleteModal.value = false
    selectedPlanToDelete.value = null
    emit('refresh')
  } catch (err) {
    alert('删除方案失败：' + (err?.response?.data?.detail || err.message))
  } finally {
    deleting.value = false
  }
}

async function onQuickExport(p, e) {
  e.stopPropagation()
  try {
    await downloadPlanIcs(p.id, `${p.title || p.exam_name}_日历`)
  } catch (err) {
    alert('日历导出失败：' + err.message)
  }
}
</script>

<template>
  <div class="space-y-7">
    <!-- 仪表盘顶栏概览粗野卡片 -->
    <div class="bg-black text-white border-[3px] border-black shadow-[6px_6px_0px_0px_#FFE600] p-6 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 relative overflow-visible">
      <div>
        <div class="flex items-center gap-2.5">
          <span class="neo-badge bg-[#FFE600] text-black">
            ⚡ 备考工作台
          </span>
          <h2 class="text-xl sm:text-2xl font-black font-neo-title tracking-tight text-white">
            {{ me ? (me.nickname || me.username) : '考生' }} 的备考规划总览
          </h2>
        </div>
        <p class="text-xs font-bold text-neutral-300 mt-2 flex flex-wrap items-center gap-2">
          <span>已归档 <strong class="bg-[#CCFF00] text-black px-1.5 py-0.5 border border-black font-black">{{ plans.length }}</strong> 份方案</span>
          <span>·</span>
          <span>24H 全景作息</span>
          <span>·</span>
          <span>Apple 日历同步</span>
          <span>·</span>
          <span>AI 导师伴学</span>
        </p>
      </div>

      <div class="flex items-center gap-3 flex-wrap">
        <button
          @click="emit('open-profile')"
          class="neo-btn bg-white hover:bg-neutral-100 text-black px-4 py-3 text-xs font-black shrink-0 border-[3px] shadow-[3px_3px_0px_0px_#00F0FF]"
        >
          <span>👤 完善考生档案</span>
        </button>

        <button
          @click="emit('new')"
          class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black px-5 py-3 text-xs font-black shrink-0 border-[3px] shadow-[4px_4px_0px_0px_#ffffff]"
        >
          <span class="text-base leading-none">＋</span>
          <span>新建备考规划方案</span>
        </button>
      </div>
    </div>

    <!-- 方案街头卡片网格 -->
    <div>
      <div class="flex items-center justify-between mb-4 px-1">
        <h3 class="text-sm font-black text-black flex items-center gap-2 uppercase tracking-wide">
          <span class="bg-[#FFE600] px-2 py-0.5 border-2 border-black shadow-[2px_2px_0px_0px_#000]">📌 我的备考手帐方案</span>
          <span class="text-xs font-bold text-neutral-500">（点击方案进入 24H 空间作息与伴学导师看板）</span>
        </h3>
      </div>

      <!-- 空状态 -->
      <div
        v-if="plans.length === 0"
        class="border-[3px] border-dashed border-black bg-white p-12 text-center shadow-[6px_6px_0px_0px_#000000]"
      >
        <div class="w-16 h-16 mx-auto bg-[#FFE600] border-2 border-black flex items-center justify-center text-3xl mb-4 shadow-[3px_3px_0px_0px_#000000] rotate-3 font-black">
          ⚡
        </div>
        <h4 class="text-lg font-black text-black font-neo-title">暂无备考规划方案</h4>
        <p class="text-xs font-bold text-neutral-600 mt-1 max-w-sm mx-auto">
          点击上方「新建备考规划方案」，AI 规划师将根据国家大纲与时间基准为您量身定制 12 周融合周作息。
        </p>
        <button
          @click="emit('new')"
          class="neo-btn bg-[#CCFF00] hover:bg-[#B8FF00] text-black px-6 py-3 text-xs font-black mt-6 border-[3px] shadow-[4px_4px_0px_0px_#000]"
        >
          立即开启四步向导 ➔
        </button>
      </div>

      <!-- 粗野主义方案卡片列表 -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="(p, pIdx) in sorted"
          :key="p.id"
          @click="emit('open', p.id)"
          :class="[
            'border-[3px] border-black shadow-[6px_6px_0px_0px_#000000] p-6 cursor-pointer flex flex-col justify-between group select-none transition-all hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[8px_8px_0px_0px_#000000] relative',
            NEO_THEMES[pIdx % NEO_THEMES.length].bg,
            NEO_THEMES[pIdx % NEO_THEMES.length].text,
          ]"
        >
          <!-- 顶部涂鸦胶带标签 -->
          <div :class="['graffiti-tape', NEO_THEMES[pIdx % NEO_THEMES.length].tape]">
            ★ WO KAO PLAN #{{ p.id }} ★
          </div>

          <div>
            <div class="flex items-start justify-between gap-2 mb-3 pt-2">
              <span class="font-black text-base sm:text-lg leading-snug line-clamp-2">
                {{ p.title || p.exam_name }}
              </span>
              <span 
                :class="[
                  'neo-badge text-[10px] shrink-0',
                  NEO_THEMES[pIdx % NEO_THEMES.length].tag
                ]"
              >
                {{ p.is_fused ? '多轨融合' : '单轨精编' }}
              </span>
            </div>

            <div class="mt-3 space-y-2 text-xs font-bold">
              <div class="flex items-center gap-1.5 truncate">
                <span>🎯 目标：</span>
                <span class="truncate font-black underline">{{ p.target_info || p.exam_name }}</span>
              </div>
              <div class="flex items-center gap-2 font-mono text-[11px] bg-black/10 p-1.5 border border-black/30">
                <span>⏱️ {{ p.daily_hours }}h / 天</span>
                <span>·</span>
                <span>📅 {{ p.created_at ? p.created_at.slice(0, 10) : '' }}</span>
              </div>
              <div v-if="p.user_feedback" class="text-[11px] p-2 bg-white text-black border-2 border-black mt-2 line-clamp-2 leading-relaxed font-bold shadow-[2px_2px_0px_0px_#000]">
                ✍️ 调整要求：{{ p.user_feedback }}
              </div>
            </div>
          </div>

          <!-- 卡片底部操作条 -->
          <div class="mt-6 pt-3 border-t-2 border-black flex items-center justify-between text-xs">
            <span class="font-black flex items-center gap-1 group-hover:translate-x-1 transition-transform">
              <span>进入 24H 作息</span>
              <span>➔</span>
            </span>

            <div class="flex items-center gap-2">
              <button
                @click="onQuickExport(p, $event)"
                title="导出到手机 Apple/Google/Outlook 日历"
                class="neo-btn bg-white hover:bg-neutral-100 text-black px-2.5 py-1 text-[11px] font-black border-2 shadow-[2px_2px_0px_0px_#000]"
              >
                📅 日历
              </button>

              <button
                @click="askDelete(p, $event)"
                title="放弃/删除此方案"
                class="neo-btn bg-[#FF3399] hover:bg-[#F43F5E] text-white px-2.5 py-1 text-[11px] font-black border-2 shadow-[2px_2px_0px_0px_#000]"
              >
                🗑️ 删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 温情挽留删除弹窗 -->
    <DeleteConfirmModal
      :show="showDeleteModal"
      :plan="selectedPlanToDelete"
      :deleting="deleting"
      @close="showDeleteModal = false"
      @confirm="onConfirmDelete"
    />
  </div>
</template>
