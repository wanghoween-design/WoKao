<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { getUserLLMConfig, saveUserLLMConfig, deleteUserLLMConfig, testUserLLMConfig } from '../api/client.js'

const props = defineProps({
  show: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'saved'])

// 服务商预置列表
const PROVIDERS = [
  {
    id: 'deepseek',
    name: 'DeepSeek (深度求索)',
    baseUrl: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat', 'deepseek-reasoner'],
    hint: '支持 deepseek-chat (V3) 与 deepseek-reasoner (R1 推理模型)'
  },
  {
    id: 'dashscope',
    name: '阿里云通义千问 / 百炼 (DashScope)',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-plus', 'qwen-max', 'qwen-turbo'],
    hint: '推荐使用通义千问 qwen-plus 或 qwen-max'
  },
  {
    id: 'zhipu',
    name: '智谱 AI / 清言 GLM',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-4-flash', 'glm-4-plus'],
    hint: '支持 glm-4-flash (高速) 与 glm-4-plus'
  },
  {
    id: 'siliconflow',
    name: '硅基流动 (SiliconFlow)',
    baseUrl: 'https://api.siliconflow.cn/v1',
    models: ['Qwen/Qwen2.5-7B-Instruct', 'deepseek-ai/DeepSeek-V3', 'deepseek-ai/DeepSeek-R1'],
    hint: '全托管开源大模型 API 平台'
  },
  {
    id: 'openai',
    name: 'OpenAI 官方',
    baseUrl: 'https://api.openai.com/v1',
    models: ['gpt-4o-mini', 'gpt-4o'],
    hint: '需国际网络环境与 OpenAI API Key'
  },
  {
    id: 'custom',
    name: '自定义 OpenAI 兼容 API (Ollama / OneAPI 等)',
    baseUrl: '',
    models: ['gpt-4o-mini', 'deepseek-chat', 'qwen-plus'],
    hint: '支持填写任何兼容 OpenAI 接口协议的服务地址'
  }
]

const form = reactive({
  provider: 'deepseek',
  model_name: 'deepseek-chat',
  api_key: '',
  base_url: 'https://api.deepseek.com/v1',
  is_active: 1
})

const showPassword = ref(false)
const isConfigured = ref(false)
const maskedKey = ref('')
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const msg = ref('')
const error = ref('')

function onProviderChange() {
  const p = PROVIDERS.find(item => item.id === form.provider)
  if (p) {
    if (p.baseUrl) form.base_url = p.baseUrl
    if (p.models && p.models.length > 0 && !p.models.includes(form.model_name)) {
      form.model_name = p.models[0]
    }
  }
  testResult.value = null
  error.value = ''
}

function selectModel(m) {
  form.model_name = m
}

async function loadConfig() {
  loading.value = true
  error.value = ''
  msg.value = ''
  testResult.value = null
  try {
    const data = await getUserLLMConfig()
    if (data.configured && data.config) {
      isConfigured.value = true
      form.provider = data.config.provider || 'custom'
      form.model_name = data.config.model_name || ''
      form.base_url = data.config.base_url || ''
      form.is_active = data.config.is_active !== undefined ? data.config.is_active : 1
      maskedKey.value = data.config.api_key_masked || ''
      form.api_key = ''
    } else {
      isConfigured.value = false
      maskedKey.value = ''
      form.provider = 'deepseek'
      onProviderChange()
    }
  } catch (e) {
    // 加载失败按未配置处理，用户可重新填写保存
  } finally {
    loading.value = false
  }
}

watch(() => props.show, (val) => {
  if (val) loadConfig()
})

onMounted(() => {
  if (props.show) loadConfig()
})

function cleanBaseUrl(url) {
  if (!url) return ''
  return url.trim().replace(/\/chat\/completions\/?$/i, '').replace(/\/+$/, '')
}

async function doTest() {
  if (!form.api_key.trim() && !maskedKey.value) {
    error.value = '请先输入 API Key 再进行测试'
    return
  }
  if (!form.model_name.trim()) {
    error.value = '请先输入模型名称'
    return
  }
  testing.value = true
  testResult.value = null
  error.value = ''
  msg.value = ''

  const cleanedUrl = cleanBaseUrl(form.base_url)
  form.base_url = cleanedUrl

  try {
    const res = await testUserLLMConfig({
      provider: form.provider,
      model_name: form.model_name.trim(),
      api_key: form.api_key.trim() || maskedKey.value,
      base_url: cleanedUrl
    })
    testResult.value = res
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.response?.data?.msg || '连接失败，请检查 Base URL 与 API 密钥'
    testResult.value = {
      success: false,
      detail: typeof detail === 'object' ? JSON.stringify(detail) : String(detail)
    }
  } finally {
    testing.value = false
  }
}

