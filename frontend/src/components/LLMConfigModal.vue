<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { getUserLLMConfig, saveUserLLMConfig, activateUserLLMConfig, deleteUserLLMConfig, testUserLLMConfig } from '../api/client.js'

const props = defineProps({
  show: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'saved'])

// 服务商预置列表：baseUrl 自动填充，keyUrl 是申请密钥的入口
const PROVIDERS = [
  {
    id: 'deepseek',
    name: 'DeepSeek (深度求索)',
    baseUrl: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat', 'deepseek-reasoner'],
    keyUrl: 'https://platform.deepseek.com',
    hint: 'deepseek-chat (V3) 与 deepseek-reasoner (R1 推理模型)'
  },
  {
    id: 'dashscope',
    name: '通义千问 Qwen (阿里云百炼)',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-plus', 'qwen-max', 'qwen-turbo'],
    keyUrl: 'https://bailian.console.aliyun.com',
    hint: '阿里云百炼开通「模型服务」后即可调用'
  },
  {
    id: 'zhipu',
    name: '智谱 GLM',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-5.2', 'glm-4-flash', 'glm-4-plus'],
    keyUrl: 'https://open.bigmodel.cn',
    hint: 'glm-4-flash 免费额度较多，适合先试水'
  },
  {
    id: 'doubao',
    name: '豆包 (火山方舟 Ark)',
    baseUrl: 'https://ark.cn-beijing.volces.com/api/v3',
    models: ['doubao-seed-1.6', 'doubao-1.5-pro-32k'],
    keyUrl: 'https://console.volcengine.com/ark',
    hint: '填模型名或你的推理接入点 ID (ep-开头)；Key 在火山方舟控制台申请'
  },
  {
    id: 'siliconflow',
    name: '硅基流动 (SiliconFlow)',
    baseUrl: 'https://api.siliconflow.cn/v1',
    models: ['Qwen/Qwen2.5-7B-Instruct', 'deepseek-ai/DeepSeek-V3', 'deepseek-ai/DeepSeek-R1'],
    keyUrl: 'https://cloud.siliconflow.cn',
    hint: '开源模型聚合平台，部分小模型免费'
  },
  {
    id: 'openai',
    name: 'OpenAI 官方',
    baseUrl: 'https://api.openai.com/v1',
    models: ['gpt-4o-mini', 'gpt-4o'],
    keyUrl: 'https://platform.openai.com',
    hint: '需国际网络环境与 OpenAI API Key'
  },
  {
    id: 'custom',
    name: '自定义 OpenAI 兼容接口 (Ollama / OneAPI 等)',
    baseUrl: '',
    models: ['gpt-4o-mini', 'deepseek-chat', 'qwen-plus'],
    keyUrl: '',
    hint: '任何兼容 OpenAI 接口协议的服务地址都可以'
  }
]

const form = reactive({
  name: '',
  provider: 'deepseek',
  model_name: 'deepseek-chat',
  api_key: '',
  base_url: 'https://api.deepseek.com/v1',
  is_active: 1
})

const showPassword = ref(false)
const isConfigured = ref(false)
const maskedKey = ref('')
const configs = ref([])          // 已保存的全部配置（脱敏）
const editingName = ref('')      // 非空 = 正在编辑这套已有配置
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const msg = ref('')
const error = ref('')

function providerOf(id) {
  return PROVIDERS.find(item => item.id === id)
}

function onProviderChange() {
  const p = providerOf(form.provider)
  if (p) {
    if (p.baseUrl) form.base_url = p.baseUrl
    if (p.models && p.models.length > 0 && !p.models.includes(form.model_name)) {
      form.model_name = p.models[0]
    }
    // 新建时配置名跟随服务商；编辑已有配置时保持原名
    if (!editingName.value && !form.name.trim()) {
      form.name = p.name.split(' (')[0]
    }
  }
  testResult.value = null
  error.value = ''
}

function selectModel(m) {
  form.model_name = m
}

