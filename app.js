/**
 * Telegram Web App for Group ШІ-11 (Lviv Polytechnic)
 * Schedule, Real-time Countdown, Deadlines & Tasks, Campuses, Teachers & Notes
 */

// Initialize Telegram WebApp SDK if available
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try {
    tg.enableClosingConfirmation();
  } catch (e) {}
}

function triggerHaptic(type = 'light') {
  if (tg?.HapticFeedback) {
    if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
    else if (type === 'medium') tg.HapticFeedback.impactOccurred('medium');
    else tg.HapticFeedback.impactOccurred('light');
  }
}

// ================= DATA DEFINITIONS =================

const BELL_SCHEDULE = [
  { pair: 1, start: "08:30", end: "09:50", startM: 8 * 60 + 30, endM: 9 * 60 + 50 },
  { pair: 2, start: "10:05", end: "11:25", startM: 10 * 60 + 5, endM: 11 * 60 + 25 },
  { pair: 3, start: "11:40", end: "13:00", startM: 11 * 60 + 40, endM: 13 * 60 + 0 },
  { pair: 4, start: "13:15", end: "14:35", startM: 13 * 60 + 15, endM: 14 * 60 + 35 },
  { pair: 5, start: "14:50", end: "16:10", startM: 14 * 60 + 50, endM: 16 * 60 + 10 },
];

const CAMPUSES = {
  "I н.к.": {
    name: "Головний (1-й) навчальний корпус",
    address: "вул. Степана Бандери, 12",
    maps: "https://maps.google.com/?q=вулиця+Степана+Бандери+12+Львів",
    desc: "Головний корпус Львівської Політехніки"
  },
  "VII н.к.": {
    name: "7-й навчальний корпус",
    address: "вул. Степана Бандери, 32 / Митрополита Андрея, 5",
    maps: "https://maps.google.com/?q=вулиця+Степана+Бандери+32+Львів",
    desc: "Корпус комп'ютерних наук (ІКНІ)"
  },
  "XX н.к.": {
    name: "20-й навчальний корпус",
    address: "вул. Княгині Ольги / Академіка Сахарова, 23",
    maps: "https://maps.google.com/?q=вулиця+Княгині+Ольги+Львів",
    desc: "Корпус кафедр програмування та штучного інтелекту"
  },
  "Самчука 21": {
    name: "Спортивний комплекс",
    address: "вул. Уласа Самчука, 21",
    maps: "https://maps.google.com/?q=вулиця+Уласа+Самчука+21+Львів",
    desc: "Спорткомплекс біля Стрийського парку"
  }
};

const TEACHERS = [
  { short: "Процах Н.П.", role: "Алгебра і геометрія" },
  { short: "Пшеничний О.Ю.", role: "Основи програмування (Лекції)" },
  { short: "Климишин Н.Т.", role: "Іноземна мова за проф. спрямуванням" },
  { short: "Репетило С.М.", role: "Математичний аналіз (Практика)" },
  { short: "Пукач П.Я.", role: "Математичний аналіз (Лекції)" },
  { short: "Хома І.Я.", role: "Історія державності та культури України" },
  { short: "Мельникова Н.І.", role: "Дискретна математика (Лекції)" },
  { short: "Пелещишин О.П.", role: "Дискретна математика (Практика)" },
  { short: "Павлик", role: "Дискретна математика (Лабораторні)" },
  { short: "Загородний І.І.", role: "Основи програмування (Практика)" },
  { short: "Тріска Р.М.", role: "Основи програмування (Лабораторні)" },
];

const ALL_SUBJECTS = [
  "Алгебра і геометрія",
  "Основи програмування",
  "Математичний аналіз",
  "Дискретна математика",
  "Іноземна мова за професійним спрямуванням",
  "Історія державності та культури України",
  "Фізичне виховання"
];

