from __future__ import annotations

"""
Telegram Bot: Розклад & Дедлайни для групи ШІ-11 (Львівська Політехніка)
Повний єдиний модуль без підпапок: розклад, асинхронна БД, дедлайни, сповіщення та Web App.
"""
import os
import sys
import re
import html
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, date, timedelta, time
from typing import List, Dict, Optional, Any, Union

import pytz
import aiosqlite
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, BotCommand,
    BotCommandScopeDefault, MenuButtonWebApp, WebAppInfo, ReplyKeyboardRemove
)
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ================= 1. CONFIGURATION =================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "8874178437:AAFFmlp4usbe7Mn1mhJE3oEJAk-xxNFwHzA")
TIMEZONE_NAME = os.getenv("TIMEZONE", "Europe/Kyiv")
DB_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "schedule_bot.db")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://fastop06.github.io/nulp-schedule/")

DEFAULT_GROUP = "ШІ-11"
DEFAULT_SUBGROUP = 1

DEFAULT_SETTINGS = {
    "notify_30m": 1,        # 30 хв до 1-ї пари або після вікна
    "notify_5m": 1,         # 5 хв до кожної пари
    "morning_summary": 1,   # Ранковий дайджест
    "morning_time": "07:30",
    "evening_summary": 1,   # Вечірній дайджест
    "evening_time": "21:00",
    "notify_deadlines": 1,  # Сповіщення про дедлайни
    "subgroup": 1,          # Підгрупа
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ================= 2. SCHEDULE DATA & MODELS =================

BELL_SCHEDULE: Dict[int, Dict[str, Any]] = {
    1: {"start": "08:30", "end": "09:50", "start_m": 8 * 60 + 30, "end_m": 9 * 60 + 50},
    2: {"start": "10:05", "end": "11:25", "start_m": 10 * 60 + 5, "end_m": 11 * 60 + 25},
    3: {"start": "11:40", "end": "13:00", "start_m": 11 * 60 + 40, "end_m": 13 * 60 + 0},
    4: {"start": "13:15", "end": "14:35", "start_m": 13 * 60 + 15, "end_m": 14 * 60 + 35},
    5: {"start": "14:50", "end": "16:10", "start_m": 14 * 60 + 50, "end_m": 16 * 60 + 10},
}

CAMPUS_INFO: Dict[str, Dict[str, str]] = {
    "I н.к.": {
        "name": "Головний (1-й) навчальний корпус",
        "address": "вул. Степана Бандери, 12",
        "maps_url": "https://maps.google.com/?q=вулиця+Степана+Бандери+12+Львів",
        "description": "Головний корпус Львівської Політехніки"
    },
    "VII н.к.": {
        "name": "7-й навчальний корпус",
        "address": "вул. Степана Бандери, 32 / Митрополита Андрея, 5",
        "maps_url": "https://maps.google.com/?q=вулиця+Степана+Бандери+32+Львів",
        "description": "Корпус комп'ютерних наук та ІТ (ІКНІ)"
    },
    "XX н.к.": {
        "name": "20-й навчальний корпус",
        "address": "вул. Княгині Ольги / Академіка Сахарова, 23",
        "maps_url": "https://maps.google.com/?q=вулиця+Княгині+Ольги+Львів",
        "description": "Корпус кафедр програмування та штучного інтелекту"
    },
    "Самчука 21": {
        "name": "Спортивний комплекс",
        "address": "вул. Уласа Самчука, 21",
        "maps_url": "https://maps.google.com/?q=вулиця+Уласа+Самчука+21+Львів",
        "description": "Спорткомплекс біля Стрийського парку"
    }
}

TEACHERS_INFO: Dict[str, Dict[str, str]] = {
    "Процах Н.П.": {"role": "Алгебра і геометрія"},
    "Пшеничний О.Ю.": {"role": "Основи програмування (Лекції)"},
    "Климишин Н.Т.": {"role": "Іноземна мова за проф. спрямуванням"},
    "Репетило С.М.": {"role": "Математичний аналіз (Практика)"},
    "Пукач П.Я.": {"role": "Математичний аналіз (Лекції)"},
    "Хома І.Я.": {"role": "Історія державності та культури України"},
    "Мельникова Н.І.": {"role": "Дискретна математика (Лекції)"},
    "Пелещишин О.П.": {"role": "Дискретна математика (Практика)"},
    "Павлик": {"role": "Дискретна математика (Лабораторні)"},
    "Загородний І.І.": {"role": "Основи програмування (Практика)"},
    "Тріска Р.М.": {"role": "Основи програмування (Лабораторні)"},
}

ALL_SUBJECTS = [
    "Алгебра і геометрія",
    "Основи програмування",
    "Математичний аналіз",
    "Дискретна математика",
    "Іноземна мова за професійним спрямуванням",
    "Історія державності та культури України",
    "Фізичне виховання"
]

DAY_NAMES = {
    0: "Понеділок",
    1: "Вівторок",
    2: "Середа",
    3: "Четвер",
    4: "П'ятниця",
    5: "Субота",
    6: "Неділя"
}

@dataclass
class Lesson:
    pair_number: int
    subject: str
    type: str
    teacher: str
    room: str
    subgroup: Optional[int] = None

    @property
    def start_time(self) -> str:
        return BELL_SCHEDULE[self.pair_number]["start"]

    @property
    def end_time(self) -> str:
        return BELL_SCHEDULE[self.pair_number]["end"]

    @property
    def start_minutes(self) -> int:
        return BELL_SCHEDULE[self.pair_number]["start_m"]

    @property
    def end_minutes(self) -> int:
        return BELL_SCHEDULE[self.pair_number]["end_m"]

    @property
    def type_icon(self) -> str:
        if "Лекція" in self.type or "лекція" in self.type:
            return "📖 Лекція"
        elif "Лабораторна" in self.type or "лаб" in self.type:
            return "🔬 Лабораторна"
        return "✍️ Практична"

    @property
    def subject_icon(self) -> str:
        s = self.subject.lower()
        if "програм" in s: return "💻"
        if "алгебр" in s or "геометр" in s: return "📐"
        if "дискретн" in s: return "🔢"
        if "аналіз" in s or "математичн" in s: return "📈"
        if "іноземн" in s or "мов" in s: return "🇬🇧"
        if "історі" in s or "культур" in s: return "🏛"
        if "фізичн" in s or "спорт" in s: return "🏃"
        return "📚"


# FULL SCHEDULE
# 1 = Знаменник (поточний), 2 = Чисельник (наступний)
SCHEDULE: Dict[int, Dict[int, List[Lesson]]] = {
    # 1 = ЗНАМЕННИК (Поточний тиждень)
    1: {
        0: [
            Lesson(1, "Алгебра і геометрія", "Практична", "Процах Н.П.", "109 I н.к."),
            Lesson(2, "Алгебра і геометрія", "Лекція", "Процах Н.П.", "117 I н.к."),
            Lesson(5, "Дискретна математика", "Лабораторна", "Павлик", "125 ХХ н.к."),
        ],
        1: [
            Lesson(1, "Основи програмування", "Лекція", "Пшеничний О.Ю.", "117 I н.к."),
            Lesson(2, "Іноземна мова за професійним спрямуванням, частина 1", "Практична", "Климишин Н.Т.", "018 VII н.к."),
            Lesson(3, "Математичний аналіз", "Практична", "Репетило С.М.", "109 I н.к."),
        ],
        2: [
            Lesson(2, "Фізичне виховання, частина 1", "Практична", "", "Самчука 21"),
            Lesson(3, "Історія державності та культури України", "Лекція", "Хома І.Я.", "117 I н.к."),
            Lesson(4, "Історія державності та культури України", "Практична", "Хома І.Я.", "109 I н.к."),
        ],
        3: [
            Lesson(1, "Алгебра і геометрія", "Лекція", "Процах Н.П.", "117 I н.к."),
            Lesson(2, "Математичний аналіз", "Лекція", "Пукач П.Я.", "117 I н.к."),
            Lesson(3, "Дискретна математика", "Лекція", "Мельникова Н.І.", "218 I н.к."),
        ],
        4: [
            Lesson(2, "Основи програмування", "Практична", "Загородний І.І.", "214 ХХ н.к."),
            Lesson(3, "Основи програмування", "Лабораторна", "Тріска Р.М.", "212 ХХ н.к."),
        ],
        5: [],
        6: [],
    },

    # 2 = ЧИСЕЛЬНИК (Наступний тиждень)
    2: {
        0: [
            Lesson(1, "Алгебра і геометрія", "Практична", "Процах Н.П.", "109 I н.к."),
            Lesson(2, "Алгебра і геометрія", "Лекція", "Процах Н.П.", "117 I н.к."),
            Lesson(5, "Дискретна математика", "Лабораторна", "Павлик", "125 ХХ н.к."),
        ],
        1: [
            Lesson(1, "Основи програмування", "Лекція", "Пшеничний О.Ю.", "117 I н.к."),
            Lesson(2, "Іноземна мова за професійним спрямуванням, частина 1", "Практична", "Климишин Н.Т.", "018 VII н.к."),
            Lesson(3, "Математичний аналіз", "Практична", "Репетило С.М.", "109 I н.к."),
            Lesson(4, "Математичний аналіз", "Практична", "Репетило С.М.", "109 I н.к."),
        ],
        2: [
            Lesson(2, "Фізичне виховання, частина 1", "Практична", "", "Самчука 21"),
            Lesson(3, "Математичний аналіз", "Лекція", "Пукач П.Я.", "117 I н.к."),
        ],
        3: [
            Lesson(2, "Математичний аналіз", "Лекція", "Пукач П.Я.", "117 I н.к."),
            Lesson(3, "Дискретна математика", "Лекція", "Мельникова Н.І.", "218 I н.к."),
        ],
        4: [
            Lesson(1, "Дискретна математика", "Практична", "Пелещишин О.П.", "123б, ХХ н.к."),
            Lesson(2, "Основи програмування", "Практична", "Загородний І.І.", "214 ХХ н.к."),
            Lesson(3, "Основи програмування", "Лабораторна", "Тріска Р.М.", "212 ХХ н.к."),
        ],
        5: [],
        6: [],
    }
}


def get_current_tz_now() -> datetime:
    return datetime.now(pytz.timezone(TIMEZONE_NAME))


def get_week_type(target_date: Optional[date] = None, week_offset: int = 0) -> int:
    """
    Returns 1 (Поточний тиждень / Знаменник) or 2 (Наступний тиждень / Чисельник).
    """
    if target_date is None:
        target_date = get_current_tz_now().date()
    cal = target_date.isocalendar()
    week_num = cal.week + week_offset
    return 1 if (week_num % 2 == 1) else 2


def get_week_name(week_type: int) -> str:
    return "Знаменник" if week_type == 1 else "Чисельник"


def get_day_lessons(day_idx: int, week_type: int, subgroup: int = 1) -> List[Lesson]:
    lessons = SCHEDULE.get(week_type, {}).get(day_idx, [])
    return [l for l in lessons if l.subgroup is None or l.subgroup == subgroup]


def analyze_day_gaps(lessons: List[Lesson]) -> List[Dict[str, Any]]:
    if not lessons:
        return []
    analyzed = []
    prev_lesson: Optional[Lesson] = None
    for i, lesson in enumerate(lessons):
        if i == 0:
            is_first = True
            has_window = False
            gap = 0
            notify_30m = True
        else:
            is_first = False
            gap = lesson.start_minutes - prev_lesson.end_minutes
            has_window = (lesson.pair_number > prev_lesson.pair_number + 1) or (gap > 20)
            notify_30m = has_window

        analyzed.append({
            "lesson": lesson,
            "is_first": is_first,
            "has_window": has_window,
            "gap_minutes": gap,
            "notify_30m": notify_30m,
            "notify_5m": True,
            "prev_lesson": prev_lesson
        })
        prev_lesson = lesson
    return analyzed


# ================= 3. TIME UTILS & MULTILINGUAL PARSER =================

UA_MONTHS = [
    "", "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"
]

MONTH_MAP = {
    "січ": 1, "лют": 2, "бер": 3, "кві": 4, "тра": 5, "чер": 6,
    "лип": 7, "сер": 8, "вер": 9, "жов": 10, "лис": 11, "гру": 12,
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "мая": 5, "июн": 6,
    "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

WEEKDAY_MAP = {
    "пон": 0, "пн": 0, "mon": 0,
    "вів": 1, "вто": 1, "вт": 1, "tue": 1,
    "сер": 2, "сре": 2, "ср": 2, "wed": 2,
    "чет": 3, "чт": 3, "thu": 3,
    "п'я": 4, "пят": 4, "пт": 4, "fri": 4,
    "суб": 5, "сб": 5, "sat": 5,
    "нед": 6, "вос": 6, "вс": 6, "нд": 6, "sun": 6
}


def get_tz() -> pytz.BaseTzInfo:
    return pytz.timezone(TIMEZONE_NAME)


def get_now() -> datetime:
    return datetime.now(get_tz())


def format_ua_date(dt: datetime, include_time: bool = True) -> str:
    month_str = UA_MONTHS[dt.month]
    weekday_str = DAY_NAMES[dt.weekday()]
    if include_time:
        return f"{weekday_str}, {dt.day} {month_str} о {dt.strftime('%H:%M')}"
    return f"{weekday_str}, {dt.day} {month_str}"


def format_time_remaining(target_dt: datetime) -> str:
    now = get_now()
    if target_dt.tzinfo is None:
        target_dt = get_tz().localize(target_dt)
    diff = target_dt - now
    total_seconds = int(diff.total_seconds())

    if total_seconds < 0:
        past_seconds = abs(total_seconds)
        if past_seconds < 60: return "прострочено щойно"
        if past_seconds < 3600: return f"прострочено на {past_seconds // 60} хв"
        if past_seconds < 86400: return f"прострочено на {past_seconds // 3600} год {(past_seconds % 3600) // 60} хв"
        return f"прострочено на {past_seconds // 86400} дн."

    if total_seconds < 60: return "менше хвилини"
    if total_seconds < 3600: return f"{total_seconds // 60} хв"
    if total_seconds < 86400:
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        return f"{h} год {m} хв" if m > 0 else f"{h} год"
    days = total_seconds // 86400
    h = (total_seconds % 86400) // 3600
    return f"{days} дн. {h} год" if h > 0 else f"{days} дн."


def parse_user_deadline_input(user_input: str) -> Optional[datetime]:
    if not user_input:
        return None
    text = user_input.strip().lower().replace("’", "'").replace("`", "'").replace("—", "-")
    now = get_now()
    tz = get_tz()

    # 1. Extract Time (HH:MM or 'о/в HH')
    target_hour = 23
    target_minute = 59
    has_explicit_time = False

    time_match = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', text)
    if time_match:
        target_hour = int(time_match.group(1))
        target_minute = int(time_match.group(2))
        has_explicit_time = True
        text = text[:time_match.start()] + " " + text[time_match.end():]
    else:
        h_match = re.search(r'\b(?:о|в|at)?\s*([01]?\d|2[0-3])\s*(?:год|годин|години|час|часов|часа|ч|h|:00)\b', text)
        if h_match:
            target_hour = int(h_match.group(1))
            target_minute = 0
            has_explicit_time = True
            text = text[:h_match.start()] + " " + text[h_match.end():]
        else:
            o_match = re.search(r'\b(?:о|в)\s+([01]?\d|2[0-3])\b', text)
            if o_match:
                target_hour = int(o_match.group(1))
                target_minute = 0
                has_explicit_time = True
                text = text[:o_match.start()] + " " + text[o_match.end():]

    # 2. Relative Keywords
    if "післязавтра" in text or "послезавтра" in text:
        target_date = (now + timedelta(days=2)).date()
        return tz.localize(datetime.combine(target_date, time(target_hour, target_minute)))

    if "завтра" in text or "tomorrow" in text:
        target_date = (now + timedelta(days=1)).date()
        return tz.localize(datetime.combine(target_date, time(target_hour, target_minute)))

    if "сьогодні" in text or "сегодня" in text or "today" in text:
        dt = datetime.combine(now.date(), time(target_hour, target_minute))
        return tz.localize(dt)

    # 3. "через X днів / дней"
    days_match = re.search(r'через\s+(\d+)\s*(?:дн|день|дні|днів|дня|дней|days?)\b', text)
    if days_match:
        days_to_add = int(days_match.group(1))
        target_date = (now + timedelta(days=days_to_add)).date()
        return tz.localize(datetime.combine(target_date, time(target_hour, target_minute)))

    # 4. "через X годин / часов"
    hours_match = re.search(r'через\s+(\d+)\s*(?:год|годин|години|час|часов|часа|hours?|h)\b', text)
    if hours_match:
        hours_to_add = int(hours_match.group(1))
        return now + timedelta(hours=hours_to_add)

    # 5. "через X хвилин / минут"
    mins_match = re.search(r'через\s+(\d+)\s*(?:хв|хвилин|хвилини|мин|минут|минуты|mins?|m)\b', text)
    if mins_match:
        mins_to_add = int(mins_match.group(1))
        return now + timedelta(minutes=mins_to_add)

    # 6. Full ISO Date: YYYY-MM-DD
    iso_match = re.search(r'\b(\d{4})[./-](\d{1,2})[./-](\d{1,2})\b', text)
    if iso_match:
        try:
            target_date = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            return tz.localize(datetime.combine(target_date, time(target_hour, target_minute)))
        except ValueError:
            pass

    # 7. Numerical Date: DD.MM.YYYY
    date_full_match = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', text)
    if date_full_match:
        try:
            target_date = date(int(date_full_match.group(3)), int(date_full_match.group(2)), int(date_full_match.group(1)))
            return tz.localize(datetime.combine(target_date, time(target_hour, target_minute)))
        except ValueError:
            pass

    # 8. Textual Month Date: e.g. "15 вересня"
    text_month_match = re.search(r'\b(\d{1,2})(?:-[еяй])?\s+([а-яa-z]{3,})\b', text)
    if text_month_match:
        day = int(text_month_match.group(1))
        m_word = text_month_match.group(2)[:3]
        if m_word in MONTH_MAP:
            month = MONTH_MAP[m_word]
            year = now.year
            try:
                target_date = date(year, month, day)
                if target_date < now.date() and month < now.month:
                    target_date = date(year + 1, month, day)
                return tz.localize(datetime.combine(target_date, time(target_hour, target_minute)))
            except ValueError:
                pass

    # 9. Short Numerical Date: DD.MM
    date_short_match = re.search(r'\b(\d{1,2})[./](\d{1,2})\b', text)
    if date_short_match:
        day = int(date_short_match.group(1))
        month = int(date_short_match.group(2))
        year = now.year
        try:
            target_date = date(year, month, day)
            if target_date < now.date() and month < now.month:
                target_date = date(year + 1, month, day)
            return tz.localize(datetime.combine(target_date, time(target_hour, target_minute)))
        except ValueError:
            pass

    # 10. Weekdays
    is_next_week = "наступн" in text or "следующ" in text or "next" in text
    for key, day_idx in WEEKDAY_MAP.items():
        if re.search(r'\b' + re.escape(key), text) or key in text:
            current_day_idx = now.weekday()
            days_ahead = day_idx - current_day_idx
            if days_ahead <= 0 or is_next_week:
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
            return tz.localize(datetime.combine(target_date, time(target_hour, target_minute)))

    # 11. Time only
    if has_explicit_time:
        candidate_dt = tz.localize(datetime.combine(now.date(), time(target_hour, target_minute)))
        if candidate_dt <= now:
            candidate_dt += timedelta(days=1)
        return candidate_dt

    return None


# ================= 4. SAFE HTML FORMATTERS =================

def esc(text: Any) -> str:
    return html.escape(str(text)) if text is not None else ""


def format_lesson_block(lesson: Lesson, is_current: bool = False, is_next: bool = False) -> str:
    room_str = lesson.room
    location_desc = ""
    for campus_code, info in CAMPUS_INFO.items():
        if campus_code in room_str or room_str in campus_code:
            location_desc = f" ({info['address']})"
            break

    status_prefix = ""
    if is_current: status_prefix = "🟢 <b>[ЗАРАЗ ЙДЕ]</b> "
    elif is_next: status_prefix = "⏳ <b>[НАСТУПНА]</b> "

    num_emojis = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣"}
    num_emoji = num_emojis.get(lesson.pair_number, f"<b>{lesson.pair_number}</b>")

    lines = [
        f"{status_prefix}{num_emoji} <b>{lesson.start_time} – {lesson.end_time}</b> | {lesson.subject_icon} <b>{esc(lesson.subject)}</b>",
        f"   {lesson.type_icon}",
    ]
    if lesson.teacher:
        lines.append(f"   👤 {esc(lesson.teacher)}")
    lines.append(f"   📍 <code>{esc(room_str)}</code>{esc(location_desc)}")
    return "\n".join(lines)


def format_day_schedule(target_date: date, week_type: int, subgroup: int = 1, highlight_current: bool = True) -> str:
    day_idx = target_date.weekday()
    day_name = DAY_NAMES.get(day_idx, "День")
    week_title = get_week_name(week_type)
    now = get_now()
    is_today = (target_date == now.date())
    now_minutes = now.hour * 60 + now.minute if is_today else None

    lessons = get_day_lessons(day_idx, week_type, subgroup)
    header = (
        f"📅 <b>{day_name}</b>, {target_date.strftime('%d.%m.%Y')}\n"
        f"🔄 <b>Тиждень:</b> {week_title}\n"
        f"👥 <b>Підгрупа:</b> {subgroup}-а\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if not lessons:
        if day_idx in (5, 6): return header + "🎉 <b>Вихідний день!</b> Пар немає, відпочивай! 🏖️"
        return header + "✨ <b>Сьогодні пар немає!</b> Вільний день 🚀"

    analyzed = analyze_day_gaps(lessons)
    body_parts = []
    for item in analyzed:
        lesson: Lesson = item["lesson"]
        if item["has_window"]:
            gap_h = item["gap_minutes"] // 60
            gap_m = item["gap_minutes"] % 60
            gap_str = f"{gap_h} год {gap_m} хв" if gap_h > 0 else f"{gap_m} хв"
            body_parts.append(f"\n☕️ <b>— ВІКНО {gap_str} —</b>\n")
            
        is_cur = False
        is_nxt = False
        if is_today and highlight_current and now_minutes is not None:
            if lesson.start_minutes <= now_minutes <= lesson.end_minutes: is_cur = True
            elif now_minutes < lesson.start_minutes:
                prev = item["prev_lesson"]
                if prev is None or now_minutes > prev.end_minutes: is_nxt = True

        body_parts.append(format_lesson_block(lesson, is_current=is_cur, is_next=is_nxt))

    return header + "\n\n".join(body_parts)


def format_week_schedule(week_type: int, subgroup: int = 1) -> str:
    week_title = get_week_name(week_type)
    text = [
        f"🗓 <b>Повний розклад на тиждень</b>\n"
        f"🔄 <b>{week_title}</b> | 👥 <b>{subgroup}-а підгрупа</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    for day_idx in range(5):
        day_name = DAY_NAMES[day_idx]
        lessons = get_day_lessons(day_idx, week_type, subgroup)
        text.append(f"📌 <b>{day_name.upper()}</b>")
        if not lessons:
            text.append("   <i>Пар немає</i>\n")
            continue
        for l in lessons:
            text.append(f"• <b>{l.pair_number} пара ({l.start_time}-{l.end_time}):</b> {l.subject_icon} {esc(l.subject)} | {l.type} (<code>{esc(l.room)}</code>)")
        text.append("")
    return "\n".join(text)


def format_live_status(subgroup: int = 1, week_offset: int = 0) -> str:
    now = get_now()
    now_date = now.date()
    day_idx = now_date.weekday()
    week_type = get_week_type(now_date, week_offset)

    if day_idx in (5, 6):
        return f"🏖️ <b>Зараз вихідний день! ({DAY_NAMES[day_idx]})</b>\n\nНасолоджуйся відпочинком перед навчальним тижнем. ☕️"

    lessons = get_day_lessons(day_idx, week_type, subgroup)
    if not lessons:
        return f"✨ <b>Сьогодні ({DAY_NAMES[day_idx]}) пар немає!</b>\n\nВільний день для відпочинку або домашки. 📚"

    now_minutes = now.hour * 60 + now.minute
    first_lesson = lessons[0]

    if now_minutes < first_lesson.start_minutes:
        diff_mins = first_lesson.start_minutes - now_minutes
        time_str = f"{diff_mins // 60} год {diff_mins % 60} хв" if diff_mins >= 60 else f"{diff_mins} хв"
        return f"🌅 <b>До початку першої пари залишилось:</b> {time_str}\n\n1️⃣ <b>Перша пара о {first_lesson.start_time}:</b>\n{format_lesson_block(first_lesson, is_next=True)}"

    for lesson in lessons:
        if lesson.start_minutes <= now_minutes <= lesson.end_minutes:
            left_mins = lesson.end_minutes - now_minutes
            next_lesson = next((l for l in lessons if l.start_minutes > lesson.end_minutes), None)
            next_info = f"\n\n⏳ <b>Далі ({next_lesson.start_time}):</b> {esc(next_lesson.subject)}" if next_lesson else "\n\n🏁 <b>Це остання пара на сьогодні!</b>"
            return f"🟢 <b>ЗАРАЗ ТРИВАЄ ПАРА</b> (до кінця {left_mins} хв):\n\n{format_lesson_block(lesson, is_current=True)}{next_info}"

    for i in range(len(lessons) - 1):
        cur, nxt = lessons[i], lessons[i + 1]
        if cur.end_minutes < now_minutes < nxt.start_minutes:
            until_next = nxt.start_minutes - now_minutes
            gap = nxt.start_minutes - cur.end_minutes
            status_title = f"☕️ <b>Зараз перерва</b> ({until_next} хв)" if gap <= 20 else f"🪟 <b>Зараз вікно</b> ({until_next // 60}г {until_next % 60}хв)"
            return f"{status_title}\n\n⏳ <b>Наступна пара ({nxt.start_time}):</b>\n{format_lesson_block(nxt, is_next=True)}"

    last_lesson = lessons[-1]
    if now_minutes > last_lesson.end_minutes:
        return f"🎉 <b>Всі пари на сьогодні завершено!</b>\n\nОстання пара закінчилась о {last_lesson.end_time}. Гарного вечора! 🌙"

    return "Статус оновлюється..."


def format_bells_message() -> str:
    return "\n".join([
        "⏰ <b>Розклад дзвінків та перерв:</b>\n",
        "1️⃣  <b>1 пара:</b>  <code>08:30 — 09:50</code>  <i>(перерва 15 хв)</i>",
        "2️⃣  <b>2 пара:</b>  <code>10:05 — 11:25</code>  <i>(перерва 15 хв)</i>",
        "3️⃣  <b>3 пара:</b>  <code>11:40 — 13:00</code>  <i>(перерва 15 хв)</i>",
        "4️⃣  <b>4 пара:</b>  <code>13:15 — 14:35</code>  <i>(перерва 15 хв)</i>",
        "5️⃣  <b>5 пара:</b>  <code>14:50 — 16:10</code>\n",
        "📌 <b>Тривалість пари:</b> 1 год 20 хв (80 хв)",
        "☕️ <b>Тривалість перерви:</b> 15 хв"
    ])


def format_homework_item(hw: Dict[str, Any], idx: int) -> str:
    prio_badges = {"high": "🔥 <b>Терміново</b>", "normal": "🟡 <b>Звичайно</b>", "low": "🟢 <b>Не терміново</b>"}
    badge = prio_badges.get(hw.get("priority", "normal"), "")
    status = "✅ <b>Виконано</b>" if hw.get("is_completed") else "⏳ <b>В процесі</b>"
    
    try:
        dt = datetime.strptime(hw["deadline"], "%Y-%m-%d %H:%M:%S")
        dl_line = f"⏰ <b>Дедлайн:</b> {format_ua_date(dt)} <i>({format_time_remaining(dt)})</i>"
    except Exception:
        dl_line = f"⏰ <b>Дедлайн:</b> <code>{esc(hw['deadline'])}</code>"

    return (
        f"📝 <b>Завдання #{idx}</b> | {status}\n"
        f"📚 <b>Предмет:</b> {esc(hw['subject'])}\n"
        f"📌 <b>Завдання:</b> {esc(hw['task_text'])}\n"
        f"{dl_line}\n"
        f"⚡️ <b>Пріоритет:</b> {badge}"
    )


def format_campuses_message() -> str:
    text = ["🏛 <b>Корпуси та локації Львівської Політехніки:</b>\n"]
    for code, info in CAMPUS_INFO.items():
        text.append(f"📍 <b>{code}</b> — {esc(info['name'])}\n   🏢 Адреса: <code>{esc(info['address'])}</code>\n   🗺 <a href=\"{info['maps_url']}\">Відкрити в Google Maps</a>\n")
    return "\n".join(text)


def format_teachers_message() -> str:
    text = ["👨‍🏫 <b>Викладачі групи ШІ-11:</b>\n"]
    for short, info in TEACHERS_INFO.items():
        text.append(f"👤 <b>{esc(short)}</b>\n   📚 {esc(info['role'])}\n")
    return "\n".join(text)


# ================= 5. ASYNC SQLITE DATABASE =================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                subgroup INTEGER DEFAULT 1,
                notify_30m INTEGER DEFAULT 1,
                notify_5m INTEGER DEFAULT 1,
                morning_summary INTEGER DEFAULT 1,
                morning_time TEXT DEFAULT '07:30',
                evening_summary INTEGER DEFAULT 1,
                evening_time TEXT DEFAULT '21:00',
                notify_deadlines INTEGER DEFAULT 1,
                custom_week_offset INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS homework (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                task_text TEXT NOT NULL,
                deadline TIMESTAMP NOT NULL,
                priority TEXT DEFAULT 'normal',
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subject_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                note_title TEXT NOT NULL,
                note_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_key TEXT NOT NULL UNIQUE,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_hw_user ON homework (user_id, is_completed);")
        await db.commit()


async def register_or_update_user(user_id: int, chat_id: int, username: Optional[str], first_name: Optional[str]) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                await db.execute("UPDATE users SET chat_id = ?, username = ?, first_name = ? WHERE user_id = ?", (chat_id, username, first_name, user_id))
                await db.commit()
                return dict(row)
            else:
                await db.execute("""
                    INSERT INTO users (user_id, chat_id, username, first_name, subgroup, notify_30m, notify_5m, morning_summary, morning_time, evening_summary, evening_time, notify_deadlines, custom_week_offset)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, chat_id, username, first_name, DEFAULT_SETTINGS["subgroup"], DEFAULT_SETTINGS["notify_30m"], DEFAULT_SETTINGS["notify_5m"], DEFAULT_SETTINGS["morning_summary"], DEFAULT_SETTINGS["morning_time"], DEFAULT_SETTINGS["evening_summary"], DEFAULT_SETTINGS["evening_time"], DEFAULT_SETTINGS["notify_deadlines"], 0))
                await db.commit()
                return await get_user(user_id)


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_active_users() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def update_user_setting(user_id: int, key: str, value: Any):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()


async def add_homework(user_id: int, subject: str, task_text: str, deadline: datetime, priority: str = "normal") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO homework (user_id, subject, task_text, deadline, priority, is_completed)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (user_id, subject, task_text, deadline.strftime("%Y-%m-%d %H:%M:%S"), priority))
        await db.commit()
        return cur.lastrowid


async def get_homework_list(user_id: int, completed: Optional[bool] = False) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM homework WHERE user_id = ?"
        params = [user_id]
        if completed is not None:
            query += " AND is_completed = ?"
            params.append(1 if completed else 0)
        query += " ORDER BY is_completed ASC, deadline ASC"
        async with db.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_homework_by_id(hw_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM homework WHERE id = ? AND user_id = ?", (hw_id, user_id)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def toggle_homework_status(hw_id: int, user_id: int) -> Optional[bool]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT is_completed FROM homework WHERE id = ? AND user_id = ?", (hw_id, user_id)) as cur:
            row = await cur.fetchone()
            if not row: return None
            new_st = 0 if row["is_completed"] == 1 else 1
            comp_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_st == 1 else None
            await db.execute("UPDATE homework SET is_completed = ?, completed_at = ? WHERE id = ? AND user_id = ?", (new_st, comp_at, hw_id, user_id))
            await db.commit()
            return bool(new_st)


async def delete_homework(hw_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM homework WHERE id = ? AND user_id = ?", (hw_id, user_id))
        await db.commit()
        return cur.rowcount > 0


async def get_all_pending_deadlines() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT h.*, u.chat_id, u.notify_deadlines, u.first_name
            FROM homework h
            JOIN users u ON h.user_id = u.user_id
            WHERE h.is_completed = 0 AND u.notify_deadlines = 1
            ORDER BY h.deadline ASC
        """) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def add_note(user_id: int, subject: str, note_title: str, note_content: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO subject_notes (user_id, subject, note_title, note_content) VALUES (?, ?, ?, ?)", (user_id, subject, note_title, note_content))
        await db.commit()
        return cur.lastrowid


async def get_notes_for_subject(user_id: int, subject: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM subject_notes WHERE (user_id = ? OR user_id = 0) AND subject = ? ORDER BY created_at DESC", (user_id, subject)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def delete_note(note_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM subject_notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        await db.commit()
        return cur.rowcount > 0


async def record_notification_sent(user_id: int, notification_key: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO sent_notifications (user_id, notification_key) VALUES (?, ?)", (user_id, notification_key))
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False


async def clean_old_notifications(days: int = 7):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sent_notifications WHERE sent_at < datetime('now', '-' || ? || ' days')", (days,))
        await db.commit()


# ================= 6. KEYBOARDS =================

def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📱 Відкрити Web App (Розклад & Дедлайни)", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="📅 Сьогодні"), KeyboardButton(text="🌅 Завтра")],
        [KeyboardButton(text="🗓 На тиждень"), KeyboardButton(text="⏳ Зараз / Наступна")],
        [KeyboardButton(text="📝 Домашка / Дедлайни"), KeyboardButton(text="➕ Додати ДЗ")],
        [KeyboardButton(text="⏰ Дзвінки"), KeyboardButton(text="🏛 Корпуси"), KeyboardButton(text="⚙️ Налаштування")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Оберіть пункт меню...")


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Скасувати")]], resize_keyboard=True)


def get_start_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📱 Відкрити Web App (Розклад & Завдання)", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])


def get_schedule_nav_keyboard(current_week: int, selected_day: Optional[int] = None) -> InlineKeyboardMarkup:
    short_names = ["Пн", "Вт", "Ср", "Чт", "Пт"]
    days_row = [
        InlineKeyboardButton(text=f"{'👉 ' if selected_day == i else ''}{name}", callback_data=f"sched_day_{i}_{current_week}")
        for i, name in enumerate(short_names)
    ]
    other_week = 2 if current_week == 1 else 1
    other_name = "По чисельнику" if current_week == 1 else "По знаменнику"
    return InlineKeyboardMarkup(inline_keyboard=[
        days_row,
        [InlineKeyboardButton(text=f"🔄 Переглянути {other_name}", callback_data=f"sched_switch_week_{other_week}")],
        [InlineKeyboardButton(text="📊 Повний розклад на цей тиждень", callback_data=f"sched_full_week_{current_week}")]
    ])


def get_homework_item_keyboard(hw_id: int, is_completed: bool) -> InlineKeyboardMarkup:
    status_text = "↩️ Відновити" if is_completed else "✅ Виконано"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=status_text, callback_data=f"hw_toggle_{hw_id}"),
        InlineKeyboardButton(text="🗑 Видалити", callback_data=f"hw_del_{hw_id}")
    ]])


def get_homework_menu_keyboard(filter_completed: bool = False) -> InlineKeyboardMarkup:
    toggle_text = "📁 Показати активні" if filter_completed else "✅ Показати виконані"
    next_filter = 0 if filter_completed else 1
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати нове завдання", callback_data="hw_add_start")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"hw_view_filter_{next_filter}")]
    ])


def get_subjects_keyboard(prefix: str) -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(text=f"📚 {s}", callback_data=f"{prefix}_{s[:25]}")] for s in ALL_SUBJECTS]
    kb.append([InlineKeyboardButton(text="✍️ Інший предмет (ввести вручну)", callback_data=f"{prefix}_custom")])
    kb.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_action")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_priority_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Терміново (Високий)", callback_data="hw_prio_high")],
        [InlineKeyboardButton(text="🟡 Звичайно (Середній)", callback_data="hw_prio_normal")],
        [InlineKeyboardButton(text="🟢 Не терміново (Низький)", callback_data="hw_prio_low")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_action")]
    ])


