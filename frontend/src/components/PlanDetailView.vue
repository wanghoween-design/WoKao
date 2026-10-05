<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import md from '../md.js'
import { getPlan, updatePlan, deletePlan, downloadPlanIcs, downloadPlanMd } from '../api/client.js'
import FusedPlanView from './FusedPlanView.vue'

const props = defineProps({
  planId: { type: Number, required: true },
  me: { type: Object, default: null },
})
const emit = defineEmits(['back', 'deleted'])

const plan = ref(null)
const loading = ref(false)
const error = ref('')
const saving = ref(false)
const msg = ref('')
const copySuccess = ref(false)

const edited = reactive({ title: '', target_info: '', daily_hours: 4 })
const feedback = ref('')

onMounted(load)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const d = await getPlan(props.planId)
    plan.value = d.plan
    edited.title = plan.value.title || ''
    edited.target_info = plan.value.target_info || ''
    edited.daily_hours = plan.value.daily_hours || 4
    feedback.value = plan.value.user_feedback || ''
  } catch (e) {
    error.value = (e.response && e.response.data && e.response.data.detail) || e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function saveMeta() {
  saving.value = true
  msg.value = ''
  error.value = ''
  try {
    const d = await updatePlan(props.planId, {
      title: edited.title,
      target_info: edited.target_info,
      daily_hours: Number(edited.daily_hours) || 4,
    })
    plan.value = d.plan
    msg.value = '✓ 基础信息修改已保存'
  } catch (e) {
    error.value = (e.response && e.response.data && e.response.data.detail) || e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function regenerate() {
  saving.value = true
  msg.value = ''
  error.value = ''
  try {
    const d = await updatePlan(props.planId, {
      user_feedback: feedback.value,
      regenerate: true,
      target_info: edited.target_info,
      daily_hours: Number(edited.daily_hours) || 4,
    })
    plan.value = d.plan
    msg.value = '✓ 已基于最新反馈重新生成备考方案'
  } catch (e) {
    error.value = (e.response && e.response.data && e.response.data.detail) || e.message || '生成失败'
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!confirm('确定注销并删除该计划？此操作不可逆。')) return
  try {
    await deletePlan(props.planId)
    emit('deleted')
  } catch (e) {
    error.value = (e.response && e.response.data && e.response.data.detail) || e.message || '删除失败'
  }
}

async function exportIcs() {
  try {
    await downloadPlanIcs(props.planId, `${plan.value?.title || plan.value?.exam_name}_备考日历`)
  } catch (e) {
    error.value = '导出日历失败：' + e.message
  }
}

async function exportMd() {
  try {
    await downloadPlanMd(props.planId, `${plan.value?.title || plan.value?.exam_name}_备考方案`)
  } catch (e) {
    error.value = '导出 Markdown 失败：' + e.message
  }
}

async function copyMarkdownText() {
  const text = plan.value?.generated_plan || ''
  try {
    await navigator.clipboard.writeText(text)
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 2000)
  } catch (e) {
    error.value = '复制到剪贴板失败，请使用导出 .md 按钮'
  }
}

const renderedHtml = computed(() => {
  return plan.value ? md.render(plan.value.generated_plan || '') : ''
})

const isFused = computed(() => {
  if (!plan.value || !plan.value.fused_plan) return false
  try {
    const obj = JSON.parse(plan.value.fused_plan)
    return Array.isArray(obj.tracks) && obj.tracks.length > 0
  } catch (e) {
    return false
  }
})
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between no-print">
      <button @click="emit('back')" class="neo-btn bg-white hover:bg-neutral-100 text-black px-4 py-2 text-xs font-black">
        ← 返回方案看板
      </button>
      <div v-if="plan && !isFused" class="flex gap-2">
        <button @click="exportIcs" class="neo-btn bg-[#FFE600] text-black text-xs px-3.5 py-1.5 shadow-[2px_2px_0px_0px_#000]">
          📅 导出手机日历 (.ics)
        </button>
        <button @click="copyMarkdownText" class="neo-btn bg-white hover:bg-neutral-100 text-black text-xs px-3.5 py-1.5 shadow-[2px_2px_0px_0px_#000]">
          {{ copySuccess ? '✓ 已复制全文' : '📋 复制 Markdown' }}
        </button>
        <button @click="exportMd" class="neo-btn bg-white hover:bg-neutral-100 text-black text-xs px-3.5 py-1.5 shadow-[2px_2px_0px_0px_#000]">
          ⬇️ 导出 .md
        </button>
      </div>
    </div>

    <div v-if="loading" class="bg-white border-[3px] border-black p-12 text-center shadow-[6px_6px_0px_0px_#000]">
      <div class="animate-spin text-3xl mb-3">⏳</div>
      <div class="font-black font-neo-title uppercase text-sm">正在加载备考方案…</div>
    </div>

    <p v-else-if="error" class="bg-[#FF3399] text-white p-4 border-2 border-black font-black text-xs shadow-[3px_3px_0px_0px_#000]">{{ error }}</p>

    <div v-else-if="plan">
      <!-- 1. 多轨融合空间看板模式 -->
      <FusedPlanView
        v-if="isFused"
        :plan="plan"
        :me="me"
        @back="emit('back')"
        @deleted="emit('deleted')"
        @updated="load"
      />

      <!-- 2. 单轨方案大纲模式 -->
      <div v-else class="space-y-6">
        <div class="bg-white border-[3px] border-black p-6 shadow-[6px_6px_0px_0px_#000] relative">
          <div class="graffiti-tape graffiti-tape-lime">
            SINGLE TRACK
          </div>
          <div class="flex justify-between items-start flex-wrap gap-4 pt-2">
            <div>
              <div class="flex items-center gap-2">
                <span class="neo-badge bg-[#FFE600] text-black">
                  PLAN #{{ plan.id }}
                </span>
                <h2 class="text-2xl font-black font-neo-title text-black">{{ plan.title || plan.exam_name }}</h2>
              </div>
              <p class="text-xs font-bold text-neutral-500 mt-1">
                创建于 {{ plan.created_at }} · 考生 {{ plan.username || '匿名' }}
              </p>
            </div>
            <div class="flex gap-2">
              <button @click="remove" class="neo-btn bg-[#FF3399] text-white text-xs px-3.5 py-1.5 shadow-[2px_2px_0px_0px_#000]">
                删除方案
              </button>
            </div>
          </div>

          <div v-if="msg" class="mt-3 text-xs font-black text-black bg-[#CCFF00] p-2.5 border-2 border-black shadow-[2px_2px_0px_0px_#000]">{{ msg }}</div>
        </div>

        <div class="bg-white border-[3px] border-black p-6 md:p-8 shadow-[6px_6px_0px_0px_#000]">
          <div class="md-body" v-html="renderedHtml"></div>
        </div>
      </div>
    </div>
  </div>
</template>