function resetForm() {
  editingName.value = ''
  form.name = ''
  form.provider = 'deepseek'
  form.model_name = 'deepseek-chat'
  form.api_key = ''
  form.base_url = 'https://api.deepseek.com/v1'
  form.is_active = 1
  maskedKey.value = ''
  isConfigured.value = false
  testResult.value = null
}

function applyConfigToForm(cfg) {
  editingName.value = cfg.name
  form.name = cfg.name
  form.provider = cfg.provider || 'custom'
  form.model_name = cfg.model_name || ''
  form.base_url = cfg.base_url || ''
  form.api_key = ''
  maskedKey.value = cfg.api_key_masked || ''
  isConfigured.value = true
  testResult.value = null
  error.value = ''
  msg.value = ''
}

async function loadConfig() {
  loading.value = true
  error.value = ''
  msg.value = ''
  testResult.value = null
  try {
    const data = await getUserLLMConfig()
    configs.value = data.configs || []
    if (data.configured && data.config) {
      applyConfigToForm(data.config)
    } else {
      resetForm()
    }
  } catch (e) {
    // 加载失败按未配置处理，用户可重新填写保存
    resetForm()
  } finally {
    loading.value = false
  }
}

async function doActivate(name) {
  error.value = ''
  msg.value = ''
  try {
    const res = await activateUserLLMConfig(name)
    configs.value = res.configs || []
    const active = (res.configs || []).find(c => c.is_active)
    if (active) applyConfigToForm(active)
    msg.value = `✓ 已切换到「${name}」，即刻生效`
    emit('saved', { configured: true, name: active?.name, model_name: active?.model_name })
  } catch (e) {
    error.value = e?.response?.data?.detail || '切换失败'
  }
}

async function doDeleteOne(name) {
  if (!confirm(`确定删除配置「${name}」吗？其 API Key 将一并清除。`)) return
  error.value = ''
  msg.value = ''
  try {
    const res = await deleteUserLLMConfig(name)
    configs.value = res.configs || []
    if (editingName.value === name) resetForm()
    const active = (res.configs || []).find(c => c.is_active)
    if (active) applyConfigToForm(active)
    else resetForm()
    msg.value = `✓ 已删除「${name}」`
    emit('saved', { configured: configs.value.length > 0 })
  } catch (e) {
    error.value = e?.response?.data?.detail || '删除失败'
  }
}

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
  if (!form.api_key.trim() && !maskedKey.value) {
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
  const name = form.name.trim() || (providerOf(form.provider)?.name.split(' (')[0] + '·' + form.model_name.trim())

  try {
    const res = await saveUserLLMConfig({
      name,
      provider: form.provider,
      model_name: form.model_name.trim(),
      api_key: form.api_key.trim() || maskedKey.value,
      base_url: cleanedUrl,
      is_active: 1
    })
    configs.value = res.configs || []
    editingName.value = name
    form.name = name
    maskedKey.value = (res.configs || []).find(c => c.name === name)?.api_key_masked || ''
    form.api_key = ''
    msg.value = '✓ 配置已保存并启用。额度用完时，可回来一键切换另一套。'
    const active = (res.configs || []).find(c => c.is_active)
    emit('saved', { configured: true, name, model_name: active?.model_name })
  } catch (e) {
    error.value = e?.response?.data?.detail || '保存配置失败'
  } finally {
    saving.value = false
  }
}

