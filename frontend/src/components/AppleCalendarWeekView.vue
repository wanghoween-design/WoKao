<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  fused: { type: Object, default: () => ({ tracks: [] }) },
  selectedWeek: { type: [Number, String], default: 1 },
  selectedTrack: { type: String, default: 'all' },
  checkedMap: { type: Object, default: () => ({}) },
  planCreatedAt: { type: String, default: '' },
})

const emit = defineEmits(['select-task', 'toggle-check'])

const viewLayout = ref('calendar') // 'calendar' (24H时间轴) | 'checklist' (本周清单)
const categoryFilter = ref('all') // 'all' (全景生活与备考) | 'study' (仅备考学习) | 'life' (仅生活与运动)

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const START_HOUR = 7  // 07:00 开始
const END_HOUR = 23   // 23:00 结束
const HOUR_HEIGHT = 68 // 每个小时网格高度（px）

const hours = computed(() => {
  const list = []
  for (let h = START_HOUR; h <= END_HOUR; h++) {
    list.push(`${String(h).padStart(2, '0')}:00`)
  }
  return list
})

function formatLocalDate(d) {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parsePlanDate(str) {
  if (!str) return new Date()
  const parts = str.match(/(\d{4})-(\d{2})-(\d{2})/)
  if (parts) {
    return new Date(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3]))
  }
  return new Date(str)
}

// 计算当前周的真实公历日期列表 (包含星期、月、日、是否为今天)
const weekDaysInfo = computed(() => {
  const base = parsePlanDate(props.planCreatedAt)
  const currentDay = base.getDay() // 0 是周日, 1 是周一...
  const distToMonday = (currentDay === 0 ? -6 : 1 - currentDay)
  const mondayOfWeek1 = new Date(base)
  mondayOfWeek1.setDate(base.getDate() + distToMonday)
  mondayOfWeek1.setHours(0, 0, 0, 0)

  const w = (props.selectedWeek === 'all' || !props.selectedWeek) ? 1 : Number(props.selectedWeek)
  const mondayOfSelectedWeek = new Date(mondayOfWeek1)
  mondayOfSelectedWeek.setDate(mondayOfWeek1.getDate() + (w - 1) * 7)

  const todayStr = formatLocalDate(new Date())

  const infoList = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(mondayOfSelectedWeek)
    d.setDate(mondayOfSelectedWeek.getDate() + i)
    const m = d.getMonth() + 1
    const dateNum = d.getDate()
    const iso = formatLocalDate(d)
    infoList.push({
      weekday: WEEKDAYS[i],
      month: m,
      day: dateNum,
      dateLabel: `${m}月${dateNum}日`,
      shortDate: `${String(m).padStart(2, '0')}/${String(dateNum).padStart(2, '0')}`,
      isToday: iso === todayStr,
      fullIso: iso
    })
  }
  return infoList
})

// 新粗野主义与涂鸦主题色系
const STICKY_THEMES = {
  study_yellow: { bg: 'bg-[#FFE600]', border: 'border-black', tape: 'bg-black text-[#FFE600]', text: 'text-black', dot: 'bg-[#FFE600]', tag: 'bg-black text-[#FFE600]', category: 'study' },
  study_lime: { bg: 'bg-[#CCFF00]', border: 'border-black', tape: 'bg-black text-[#CCFF00]', text: 'text-black', dot: 'bg-[#CCFF00]', tag: 'bg-black text-[#CCFF00]', category: 'study' },
  study_cyan: { bg: 'bg-[#00F0FF]', border: 'border-black', tape: 'bg-black text-[#00F0FF]', text: 'text-black', dot: 'bg-[#00F0FF]', tag: 'bg-black text-[#00F0FF]', category: 'study' },
  study_purple: { bg: 'bg-[#B388FF]', border: 'border-black', tape: 'bg-black text-[#B388FF]', text: 'text-black', dot: 'bg-[#B388FF]', tag: 'bg-black text-[#B388FF]', category: 'study' },
  fitness: { bg: 'bg-[#FF3399]', border: 'border-black', tape: 'bg-black text-[#FF3399]', text: 'text-white', dot: 'bg-[#FF3399]', tag: 'bg-black text-[#FF3399]', category: 'life' },
  meal: { bg: 'bg-[#FFA34D]', border: 'border-black', tape: 'bg-black text-[#FFA34D]', text: 'text-black', dot: 'bg-[#FFA34D]', tag: 'bg-black text-[#FFA34D]', category: 'life' },
  rest: { bg: 'bg-[#80F8FF]', border: 'border-black', tape: 'bg-black text-[#80F8FF]', text: 'text-black', dot: 'bg-[#80F8FF]', tag: 'bg-black text-[#80F8FF]', category: 'life' },
  sleep: { bg: 'bg-[#18181B]', border: 'border-black', tape: 'bg-[#FFE600] text-black', text: 'text-[#FFE600]', dot: 'bg-[#FFE600]', tag: 'bg-[#FFE600] text-black', category: 'life' },
}