// Week 1 = Знаменник (current), Week 2 = Чисельник (next)
const SCHEDULE = {
  1: { // ЗНАМЕННИК (поточний тиждень)
    0: [
      { pair: 1, subject: "Алгебра і геометрія", type: "Практична", teacher: "Процах Н.П.", room: "109 I н.к." },
      { pair: 2, subject: "Алгебра і геометрія", type: "Лекція", teacher: "Процах Н.П.", room: "117 I н.к." },
      { pair: 5, subject: "Дискретна математика", type: "Лабораторна", teacher: "Павлик", room: "125 ХХ н.к." },
    ],
    1: [
      { pair: 1, subject: "Основи програмування", type: "Лекція", teacher: "Пшеничний О.Ю.", room: "117 I н.к." },
      { pair: 2, subject: "Іноземна мова за професійним спрямуванням, частина 1", type: "Практична", teacher: "Климишин Н.Т.", room: "018 VII н.к." },
      { pair: 3, subject: "Математичний аналіз", type: "Практична", teacher: "Репетило С.М.", room: "109 I н.к." },
    ],
    2: [
      { pair: 2, subject: "Фізичне виховання, частина 1", type: "Практична", teacher: "", room: "Самчука 21" },
      { pair: 3, subject: "Історія державності та культури України", type: "Лекція", teacher: "Хома І.Я.", room: "117 I н.к." },
      { pair: 4, subject: "Історія державності та культури України", type: "Практична", teacher: "Хома І.Я.", room: "109 I н.к." },
    ],
    3: [
      { pair: 1, subject: "Алгебра і геометрія", type: "Лекція", teacher: "Процах Н.П.", room: "117 I н.к." },
      { pair: 2, subject: "Математичний аналіз", type: "Лекція", teacher: "Пукач П.Я.", room: "117 I н.к." },
      { pair: 3, subject: "Дискретна математика", type: "Лекція", teacher: "Мельникова Н.І.", room: "218 I н.к." },
    ],
    4: [
      { pair: 2, subject: "Основи програмування", type: "Практична", teacher: "Загородний І.І.", room: "214 ХХ н.к." },
      { pair: 3, subject: "Основи програмування", type: "Лабораторна", teacher: "Тріска Р.М.", room: "212 ХХ н.к." },
    ],
    5: [],
    6: [],
  },
  2: { // ЧИСЕЛЬНИК (наступний тиждень)
    0: [
      { pair: 1, subject: "Алгебра і геометрія", type: "Практична", teacher: "Процах Н.П.", room: "109 I н.к." },
      { pair: 2, subject: "Алгебра і геометрія", type: "Лекція", teacher: "Процах Н.П.", room: "117 I н.к." },
      { pair: 5, subject: "Дискретна математика", type: "Лабораторна", teacher: "Павлик", room: "125 ХХ н.к." },
    ],
    1: [
      { pair: 1, subject: "Основи програмування", type: "Лекція", teacher: "Пшеничний О.Ю.", room: "117 I н.к." },
      { pair: 2, subject: "Іноземна мова за професійним спрямуванням, частина 1", type: "Практична", teacher: "Климишин Н.Т.", room: "018 VII н.к." },
      { pair: 3, subject: "Математичний аналіз", type: "Практична", teacher: "Репетило С.М.", room: "109 I н.к." },
      { pair: 4, subject: "Математичний аналіз", type: "Практична", teacher: "Репетило С.М.", room: "109 I н.к." },
    ],
    2: [
      { pair: 2, subject: "Фізичне виховання, частина 1", type: "Практична", teacher: "", room: "Самчука 21" },
      { pair: 3, subject: "Математичний аналіз", type: "Лекція", teacher: "Пукач П.Я.", room: "117 I н.к." },
    ],
    3: [
      { pair: 2, subject: "Математичний аналіз", type: "Лекція", teacher: "Пукач П.Я.", room: "117 I н.к." },
      { pair: 3, subject: "Дискретна математика", type: "Лекція", teacher: "Мельникова Н.І.", room: "218 I н.к." },
    ],
    4: [
      { pair: 1, subject: "Дискретна математика", type: "Практична", teacher: "Пелещишин О.П.", room: "123б, ХХ н.к." },
      { pair: 2, subject: "Основи програмування", type: "Практична", teacher: "Загородний І.І.", room: "214 ХХ н.к." },
      { pair: 3, subject: "Основи програмування", type: "Лабораторна", teacher: "Тріска Р.М.", room: "212 ХХ н.к." },
    ],
    5: [],
    6: [],
  }
};

const DAY_NAMES_UA = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"];
const DAY_SHORT_UA = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"];

// ================= STATE =================

let state = {
  currentWeek: parseInt(localStorage.getItem('nulp_week') || '1'), // 1 = Знаменник, 2 = Чисельник
  subgroup: parseInt(localStorage.getItem('nulp_subgroup') || '1'),
  selectedDay: new Date().getDay() === 0 ? 6 : new Date().getDay() - 1, // 0 = Mon .. 6 = Sun
  tasksFilter: 'active',
  tasks: JSON.parse(localStorage.getItem('nulp_tasks') || '[]'),
  notes: JSON.parse(localStorage.getItem('nulp_notes') || '[]'),
};

// If tasks empty, populate initial sample tasks
if (state.tasks.length === 0) {
  state.tasks = [
    {
      id: Date.now() - 1000,
      subject: "Дискретна математика",
      text: "Лабораторна робота №1",
      deadline: new Date(Date.now() + 86400000 * 2).toISOString().slice(0, 16).replace('T', ' '),
      priority: "high",
      completed: false
    }
  ];
  localStorage.setItem('nulp_tasks', JSON.stringify(state.tasks));
}