async function doReset() {
  if (!confirm('确定清空全部已保存的模型配置吗？所有 API Key 将被删除，回到系统默认模型。')) return
  saving.value = true
  error.value = ''
  msg.value = ''
  try {
    await deleteUserLLMConfig()
    configs.value = []
    resetForm()
    msg.value = '✓ 已清空全部配置，恢复系统默认'
    emit('saved', { configured: false })
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
            <p class="text-xs font-bold text-neutral-400">可保存多套配置，额度用完一键切换</p>
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
            <span class="font-black bg-[#FFE600] px-1">严格物理隔离：</span>您的 API Key 与接口配置仅与当前账号绑定，加密存储，其他用户无法查看或调用。
          </div>
        </div>

        <!-- 已保存配置列表 -->
        <div v-if="configs.length > 0">
          <label class="block text-xs font-black uppercase text-black mb-1.5">已保存配置（点「启用」即时切换）</label>
          <div class="space-y-2">
            <div
              v-for="c in configs"
              :key="c.name"
              :class="[
                'p-3 border-2 flex items-center justify-between gap-2',
                c.is_active ? 'bg-[#FFFDE6] border-black shadow-[3px_3px_0px_0px_#000]' : 'bg-white border-black'
              ]"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="text-xs font-black text-black truncate">{{ c.name }}</span>
                  <span v-if="c.is_active" class="neo-badge bg-[#CCFF00] text-black text-[10px] shrink-0">✓ 使用中</span>
                </div>
                <div class="text-[11px] font-bold text-neutral-500 font-mono truncate">
                  {{ c.model_name }} · {{ c.base_url || '默认端点' }} · Key {{ c.api_key_masked }}
                </div>
              </div>
              <div class="flex items-center gap-1.5 shrink-0">
                <button
                  v-if="!c.is_active"
                  type="button"
                  @click="doActivate(c.name)"
                  class="neo-btn bg-[#CCFF00] text-black text-[11px] px-2 py-1 font-black border-2"
                >启用</button>
                <button
                  type="button"
                  @click="applyConfigToForm(c)"
                  class="neo-btn bg-white text-black text-[11px] px-2 py-1 font-black border-2"
                >编辑</button>
                <button
                  type="button"
                  @click="doDeleteOne(c.name)"
                  class="neo-btn bg-[#FF3399] text-white text-[11px] px-2 py-1 font-black border-2"
                >删除</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 1. 配置名称 -->
        <div>
          <label class="block text-xs font-black uppercase text-black mb-1.5">
            配置名称 (Name)
            <span class="text-neutral-500 normal-case font-bold">—— 建议按用途起名，如「DeepSeek 主力」「GLM 备用」</span>
          </label>
          <input
            v-model="form.name"
            type="text"
            :placeholder="editingName ? '保持原名即覆盖保存' : '留空则自动以 服务商·模型 命名'"
            class="neo-input text-sm"
          />
        </div>

        <!-- 2. 服务商选择 -->
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
            {{ providerOf(form.provider)?.hint }}
            <a
              v-if="providerOf(form.provider)?.keyUrl"
              :href="providerOf(form.provider)?.keyUrl"
              target="_blank"
              rel="noopener"
              class="text-black underline font-black ml-1"
            >未申请 Key？去开放平台申请 ↗</a>
          </p>
        </div>

        <!-- 3. Base URL -->
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

        <!-- 4. API Key -->
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-xs font-black uppercase text-black">API 密钥 (API Key)</label>
            <span v-if="maskedKey" class="neo-badge bg-[#CCFF00] text-black text-[10px]">
              已保存：<span class="font-mono">{{ maskedKey }}</span>
            </span>
          </div>
          <div class="relative">
            <input
              v-model="form.api_key"
              :type="showPassword ? 'text' : 'password'"
              :placeholder="maskedKey ? '留空表示沿用已保存的密钥，输入新内容则更新' : '粘贴您的 sk-****** 密钥'"
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

        <!-- 5. 模型名称 -->
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
              v-for="m in providerOf(form.provider)?.models || []"
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
            v-if="configs.length > 0"
            type="button"
            @click="doReset"
            :disabled="saving || testing"
            class="neo-btn bg-[#FF3399] hover:bg-[#F43F5E] text-white text-xs px-3.5 py-2 font-black shadow-[2px_2px_0px_0px_#000]"
          >
            清空全部
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
              <span>{{ saving ? '保存中…' : '💾 保存并启用' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