def get_quick_deadline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сьогодні 23:59", callback_data="hw_dl_today_2359"), InlineKeyboardButton(text="Завтра 23:59", callback_data="hw_dl_tmrw_2359")],
        [InlineKeyboardButton(text="Через 2 дні", callback_data="hw_dl_2days"), InlineKeyboardButton(text="Через 3 дні", callback_data="hw_dl_3days")],
        [InlineKeyboardButton(text="До наступного понеділка", callback_data="hw_dl_next_mon"), InlineKeyboardButton(text="До п'ятниці", callback_data="hw_dl_friday")],
        [InlineKeyboardButton(text="⌨️ Ввести дату вручну текстом", callback_data="hw_dl_manual")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_action")]
    ])


def get_settings_keyboard(u: Dict[str, Any]) -> InlineKeyboardMarkup:
    chk = lambda v: "✅ Увімкнено" if v else "❌ Вимкнено"
    subgroup = u.get("subgroup", 1)
    offset = u.get("custom_week_offset", 0)
    parity = "За календарем" if offset == 0 else "Зміщено (інверсія)"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔔 30 хв (1 пара/вікно): {chk(u.get('notify_30m', 1))}", callback_data="cfg_toggle_notify_30m")],
        [InlineKeyboardButton(text=f"⏱ 5 хв до кожної пари: {chk(u.get('notify_5m', 1))}", callback_data="cfg_toggle_notify_5m")],
        [InlineKeyboardButton(text=f"🌅 Ранковий розклад ({u.get('morning_time', '07:30')}): {chk(u.get('morning_summary', 1))}", callback_data="cfg_toggle_morning_summary")],
        [InlineKeyboardButton(text=f"🌙 Вечірній дайджест ({u.get('evening_time', '21:00')}): {chk(u.get('evening_summary', 1))}", callback_data="cfg_toggle_evening_summary")],
        [InlineKeyboardButton(text=f"⏳ Нагадування дедлайнів: {chk(u.get('notify_deadlines', 1))}", callback_data="cfg_toggle_notify_deadlines")],
        [InlineKeyboardButton(text=f"👥 Підгрупа: {subgroup}-а (Змінити)", callback_data="cfg_toggle_subgroup")],
        [InlineKeyboardButton(text=f"🔄 Тиждень: {parity}", callback_data="cfg_toggle_week_offset")],
        [InlineKeyboardButton(text="👨‍🏫 Викладачі", callback_data="info_teachers"), InlineKeyboardButton(text="🏛 Корпуси", callback_data="info_campuses")]
    ])