// If notes empty, populate initial links
if (state.notes.length === 0) {
  state.notes = [
    {
      id: Date.now() - 2000,
      subject: "Основи програмування",
      title: "GitHub репозиторій завдань",
      content: "https://github.com"
    },
    {
      id: Date.now() - 1000,
      subject: "Математичний аналіз",
      title: "Google Drive матеріалів та лекцій",
      content: "Матеріали лекцій професора Пукача П.Я."
    }
  ];
  localStorage.setItem('nulp_notes', JSON.stringify(state.notes));
}

// ================= UTILITIES =================

function getSubjectIcon(subj) {
  const s = subj.toLowerCase();
  if (s.includes("програм")) return "💻";
  if (s.includes("алгебр") || s.includes("геометр")) return "📐";
  if (s.includes("дискретн")) return "🔢";
  if (s.includes("аналіз") || s.includes("математич")) return "📈";
  if (s.includes("мов") || s.includes("інозем")) return "🇬🇧";
  if (s.includes("істор") || s.includes("культур")) return "🏛";
  if (s.includes("фізич") || s.includes("спорт")) return "🏃";
  return "📚";
}

function getTypeBadge(type) {
  if (type.includes("Лекція")) {
    return `<span class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">📖 Лекція</span>`;
  }
  if (type.includes("Лабораторна") || type.includes("лаб")) {
    return `<span class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">🔬 Лабораторна</span>`;
  }
  return `<span class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">✍️ Практична</span>`;
}

function formatTimeRemaining(dlDate) {
  const now = new Date();
  const diff = dlDate - now;
  const totalSecs = Math.floor(diff / 1000);

  if (totalSecs < 0) {
    const past = Math.abs(totalSecs);
    if (past < 3600) return `прострочено на ${Math.floor(past / 60)} хв`;
    if (past < 86400) return `прострочено на ${Math.floor(past / 3600)} год`;
    return `прострочено на ${Math.floor(past / 86400)} дн.`;
  }

  if (totalSecs < 3600) return `${Math.floor(totalSecs / 60)} хв`;
  if (totalSecs < 86400) {
    const h = Math.floor(totalSecs / 3600);
    const m = Math.floor((totalSecs % 3600) / 60);
    return m > 0 ? `${h} год ${m} хв` : `${h} год`;
  }
  const days = Math.floor(totalSecs / 86400);
  const h = Math.floor((totalSecs % 86400) / 3600);
  return h > 0 ? `${days} дн. ${h} год` : `${days} дн.`;
}

// ================= RENDERERS =================

function updateHeader() {
  const now = new Date();
  const options = { weekday: 'long', day: 'numeric', month: 'long' };
  document.getElementById('header-date').innerText = now.toLocaleDateString('uk-UA', options);
  
  const weekText = state.currentWeek === 1 ? "Знаменник" : "Чисельник";
  document.getElementById('week-toggle-text').innerText = weekText;
  document.getElementById('subgroup-toggle-text').innerText = `${state.subgroup === 1 ? 'I' : 'II'} підгр.`;
}

function renderDaySelector() {
  const container = document.getElementById('day-selector-container');
  container.innerHTML = '';

  const todayIdx = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;

  DAY_SHORT_UA.forEach((name, idx) => {
    const isSelected = state.selectedDay === idx;
    const isToday = todayIdx === idx;

    const btn = document.createElement('button');
    btn.className = `flex-1 min-w-[44px] py-2 px-1.5 rounded-xl text-xs font-bold transition flex flex-col items-center gap-0.5 active:scale-95 ${
      isSelected 
        ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30' 
        : 'bg-gray-900/80 text-gray-400 hover:bg-gray-800 border border-gray-800/60'
    }`;

    btn.innerHTML = `
      <span class="text-[11px]">${name}</span>
      ${isToday ? '<span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>' : '<span class="w-1.5 h-1.5"></span>'}
    `;

    btn.onclick = () => {
      triggerHaptic();
      state.selectedDay = idx;
      renderDaySelector();
      renderSchedule();
    };

    container.appendChild(btn);
  });
}

