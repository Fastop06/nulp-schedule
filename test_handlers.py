from __future__ import annotations

"""
Simulated Integration & Handler Tests for aiogram 3 Dispatcher.
"""
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import User, Chat, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey

from main import (
    BOT_TOKEN, init_db, register_or_update_user, get_homework_list, add_homework,
    cmd_start, cmd_help, handle_today_schedule, handle_tomorrow_schedule,
    handle_week_schedule, handle_now_pair, handle_bells, handle_campuses,
    handle_teachers, callback_sched_day, callback_sched_switch_week,
    handle_view_homework, start_add_homework, process_subject_btn,
    process_task_text, process_deadline_btn, process_deadline_text,
    process_priority_btn, callback_toggle_hw, callback_del_hw, AddHomeworkFSM,
    handle_settings, callback_toggle_setting, cmd_notes,
    callback_view_subject_notes, cmd_search
)


async def run_handler_tests():
    print("=== STARTING AIOGRAM HANDLER & CALLBACK SIMULATION ===")
    await init_db()
    
    storage = MemoryStorage()
    dummy_user = User(id=777888999, is_bot=False, first_name="Tester", username="tester")
    dummy_chat = Chat(id=777888999, type="private")
    
    def make_msg(text: str = ""):
        m = MagicMock(spec=Message)
        m.from_user = dummy_user
        m.chat = dummy_chat
        m.text = text
        m.answer = AsyncMock()
        m.delete = AsyncMock()
        return m

    def make_cb(data: str):
        c = MagicMock(spec=CallbackQuery)
        c.from_user = dummy_user
        c.data = data
        c.message = make_msg()
        c.message.edit_text = AsyncMock()
        c.answer = AsyncMock()
        return c

    key = StorageKey(bot_id=123, chat_id=777888999, user_id=777888999)
    state = FSMContext(storage=storage, key=key)

    # 1. /start and /help
    msg = make_msg("/start")
    await cmd_start(msg)
    assert msg.answer.called
    print("✅ /start handler passed")

    msg = make_msg("/help")
    await cmd_help(msg)
    assert msg.answer.called
    print("✅ /help handler passed")

    # 2. Schedule Handlers
    msg = make_msg("📅 Сьогодні")
    await handle_today_schedule(msg)
    assert msg.answer.called

    msg = make_msg("🌅 Завтра")
    await handle_tomorrow_schedule(msg)
    assert msg.answer.called

    msg = make_msg("🗓 На тиждень")
    await handle_week_schedule(msg)
    assert msg.answer.called

    msg = make_msg("⏳ Зараз / Наступна")
    await handle_now_pair(msg)
    assert msg.answer.called

    msg = make_msg("⏰ Дзвінки")
    await handle_bells(msg)
    assert msg.answer.called

    msg = make_msg("🏛 Корпуси")
    await handle_campuses(msg)
    assert msg.answer.called

    msg = make_msg("/teachers")
    await handle_teachers(msg)
    assert msg.answer.called
    print("✅ All schedule command handlers passed")

    # 3. Schedule Callbacks
    cb = make_cb("sched_day_0_1")
    await callback_sched_day(cb)
    assert cb.answer.called

    cb = make_cb("sched_switch_week_2")
    await callback_sched_switch_week(cb)
    assert cb.answer.called
    print("✅ Schedule callbacks passed")

    # 4. Homework FSM Workflow
    # Step 1: Start add
    msg = make_msg("➕ Додати ДЗ")
    await start_add_homework(msg, state)
    
    # Step 2: Pick subject
    cb = make_cb("hw_subj_Дискретна математика")
    await process_subject_btn(cb, state)
    
    # Step 3: Enter task text
    msg = make_msg("Лабораторна робота №1 <варіант 3> & тест")
    await process_task_text(msg, state)
    
    # Step 4: Pick quick deadline
    cb = make_cb("hw_dl_tmrw_2359")
    await process_deadline_btn(cb, state)
    
    # Step 5: Pick priority
    cb = make_cb("hw_prio_high")
    await process_priority_btn(cb, state)
    assert cb.answer.called
    print("✅ Homework addition FSM workflow passed")

    # Check homework was added to DB
    hw_list = await get_homework_list(777888999, completed=False)
    assert len(hw_list) >= 1
    hw_id = hw_list[0]["id"]

    # Toggle homework status
    cb = make_cb(f"hw_toggle_{hw_id}")
    await callback_toggle_hw(cb)
    assert cb.answer.called

    # Delete homework
    cb = make_cb(f"hw_del_{hw_id}")
    await callback_del_hw(cb)
    assert cb.answer.called
    print("✅ Homework toggle and delete callbacks passed")

    # 5. Settings
    msg = make_msg("⚙️ Налаштування")
    await handle_settings(msg)
    assert msg.answer.called

    cb = make_cb("cfg_toggle_notify_30m")
    await callback_toggle_setting(cb)
    assert cb.answer.called
    print("✅ Settings handlers passed")

    # 6. Notes & Search
    msg = make_msg("/notes")
    await cmd_notes(msg)
    assert msg.answer.called

    cb = make_cb("note_view_Основи програмування")
    await callback_view_subject_notes(cb)
    assert cb.answer.called

    msg = make_msg("/find Пукач")
    await cmd_search(msg)
    assert msg.answer.called
    print("✅ Notes and Search handlers passed")

    print("\n🎉 ALL AIOGRAM HANDLERS & CALLBACK TESTS PASSED 100%! 🚀")


if __name__ == "__main__":
    asyncio.run(run_handler_tests())