# ================= 7. FSM STATES =================

class AddHomeworkFSM(StatesGroup):
    waiting_for_subject = State()
    waiting_for_task = State()
    waiting_for_deadline = State()
    waiting_for_priority = State()

class AddNoteFSM(StatesGroup):
    waiting_for_subject = State()
    waiting_for_title = State()
    waiting_for_content = State()


# ================= 8. ROUTERS & HANDLERS =================

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    if not user: return
    db_user = await register_or_update_user(user.id, message.chat.id, user.username, user.first_name)
    now = get_now()
    week_title = get_week_name(get_week_type(now.date(), db_user.get("custom_week_offset", 0)))
    first_name_esc = esc(user.first_name or "студенте")

    welcome_text = (
        f"👋 <b>Привіт, {first_name_esc}!</b>\n\n"
        f"Я твій <b>розумний помічник з розкладу та дедлайнів</b> для групи <b>ШІ-11</b> 🎓\n\n"
        f"📅 <b>Поточний тиждень:</b> <code>{esc(week_title)}</code>\n"
        f"👥 <b>Підгрупа:</b> <code>{db_user.get('subgroup', 1)}-а</code>\n\n"
        f"✨ <b>Доступний Web App!</b>\n"
        f"Натискай кнопку нижче, щоб відкрити інтерактивний додаток з красивим розкладом та дедлайнами 👇"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_start_inline_keyboard())
    await message.answer("Головне меню 👇", reply_markup=get_main_keyboard())