// 默认健康生活作息基线（跑步/健身/三餐/午休/睡眠）
function generateDailyLifeHabits(weekday, weekNum) {
  return [
    {
      _id: `life-wake-${weekday}-${weekNum}`,
      title: '晨起唤醒 · 营养早餐与晨读',
      week: weekNum,
      weekday: weekday,
      time_block: '07:00-08:00',
      duration_hours: 1.0,
      type: '生活',
      metric: '温水唤醒、健康高蛋白早餐、过筛 30 个高频词',
      category: 'life',
      icon: '🌅',
      theme: STICKY_THEMES.meal,
      trackName: '健康生活'
    },
    {
      _id: `life-lunch-${weekday}-${weekNum}`,
      title: '营养午餐 · 充能与精力小憩',
      week: weekNum,
      weekday: weekday,
      time_block: '11:45-13:30',
      duration_hours: 1.75,
      type: '生活',
      metric: '饱腹少油午餐，午后闭目小憩 20 分钟唤醒下午精力',
      category: 'life',
      icon: '🍱',
      theme: STICKY_THEMES.meal,
      trackName: '健康生活'
    },
    {
      _id: `life-sport-${weekday}-${weekNum}`,
      title: weekday === '周三' || weekday === '周五' || weekday === '周六' ? '傍晚运动 · 跑步/力量健身 5km' : '傍晚休闲 · 户外散步与有氧放松',
      week: weekNum,
      weekday: weekday,
      time_block: '17:30-18:30',
      duration_hours: 1.0,
      type: '运动',
      metric: weekday === '周三' || weekday === '周五' || weekday === '周六' ? '有氧慢跑 5km 或力量训练，激活多巴胺与体能' : '户外散步 30~45 分钟，听听轻音乐放松眼部与颈椎',
      category: 'life',
      icon: weekday === '周三' || weekday === '周五' || weekday === '周六' ? '🏋️' : '🏃',
      theme: STICKY_THEMES.fitness,
      trackName: '运动健身'
    },
    {
      _id: `life-dinner-${weekday}-${weekNum}`,
      title: '健康晚餐 · 慢享生活与短休',
      week: weekNum,
      weekday: weekday,
      time_block: '18:30-19:30',
      duration_hours: 1.0,
      type: '生活',
      metric: '适度清淡晚餐，与家人朋友交流放松身心',
      category: 'life',
      icon: '🍲',
      theme: STICKY_THEMES.meal,
      trackName: '健康生活'
    },
    {
      _id: `life-sleep-${weekday}-${weekNum}`,
      title: '睡前拉伸 · 冥想与按时就寝',
      week: weekNum,
      weekday: weekday,
      time_block: '22:30-23:00',
      duration_hours: 0.5,
      type: '作息',
      metric: '放下手机，睡前 10 分钟拉伸冥想，保证 7.5 小时深度睡眠',
      category: 'life',
      icon: '🌙',
      theme: STICKY_THEMES.sleep,
      trackName: '健康作息'
    }
  ]
}