function renderLiveStatus() {
  const now = new Date();
  const todayIdx = now.getDay() === 0 ? 6 : now.getDay() - 1;

  const card = document.getElementById('live-status-card');
  const badge = document.getElementById('live-badge');
  const countdown = document.getElementById('live-countdown');
  const title = document.getElementById('live-title');
  const details = document.getElementById('live-details');

  if (todayIdx >= 5) {
    badge.className = "px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30";
    badge.innerHTML = "🏖️ Вихідний";
    countdown.innerText = "";
    title.innerText = "Сьогодні пар немає!";
    details.innerText = "Гарних вихідних та гарного відпочинку ☕️";
    return;
  }

  const lessons = SCHEDULE[state.currentWeek][todayIdx] || [];
  if (lessons.length === 0) {
    badge.className = "px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
    badge.innerHTML = "✨ Вільний день";
    countdown.innerText = "";
    title.innerText = "Сьогодні пар немає";
    details.innerText = "Можна зробити домашку або відпочити 🚀";
    return;
  }

  const nowM = now.getHours() * 60 + now.getMinutes();
  const first = lessons[0];
  const firstBell = BELL_SCHEDULE.find(b => b.pair === first.pair);

  // 1. Before classes start
  if (nowM < firstBell.startM) {
    const diff = firstBell.startM - nowM;
    badge.className = "px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30";
    badge.innerHTML = "🌅 Наступна";
    countdown.innerText = `через ${Math.floor(diff / 60)}г ${diff % 60}хв`;
    title.innerText = `1-а пара о ${firstBell.start}: ${first.subject}`;
    details.innerText = `📍 ${first.room} | 👤 ${first.teacher || 'Кафедра'}`;
    return;
  }

  // 2. Currently in class
  for (const l of lessons) {
    const bell = BELL_SCHEDULE.find(b => b.pair === l.pair);
    if (nowM >= bell.startM && nowM <= bell.endM) {
      const left = bell.endM - nowM;
      badge.className = "px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5";
      badge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span> Зараз (${l.pair} пара)`;
      countdown.innerText = `до кінця ${left} хв`;
      title.innerText = `${getSubjectIcon(l.subject)} ${l.subject}`;
      details.innerText = `📍 ${l.room} | 👤 ${l.teacher || 'Кафедра'} (${l.type})`;
      return;
    }
  }

  // 3. In break or window
  for (let i = 0; i < lessons.length - 1; i++) {
    const curL = lessons[i];
    const nxtL = lessons[i + 1];
    const curBell = BELL_SCHEDULE.find(b => b.pair === curL.pair);
    const nxtBell = BELL_SCHEDULE.find(b => b.pair === nxtL.pair);

    if (nowM > curBell.endM && nowM < nxtBell.startM) {
      const untilNext = nxtBell.startM - nowM;
      const gap = nxtBell.startM - curBell.endM;
      const isWindow = gap > 20;

      badge.className = "px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30";
      badge.innerHTML = isWindow ? "🪟 Вікно" : "☕️ Перерва";
      countdown.innerText = `до пари ${Math.floor(untilNext / 60)}г ${untilNext % 60}хв`;
      title.innerText = `Далі (${nxtBell.start}): ${nxtL.subject}`;
      details.innerText = `📍 ${nxtL.room} | 👤 ${nxtL.teacher || 'Кафедра'}`;
      return;
    }
  }

  // 4. After all classes
  const last = lessons[lessons.length - 1];
  const lastBell = BELL_SCHEDULE.find(b => b.pair === last.pair);
  if (nowM > lastBell.endM) {
    badge.className = "px-2 py-0.5 rounded-full text-[11px] font-bold uppercase bg-purple-500/20 text-purple-400 border border-purple-500/30";
    badge.innerHTML = "🏁 Пари завершено";
    countdown.innerText = "";
    title.innerText = "Всі пари на сьогодні закінчились!";
    details.innerText = "Чудового та продуктивного вечора 🌙";
  }
}

function renderSchedule() {
  const container = document.getElementById('lessons-list');
  container.innerHTML = '';

  const dayIdx = state.selectedDay;
  const dayName = DAY_NAMES_UA[dayIdx];
  const weekName = state.currentWeek === 1 ? "Знаменник" : "Чисельник";

  document.getElementById('current-day-heading').innerText = `${dayName} (${weekName})`;

  const lessons = SCHEDULE[state.currentWeek][dayIdx] || [];
  document.getElementById('current-day-count').innerText = `${lessons.length} пар`;

  if (lessons.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center rounded-2xl bg-gray-900/60 border border-gray-800/80 space-y-2">
        <div class="text-3xl">🏖️</div>
        <h4 class="font-bold text-sm text-gray-200">${dayIdx >= 5 ? 'Вихідний день' : 'Вільний день'}</h4>
        <p class="text-xs text-gray-400">Пар у розкладі на цей день немає.</p>
      </div>
    `;
    return;
  }

  const now = new Date();
  const isToday = (now.getDay() === 0 ? 6 : now.getDay() - 1) === dayIdx;
  const nowM = now.getHours() * 60 + now.getMinutes();

  let prevPair = null;

  lessons.forEach((l) => {
    const bell = BELL_SCHEDULE.find(b => b.pair === l.pair);

    // Check window / gap before
    if (prevPair && (l.pair > prevPair.pair + 1)) {
      const prevBell = BELL_SCHEDULE.find(b => b.pair === prevPair.pair);
      const gapM = bell.startM - prevBell.endM;
      const gapDiv = document.createElement('div');
      gapDiv.className = "py-2 px-3 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs text-amber-300 font-medium";
      gapDiv.innerHTML = `
        <span class="flex items-center gap-1.5">
          <i data-lucide="coffee" class="w-4 h-4"></i>
          Вікно між парами
        </span>
        <span class="font-bold">${Math.floor(gapM / 60)}г ${gapM % 60}хв</span>
      `;
      container.appendChild(gapDiv);
    }
    prevPair = l;

    const isCurrent = isToday && (nowM >= bell.startM && nowM <= bell.endM);

    const card = document.createElement('div');
    card.className = `p-4 rounded-2xl border transition-all ${
      isCurrent 
        ? 'bg-gradient-to-r from-emerald-950/40 to-gray-900 border-emerald-500/50 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/30' 
        : 'bg-gray-900/90 hover:bg-gray-800/90 border-gray-800/80 shadow-md'
    }`;

    // Find campus map url
    let mapsUrl = null;
    for (const [code, info] of Object.entries(CAMPUSES)) {
      if (l.room.includes(code)) {
        mapsUrl = info.maps;
        break;
      }
    }

    card.innerHTML = `
      <div class="flex items-start justify-between gap-3">
        <div class="space-y-1 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-md border border-indigo-500/20">
              ${l.pair} пара • ${bell.start} - ${bell.end}
            </span>
            ${getTypeBadge(l.type)}
            ${isCurrent ? '<span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/20 text-emerald-400 animate-pulse">● ЗАРАЗ</span>' : ''}
          </div>

          <h4 class="font-bold text-base text-white leading-tight pt-1">
            ${getSubjectIcon(l.subject)} ${l.subject}
          </h4>

          <div class="flex items-center gap-4 text-xs text-gray-300 pt-1 flex-wrap">
            ${l.teacher ? `<span class="flex items-center gap-1.5"><i data-lucide="user" class="w-3.5 h-3.5 text-gray-400"></i> ${l.teacher}</span>` : ''}
            <span class="flex items-center gap-1.5 font-mono text-indigo-300 font-semibold">
              <i data-lucide="map-pin" class="w-3.5 h-3.5 text-gray-400"></i> 
              ${l.room}
            </span>
          </div>
        </div>

        ${mapsUrl ? `
          <a href="${mapsUrl}" target="_blank" class="p-2.5 rounded-xl bg-gray-800 hover:bg-indigo-600 active:scale-95 text-gray-300 hover:text-white transition shrink-0 border border-gray-700/60" title="Відкрити карту">
            <i data-lucide="navigation" class="w-4 h-4"></i>
          </a>
        ` : ''}
      </div>
    `;

    container.appendChild(card);
  });

  lucide.createIcons();
}

function renderTasks() {
  const container = document.getElementById('tasks-list');
  container.innerHTML = '';

  let filtered = state.tasks;
  if (state.tasksFilter === 'active') {
    filtered = state.tasks.filter(t => !t.completed);
  } else if (state.tasksFilter === 'completed') {
    filtered = state.tasks.filter(t => t.completed);
  } else if (state.tasksFilter === 'high') {
    filtered = state.tasks.filter(t => t.priority === 'high' && !t.completed);
  }

  // Update badge count
  const activeCount = state.tasks.filter(t => !t.completed).length;
  const badgeEl = document.getElementById('nav-task-badge');
  if (activeCount > 0) {
    badgeEl.classList.remove('hidden');
  } else {
    badgeEl.classList.add('hidden');
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center rounded-2xl bg-gray-900/60 border border-gray-800/80 space-y-2">
        <div class="text-3xl">🎉</div>
        <h4 class="font-bold text-sm text-gray-200">Немає завдань</h4>
        <p class="text-xs text-gray-400">Всі завдання у цій категорії виконано або ще не створено.</p>
      </div>
    `;
    return;
  }

  filtered.forEach(task => {
    const dlDate = new Date(task.deadline);
    const timeLeft = formatTimeRemaining(dlDate);

    const prioBadges = {
      high: '<span class="text-[11px] font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded-md border border-red-500/20">🔥 Терміново</span>',
      normal: '<span class="text-[11px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20">🟡 Звичайно</span>',
      low: '<span class="text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">🟢 Не терміново</span>'
    };

    const card = document.createElement('div');
    card.className = `p-3.5 rounded-2xl border transition-all flex items-start gap-3 ${
      task.completed 
        ? 'bg-gray-900/40 border-gray-800/40 opacity-60' 
        : 'bg-gray-900/90 border-gray-800/80 shadow-md hover:border-gray-700'
    }`;

    card.innerHTML = `
      <input type="checkbox" class="custom-checkbox mt-1 shrink-0" ${task.completed ? 'checked' : ''} data-id="${task.id}">
      
      <div class="flex-1 min-w-0 space-y-1">
        <div class="flex items-center gap-2 flex-wrap justify-between">
          <span class="text-xs font-semibold text-indigo-300 truncate max-w-[200px]">${task.subject}</span>
          ${prioBadges[task.priority] || ''}
        </div>

        <p class="text-sm font-medium text-white ${task.completed ? 'line-through text-gray-400' : ''}">${task.text}</p>

        <div class="flex items-center justify-between text-xs text-gray-400 pt-1">
          <span class="flex items-center gap-1 font-mono">
            <i data-lucide="clock" class="w-3.5 h-3.5"></i>
            ${task.deadline} (${timeLeft})
          </span>

          <button class="delete-task-btn text-gray-500 hover:text-red-400 p-1 rounded-lg transition" data-id="${task.id}">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  // Attach handlers
  container.querySelectorAll('.custom-checkbox').forEach(cb => {
    cb.onchange = (e) => {
      const id = parseInt(e.target.dataset.id);
      const t = state.tasks.find(x => x.id === id);
      if (t) {
        t.completed = e.target.checked;
        localStorage.setItem('nulp_tasks', JSON.stringify(state.tasks));
        triggerHaptic('success');
        renderTasks();
      }
    };
  });

  container.querySelectorAll('.delete-task-btn').forEach(btn => {
    btn.onclick = (e) => {
      const id = parseInt(btn.closest('button').dataset.id);
      state.tasks = state.tasks.filter(x => x.id !== id);
      localStorage.setItem('nulp_tasks', JSON.stringify(state.tasks));
      triggerHaptic();
      renderTasks();
    };
  });

  lucide.createIcons();
}

function renderBells() {
  const container = document.getElementById('bells-list');
  container.innerHTML = '';

  const now = new Date();
  const nowM = now.getHours() * 60 + now.getMinutes();

  BELL_SCHEDULE.forEach(b => {
    const isCurrent = (nowM >= b.startM && nowM <= b.endM);

    const card = document.createElement('div');
    card.className = `p-3.5 rounded-2xl border transition flex items-center justify-between ${
      isCurrent 
        ? 'bg-gradient-to-r from-indigo-950/60 to-purple-950/50 border-indigo-500/50 shadow-lg' 
        : 'bg-gray-900/80 border-gray-800'
    }`;

    card.innerHTML = `
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl ${isCurrent ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400'} flex items-center justify-center font-bold text-sm">
          ${b.pair}
        </div>
        <div>
          <h4 class="font-bold text-sm text-white">${b.pair} пара</h4>
          <p class="text-xs text-gray-400">Тривалість: 80 хвилин</p>
        </div>
      </div>
      <div class="text-right">
        <span class="font-mono font-bold text-sm text-indigo-300">${b.start} — ${b.end}</span>
        ${isCurrent ? '<p class="text-[10px] font-bold text-emerald-400">● ЗАРАЗ ЙДЕ</p>' : ''}
      </div>
    `;

    container.appendChild(card);
  });
}

function renderDirectory() {
  const campusesContainer = document.getElementById('dir-campuses-view');
  campusesContainer.innerHTML = '';

  Object.entries(CAMPUSES).forEach(([code, info]) => {
    const card = document.createElement('div');
    card.className = "p-4 rounded-2xl bg-gray-900/90 border border-gray-800 space-y-2";
    card.innerHTML = `
      <div class="flex items-start justify-between gap-3">
        <div>
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded-md text-xs font-bold font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">${code}</span>
            <h4 class="font-bold text-sm text-white">${info.name}</h4>
          </div>
          <p class="text-xs text-gray-400 pt-1">📍 ${info.address}</p>
          <p class="text-xs text-gray-500 pt-0.5">${info.desc}</p>
        </div>
        <a href="${info.maps}" target="_blank" class="px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 text-xs font-bold transition flex items-center gap-1.5 shrink-0">
          <i data-lucide="map" class="w-3.5 h-3.5"></i>
          Карта
        </a>
      </div>
    `;
    campusesContainer.appendChild(card);
  });

  const teachersContainer = document.getElementById('dir-teachers-view');
  teachersContainer.innerHTML = '';

  TEACHERS.forEach(t => {
    const card = document.createElement('div');
    card.className = "p-3 rounded-xl bg-gray-900/80 border border-gray-800 flex items-center justify-between gap-3";
    card.innerHTML = `
      <div>
        <h4 class="font-bold text-sm text-white">👤 ${t.short}</h4>
        <p class="text-xs text-gray-400">📚 ${t.role}</p>
      </div>
    `;
    teachersContainer.appendChild(card);
  });

  lucide.createIcons();
}

function renderNotes() {
  const container = document.getElementById('notes-list');
  container.innerHTML = '';

  if (state.notes.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center rounded-2xl bg-gray-900/60 border border-gray-800/80 space-y-2">
        <div class="text-3xl">📚</div>
        <h4 class="font-bold text-sm text-gray-200">Немає збережених матеріалів</h4>
        <p class="text-xs text-gray-400">Натисніть «Нотатка», щоб додати посилання на диск або конспект.</p>
      </div>
    `;
    return;
  }

  state.notes.forEach(note => {
    const isUrl = note.content.startsWith('http://') || note.content.startsWith('https://');

    const card = document.createElement('div');
    card.className = "p-4 rounded-2xl bg-gray-900/90 border border-gray-800 space-y-2";
    card.innerHTML = `
      <div class="flex items-start justify-between gap-2">
        <div>
          <span class="text-xs font-semibold text-indigo-400">${note.subject}</span>
          <h4 class="font-bold text-sm text-white pt-0.5">${note.title}</h4>
        </div>
        <button class="delete-note-btn text-gray-500 hover:text-red-400 p-1 rounded-lg transition" data-id="${note.id}">
          <i data-lucide="trash-2" class="w-4 h-4"></i>
        </button>
      </div>
      <div class="text-xs text-gray-300 break-words bg-gray-950/60 p-2.5 rounded-xl border border-gray-800/80">
        ${isUrl ? `<a href="${note.content}" target="_blank" class="text-indigo-400 underline font-mono flex items-center gap-1.5"><i data-lucide="external-link" class="w-3.5 h-3.5"></i> ${note.content}</a>` : note.content}
      </div>
    `;
    container.appendChild(card);
  });

  container.querySelectorAll('.delete-note-btn').forEach(btn => {
    btn.onclick = () => {
      const id = parseInt(btn.dataset.id);
      state.notes = state.notes.filter(x => x.id !== id);
      localStorage.setItem('nulp_notes', JSON.stringify(state.notes));
      triggerHaptic();
      renderNotes();
    };
  });

  lucide.createIcons();
}

function populateDropdowns() {
  const taskSubjSelect = document.getElementById('task-subject-input');
  const noteSubjSelect = document.getElementById('note-subject-input');

  taskSubjSelect.innerHTML = '';
  noteSubjSelect.innerHTML = '';

  ALL_SUBJECTS.forEach(s => {
    const opt1 = document.createElement('option');
    opt1.value = s;
    opt1.innerText = s;
    taskSubjSelect.appendChild(opt1);

    const opt2 = document.createElement('option');
    opt2.value = s;
    opt2.innerText = s;
    noteSubjSelect.appendChild(opt2);
  });
}

// ================= EVENT LISTENERS =================

document.addEventListener('DOMContentLoaded', () => {
  updateHeader();
  renderDaySelector();
  renderLiveStatus();
  renderSchedule();
  renderTasks();
  renderBells();
  renderDirectory();
  renderNotes();
  populateDropdowns();

  // Periodic real-time update
  setInterval(() => {
    renderLiveStatus();
  }, 10000);

  // Week toggle
  document.getElementById('week-toggle-btn').onclick = () => {
    triggerHaptic('medium');
    state.currentWeek = state.currentWeek === 1 ? 2 : 1;
    localStorage.setItem('nulp_week', state.currentWeek);
    updateHeader();
    renderLiveStatus();
    renderSchedule();
  };

  // Subgroup toggle
  document.getElementById('subgroup-toggle-btn').onclick = () => {
    triggerHaptic('medium');
    state.subgroup = state.subgroup === 1 ? 2 : 1;
    localStorage.setItem('nulp_subgroup', state.subgroup);
    updateHeader();
    renderSchedule();
  };

  // Tab Navigation
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.onclick = () => {
      triggerHaptic();
      const tabId = btn.dataset.tab;

      document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.remove('active', 'text-indigo-400');
        b.classList.add('text-gray-400');
      });
      btn.classList.add('active', 'text-indigo-400');
      btn.classList.remove('text-gray-400');

      document.querySelectorAll('.tab-content').forEach(tc => {
        tc.classList.add('hidden');
        tc.classList.remove('active');
      });

      const activeTab = document.getElementById(tabId);
      if (activeTab) {
        activeTab.classList.remove('hidden');
        activeTab.classList.add('active');
      }

      window.scrollTo({ top: 0, behavior: 'smooth' });
    };
  });

  // Task Filters
  document.querySelectorAll('.task-filter-btn').forEach(btn => {
    btn.onclick = () => {
      triggerHaptic();
      document.querySelectorAll('.task-filter-btn').forEach(b => {
        b.className = "task-filter-btn px-3 py-1 rounded-lg text-xs font-semibold bg-gray-800 text-gray-300 hover:bg-gray-700 transition active:scale-95";
      });
      btn.className = "task-filter-btn px-3 py-1 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition active:scale-95";

      state.tasksFilter = btn.dataset.filter;
      renderTasks();
    };
  });

  // Directory Sub-tabs
  const dirCampusesBtn = document.getElementById('dir-tab-campuses');
  const dirTeachersBtn = document.getElementById('dir-tab-teachers');
  const dirCampusesView = document.getElementById('dir-campuses-view');
  const dirTeachersView = document.getElementById('dir-teachers-view');

  dirCampusesBtn.onclick = () => {
    triggerHaptic();
    dirCampusesBtn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white transition";
    dirTeachersBtn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition";
    dirCampusesView.classList.remove('hidden');
    dirTeachersView.classList.add('hidden');
  };

  dirTeachersBtn.onclick = () => {
    triggerHaptic();
    dirTeachersBtn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white transition";
    dirCampusesBtn.className = "flex-1 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition";
    dirTeachersView.classList.remove('hidden');
    dirCampusesView.classList.add('hidden');
  };

  // Modals
  const taskModal = document.getElementById('task-modal');
  const noteModal = document.getElementById('note-modal');

  document.getElementById('add-task-btn').onclick = () => {
    triggerHaptic();
    const todayStr = new Date().toISOString().slice(0, 10);
    document.getElementById('task-date-input').value = todayStr;
    taskModal.classList.remove('hidden');
    setTimeout(() => taskModal.classList.add('show'), 10);
  };

  document.getElementById('close-task-modal').onclick = () => {
    taskModal.classList.remove('show');
    setTimeout(() => taskModal.classList.add('hidden'), 200);
  };

  document.getElementById('add-note-btn').onclick = () => {
    triggerHaptic();
    noteModal.classList.remove('hidden');
    setTimeout(() => noteModal.classList.add('show'), 10);
  };

  document.getElementById('close-note-modal').onclick = () => {
    noteModal.classList.remove('show');
    setTimeout(() => noteModal.classList.add('hidden'), 200);
  };

  // Quick Deadline buttons in modal
  document.querySelectorAll('.quick-dl-btn').forEach(btn => {
    btn.onclick = () => {
      triggerHaptic();
      const type = btn.dataset.dl;
      const now = new Date();
      let target = new Date();

      if (type === 'today') {
        target.setHours(23, 59, 0, 0);
      } else if (type === 'tmrw') {
        target.setDate(target.getDate() + 1);
        target.setHours(23, 59, 0, 0);
      } else if (type === '2days') {
        target.setDate(target.getDate() + 2);
        target.setHours(23, 59, 0, 0);
      } else if (type === 'friday') {
        const curDay = target.getDay();
        const diff = (5 - curDay + 7) % 7 || 7;
        target.setDate(target.getDate() + diff);
        target.setHours(23, 59, 0, 0);
      }

      document.getElementById('task-date-input').value = target.toISOString().slice(0, 10);
      document.getElementById('task-time-input').value = "23:59";
    };
  });

  // Save Task
  document.getElementById('save-task-btn').onclick = () => {
    const subject = document.getElementById('task-subject-input').value;
    const text = document.getElementById('task-desc-input').value.trim();
    const dateVal = document.getElementById('task-date-input').value;
    const timeVal = document.getElementById('task-time-input').value || "23:59";
    const priority = document.querySelector('input[name="priority"]:checked')?.value || "normal";

    if (!text) {
      alert("Будь ласка, введіть опис завдання.");
      return;
    }

    const newTask = {
      id: Date.now(),
      subject: subject,
      text: text,
      deadline: `${dateVal} ${timeVal}`,
      priority: priority,
      completed: false
    };

    state.tasks.unshift(newTask);
    localStorage.setItem('nulp_tasks', JSON.stringify(state.tasks));

    triggerHaptic('success');
    document.getElementById('task-desc-input').value = '';
    taskModal.classList.remove('show');
    setTimeout(() => taskModal.classList.add('hidden'), 200);

    renderTasks();
  };

  // Save Note
  document.getElementById('save-note-btn').onclick = () => {
    const subject = document.getElementById('note-subject-input').value;
    const title = document.getElementById('note-title-input').value.trim();
    const content = document.getElementById('note-content-input').value.trim();

    if (!title || !content) {
      alert("Будь ласка, заповніть заголовок та вміст нотатки.");
      return;
    }

    const newNote = {
      id: Date.now(),
      subject: subject,
      title: title,
      content: content
    };

    state.notes.unshift(newNote);
    localStorage.setItem('nulp_notes', JSON.stringify(state.notes));

    triggerHaptic('success');
    document.getElementById('note-title-input').value = '';
    document.getElementById('note-content-input').value = '';
    noteModal.classList.remove('show');
    setTimeout(() => noteModal.classList.add('hidden'), 200);

    renderNotes();
  };
});