@router.message(Command("app"))
@router.message(Command("webapp"))
async def cmd_app(message: Message):
    await message.answer("📱 <b>Інтерактивний Web App для групи ШІ-11</b>\n\nНатисніть кнопку нижче, щоб відкрити додаток:", parse_mode="HTML", reply_markup=get_start_inline_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "ℹ️ <b>Довідка по командам:</b>\n\n"
        "/app — Відкрити Web App\n"
        "/today — Розклад на сьогодні\n"
        "/tomorrow — Розклад на завтра\n"
        "/week — Повний розклад на тиждень\n"
        "/now — Яка пара зараз і яка наступна\n"
        "/hw — Список домашніх завдань та дедлайнів\n"
        "/add — Додати нове завдання\n"
        "/bells — Розклад дзвінків\n"
        "/campuses — Корпуси та адреси\n"
        "/teachers — Викладачі\n"
        "/notes — Матеріали та конспекти\n"
        "/find — Пошук по розкладу\n"
        "/settings — Налаштування сповіщень\n\n"
        "🔔 <b>Сповіщення:</b> 30 хв (1 пара/вікно), 5 хв (кожна пара), дедлайни (48г, 24г, 3г, 1г, 15хв)."
    )
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())


@router.message(F.text == "📅 Сьогодні")
@router.message(Command("today"))
async def handle_today_schedule(message: Message):
    now = get_now()
    user = await get_user(message.from_user.id)
    subgroup = user.get("subgroup", 1) if user else 1
    offset = user.get("custom_week_offset", 0) if user else 0
    week_type = get_week_type(now.date(), offset)
    text = format_day_schedule(now.date(), week_type, subgroup, highlight_current=True)
    kb = get_schedule_nav_keyboard(week_type, selected_day=now.weekday() if now.weekday() < 5 else None)
    await message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


