<template>
  <div class="fixed inset-0 z-50 bg-black/60 flex justify-center items-center p-4 sm:p-8">
    <div class="bg-white w-full max-w-6xl h-full max-h-full border-[3px] border-black shadow-[8px_8px_0px_0px_#000] flex flex-col overflow-hidden relative">
      
      <!-- 顶部涂鸦胶带 -->
      <div class="graffiti-tape graffiti-tape-lime">
        SCHEDULE EDITOR
      </div>

      <!-- Header -->
      <div class="px-6 py-4 border-b-[3px] border-black bg-[#FFE600] flex justify-between items-center shrink-0">
        <h2 class="text-xl font-black font-neo-title text-black flex items-center gap-2 uppercase tracking-tight">
          <span>✏️</span>
          <span>交互式日程微调编辑器</span>
        </h2>
        <div class="flex items-center gap-4">
          <select 
            v-model="selectedTrack"
            class="neo-input text-xs font-black bg-white py-1 px-3"
          >
            <option value="all">所有考试轨道</option>
            <option v-for="name in trackNames" :key="name" :value="name">
              {{ name }}
            </option>
          </select>
          <button @click="emit('close')" class="neo-badge bg-black text-white cursor-pointer">
            ✕
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-auto p-6 space-y-7 bg-[#FAF7F2]">
        <div v-if="error" class="bg-[#FF3399] text-white p-3.5 border-2 border-black font-black text-xs shadow-[2px_2px_0px_0px_#000] flex items-center gap-2">
          <span>⚠️</span> {{ error }}
        </div>
        
        <div v-for="[week, weekTasks] in weekGroups" :key="week" class="bg-white border-2 border-black shadow-[4px_4px_0px_0px_#000] overflow-hidden">
          <!-- Week Header -->
          <div class="px-5 py-3 border-b-2 border-black bg-[#FFE600] flex justify-between items-center">
            <h3 class="font-black font-neo-title text-sm uppercase text-black">第 {{ week }} 周任务编排</h3>
            <button 
              @click="addTask(Number(week))"
              class="neo-btn bg-white hover:bg-neutral-100 text-black text-xs px-3 py-1 font-black shadow-[2px_2px_0px_0px_#000]"
            >
              <span>+</span>
              <span>添加任务</span>
            </button>
          </div>
          
          <!-- Table -->
          <div class="overflow-x-auto">
            <table class="w-full text-xs text-left">
              <thead class="bg-black text-white border-b-2 border-black uppercase font-black">
                <tr>
                  <th class="px-4 py-2.5 w-28 border-r border-neutral-700">考试轨道</th>
                  <th class="px-4 py-2.5 w-24 border-r border-neutral-700">星期</th>
                  <th class="px-4 py-2.5 w-32 border-r border-neutral-700">时间段</th>
                  <th class="px-4 py-2.5 w-48 border-r border-neutral-700">任务名称</th>
                  <th class="px-4 py-2.5 border-r border-neutral-700">量化指标 / 抓手</th>
                  <th class="px-4 py-2.5 w-24 border-r border-neutral-700">时长(h)</th>
                  <th class="px-4 py-2.5 w-16 text-center">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y-2 divide-black/10 font-bold">
                <tr v-for="task in weekTasks" :key="task.id" class="hover:bg-[#FFFDE6] transition-colors group">
                  <td class="px-3 py-2 border-r border-black/10">
                    <select v-model="task.trackName" class="w-full bg-white border border-black p-1 text-black font-bold">
                      <option v-for="name in trackNames" :key="name" :value="name">{{ name }}</option>
                    </select>
                  </td>
                  <td class="px-3 py-2 border-r border-black/10">
                    <select v-model="task.weekday" class="w-full bg-white border border-black p-1 text-black font-bold">
                      <option v-for="day in ['周一','周二','周三','周四','周五','周六','周日']" :key="day" :value="day">{{ day }}</option>
                    </select>
                  </td>
                  <td class="px-3 py-2 border-r border-black/10">
                    <input type="text" v-model="task.time_block" class="w-full bg-white border border-black p-1 text-black font-mono font-bold" placeholder="09:00-10:00">
                  </td>
                  <td class="px-3 py-2 border-r border-black/10">
                    <input type="text" v-model="task.title" class="w-full bg-white border border-black p-1 text-black font-black" placeholder="任务名称">
                  </td>
                  <td class="px-3 py-2 border-r border-black/10">
                    <input type="text" v-model="task.metric" class="w-full bg-white border border-black p-1 text-black" placeholder="完成指标或备注">
                  </td>
                  <td class="px-3 py-2 border-r border-black/10">
                    <input type="number" v-model.number="task.duration_hours" min="0.5" step="0.5" class="w-full bg-white border border-black p-1 text-black font-mono font-bold">
                  </td>
                  <td class="px-3 py-2 text-center">
                    <button 
                      @click="removeTask(task.id)"
                      class="neo-badge bg-[#FF3399] text-white cursor-pointer"
                      title="删除任务"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
                <tr v-if="weekTasks.length === 0">
                  <td colspan="7" class="px-4 py-6 text-center text-neutral-400 font-bold italic">
                    本周暂无任务
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <div v-if="tasks.length === 0" class="text-center py-12">
          <div class="text-4xl mb-3">📭</div>
          <p class="font-bold text-neutral-500">暂无日程任务</p>
          <button @click="addTask(1)" class="neo-btn bg-[#FFE600] text-black px-5 py-2 text-xs font-black mt-4 shadow-[2px_2px_0px_0px_#000]">
            添加第一周任务
          </button>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t-[3px] border-black bg-white flex justify-between items-center shrink-0">
        <div class="text-xs font-black text-black flex items-center gap-2 h-6">
          <span v-if="msg" class="neo-badge bg-[#CCFF00] text-black">✅ {{ msg }}</span>
        </div>
        <div class="flex items-center gap-3">
          <button 
            @click="emit('close')"
            class="neo-btn bg-white hover:bg-neutral-100 text-black px-4 py-2 text-xs font-black"
            :disabled="saving"
          >
            取消
          </button>
          <button 
            @click="save"
            class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black px-6 py-2 text-xs font-black border-[3px] shadow-[3px_3px_0px_0px_#000]"
            :disabled="saving"
          >
            <span v-if="saving" class="animate-spin text-sm">⏳</span>
            <span v-else>💾</span>
            <span>{{ saving ? '保存中...' : '保存修改' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { updateSchedule } from '../api/client.js'

const props = defineProps({
  plan: { type: Object, required: true },
  planId: { type: Number, required: true }
})

const emit = defineEmits(['saved', 'close'])

// Parse fused_plan JSON
const tasks = ref([])
const trackNames = ref([])
const selectedTrack = ref('all')
const saving = ref(false)
const msg = ref('')
const error = ref('')

function parsePlan() {
  try {
    const fused = typeof props.plan.fused_plan === 'string'
      ? JSON.parse(props.plan.fused_plan)
      : props.plan.fused_plan
    if (!fused || !fused.tracks) return
    
    const allTasks = []
    const names = new Set()
    fused.tracks.forEach((track, tIdx) => {
      names.add(track.exam_name || `Track ${tIdx + 1}`)
      ;(track.tasks || []).forEach((task, taskIdx) => {
        allTasks.push({
          id: `${tIdx}-${taskIdx}`,
          trackIdx: tIdx,
          trackName: track.exam_name || `Track ${tIdx + 1}`,
          week: task.week || 1,
          weekday: task.weekday || '周一',
          time_block: task.time_block || '09:00-10:00',
          title: task.title || '',
          metric: task.metric || '',
          duration_hours: task.duration_hours || 1,
          type: task.type || 'study',
          status: task.status || 'todo'
        })
      })
    })
    tasks.value = allTasks.sort((a, b) => {
      if (a.week !== b.week) return a.week - b.week
      const days = ['周一','周二','周三','周四','周五','周六','周日']
      return days.indexOf(a.weekday) - days.indexOf(b.weekday)
    })
    trackNames.value = [...names]
  } catch (e) {
    error.value = '解析计划数据失败'
  }
}

watch(() => props.plan, parsePlan, { immediate: true })

const filteredTasks = computed(() => {
  if (selectedTrack.value === 'all') return tasks.value
  return tasks.value.filter(t => t.trackName === selectedTrack.value)
})

// Group by week for display
const weekGroups = computed(() => {
  const groups = {}
  filteredTasks.value.forEach(t => {
    if (!groups[t.week]) groups[t.week] = []
    groups[t.week].push(t)
  })
  return Object.entries(groups).sort(([a],[b]) => Number(a) - Number(b))
})

function addTask(week) {
  tasks.value.push({
    id: `new-${Date.now()}`,
    trackIdx: 0,
    trackName: trackNames.value[0] || 'Default',
    week: week,
    weekday: '周一',
    time_block: '09:00-10:00',
    title: '',
    metric: '',
    duration_hours: 1,
    type: 'study',
    status: 'todo'
  })
}

function removeTask(taskId) {
  tasks.value = tasks.value.filter(t => t.id !== taskId)
}

async function save() {
  saving.value = true
  error.value = ''
  msg.value = ''
  try {
    const fused = typeof props.plan.fused_plan === 'string'
      ? JSON.parse(props.plan.fused_plan)
      : { ...props.plan.fused_plan }
    
    const trackMap = {}
    tasks.value.forEach(t => {
      if (!trackMap[t.trackName]) trackMap[t.trackName] = []
      trackMap[t.trackName].push({
        week: t.week,
        weekday: t.weekday,
        time_block: t.time_block,
        title: t.title,
        metric: t.metric,
        duration_hours: t.duration_hours,
        type: t.type,
        status: t.status
      })
    })
    
    if (fused.tracks) {
      fused.tracks.forEach(track => {
        const name = track.exam_name
        if (trackMap[name]) {
          track.tasks = trackMap[name]
        }
      })
    }
    
    await updateSchedule(props.planId, {
      schedule_json: JSON.stringify(fused)
    })
    msg.value = '日程已保存'
    setTimeout(() => emit('saved'), 800)
  } catch (e) {
    error.value = e?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>
