<script setup>
import { ref } from 'vue'
import { registerUser, loginUser } from '../api/client.js'

const emit = defineEmits(['authed'])
const mode = ref('login') // login | register
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  const name = username.value.trim()
  if (!name || !password.value) {
    error.value = '请输入考生标识（用户名）与密码凭据'
    return
  }
  if (mode.value === 'register' && password.value.length < 6) {
    error.value = '为保障档案安全，密码请至少设置 6 位'
    return
  }
  loading.value = true
  try {
    const fn = mode.value === 'register' ? registerUser : loginUser
    const d = await fn({ username: name, password: password.value })
    emit('authed', d)
  } catch (e) {
    const detail = (e.response && e.response.data && e.response.data.detail) || e.message || '操作失败'
    if (mode.value === 'register' && /已被注册|已存在|已占用/i.test(detail)) {
      error.value = '该考生标识已存在，已自动切换至「登录」，请输入密码直接登录。'
      switchMode('login')
    } else {
      error.value = detail
    }
  } finally {
    loading.value = false
  }
}

function switchMode(m) {
  mode.value = m
  error.value = ''
}
</script>

<template>
  <div class="min-h-[78vh] flex items-center justify-center p-4">
    <!-- 新粗野主义与涂鸦街头登录海报卡片 -->
    <div class="w-full max-w-md bg-white border-[3px] border-black shadow-[8px_8px_0px_0px_#000000] p-8 sm:p-10 relative rotate-[-0.5deg]">
      <!-- 顶部涂鸦荧光胶带标签 -->
      <div class="graffiti-tape graffiti-tape-lime">
        ★ AUTHENTICATION PORTAL ★
      </div>

      <div class="text-center mb-7 pt-2">
        <div class="w-14 h-14 mx-auto bg-[#FFE600] border-2 border-black text-2xl font-black flex items-center justify-center shadow-[3px_3px_0px_0px_#000000] transform -rotate-3">
          ⚡
        </div>
        <h2 class="text-2xl font-black font-neo-title text-black mt-3 tracking-tight">
          我考 · WO KAO !
        </h2>
        <p class="text-xs font-bold text-black/70 mt-1">
          多目标协同融合 · 24H 涂鸦作息手帐 · AI 伴学导师
        </p>
      </div>

      <!-- 模式切换粗野标签 -->
      <div class="grid grid-cols-2 gap-2 mb-6 p-1 bg-[#FAF7F2] border-2 border-black shadow-[2px_2px_0px_0px_#000000]">
        <button
          @click="switchMode('login')"
          :class="[
            'py-2 text-xs font-black uppercase transition-all cursor-pointer border-2',
            mode === 'login' ? 'bg-[#FFE600] text-black border-black shadow-[2px_2px_0px_0px_#000]' : 'bg-transparent text-black/70 border-transparent hover:text-black',
          ]"
        >
          📌 考生登录
        </button>
        <button
          @click="switchMode('register')"
          :class="[
            'py-2 text-xs font-black uppercase transition-all cursor-pointer border-2',
            mode === 'register' ? 'bg-[#00F0FF] text-black border-black shadow-[2px_2px_0px_0px_#000]' : 'bg-transparent text-black/70 border-transparent hover:text-black',
          ]"
        >
          ✨ 新考生注册
        </button>
      </div>

      <!-- 表单输入区 -->
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-black text-black mb-1 uppercase tracking-wide">
            考生标识 / 用户名
          </label>
          <input
            v-model="username"
            @keydown.enter="submit"
            placeholder="输入用户名（如：kaoyan2026）"
            class="neo-input text-sm"
          />
        </div>

        <div>
          <label class="block text-xs font-black text-black mb-1 uppercase tracking-wide">
            安全凭据 / 密码
          </label>
          <input
            v-model="password"
            type="password"
            @keydown.enter="submit"
            placeholder="输入密码（不少于 6 位）"
            class="neo-input text-sm"
          />
        </div>

        <div v-if="error" class="p-3 bg-[#FF3399] text-white border-2 border-black text-xs font-black shadow-[2px_2px_0px_0px_#000000]">
          💥 {{ error }}
        </div>

        <button
          @click="submit"
          :disabled="loading"
          class="neo-btn bg-[#FFE600] text-black hover:bg-[#FFF066] w-full py-3.5 text-sm font-black border-[3px] shadow-[4px_4px_0px_0px_#000000] mt-2"
        >
          <span v-if="loading" class="animate-spin text-base">⏳</span>
          <span>{{ loading ? '连接档案库中…' : (mode === 'login' ? '登录并进入备考手帐 ➔' : '立即创建档案开启规划 ➔') }}</span>
        </button>
      </div>

      <!-- 底部提示 -->
      <div class="mt-6 pt-4 border-t-2 border-dashed border-black text-center">
        <p class="text-[11px] font-bold text-black/60">
          🔒 提示：支持考生多账号物理隔离与各自主机/云端大模型接入
        </p>
      </div>
    </div>
  </div>
</template>