@router.message(F.text == "🌅 Завтра")
@router.message(Command("tomorrow"))
async def handle_tomorrow_schedule(message: Message):
    now = get_now()
    tmrw = now.date() + timedelta(days=1)
    user = await get_user(message.from_user.id)
    subgroup = user.get("subgroup", 1) if user else 1
    offset = user.get("custom_week_offset", 0) if user else 0
    week_type = get_week_type(tmrw, offset)
    text = format_day_schedule(tmrw, week_type, subgroup, highlight_current=False)
    kb = get_schedule_nav_keyboard(week_type, selected_day=tmrw.weekday() if tmrw.weekday() < 5 else None)
    await message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


@router.message(F.text == "🗓 На тиждень")
@router.message(Command("week"))
async def handle_week_schedule(message: Message):
    now = get_now()
    user = await get_user(message.from_user.id)
    subgroup = user.get("subgroup", 1) if user else 1
    offset = user.get("custom_week_offset", 0) if user else 0
    week_type = get_week_type(now.date(), offset)
    text = format_week_schedule(week_type, subgroup)
    kb = get_schedule_nav_keyboard(week_type)
    await message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


@router.message(F.text == "⏳ Зараз / Наступна")
@router.message(Command("now"))
async def handle_now_pair(message: Message):
    user = await get_user(message.from_user.id)
    subgroup = user.get("subgroup", 1) if user else 1
    offset = user.get("custom_week_offset", 0) if user else 0
    text = format_live_status(subgroup, offset)
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(F.text == "⏰ Дзвінки")
@router.message(Command("bells"))
async def handle_bells(message: Message):
    await message.answer(format_bells_message(), parse_mode="HTML")


@router.message(F.text == "🏛 Корпуси")
@router.message(Command("campuses"))
async def handle_campuses(message: Message):
    await message.answer(format_campuses_message(), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("teachers"))
async def handle_teachers(message: Message):
    await message.answer(format_teachers_message(), parse_mode="HTML")


