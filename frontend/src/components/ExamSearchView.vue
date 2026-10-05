<template>
  <div class="fixed inset-0 z-50 bg-black/60 flex justify-center items-center p-4 sm:p-8">
    <div class="bg-white w-full max-w-4xl max-h-full border-[3px] border-black shadow-[8px_8px_0px_0px_#000] flex flex-col overflow-hidden relative">
      
      <!-- 顶部涂鸦胶带 -->
      <div class="graffiti-tape graffiti-tape-pink">
        SEARCH VERIFICATION PIPELINE
      </div>

      <!-- Header -->
      <div class="px-6 py-4 border-b-[3px] border-black bg-[#FFE600] flex justify-between items-center shrink-0">
        <div>
          <h2 class="text-xl font-black font-neo-title text-black flex items-center gap-2 uppercase">
            <span>🔍</span>
            <span>权威考试情报智能核验</span>
          </h2>
          <p class="text-xs font-black text-neutral-800 mt-1" v-if="school || major || examType">
            {{ school }} · {{ major }} · {{ examType }}
          </p>
        </div>
        <div class="flex items-center gap-3">
          <button 
            @click="doSearch" 
            class="neo-btn bg-white hover:bg-neutral-100 text-black px-4 py-2 text-xs font-black shadow-[2px_2px_0px_0px_#000]"
            :disabled="loading"
          >
            <span v-if="loading" class="animate-spin text-sm">⏳</span>
            <span>{{ loading ? '检索中...' : '重新检索' }}</span>
          </button>
          <button @click="emit('close')" class="neo-badge bg-black text-white cursor-pointer">
            ✕
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-auto p-6 bg-[#FAF7F2] relative">
        <div v-if="loading && !result" class="absolute inset-0 flex flex-col items-center justify-center bg-white/90 z-10">
          <div class="w-12 h-12 border-4 border-black border-t-[#FFE600] animate-spin"></div>
          <p class="mt-4 text-black font-black uppercase font-neo-title text-sm">正在全网智能检索并交叉验证考试信息...</p>
        </div>

        <div v-if="error" class="bg-[#FF3399] text-white p-4 border-2 border-black font-black text-xs shadow-[3px_3px_0px_0px_#000] flex items-center gap-2 mb-6">
          <span>⚠️</span> {{ error }}
        </div>
        
        <div v-if="result" class="space-y-6">
          
          <!-- Sections -->
          <div class="grid gap-5">
            <template v-for="section in [
              { key: 'subjects', title: '📚 考试科目', data: result.subjects },
              { key: 'books', title: '📖 参考书目', data: result.books },
              { key: 'score_lines', title: '📊 分数线', data: result.score_lines },
              { key: 'registration_time', title: '📅 报名时间', data: result.registration_time },
              { key: 'exam_time', title: '📅 考试时间', data: result.exam_time }
            ]" :key="section.key">
              
              <div class="bg-white border-2 border-black shadow-[4px_4px_0px_0px_#000] p-5">
                <div class="flex justify-between items-start mb-3 border-b-2 border-black pb-2">
                  <h3 class="font-black font-neo-title uppercase text-sm text-black">{{ section.title }}</h3>
                  <div v-if="section.data" :class="`neo-badge text-[10px] ${confidenceBadge(section.data).color}`">
                    <span>{{ confidenceBadge(section.data).icon }}</span>
                    <span>{{ confidenceBadge(section.data).label }}</span>
                  </div>
                </div>

                <div v-if="!section.data || !section.data.value && !section.data.conflict_values" class="text-neutral-400 text-xs font-bold italic">
                  未检索到相关信息
                </div>
                
                <div v-else>
                  <!-- Normal display -->
                  <div v-if="section.data.confidence !== 'conflict'">
                    <div class="text-black font-bold whitespace-pre-wrap text-xs leading-relaxed">{{ section.data.value }}</div>
                    <div class="mt-3 flex flex-wrap gap-2" v-if="getSourceUrls(section.data).length">
                      <a v-for="source in getSourceUrls(section.data)" :key="source.id" :href="source.url" target="_blank" class="neo-badge bg-[#CCFF00] text-black text-[10px] hover:underline">
                        🔗 来源 [{{ source.id }}]
                      </a>
                    </div>
                  </div>
                  
                  <!-- Conflict display -->
                  <div v-else class="space-y-3">
                    <div v-for="(conflict, idx) in section.data.conflict_values || [{value: section.data.value, source_ids: section.data.source_ids}]" :key="idx" class="p-3 bg-[#FFE600] border-2 border-black">
                      <div class="text-black font-bold whitespace-pre-wrap text-xs leading-relaxed">{{ conflict.value }}</div>
                      <div class="mt-2 flex flex-wrap gap-2" v-if="conflict.source_ids">
                        <a v-for="id in conflict.source_ids" :key="id" :href="(result.sources?.find(s => s.id === id) || {}).url" target="_blank" class="neo-badge bg-black text-white text-[10px] hover:underline">
                          🔗 来源 [{{ id }}]
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
            </template>
          </div>

          <!-- Sources -->
          <div v-if="result.sources && result.sources.length" class="mt-8">
            <h3 class="font-black font-neo-title uppercase text-base text-black mb-3 flex items-center gap-2">
              <span>📑</span> 引用信息源与可信度
            </h3>
            <div class="bg-white border-2 border-black shadow-[4px_4px_0px_0px_#000] overflow-hidden">
              <ul class="divide-y-2 divide-black/10">
                <li v-for="source in result.sources" :key="source.id" class="p-3.5 hover:bg-[#FFFDE6] transition-colors">
                  <div class="flex items-start gap-3">
                    <span :class="`neo-badge text-[10px] shrink-0 ${trustBadge(source.trust_level).color}`">
                      {{ trustBadge(source.trust_level).label }}
                    </span>
                    <div>
                      <a :href="source.url" target="_blank" class="text-black font-bold hover:underline text-xs break-all">
                        [{{ source.id }}] {{ source.title || source.url }}
                      </a>
                    </div>
                  </div>
                </li>
              </ul>
            </div>
          </div>
          
        </div>
        
        <div v-if="!result && !loading && !error" class="text-center py-16">
          <div class="text-5xl mb-4">🏫</div>
          <p class="font-bold text-neutral-500 mb-6">点击右上角"重新检索"获取最新权威招生信息</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { searchExamInfo } from '../api/client.js'

