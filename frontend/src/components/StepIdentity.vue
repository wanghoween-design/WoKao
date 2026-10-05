<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  identity: { type: String, default: '' },
  nickname: { type: String, default: '' },
})
const emit = defineEmits(['next'])

const IDENTITIES = [
  { key: '高校在校生', tag: '学生 / 本硕在读', icon: '🎓', desc: '在校在读，拥有相对规律的学习时间与校园自习资源', bg: 'bg-[#FFE600]', tape: 'graffiti-tape-lime', rot: 'sticker-rot-1' },
  { key: '应届毕业生', tag: '应届冲刺', icon: '🏛️', desc: '临近毕业或初入社会，全力以赴备战考研/国考省考/校招', bg: 'bg-[#CCFF00]', tape: 'graffiti-tape-pink', rot: 'sticker-rot-2' },
  { key: '职场在职人', tag: '在职提升', icon: '💼', desc: '工作日碎片化备考，需科学权衡工作负荷与晚间/周末复习', bg: 'bg-[#00F0FF]', tape: 'graffiti-tape-lime', rot: 'sticker-rot-3' },
  { key: '全职备考生', tag: '全职脱产', icon: '⏳', desc: '全天脱产备战，追求极高的执行力、节奏控制与心理稳定', bg: 'bg-[#FF3399]', tape: 'graffiti-tape-cyan', rot: 'sticker-rot-1', textColor: 'text-white' },
  { key: '自由职业者', tag: '灵活时间', icon: '🌿', desc: '时间支配度高，需建立自我约束与周期性模考机制', bg: 'bg-[#B388FF]', tape: 'graffiti-tape-lime', rot: 'sticker-rot-2' },
  { key: '终身学习者', tag: '跨界探索', icon: '📜', desc: '拓展职业技能或兴趣考证，注重知识积累与稳步推进', bg: 'bg-[#FFA34D]', tape: 'graffiti-tape-pink', rot: 'sticker-rot-3' },
]

const selected = ref(props.identity || '')
const name = ref(props.nickname || '')

const canNext = computed(() => !!selected.value)

function pick(k) {
  selected.value = k
}
function submit() {
  if (!canNext.value) return
  emit('next', { identity: selected.value, nickname: name.value.trim() || '考生' })
}
</script>

<template>
  <div>
    <div class="border-b-[3px] border-black pb-4 mb-6">
      <div class="flex items-center gap-2">
        <span class="neo-badge bg-[#FFE600] text-black">STEP 01</span>
        <h2 class="text-xl font-black font-neo-title text-black">
          设定考生背景与作息模式
        </h2>
      </div>
      <p class="text-xs font-bold text-neutral-600 mt-1">
        不同的备考背景决定了 24H 作息分布（如上班族晚间模式 vs 在校全天模式），我们将以此为您生成精准排期。
      </p>
    </div>

    <!-- 粗野主义身份卡片网格 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 mt-4">
      <div
        v-for="it in IDENTITIES"
        :key="it.key"
        @click="pick(it.key)"
        :class="[
          'border-[3px] border-black p-5 cursor-pointer flex flex-col justify-between select-none transition-all relative',
          it.bg,
          it.textColor || 'text-black',
          selected === it.key
            ? 'shadow-[6px_6px_0px_0px_#000000] translate-x-[-2px] translate-y-[-2px] ring-4 ring-black'
            : 'shadow-[4px_4px_0px_0px_#000000] hover:shadow-[6px_6px_0px_0px_#000000] hover:translate-x-[-1px] hover:translate-y-[-1px]',
        ]"
      >
        <!-- 涂鸦胶带 -->
        <div :class="['graffiti-tape', it.tape]">
          {{ it.tag }}
        </div>

        <div>
          <div class="flex items-center justify-between mb-3 pt-2">
            <span class="text-3xl bg-white/40 p-1 border border-black/20">{{ it.icon }}</span>
            <span
              :class="[
                'neo-badge text-[10px]',
                selected === it.key ? 'bg-black text-[#FFE600]' : 'bg-white text-black'
              ]"
            >
              {{ selected === it.key ? '★ CURRENT ★' : 'SELECT' }}
            </span>
          </div>
          <div class="font-black text-lg font-neo-title tracking-tight">
            {{ it.key }}
          </div>
          <div class="text-xs mt-2 leading-relaxed font-bold opacity-90">
            {{ it.desc }}
          </div>
        </div>

        <div class="mt-4 pt-2 border-t-2 border-black/20 flex items-center justify-between text-[11px] font-black">
          <span v-if="selected === it.key" class="bg-black text-[#CCFF00] px-2 py-0.5 border border-black">
            ✓ 已选中该背景
          </span>
          <span v-else class="opacity-70">点击选择此背景 ➔</span>
        </div>
      </div>
    </div>

    <!-- 昵称卡片 -->
    <div class="mt-8 p-5 bg-white border-[3px] border-black shadow-[4px_4px_0px_0px_#000000] max-w-md relative">
      <div class="graffiti-tape graffiti-tape-lime">
        NICKNAME
      </div>
      <label class="block text-xs font-black text-black mb-1.5 uppercase">
        ✍️ 考生称呼 / 自定义昵称 <span class="text-neutral-500 font-bold">（选填）</span>
      </label>
      <input
        v-model="name"
        placeholder="如：林同学 / 考研战神 / 必胜"
        class="neo-input text-sm"
      />
    </div>

    <div class="mt-8 pt-4 border-t-[3px] border-black flex justify-end">
      <button
        @click="submit"
        :disabled="!canNext"
        :class="[
          'neo-btn px-8 py-3.5 text-xs font-black border-[3px]',
          canNext
            ? 'bg-[#FFE600] text-black hover:bg-[#FFF066] shadow-[4px_4px_0px_0px_#000]'
            : 'bg-neutral-200 text-neutral-400 border-neutral-400 cursor-not-allowed shadow-none',
        ]"
      >
        <span>下一步：选择备考目标 ➔</span>
      </button>
    </div>
  </div>
</template>