@router.callback_query(F.data.startswith("sched_day_"))
async def callback_sched_day(callback: CallbackQuery):
    parts = callback.data.split("_")
    day_idx, week_type = int(parts[2]), int(parts[3])
    user = await get_user(callback.from_user.id)
    subgroup = user.get("subgroup", 1) if user else 1
    now = get_now()
    target_date = now.date() + timedelta(days=(day_idx - now.weekday()))
    text = format_day_schedule(target_date, week_type, subgroup, highlight_current=True)
    kb = get_schedule_nav_keyboard(week_type, selected_day=day_idx)
    try: await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    except Exception: pass
    await callback.answer()


@router.callback_query(F.data.startswith("sched_switch_week_"))
async def callback_sched_switch_week(callback: CallbackQuery):
    week_type = int(callback.data.split("_")[3])
    user = await get_user(callback.from_user.id)
    subgroup = user.get("subgroup", 1) if user else 1
    text = format_week_schedule(week_type, subgroup)
    kb = get_schedule_nav_keyboard(week_type)
    try: await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    except Exception: pass
    await callback.answer(f"Відображено розклад: {get_week_name(week_type)}")


@router.callback_query(F.data.startswith("sched_full_week_"))
async def callback_sched_full_week(callback: CallbackQuery):
    week_type = int(callback.data.split("_")[3])
    user = await get_user(callback.from_user.id)
    subgroup = user.get("subgroup", 1) if user else 1
    text = format_week_schedule(week_type, subgroup)
    kb = get_schedule_nav_keyboard(week_type)
    try: await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    except Exception: pass
    await callback.answer()