function extractTimeSegments(tb) {
  if (!tb) return [{ time_block: '08:30-10:00', start: 8.5, end: 10, dur: 1.5 }]
  const regex = /(\d{1,2})[:：](\d{2})\s*[-~至到]\s*(\d{1,2})[:：](\d{2})/g
  const segments = []
  let match
  while ((match = regex.exec(tb)) !== null) {
    const sH = Number(match[1])
    const sM = Number(match[2])
    const eH = Number(match[3])
    const eM = Number(match[4])
    const startHour = sH + sM / 60
    const endHour = eH + eM / 60
    const dur = Math.max(0.4, endHour - startHour)
    const formatted = `${String(sH).padStart(2, '0')}:${String(sM).padStart(2, '0')}-${String(eH).padStart(2, '0')}:${String(eM).padStart(2, '0')}`
    segments.push({
      time_block: formatted,
      start: startHour,
      end: endHour,
      dur: dur
    })
  }

  if (segments.length > 0) {
    return segments
  }

  const single = /(\d{1,2})[:：](\d{2})/.exec(tb)
  if (single) {
    const sH = Number(single[1])
    const sM = Number(single[2])
    return [{
      time_block: `${String(sH).padStart(2, '0')}:${String(sM).padStart(2, '0')}-+1.5h`,
      start: sH + sM / 60,
      end: sH + sM / 60 + 1.5,
      dur: 1.5
    }]
  }

  return [{ time_block: '09:00-10:30', start: 9, end: 10.5, dur: 1.5 }]
}

function getTaskIcon(task) {
  if (task.icon) return task.icon
  const t = (task.title || '') + (task.type || '')
  if (/跑|健|步|训|运/.test(t)) return '🏃'
  if (/早|餐|食|午|饭|饭/.test(t)) return '🍱'
  if (/睡|寝|休|息|冥|眠/.test(t)) return '🌙'
  if (/模|考|测|试|卷|真/.test(t)) return '📝'
  if (/背|词|英|语|听/.test(t)) return '🎧'
  if (/数|理|计|算|代/.test(t)) return '🔢'
  if (/申|博|导|研|开/.test(t)) return '🎓'
  return '📖'
}

const studyThemes = [
  STICKY_THEMES.study_yellow,
  STICKY_THEMES.study_lime,
  STICKY_THEMES.study_cyan,
  STICKY_THEMES.study_purple,
]

// 收集当前周的全部任务（包含学习轨道与生活基线），并做空间解耦与重叠错峰
const allWeekTasks = computed(() => {
  const map = {}
  WEEKDAYS.forEach(wd => (map[wd] = []))

  const currentW = (props.selectedWeek === 'all' || !props.selectedWeek) ? 1 : Number(props.selectedWeek)
  const tracks = props.fused?.tracks || []

  // 1. 注入生活习惯基线
  if (categoryFilter.value === 'all' || categoryFilter.value === 'life') {
    WEEKDAYS.forEach(wd => {
      const habits = generateDailyLifeHabits(wd, currentW)
      habits.forEach(h => {
        const segs = extractTimeSegments(h.time_block)
        segs.forEach(seg => {
          const topPx = (seg.start - START_HOUR) * HOUR_HEIGHT
          const heightPx = Math.max(28, seg.dur * HOUR_HEIGHT - 4)
          const isDone = !!props.checkedMap[h._id]
          map[wd].push({
            id: h._id,
            task: { ...h, time_block: seg.time_block },
            trackName: h.trackName,
            icon: h.icon,
            theme: h.theme,
            isDone: isDone,
            startHour: seg.start,
            endHour: seg.end,
            top: topPx,
            height: heightPx,
            category: 'life'
          })
        })
      })
    })
  }

  // 2. 注入备考学习轨道任务
  if (categoryFilter.value === 'all' || categoryFilter.value === 'study') {
    tracks.forEach((track, tIdx) => {
      if (props.selectedTrack !== 'all' && track.exam_name !== props.selectedTrack) {
        return
      }
      const trackTheme = studyThemes[tIdx % studyThemes.length]
      const tasks = track.tasks || []

      tasks.forEach((task, taskIdx) => {
        const tWeek = Number(task.week || 1)
        if (tWeek !== currentW) return

        const wd = task.weekday || '周一'
        if (!map[wd]) map[wd] = []

        const taskId = task.id || `${tIdx}-${taskIdx}-${tWeek}-${wd}`
        const isDone = !!props.checkedMap[taskId]

        const segs = extractTimeSegments(task.time_block)
        segs.forEach((seg, sIdx) => {
          const segId = segs.length > 1 ? `${taskId}_seg_${sIdx}` : taskId
          const topPx = (seg.start - START_HOUR) * HOUR_HEIGHT
          const heightPx = Math.max(32, seg.dur * HOUR_HEIGHT - 4)

          map[wd].push({
            id: segId,
            originId: taskId,
            task: {
              ...task,
              time_block: seg.time_block,
            },
            trackName: track.exam_name || `轨道 ${tIdx + 1}`,
            icon: getTaskIcon(task),
            theme: trackTheme,
            isDone: isDone,
            startHour: seg.start,
            endHour: seg.end,
            top: topPx,
            height: heightPx,
            category: 'study'
          })
        })
      })
    })
  }

  // 3. 计算同一天内重叠任务的左右分栏 (Layout overlapping cards)
  WEEKDAYS.forEach(wd => {
    const list = map[wd]
    list.sort((a, b) => a.startHour - b.startHour || b.height - a.height)

    for (let i = 0; i < list.length; i++) {
      const item = list[i]
      const overlaps = [item]
      for (let j = 0; j < list.length; j++) {
        if (i === j) continue
        const other = list[j]
        if (Math.max(item.startHour, other.startHour) < Math.min(item.endHour, other.endHour)) {
          overlaps.push(other)
        }
      }

      overlaps.sort((a, b) => a.id.localeCompare(b.id))
      const colIndex = overlaps.indexOf(item)
      const colCount = overlaps.length

      if (colCount > 1) {
        item.widthStyle = `calc(${100 / colCount}% - 4px)`
        item.leftStyle = `calc(${(colIndex * 100) / colCount}% + 2px)`
      } else {
        item.widthStyle = 'calc(100% - 6px)'
        item.leftStyle = '3px'
      }
    }
  })

  return map
})