const props = defineProps({
  examType: { type: String, default: '' },
  school: { type: String, default: '' },
  major: { type: String, default: '' }
})

const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref('')
const result = ref(null)

async function doSearch() {
  if (!props.examType) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const res = await searchExamInfo({
      exam_type: props.examType,
      school: props.school,
      major: props.major
    })
    result.value = res
  } catch (e) {
    error.value = e?.response?.data?.detail || '搜索失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function confidenceBadge(field) {
  if (!field) return { label: '未检索到', color: 'bg-neutral-200 text-black', icon: '🔍' }
  const map = {
    high: { label: '多源验证', color: 'bg-[#CCFF00] text-black', icon: '✅' },
    medium: { label: '建议核实', color: 'bg-[#FFE600] text-black', icon: '⚠️' },
    low: { label: '单一来源', color: 'bg-[#FFA34D] text-black', icon: '⚠️' },
    conflict: { label: '信息冲突', color: 'bg-[#FF3399] text-white', icon: '❌' },
    not_found: { label: '未检索到', color: 'bg-neutral-200 text-black', icon: '🔍' }
  }
  return map[field.confidence] || map.not_found
}

function trustBadge(level) {
  const map = {
    S: { label: '官方权威 S级', color: 'bg-[#CCFF00] text-black' },
    A: { label: '高信社区 A级', color: 'bg-[#00F0FF] text-black' },
    B: { label: '网络参考 B级', color: 'bg-neutral-200 text-black' }
  }
  return map[level] || map.B
}

function getSourceUrls(field) {
  if (!field || !field.source_ids || !result.value?.sources) return []
  return field.source_ids.map(id => result.value.sources.find(s => s.id === id)).filter(Boolean)
}

onMounted(() => {
  doSearch()
})
</script>