@router.callback_query(F.data == "info_teachers")
async def callback_info_teachers(callback: CallbackQuery):
    await callback.message.answer(format_teachers_message(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "info_campuses")
async def callback_info_campuses(callback: CallbackQuery):
    await callback.message.answer(format_campuses_message(), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


# ================= HOMEWORK HANDLERS =================

@router.message(F.text == "📝 Домашка / Дедлайни")
@router.message(Command("hw"))
async def handle_view_homework(message: Message, show_completed: bool = False):
    user_id = message.from_user.id
    hw_list = await get_homework_list(user_id, completed=show_completed)
    if not hw_list:
        status_word = "виконаних" if show_completed else "активних"
        await message.answer(f"📋 <b>Список {status_word} завдань порожній!</b>\n\nНатисни кнопку нижче, щоб додати перше завдання 👇", parse_mode="HTML", reply_markup=get_homework_menu_keyboard(filter_completed=show_completed))
        return

    title = "✅ <b>Виконані завдання:</b>" if show_completed else "📝 <b>Активні завдання та дедлайни:</b>"
    await message.answer(f"{title}\nВсього завдань: {len(hw_list)}\n━━━━━━━━━━━━━━━━━━━━━━", parse_mode="HTML")
    for idx, hw in enumerate(hw_list, 1):
        await message.answer(format_homework_item(hw, idx), parse_mode="HTML", reply_markup=get_homework_item_keyboard(hw["id"], bool(hw["is_completed"])))
    await message.answer("⚡️ <b>Керування списком:</b>", parse_mode="HTML", reply_markup=get_homework_menu_keyboard(filter_completed=show_completed))


@router.message(F.text == "❌ Скасувати", StateFilter("*"))
@router.callback_query(F.data == "cancel_action", StateFilter("*"))
async def handle_cancel(event: Union[Message, CallbackQuery], state: FSMContext):
    await state.clear()
    text = "❌ Дію скасовано. Повертаю до головного меню."
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=get_main_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_main_keyboard())


@router.message(F.text == "➕ Додати ДЗ")
@router.message(Command("add"))
@router.callback_query(F.data == "hw_add_start")
async def start_add_homework(event: Union[Message, CallbackQuery], state: FSMContext):
    await state.clear()
    await state.set_state(AddHomeworkFSM.waiting_for_subject)
    prompt = "📚 <b>Крок 1/4: Оберіть предмет</b>\n\nНатисніть кнопку зі списку або оберіть «Ввести вручну» 👇"
    kb = get_subjects_keyboard("hw_subj")
    if isinstance(event, CallbackQuery):
        await event.message.answer(prompt, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(prompt, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("hw_subj_"), AddHomeworkFSM.waiting_for_subject)
async def process_subject_btn(callback: CallbackQuery, state: FSMContext):
    data_val = callback.data.replace("hw_subj_", "")
    if data_val == "custom":
        await callback.message.answer("✍️ Введіть повну назву предмету текстом:", reply_markup=get_cancel_keyboard())
        await callback.answer()
        return
    matched = next((s for s in ALL_SUBJECTS if s.startswith(data_val)), data_val)
    await state.update_data(subject=matched)
    await state.set_state(AddHomeworkFSM.waiting_for_task)
    await callback.message.answer(f"✅ Предмет: <b>{esc(matched)}</b>\n\n📝 <b>Крок 2/4: Опишіть завдання</b>\nВведіть текст завдання:", parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(AddHomeworkFSM.waiting_for_subject)
async def process_subject_text(message: Message, state: FSMContext):
    subj = message.text.strip()
    if not subj: return
    await state.update_data(subject=subj)
    await state.set_state(AddHomeworkFSM.waiting_for_task)
    await message.answer(f"✅ Предмет: <b>{esc(subj)}</b>\n\n📝 <b>Крок 2/4: Опишіть завдання</b>\nВведіть текст завдання:", parse_mode="HTML", reply_markup=get_cancel_keyboard())


@router.message(AddHomeworkFSM.waiting_for_task)
async def process_task_text(message: Message, state: FSMContext):
    task = message.text.strip()
    if not task: return
    await state.update_data(task_text=task)
    await state.set_state(AddHomeworkFSM.waiting_for_deadline)
    await message.answer("✅ Завдання записано!\n\n⏰ <b>Крок 3/4: Вкажіть дедлайн</b>\n\nОберіть швидкий варіант або введіть свій:\n<i>(наприклад: «завтра 18:00», «15.09 23:59», «через 3 дні»)</i> 👇", parse_mode="HTML", reply_markup=get_quick_deadline_keyboard())


@router.callback_query(F.data.startswith("hw_dl_"), AddHomeworkFSM.waiting_for_deadline)
async def process_deadline_btn(callback: CallbackQuery, state: FSMContext):
    dl_type = callback.data.replace("hw_dl_", "")
    if dl_type == "manual":
        await callback.message.answer("⌨️ Введіть дедлайн текстом <i>(наприклад: «завтра о 20:00», «15.09 23:59», «п'ятниця 18:00»)</i>:", parse_mode="HTML", reply_markup=get_cancel_keyboard())
        await callback.answer()
        return

    mapping = {
        "today_2359": "сьогодні 23:59", "tmrw_2359": "завтра 23:59",
        "2days": "через 2 дні 23:59", "3days": "через 3 дні 23:59",
        "next_mon": "наступний понеділок 08:30", "friday": "п'ятниця 23:59"
    }
    target_dt = parse_user_deadline_input(mapping.get(dl_type, "завтра 23:59"))
    if not target_dt: return
    await state.update_data(deadline=target_dt.strftime("%Y-%m-%d %H:%M:%S"))
    await state.set_state(AddHomeworkFSM.waiting_for_priority)
    await callback.message.answer(f"⏰ Дедлайн: <b>{format_ua_date(target_dt)}</b> <i>(залишилось {format_time_remaining(target_dt)})</i>\n\n⚡️ <b>Крок 4/4: Оберіть пріоритет:</b>", parse_mode="HTML", reply_markup=get_priority_keyboard())
    await callback.answer()


@router.message(AddHomeworkFSM.waiting_for_deadline)
async def process_deadline_text(message: Message, state: FSMContext):
    target_dt = parse_user_deadline_input(message.text)
    if not target_dt:
        await message.answer("⚠️ Не вдалося розпізнати дату. Спробуйте: <code>завтра 20:00</code>, <code>15.09 23:59</code>, <code>через 3 дні</code>", parse_mode="HTML")
        return
    await state.update_data(deadline=target_dt.strftime("%Y-%m-%d %H:%M:%S"))
    await state.set_state(AddHomeworkFSM.waiting_for_priority)
    await message.answer(f"⏰ Дедлайн: <b>{format_ua_date(target_dt)}</b> <i>(залишилось {format_time_remaining(target_dt)})</i>\n\n⚡️ <b>Крок 4/4: Оберіть пріоритет:</b>", parse_mode="HTML", reply_markup=get_priority_keyboard())


@router.callback_query(F.data.startswith("hw_prio_"), AddHomeworkFSM.waiting_for_priority)
async def process_priority_btn(callback: CallbackQuery, state: FSMContext):
    prio = callback.data.replace("hw_prio_", "")
    data = await state.get_data()
    await state.clear()
    subject = data.get("subject", "Предмет")
    task_text = data.get("task_text", "")
    deadline_dt = datetime.strptime(data.get("deadline"), "%Y-%m-%d %H:%M:%S")
    await add_homework(callback.from_user.id, subject, task_text, deadline_dt, prio)

    prio_titles = {"high": "🔥 Високий", "normal": "🟡 Звичайний", "low": "🟢 Низький"}
    msg = (
        f"🎉 <b>Завдання успішно додано!</b>\n\n"
        f"📚 <b>Предмет:</b> {esc(subject)}\n"
        f"📌 <b>Завдання:</b> {esc(task_text)}\n"
        f"⏰ <b>Дедлайн:</b> {format_ua_date(deadline_dt)} <i>(через {format_time_remaining(deadline_dt)})</i>\n"
        f"⚡️ <b>Пріоритет:</b> {prio_titles.get(prio, prio)}\n\n"
        f"🔔 Сповіщення прийдуть за 2 дні, 1 день, 3 години, 1 годину та 15 хвилин!"
    )
    await callback.message.answer(msg, parse_mode="HTML", reply_markup=get_main_keyboard())
    await callback.answer("Збережено!")


@router.callback_query(F.data.startswith("hw_toggle_"))
async def callback_toggle_hw(callback: CallbackQuery):
    hw_id = int(callback.data.replace("hw_toggle_", ""))
    new_status = await toggle_homework_status(hw_id, callback.from_user.id)
    if new_status is None: return
    hw = await get_homework_by_id(hw_id, callback.from_user.id)
    if hw:
        try: await callback.message.edit_text(format_homework_item(hw, 1), parse_mode="HTML", reply_markup=get_homework_item_keyboard(hw_id, bool(new_status)))
        except Exception: pass
    await callback.answer("🎉 Відмічено виконаним!" if new_status else "↩️ Повернуто до активних.")


@router.callback_query(F.data.startswith("hw_del_"))
async def callback_del_hw(callback: CallbackQuery):
    hw_id = int(callback.data.replace("hw_del_", ""))
    if await delete_homework(hw_id, callback.from_user.id):
        try: await callback.message.edit_text("🗑 <b>Завдання видалено.</b>", parse_mode="HTML")
        except Exception: pass
        await callback.answer("Видалено!")


@router.callback_query(F.data.startswith("hw_view_filter_"))
async def callback_filter_hw(callback: CallbackQuery):
    show_completed = bool(int(callback.data.replace("hw_view_filter_", "")))
    hw_list = await get_homework_list(callback.from_user.id, completed=show_completed)
    status_word = "виконаних" if show_completed else "активних"
    if not hw_list:
        try: await callback.message.edit_text(f"📋 <b>Список {status_word} завдань порожній!</b>", parse_mode="HTML", reply_markup=get_homework_menu_keyboard(filter_completed=show_completed))
        except Exception: pass
        await callback.answer()
        return

    await callback.message.delete()
    title = "✅ <b>Виконані завдання:</b>" if show_completed else "📝 <b>Активні завдання та дедлайни:</b>"
    await callback.message.answer(f"{title}\nВсього завдань: {len(hw_list)}\n━━━━━━━━━━━━━━━━━━━━━━", parse_mode="HTML")
    for idx, hw in enumerate(hw_list, 1):
        await callback.message.answer(format_homework_item(hw, idx), parse_mode="HTML", reply_markup=get_homework_item_keyboard(hw["id"], bool(hw["is_completed"])))
    await callback.message.answer("⚡️ <b>Керування списком:</b>", parse_mode="HTML", reply_markup=get_homework_menu_keyboard(filter_completed=show_completed))
    await callback.answer()


# ================= SETTINGS & NOTES HANDLERS =================

@router.message(F.text == "⚙️ Налаштування")
@router.message(Command("settings"))
async def handle_settings(message: Message):
    user = await get_user(message.from_user.id) or await register_or_update_user(message.from_user.id, message.chat.id, message.from_user.username, message.from_user.first_name)
    now = get_now()
    week_title = get_week_name(get_week_type(now.date(), user.get("custom_week_offset", 0)))
    text = f"⚙️ <b>Налаштування бота</b>\n\n👤 <b>Студент:</b> {esc(message.from_user.first_name or 'Користувач')}\n👥 <b>Підгрупа:</b> {user.get('subgroup', 1)}-а\n📅 <b>Поточний розклад:</b> <code>{esc(week_title)}</code>\n\n🔔 <b>Керування сповіщеннями:</b>"
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard(user))


@router.callback_query(F.data.startswith("cfg_toggle_"))
async def callback_toggle_setting(callback: CallbackQuery):
    key = callback.data.replace("cfg_toggle_", "")
    user = await get_user(callback.from_user.id)
    if not user: return

    if key == "subgroup":
        new_val = 2 if user.get("subgroup", 1) == 1 else 1
        await update_user_setting(callback.from_user.id, "subgroup", new_val)
        await callback.answer(f"Обрано {new_val}-у підгрупу!")
    elif key == "week_offset":
        new_val = 1 if user.get("custom_week_offset", 0) == 0 else 0
        await update_user_setting(callback.from_user.id, "custom_week_offset", new_val)
        now = get_now()
        await callback.answer(f"Тиждень: {get_week_name(get_week_type(now.date(), new_val))}")
    else:
        new_val = 0 if user.get(key, 1) == 1 else 1
        await update_user_setting(callback.from_user.id, key, new_val)
        await callback.answer("Увімкнено!" if new_val else "Вимкнено!")

    updated = await get_user(callback.from_user.id)
    now = get_now()
    week_title = get_week_name(get_week_type(now.date(), updated.get("custom_week_offset", 0)))
    text = f"⚙️ <b>Налаштування бота</b>\n\n👤 <b>Студент:</b> {esc(callback.from_user.first_name or 'Користувач')}\n👥 <b>Підгрупа:</b> {updated.get('subgroup', 1)}-а\n📅 <b>Поточний розклад:</b> <code>{esc(week_title)}</code>\n\n🔔 <b>Керування сповіщеннями:</b>"
    try: await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_settings_keyboard(updated))
    except Exception: pass


@router.message(Command("notes"))
async def cmd_notes(message: Message):
    await message.answer("📚 <b>Конспекти та матеріали</b>\n\nОберіть предмет:", parse_mode="HTML", reply_markup=get_subjects_keyboard("note_view"))


@router.callback_query(F.data.startswith("note_view_"))
async def callback_view_subject_notes(callback: CallbackQuery):
    data_val = callback.data.replace("note_view_", "")
    matched = next((s for s in ALL_SUBJECTS if s.startswith(data_val)), data_val)
    notes = await get_notes_for_subject(callback.from_user.id, matched)
    text = [f"📚 <b>Матеріали:</b> {esc(matched)}\n━━━━━━━━━━━━━━━━━━━━━━\n"]
    if not notes: text.append("<i>Поки що немає збережених матеріалів.</i>\n")
    else:
        for idx, n in enumerate(notes, 1):
            text.append(f"📌 <b>{idx}. {esc(n['note_title'])}</b>\n{esc(n['note_content'])}\n")
    text.append("\nЩоб додати нотатку: /add_note")
    await callback.message.answer("\n".join(text), parse_mode="HTML")
    await callback.answer()


@router.message(Command("add_note"))
async def cmd_add_note(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddNoteFSM.waiting_for_subject)
    await message.answer("📚 Оберіть предмет для нотатки:", parse_mode="HTML", reply_markup=get_subjects_keyboard("note_add"))


@router.callback_query(F.data.startswith("note_add_"), AddNoteFSM.waiting_for_subject)
async def process_note_subject(callback: CallbackQuery, state: FSMContext):
    data_val = callback.data.replace("note_add_", "")
    matched = next((s for s in ALL_SUBJECTS if s.startswith(data_val)), data_val)
    await state.update_data(subject=matched)
    await state.set_state(AddNoteFSM.waiting_for_title)
    await callback.message.answer(f"✅ Предмет: <b>{esc(matched)}</b>\n\nВведіть заголовок нотатки:", parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(AddNoteFSM.waiting_for_title)
async def process_note_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title: return
    await state.update_data(title=title)
    await state.set_state(AddNoteFSM.waiting_for_content)
    await message.answer(f"📝 Заголовок: <b>{esc(title)}</b>\n\nНадішліть вміст або посилання:", parse_mode="HTML", reply_markup=get_cancel_keyboard())


@router.message(AddNoteFSM.waiting_for_content)
async def process_note_content(message: Message, state: FSMContext):
    content = message.text.strip()
    data = await state.get_data()
    await state.clear()
    await add_note(message.from_user.id, data.get("subject", "Предмет"), data.get("title", "Нотатка"), content)
    await message.answer(f"🎉 <b>Нотатку збережено!</b>\n\n📚 <b>Предмет:</b> {esc(data.get('subject'))}\n📌 <b>Заголовок:</b> {esc(data.get('title'))}\n📄 <b>Вміст:</b>\n{esc(content)}", parse_mode="HTML", reply_markup=get_main_keyboard())


@router.message(Command("find"))
@router.message(Command("search"))
async def cmd_search(message: Message):
    query = message.text.replace("/find", "").replace("/search", "").strip().lower()
    if not query:
        await message.answer("🔍 Введіть запит після команди:\n• <code>/find Пукач</code>\n• <code>/find Програмування</code>", parse_mode="HTML")
        return

    results = []
    for short, info in TEACHERS_INFO.items():
        if query in short.lower(): results.append(f"👨‍🏫 <b>Викладач:</b> <code>{esc(short)}</code>\n   📚 {esc(info['role'])}")
    for code, info in CAMPUS_INFO.items():
        if query in code.lower() or query in info["name"].lower(): results.append(f"🏛 <b>Корпус:</b> {esc(code)} — {esc(info['name'])}\n   📍 {esc(info['address'])}")
    found_lessons = []
    for w_num, w_sched in SCHEDULE.items():
        w_name = "Знаменник" if w_num == 1 else "Чисельник"
        for d_idx, lessons in w_sched.items():
            for l in lessons:
                if query in l.subject.lower() or query in l.teacher.lower() or query in l.room.lower():
                    found_lessons.append(f"• <b>{w_name}</b> | {DAY_NAMES[d_idx]} ({l.pair_number} пара, {l.start_time}): {esc(l.subject)} — <code>{esc(l.room)}</code>, {esc(l.teacher)}")
    if found_lessons: results.append("📅 <b>Знайдені пари:</b>\n" + "\n".join(found_lessons[:8]))
    if not results:
        await message.answer(f"🔍 За запитом «{esc(query)}» нічого не знайдено.", parse_mode="HTML")
        return
    await message.answer("🔍 <b>Результати пошуку:</b>\n\n" + "\n\n".join(results), parse_mode="HTML")


# ================= 9. BACKGROUND SCHEDULER =================

async def check_pair_notifications(bot: Bot):
    now = get_now()
    if now.weekday() in (5, 6): return
    now_minutes = now.hour * 60 + now.minute
    users = await get_all_active_users()

    for u in users:
        week_type = get_week_type(now.date(), u.get("custom_week_offset", 0))
        lessons = get_day_lessons(now.weekday(), week_type, u.get("subgroup", 1))
        if not lessons: continue

        for item in analyze_day_gaps(lessons):
            lesson: Lesson = item["lesson"]
            diff = lesson.start_minutes - now_minutes

            # 30m Notification
            if u.get("notify_30m", 1) and item["notify_30m"] and (28 <= diff <= 30):
                if await record_notification_sent(u["user_id"], f"pair_30m_{now.date()}_{lesson.pair_number}"):
                    reason = "🌅 <b>Перша пара дня!</b>" if item["is_first"] else "☕️ <b>Пара після вікна!</b>"
                    msg = f"⏰ <b>Нагадування: через 30 хвилин розпочнеться пара!</b>\n{reason}\n\n{format_lesson_block(lesson)}\n\n🚶‍♂️ Час збиратись!"
                    try: await bot.send_message(u["chat_id"], msg, parse_mode="HTML")
                    except Exception: pass

            # 5m Notification
            if u.get("notify_5m", 1) and (4 <= diff <= 5):
                if await record_notification_sent(u["user_id"], f"pair_5m_{now.date()}_{lesson.pair_number}"):
                    msg = f"⚡️ <b>Увага! Через 5 хвилин дзвінок на пару!</b>\n\n{format_lesson_block(lesson)}\n\n🚪 Заходь до аудиторії!"
                    try: await bot.send_message(u["chat_id"], msg, parse_mode="HTML")
                    except Exception: pass


async def check_deadline_notifications(bot: Bot):
    now = get_now()
    for hw in await get_all_pending_deadlines():
        try:
            dl_dt = datetime.strptime(hw["deadline"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=now.tzinfo)
        except Exception: continue
        diff_seconds = (dl_dt - now).total_seconds()

        checkpoints = [
            ("48h", 47 * 3600, 48 * 3600 + 300, "⚠️ <b>Нагадування про дедлайн (через 2 дні)!</b>"),
            ("24h", 23 * 3600, 24 * 3600 + 300, "🔔 <b>Увага! До дедлайну залишилась 1 доба!</b>"),
            ("3h", 2 * 3600 + 50 * 60, 3 * 3600 + 300, "⏳ <b>Терміново! До дедлайну залишилось 3 години!</b>"),
            ("1h", 55 * 60, 65 * 60, "🚨 <b>Горить дедлайн! Залишилась лише 1 година!</b>"),
            ("15m", 10 * 60, 16 * 60, "🔥 <b>Останні 15 хвилин до кінця дедлайну!</b>"),
        ]
        for name, min_s, max_s, title in checkpoints:
            if min_s <= diff_seconds <= max_s:
                if await record_notification_sent(hw["user_id"], f"deadline_{name}_hw_{hw['id']}"):
                    msg = f"{title}\n\n📚 <b>Предмет:</b> {esc(hw['subject'])}\n📝 <b>Завдання:</b> {esc(hw['task_text'])}\n⏰ <b>Дедлайн:</b> {format_ua_date(dl_dt)} <i>(залишилось {format_time_remaining(dl_dt)})</i>"
                    try: await bot.send_message(hw["chat_id"], msg, parse_mode="HTML", reply_markup=get_homework_item_keyboard(hw["id"], False))
                    except Exception: pass


async def check_morning_summaries(bot: Bot):
    now = get_now()
    cur_time = now.strftime("%H:%M")
    for u in await get_all_active_users():
        if u.get("morning_summary", 1) and u.get("morning_time", "07:30") == cur_time:
            if await record_notification_sent(u["user_id"], f"morning_{now.date()}"):
                sched = format_day_schedule(now.date(), get_week_type(now.date(), u.get("custom_week_offset", 0)), u.get("subgroup", 1))
                hw_list = await get_homework_list(u["user_id"], completed=False)
                hw_sec = "\n\n📌 <b>Завдання на сьогодні:</b>\n" + "\n".join([f"• <b>{esc(h['subject'])}:</b> {esc(h['task_text'])}" for h in hw_list[:3]]) if hw_list else ""
                try: await bot.send_message(u["chat_id"], f"🌅 <b>Доброго ранку, {esc(u.get('first_name') or 'студенте')}!</b>\n\n{sched}{hw_sec}", parse_mode="HTML")
                except Exception: pass


async def check_evening_summaries(bot: Bot):
    now = get_now()
    cur_time = now.strftime("%H:%M")
    tmrw = now.date() + timedelta(days=1)
    for u in await get_all_active_users():
        if u.get("evening_summary", 1) and u.get("evening_time", "21:00") == cur_time:
            if await record_notification_sent(u["user_id"], f"evening_{now.date()}"):
                sched = format_day_schedule(tmrw, get_week_type(tmrw, u.get("custom_week_offset", 0)), u.get("subgroup", 1))
                hw_list = await get_homework_list(u["user_id"], completed=False)
                hw_sec = "\n\n📝 <b>Домашка на завтра:</b>\n" + "\n".join([f"• <b>{esc(h['subject'])}:</b> {esc(h['task_text'])}" for h in hw_list[:3]]) if hw_list else ""
                try: await bot.send_message(u["chat_id"], f"🌙 <b>Вечірній підсумок: план на завтра</b>\n\n{sched}{hw_sec}\n\nГарного відпочинку! 😴", parse_mode="HTML")
                except Exception: pass


async def scheduler_loop(bot: Bot):
    logger.info("Scheduler daemon started.")
    last_cleanup = -1
    while True:
        try:
            await check_pair_notifications(bot)
            await check_deadline_notifications(bot)
            await check_morning_summaries(bot)
            await check_evening_summaries(bot)
            now = get_now()
            if now.day != last_cleanup and now.hour == 3:
                await clean_old_notifications(days=7)
                last_cleanup = now.day
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
        await asyncio.sleep(30)


# ================= 10. ENTRYPOINT =================

async def setup_bot_interface(bot: Bot):
    commands = [
        BotCommand(command="app", description="📱 Відкрити Web App"),
        BotCommand(command="start", description="🏠 Головне меню"),
        BotCommand(command="today", description="📅 Розклад на сьогодні"),
        BotCommand(command="tomorrow", description="🌅 Розклад на завтра"),
        BotCommand(command="week", description="🗓 Розклад на тиждень"),
        BotCommand(command="now", description="⏳ Зараз / Наступна"),
        BotCommand(command="hw", description="📝 Домашка та дедлайни"),
        BotCommand(command="add", description="➕ Додати завдання"),
        BotCommand(command="bells", description="⏰ Розклад дзвінків"),
        BotCommand(command="campuses", description="🏛 Корпуси та адреси"),
        BotCommand(command="teachers", description="👨‍🏫 Викладачі"),
        BotCommand(command="notes", description="📚 Матеріали та нотатки"),
        BotCommand(command="find", description="🔍 Пошук по розкладу"),
        BotCommand(command="settings", description="⚙️ Налаштування сповіщень"),
        BotCommand(command="help", description="ℹ️ Довідка та команди"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="📱 Web App", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    except Exception as e:
        logger.warning(f"Menu button set failed: {e}")


async def main():
    logger.info("Starting Schedule & Deadline Bot for group ШІ-11...")
    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    await setup_bot_interface(bot)
    scheduler_task = asyncio.create_task(scheduler_loop(bot))

    logger.info("Bot is polling updates...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