// 本周统计进度
const weekStats = computed(() => {
  let total = 0
  let done = 0
  WEEKDAYS.forEach(wd => {
    const list = allWeekTasks.value[wd] || []
    list.forEach(item => {
      total++
      if (item.isDone) done++
    })
  })
  const pct = total ? Math.round((done / total) * 100) : 0
  return { total, done, pct }
})

// 扁平化本周清单列表（按星期与时段排序）
const flatWeekTasksList = computed(() => {
  const list = []
  WEEKDAYS.forEach(wd => {
    const dayTasks = allWeekTasks.value[wd] || []
    dayTasks.forEach(t => list.push({ ...t, weekday: wd }))
  })
  return list
})

function onTaskClick(item) {
  emit('select-task', {
    task: item.task,
    trackName: item.trackName,
    isDone: item.isDone,
    color: item.theme.dot
  })
}
</script>

<template>
  <div class="bg-white border-[3px] border-black shadow-[6px_6px_0px_0px_#000000] overflow-hidden flex flex-col font-sans select-none">
    <!-- 顶部状态栏：本周打卡仪表盘 + 视图模式切换 (24H时间轴 / 本周清单) + 分类过滤器 -->
    <div class="p-4 bg-black text-white border-b-[3px] border-black flex flex-wrap items-center justify-between gap-3">
      <!-- 本周打卡进度条 -->
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2 text-xs font-black uppercase font-neo-title tracking-wide text-[#FFE600]">
          <span>📊 本周作息执行进度：</span>
          <span class="text-white font-mono text-sm bg-neutral-800 px-1.5 py-0.5 border border-neutral-700">{{ weekStats.done }}</span>
          <span class="text-neutral-400 text-xs">/ {{ weekStats.total }} 项</span>
          <span class="ml-1 text-[11px] px-2 py-0.5 bg-[#CCFF00] text-black font-black font-mono border border-black shadow-[2px_2px_0px_0px_#fff]">
            {{ weekStats.pct }}%
          </span>
        </div>
        <div class="w-24 h-3 bg-neutral-900 border-2 border-white overflow-hidden hidden sm:block">
          <div class="h-full bg-[#FFE600] transition-all duration-300" :style="{ width: `${weekStats.pct}%` }"></div>
        </div>
      </div>

      <!-- 分类过滤器 (全景 / 备考 / 生活) -->
      <div class="flex items-center gap-1.5 bg-neutral-900 p-1 border-2 border-neutral-700 text-xs">
        <button
          @click="categoryFilter = 'all'"
          :class="['px-3 py-1 font-black transition cursor-pointer border', categoryFilter === 'all' ? 'bg-[#FFE600] text-black border-black shadow-[2px_2px_0px_0px_#fff]' : 'text-neutral-300 border-transparent hover:text-white']"
        >
          🔘 全景作息 (全部)
        </button>
        <button
          @click="categoryFilter = 'study'"
          :class="['px-3 py-1 font-black transition cursor-pointer border', categoryFilter === 'study' ? 'bg-[#FFE600] text-black border-black shadow-[2px_2px_0px_0px_#fff]' : 'text-neutral-300 border-transparent hover:text-white']"
        >
          📖 仅备考学习
        </button>
        <button
          @click="categoryFilter = 'life'"
          :class="['px-3 py-1 font-black transition cursor-pointer border', categoryFilter === 'life' ? 'bg-[#FFE600] text-black border-black shadow-[2px_2px_0px_0px_#fff]' : 'text-neutral-300 border-transparent hover:text-white']"
        >
          🏃 生活·运动·作息
        </button>
      </div>

      <!-- 视图模式切换：24H 时间轴 vs 本周清单 -->
      <div class="flex items-center gap-1.5 bg-neutral-900 p-1 border-2 border-neutral-700 text-xs font-black">
        <button
          @click="viewLayout = 'calendar'"
          :class="['px-3 py-1 transition cursor-pointer border', viewLayout === 'calendar' ? 'bg-white text-black border-black shadow-[2px_2px_0px_0px_#FFE600]' : 'text-neutral-300 border-transparent hover:text-white']"
        >
          ⏱️ 24H 时间轴
        </button>
        <button
          @click="viewLayout = 'checklist'"
          :class="['px-3 py-1 transition cursor-pointer border', viewLayout === 'checklist' ? 'bg-white text-black border-black shadow-[2px_2px_0px_0px_#FFE600]' : 'text-neutral-300 border-transparent hover:text-white']"
        >
          📋 本周任务清单
        </button>
      </div>
    </div>

    <!-- 模式 A：24H 时间轴周视图 -->
    <div v-if="viewLayout === 'calendar'" class="flex flex-col">
      <!-- 日历表头：展示周一至周日 + 真实公历日期 -->
      <div class="grid grid-cols-[60px_repeat(7,1fr)] bg-[#FAF7F2] border-b-[3px] border-black sticky top-0 z-20">
        <div class="py-2.5 text-center text-[11px] text-black font-black font-mono flex flex-col items-center justify-center border-r-2 border-black bg-[#FFE600]">
          <span>标尺</span>
          <span class="text-[9px]">24H</span>
        </div>
        <div 
          v-for="dayInfo in weekDaysInfo" 
          :key="dayInfo.weekday"
          :class="[
            'py-2 px-1 text-center border-r-2 border-black last:border-r-0 relative transition',
            dayInfo.isToday ? 'bg-[#CCFF00]' : 'bg-[#FAF7F2]'
          ]"
        >
          <div class="flex items-center justify-center gap-1">
            <span class="text-xs font-black uppercase" :class="dayInfo.isToday ? 'text-black underline' : 'text-black'">
              {{ dayInfo.weekday }}
            </span>
            <span v-if="dayInfo.isToday" class="neo-badge bg-black text-[#CCFF00] text-[9px] px-1 py-0">
              TODAY
            </span>
          </div>
          <div class="text-[11px] font-mono font-bold mt-0.5 text-black/70">
            {{ dayInfo.shortDate }}
          </div>
        </div>
      </div>

      <!-- 日历主体：时间标尺 + 7 列解耦粗野卡片网格 -->
      <div class="overflow-y-auto max-h-[640px] relative bg-[#FAF7F2]">
        <div 
          class="grid grid-cols-[60px_repeat(7,1fr)] relative"
          :style="{ height: `${hours.length * HOUR_HEIGHT}px` }"
        >
          <!-- 左侧时间标尺 (07:00 ~ 23:00) -->
          <div class="border-r-2 border-black bg-white">
            <div 
              v-for="h in hours" 
              :key="h"
              class="text-[11px] font-mono font-black text-black pr-2 text-right border-b border-black/20 flex items-start justify-end pt-1"
              :style="{ height: `${HOUR_HEIGHT}px` }"
            >
              {{ h }}
            </div>
          </div>

          <!-- 周一至周日 7 列时间网格 -->
          <div 
            v-for="dayInfo in weekDaysInfo" 
            :key="dayInfo.weekday"
            :class="[
              'relative border-r-2 border-black last:border-r-0 transition',
              dayInfo.isToday ? 'bg-[#CCFF00]/10' : 'bg-transparent'
            ]"
          >
            <!-- 背景等高横线（每小时一条） -->
            <div 
              v-for="h in hours" 
              :key="h"
              class="border-b border-black/15 w-full"
              :style="{ height: `${HOUR_HEIGHT}px` }"
            ></div>

            <!-- 解耦的独立粗野主义任务卡片 -->
            <div
              v-for="item in allWeekTasks[dayInfo.weekday]"
              :key="item.id"
              @click="onTaskClick(item)"
              :style="{
                top: `${item.top}px`,
                height: `${item.height}px`,
                left: item.leftStyle,
                width: item.widthStyle,
              }"
              :class="[
                'absolute p-2 cursor-pointer transition-all duration-150 z-10 border-2 border-black shadow-[3px_3px_0px_0px_#000] hover:shadow-[4px_4px_0px_0px_#000] hover:-translate-y-0.5 group overflow-hidden flex flex-col justify-between',
                item.theme.bg,
                item.theme.text,
                item.isDone ? 'opacity-50 grayscale line-through' : ''
              ]"
            >
              <!-- 卡片上部：时段、图标与快捷打卡圆圈 -->
              <div>
                <div class="flex items-center justify-between gap-1 mb-0.5">
                  <span class="text-[10px] font-black font-mono px-1 py-0.2 bg-black text-white truncate max-w-[85px] flex items-center gap-0.5">
                    <span>{{ item.icon }}</span>
                    <span>{{ item.task.time_block || '08:30-10:00' }}</span>
                  </span>

                  <!-- 右上角打卡框 -->
                  <button
                    @click.stop="emit('toggle-check', item.id)"
                    :class="[
                      'w-4 h-4 border-2 border-black flex items-center justify-center text-[10px] font-black transition cursor-pointer shrink-0',
                      item.isDone 
                        ? 'bg-black text-[#CCFF00]' 
                        : 'bg-white text-transparent hover:text-black'
                    ]"
                    :title="item.isDone ? '标记为待办' : '快捷打卡完成'"
                  >
                    ✓
                  </button>
                </div>

                <!-- 任务标题 -->
                <div class="font-black text-xs leading-snug line-clamp-2 mt-0.5">
                  {{ item.task.title }}
                </div>
              </div>

              <!-- 卡片底部指标 / 抓手 -->
              <div v-if="item.height > 48" class="mt-1 pt-1 border-t border-black/20 text-[10px] truncate opacity-90 font-bold">
                {{ item.task.metric || item.trackName }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 模式 B：本周任务清单视图 -->
    <div v-else-if="viewLayout === 'checklist'" class="p-6 bg-[#FAF7F2]">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="item in flatWeekTasksList"
          :key="item.id"
          @click="onTaskClick(item)"
          :class="[
            'border-[3px] border-black p-4 cursor-pointer transition-all shadow-[4px_4px_0px_0px_#000] hover:shadow-[6px_6px_0px_0px_#000] hover:-translate-y-0.5 flex flex-col justify-between',
            item.theme.bg,
            item.theme.text,
            item.isDone ? 'opacity-50 grayscale line-through' : ''
          ]"
        >
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <div class="flex items-center gap-1.5">
                <span class="neo-badge bg-black text-white text-[10px]">
                  {{ item.weekday }}
                </span>
                <span class="text-xs font-mono font-black underline">
                  {{ item.task.time_block }}
                </span>
              </div>

              <button
                @click.stop="emit('toggle-check', item.id)"
                :class="[
                  'w-5 h-5 border-2 border-black flex items-center justify-center text-xs font-black transition cursor-pointer',
                  item.isDone 
                    ? 'bg-black text-[#CCFF00]' 
                    : 'bg-white text-transparent hover:text-black'
                ]"
              >
                ✓
              </button>
            </div>

            <div class="font-black text-sm leading-snug">
              {{ item.icon }} {{ item.task.title }}
            </div>

            <div v-if="item.task.metric" class="text-xs mt-2 opacity-90 font-bold bg-black/10 p-1.5 border border-black/20">
              📌 抓手：{{ item.task.metric }}
            </div>
          </div>

          <div class="mt-3 pt-2 border-t-2 border-black/20 flex items-center justify-between text-[11px] font-black">
            <span class="neo-badge bg-white text-black text-[10px]">
              {{ item.trackName }}
            </span>
            <span>⏱️ {{ item.task.duration_hours || 1 }}h</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
