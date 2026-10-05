<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { getProfile, updateProfile } from '../api/client.js'

const props = defineProps({
  show: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'saved'])

const form = reactive({
  nickname: '',
  birthday: '',
  school: '',
  major: '',
  current_plan: '',
  target_degree: '硕士研究生 (考研/保研)',
  phone: '',
  bio: '',
  resume_text: '',
})

const DEGREE_OPTIONS = [
  '高校在读本科/专科',
  '应届硕士/博士冲刺',
  '硕士研究生 (考研/保研)',
  '博士研究生 (申请考核/考博)',
  '国家/地方公务员 (国考/省考)',
  '事业单位与军队文职',
  '教师资格证与教招编制',
  '法律职业资格考试 (法考)',
  '注册会计师 (CPA/经济师)',
  '跨界学习与技能考证',
]

const loading = ref(false)
const saving = ref(false)
const msg = ref('')
const error = ref('')

async function loadData() {
  loading.value = true
  error.value = ''
  msg.value = ''
  try {
    const data = await getProfile()
    if (data) {
      form.nickname = data.nickname || ''
      form.birthday = data.birthday || ''
      form.school = data.school || ''
      form.major = data.major || ''
      form.current_plan = data.current_plan || ''
      form.target_degree = data.target_degree || '硕士研究生 (考研/保研)'
      form.phone = data.phone || ''
      form.bio = data.bio || ''
      form.resume_text = data.resume_text || ''
    }
  } catch (e) {
    error.value = '加载个人档案失败：' + (e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

watch(() => props.show, (val) => {
  if (val) loadData()
})

onMounted(() => {
  if (props.show) loadData()
})

async function doSave() {
  saving.value = true
  error.value = ''
  msg.value = ''
  try {
    const res = await updateProfile({ ...form })
    msg.value = '✓ 个人档案信息已成功保存并同步！'
    emit('saved', res.profile || form)
    setTimeout(() => {
      emit('close')
    }, 1000)
  } catch (e) {
    error.value = '保存档案失败：' + (e?.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
    <div class="bg-white border-[3px] border-black shadow-[8px_8px_0px_0px_#000] w-full max-w-2xl overflow-hidden relative">
      <!-- 顶部涂鸦胶带 -->
      <div class="graffiti-tape graffiti-tape-lime">
        USER PROFILE ARCHIVE
      </div>

      <!-- 弹窗顶栏 -->
      <div class="bg-black text-white px-6 py-4 flex items-center justify-between border-b-[3px] border-black">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-[#FFE600] text-black border-2 border-black flex items-center justify-center text-lg font-black shadow-[2px_2px_0px_0px_#fff]">
            👤
          </div>
          <div>
            <h3 class="text-base font-black font-neo-title uppercase text-[#FFE600]">完善考生个人信息档案</h3>
            <p class="text-xs font-bold text-neutral-400">丰富画像数据 · 深度匹配备考计划与导师分析</p>
          </div>
        </div>
        <button @click="emit('close')" class="neo-badge bg-[#FF3399] text-white cursor-pointer">✕</button>
      </div>

      <!-- 内容主体 -->
      <div class="p-6 space-y-5 bg-[#FAF7F2] max-h-[75vh] overflow-y-auto">
        <!-- 基础信息行 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-black uppercase text-black mb-1">
              ✍️ 考生称呼 / 昵称
            </label>
            <input
              v-model="form.nickname"
              type="text"
              placeholder="如：林同学 / 考研战神"
              class="neo-input text-sm"
            />
          </div>

          <div>
            <label class="block text-xs font-black uppercase text-black mb-1">
              🎂 出生日期 (生日)
            </label>
            <input
              v-model="form.birthday"
              type="date"
              class="neo-input text-sm font-mono cursor-pointer"
            />
          </div>
        </div>

        <!-- 院校与专业行 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-black uppercase text-black mb-1">
              🏛️ 毕业 / 在读院校
            </label>
            <input
              v-model="form.school"
              type="text"
              placeholder="如：吉林大学 / 东北师范大学"
              class="neo-input text-sm"
            />
          </div>

          <div>
            <label class="block text-xs font-black uppercase text-black mb-1">
              📚 专业名称 / 方向
            </label>
            <input
              v-model="form.major"
              type="text"
              placeholder="如：计算机科学与技术 / 法学"
              class="neo-input text-sm"
            />
          </div>
        </div>

        <!-- 目标层次与联系方式 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-black uppercase text-black mb-1">
              🎓 目标备考层次
            </label>
            <select
              v-model="form.target_degree"
              class="neo-input text-sm cursor-pointer"
            >
              <option v-for="d in DEGREE_OPTIONS" :key="d" :value="d">
                {{ d }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-black uppercase text-black mb-1">
              📱 联系方式 / 邮箱 (选填)
            </label>
            <input
              v-model="form.phone"
              type="text"
              placeholder="用于日程备份与重要考期提醒"
              class="neo-input text-sm font-mono"
            />
          </div>
        </div>

        <!-- 目前备考计划与目标方向 -->
        <div>
          <label class="block text-xs font-black uppercase text-black mb-1">
            🎯 目前备考计划与主攻方向
          </label>
          <input
            v-model="form.current_plan"
            type="text"
            placeholder="如：2026年秋季申博申请考核 + 年底国考综合管理岗协同"
            class="neo-input text-sm"
          />
        </div>

        <!-- 备考座右铭 -->
        <div>
          <label class="block text-xs font-black uppercase text-black mb-1">
            💬 备考宣言 / 个人座右铭
          </label>
          <input
            v-model="form.bio"
            type="text"
            placeholder="如：行百里者半九十，坚持到最后一刻！"
            class="neo-input text-sm font-bold"
          />
        </div>

        <!-- 个人简历文本 -->
        <div class="p-4 bg-white border-2 border-black shadow-[3px_3px_0px_0px_#000]">
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-xs font-black uppercase text-black font-neo-title flex items-center gap-1.5">
              <span>📋</span> 详细个人简历 / 备考背景（纯文本）
            </label>
            <span class="text-[11px] font-mono font-bold text-neutral-500">{{ form.resume_text.length }} 字</span>
          </div>
          <p class="text-xs font-bold text-neutral-500 mb-2">
            包含学术科研成果、四六级/考级分数、实习经历等，AI 伴学导师将据此给出超高精准度的复习指导。
          </p>
          <textarea
            v-model="form.resume_text"
            rows="5"
            placeholder="粘贴简历正文，如：
1. 教育背景：某大学 计算机本科（GPA 3.8/4.0）
2. 英语水平：CET-6 580分，雅思 7.0
3. 科研/竞赛：发表 CCF-B 论文一篇，国家级奖学金..."
            class="neo-input text-xs leading-relaxed"
          ></textarea>
        </div>

        <!-- 提示信息 -->
        <div v-if="msg" class="p-3 bg-[#CCFF00] border-2 border-black text-black font-black text-xs shadow-[2px_2px_0px_0px_#000]">
          {{ msg }}
        </div>
        <div v-if="error" class="p-3 bg-[#FF3399] border-2 border-black text-white font-black text-xs shadow-[2px_2px_0px_0px_#000]">
          ⚠️ {{ error }}
        </div>

        <!-- 底部保存按钮 -->
        <div class="pt-3 border-t-2 border-black flex items-center justify-between gap-3">
          <button
            type="button"
            @click="emit('close')"
            class="neo-btn bg-white hover:bg-neutral-100 text-black px-5 py-2.5 text-xs font-black"
          >
            取消
          </button>

          <button
            type="button"
            @click="doSave"
            :disabled="saving"
            class="neo-btn bg-[#FFE600] hover:bg-[#FFF066] text-black px-7 py-2.5 text-xs font-black border-[3px] shadow-[3px_3px_0px_0px_#000]"
          >
            <span v-if="saving" class="animate-spin text-sm">⏳</span>
            <span>{{ saving ? '保存中…' : '💾 保存个人档案 ➔' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