async function doSave() {
  if (!form.api_key.trim() && !isConfigured.value) {
    error.value = 'API 密钥 (API Key) 不能为空'
    return
  }
  if (!form.model_name.trim()) {
    error.value = '模型名称 (Model Name) 不能为空'
    return
  }
  saving.value = true
  error.value = ''
  msg.value = ''

  const cleanedUrl = cleanBaseUrl(form.base_url)
  form.base_url = cleanedUrl

  try {
    await saveUserLLMConfig({
      provider: form.provider,
      model_name: form.model_name.trim(),
      api_key: form.api_key.trim() || maskedKey.value,
      base_url: cleanedUrl,
      is_active: form.is_active
    })
    msg.value = '✓ 模型配置已成功保存并立即生效'
    emit('saved', {
      configured: true,
      provider: form.provider,
      model_name: form.model_name.trim()
    })
    setTimeout(() => {
      emit('close')
    }, 1000)
  } catch (e) {
    error.value = e?.response?.data?.detail || '保存配置失败'
  } finally {
    saving.value = false
  }
}

async function doReset() {
  if (!confirm('确定要恢复系统全局默认模型吗？此操作将清除您当前账号保存的 API 密钥。')) return
  saving.value = true
  error.value = ''
  msg.value = ''
  try {
    await deleteUserLLMConfig()
    msg.value = '✓ 已恢复系统全局默认配置'
    isConfigured.value = false
    maskedKey.value = ''
    form.api_key = ''
    emit('saved', { configured: false })
    setTimeout(() => {
      emit('close')
    }, 1000)
  } catch (e) {
    error.value = e?.response?.data?.detail || '重置失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
    <div class="bg-white border-[3px] border-black shadow-[8px_8px_0px_0px_#000] w-full max-w-xl overflow-hidden relative">
      <!-- 顶部涂鸦胶带 -->
      <div class="graffiti-tape graffiti-tape-lime">
        BYOK LLM CONFIGURATION
      </div>

      <!-- 弹窗顶栏 -->
      <div class="bg-black text-white px-6 py-4 flex items-center justify-between border-b-[3px] border-black">
        <div class="flex items-center gap-2.5">
          <span class="text-2xl font-black">⚙️</span>
          <div>
            <h3 class="text-base font-black font-neo-title uppercase text-[#FFE600]">自定义大模型与 API 配置</h3>
            <p class="text-xs font-bold text-neutral-400">Bring Your Own Key (BYOK) · 独立账号隔离存储</p>
          </div>
        </div>
        <button @click="emit('close')" class="neo-badge bg-[#FF3399] text-white cursor-pointer">✕</button>
      </div>

      <!-- 内容主体 -->
      <div class="p-6 space-y-5 bg-[#FAF7F2]">
        <!-- 账号物理隔离安全提示 -->
        <div class="p-3.5 bg-[#FFFDE6] border-2 border-black flex items-start gap-2.5 text-xs text-black shadow-[3px_3px_0px_0px_#000]">
          <span class="text-base shrink-0">🔒</span>
          <div class="font-bold">
            <span class="font-black bg-[#FFE600] px-1">严格物理隔离：</span>您的 API Key 与接口配置仅与当前账号绑定，加密存储，其他用户绝对无法查看或调用您的密钥。
          </div>
        </div>

        <!-- 1. 服务商选择 -->
        <div>
          <label class="block text-xs font-black uppercase text-black mb-1.5">选择模型服务商 (Provider)</label>
          <select 
            v-model="form.provider" 
            @change="onProviderChange"
            class="neo-input text-sm cursor-pointer"
          >
            <option v-for="p in PROVIDERS" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
          <p class="text-[11px] font-bold text-neutral-500 mt-1">
            {{ PROVIDERS.find(p => p.id === form.provider)?.hint }}
          </p>
        </div>

        <!-- 2. Base URL -->
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-xs font-black uppercase text-black">接口基地址 (Base URL)</label>
            <span class="text-[11px] font-bold text-neutral-500">须兼容 OpenAI 格式</span>
          </div>
          <input 
            v-model="form.base_url" 
            type="text" 
            placeholder="例如：https://api.deepseek.com/v1"
            class="neo-input text-sm font-mono"
          />
        </div>

        <!-- 3. API Key -->
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-xs font-black uppercase text-black">API 密钥 (API Key)</label>
            <span v-if="isConfigured && maskedKey" class="neo-badge bg-[#CCFF00] text-black text-[10px]">
              已保存：<span class="font-mono">{{ maskedKey }}</span>
            </span>
          </div>
          <div class="relative">
            <input 
              v-model="form.api_key" 
              :type="showPassword ? 'text' : 'password'" 
              :placeholder="isConfigured ? '留空表示沿用已保存的密钥，输入新内容则更新' : '粘贴您的 sk-****** 密钥'"
              class="neo-input text-sm font-mono pr-16"
            />
            <button 
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-2.5 top-2.5 neo-badge bg-black text-white text-[10px] cursor-pointer"
            >
              {{ showPassword ? '🙈 隐藏' : '👁️ 显示' }}
            </button>
          </div>
        </div>

        <!-- 4. 模型名称 -->
        <div>
          <label class="block text-xs font-black uppercase text-black mb-1.5">模型标识 (Model Name)</label>
          <input 
            v-model="form.model_name" 
            type="text" 
            placeholder="例如：deepseek-chat 或 qwen-plus"
            class="neo-input text-sm font-mono"
          />
          <!-- 快捷推荐标签 -->
          <div class="flex flex-wrap items-center gap-1.5 mt-2">
            <span class="text-[11px] font-black text-neutral-500">常用模型：</span>
            <button
              v-for="m in PROVIDERS.find(p => p.id === form.provider)?.models || []"
              :key="m"
              type="button"
              @click="selectModel(m)"
              :class="[
                'px-2 py-0.5 text-[11px] font-mono font-bold transition cursor-pointer border-2',
                form.model_name === m
                  ? 'bg-[#FFE600] border-black text-black shadow-[2px_2px_0px_0px_#000]'
                  : 'bg-white border-black text-black hover:bg-[#FFFDE6]'
              ]"
            >
              {{ m }}
            </button>
          </div>
        </div>

        <!-- 测试连通性结果反馈 -->
        <div v-if="testResult" :class="[
          'p-3.5 border-2 border-black text-xs font-bold shadow-[3px_3px_0px_0px_#000]',
          testResult.success ? 'bg-[#CCFF00] text-black' : 'bg-[#FF3399] text-white'
        ]">
          <div class="font-black flex items-center gap-1.5 mb-1">
            <span>{{ testResult.success ? '✅ 接口连通测试成功！' : '❌ 接口连通失败' }}</span>
            <span v-if="testResult.latency_ms" class="neo-badge bg-black text-white text-[10px]">
              延时：{{ testResult.latency_ms }}ms
            </span>
          </div>
          <div v-if="testResult.reply" class="text-[11px] mt-1 font-mono bg-black/10 p-1 border border-black/20">
            模型回复：{{ testResult.reply }}
          </div>
          <div v-if="testResult.detail" class="text-[11px] mt-1 opacity-90">
            {{ testResult.detail }}
          </div>
        </div>

        <!-- 提示信息 -->
        <div v-if="msg" class="p-3 bg-[#CCFF00] border-2 border-black text-black font-black text-xs shadow-[2px_2px_0px_0px_#000]">
          {{ msg }}
        </div>
        <div v-if="error" class="p-3 bg-[#FF3399] border-2 border-black text-white font-black text-xs shadow-[2px_2px_0px_0px_#000]">
          ⚠️ {{ error }}
        </div>

        <!-- 底部按钮操作栏 -->
        <div class="pt-4 border-t-2 border-black flex items-center justify-between gap-3">
          <button
            v-if="isConfigured"
            type="button"
            @click="doReset"
            :disabled="saving || testing"
            class="neo-btn bg-[#FF3399] hover:bg-[#F43F5E] text-white text-xs px-3.5 py-2 font-black shadow-[2px_2px_0px_0px_#000]"
          >
            恢复默认
          </button>
          <div v-else></div>

          <div class="flex items-center gap-2.5">
            <button
              type="button"
              @click="doTest"
              :disabled="testing || saving"
              class="neo-btn bg-[#00F0FF] hover:bg-[#80F8FF] text-black text-xs px-4 py-2 font-black shadow-[2px_2px_0px_0px_#000]"
            >
              <span v-if="testing" class="animate-spin text-sm">⏳</span>
              <span>{{ testing ? '测试中…' : '🧪 测试连通性' }}</span>
            </button>
            <button
              type="button"
              @click="doSave"
              :disabled="saving || testing"
              class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black text-xs px-5 py-2 font-black border-[3px] shadow-[3px_3px_0px_0px_#000]"
            >
              <span v-if="saving" class="animate-spin text-sm">⏳</span>
              <span>{{ saving ? '保存中…' : '💾 保存并生效' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
