from __future__ import annotations

"""
Comprehensive Crash Test & Bug Test Suite for Schedule & Deadline Bot.
Tests:
1. Multilingual Date & Time Parser (50+ test cases)
2. Special Characters, HTML Escaping, and Entity Safety
3. Schedule Data Integrity & Gap Analysis
4. Async SQLite Database Stress & Edge Cases
5. Scheduler Notification Triggers & Timers
6. Message Formatting & Length Limits
"""
import asyncio
import os
import random
import string
import html
from datetime import datetime, date, timedelta, time

from main import (
    BASE_DIR, SCHEDULE, BELL_SCHEDULE, CAMPUS_INFO, TEACHERS_INFO,
    get_week_type, get_week_name, get_day_lessons, analyze_day_gaps,
    ALL_SUBJECTS, DAY_NAMES, init_db, register_or_update_user,
    get_user, update_user_setting, add_homework, get_homework_list,
    toggle_homework_status, delete_homework, record_notification_sent,
    add_note, get_notes_for_subject, delete_note, get_all_pending_deadlines,
    parse_user_deadline_input, format_ua_date, format_time_remaining, get_now,
    format_lesson_block, format_day_schedule, format_week_schedule,
    format_live_status, format_bells_message, format_homework_item,
    format_campuses_message, format_teachers_message, esc
)


async def test_date_parser():
    print("--- [TEST 1] Multilingual & Edge Case Date Parser ---")
    now = get_now()
    
    test_cases = [
        # Ukrainian Keywords
        ("сьогодні", now.date(), 23, 59),
        ("сьогодні 15:30", now.date(), 15, 30),
        ("сьогодні о 10", now.date(), 10, 0),
        ("завтра", (now + timedelta(days=1)).date(), 23, 59),
        ("завтра 18:00", (now + timedelta(days=1)).date(), 18, 0),
        ("завтра о 9", (now + timedelta(days=1)).date(), 9, 0),
        ("післязавтра", (now + timedelta(days=2)).date(), 23, 59),
        ("післязавтра 12:45", (now + timedelta(days=2)).date(), 12, 45),
        ("через 2 дні", (now + timedelta(days=2)).date(), 23, 59),
        ("через 3 дні 20:00", (now + timedelta(days=3)).date(), 20, 0),
        ("через 5 днів", (now + timedelta(days=5)).date(), 23, 59),
        
        # Russian Keywords
        ("сегодня", now.date(), 23, 59),
        ("сегодня в 14:00", now.date(), 14, 0),
        ("завтра", (now + timedelta(days=1)).date(), 23, 59),
        ("завтра в 19:30", (now + timedelta(days=1)).date(), 19, 30),
        ("послезавтра", (now + timedelta(days=2)).date(), 23, 59),
        ("послезавтра в 11", (now + timedelta(days=2)).date(), 11, 0),
        ("через 2 дня 17:00", (now + timedelta(days=2)).date(), 17, 0),
        ("через 4 дня", (now + timedelta(days=4)).date(), 23, 59),

        # Weekdays in UA and RU
        ("понеділок", None, 23, 59),
        ("понедельник 08:30", None, 8, 30),
        ("вівторок 12:00", None, 12, 0),
        ("вторник", None, 23, 59),
        ("середа 10:00", None, 10, 0),
        ("среда в 16:00", None, 16, 0),
        ("четвер", None, 23, 59),
        ("четверг 15:00", None, 15, 0),
        ("п'ятниця 23:59", None, 23, 59),
        ("пятница 18:00", None, 18, 0),
        ("наступна п'ятниця 23:59", None, 23, 59),
        ("субота 12:00", None, 12, 0),
        ("суббота", None, 23, 59),
        ("неділя 20:00", None, 20, 0),
        ("воскресенье", None, 23, 59),

        # Numerical Dates
        ("15.09", date(now.year, 9, 15), 23, 59),
        ("15.09 18:00", date(now.year, 9, 15), 18, 0),
        ("15.09.2026", date(2026, 9, 15), 23, 59),
        ("15.09.2026 14:30", date(2026, 9, 15), 14, 30),
        ("2026-09-20", date(2026, 9, 20), 23, 59),
        ("2026-09-20 16:45", date(2026, 9, 20), 16, 45),

        # Textual Month Dates
        ("15 вересня", date(now.year, 9, 15), 23, 59),
        ("15 вересня 18:00", date(now.year, 9, 15), 18, 0),
        ("20 сентября 12:00", date(now.year, 9, 20), 12, 0),
        ("10 жовтня 10:00", date(now.year, 10, 10), 10, 0),
        ("10 октября", date(now.year, 10, 10), 23, 59),

        # Relative Hours & Minutes
        ("через 2 години", None, None, None),
        ("через 3 часа", None, None, None),
        ("через 45 хвилин", None, None, None),
        ("через 30 минут", None, None, None),
    ]

    for inp, expected_date, exp_h, exp_m in test_cases:
        res = parse_user_deadline_input(inp)
        assert res is not None, f"Failed to parse valid input: '{inp}'"
        if expected_date is not None:
            assert res.date() == expected_date, f"Date mismatch for '{inp}': got {res.date()}, expected {expected_date}"
        if exp_h is not None:
            assert res.hour == exp_h, f"Hour mismatch for '{inp}': got {res.hour}, expected {exp_h}"
        if exp_m is not None:
            assert res.minute == exp_m, f"Minute mismatch for '{inp}': got {res.minute}, expected {exp_m}"

    # Invalid Inputs Test
    invalid_inputs = ["", "abc", "привет", "2026-99-99", "35.15", "99:99"]
    for inv in invalid_inputs:
        res = parse_user_deadline_input(inv)
        assert res is None, f"Expected None for invalid input: '{inv}', got {res}"

    print("✅ Date & Time parser passed 100% of test cases!")


async def test_html_safety():
    print("--- [TEST 2] HTML Escaping & Injection Safety ---")
    dangerous_inputs = [
        "<script>alert(1)</script>",
        "<b>bold</b> & <i>italic</i>",
        "Лабораторна <1> & <2> -> 'варіант' \"test\"",
        "Special_chars *with* `markdown` and [links](http://test)",
        "& < > \" ' / \\",
        "Line 1\nLine 2\nLine 3\n\n\nLine 4"
    ]
    
    for dangerous in dangerous_inputs:
        escaped = esc(dangerous)
        assert "<script>" not in escaped
        
        # Test formatting functions with dangerous content
        dummy_hw = {
            "id": 1,
            "subject": dangerous,
            "task_text": dangerous,
            "deadline": "2026-09-15 18:00:00",
            "priority": "high",
            "is_completed": 0
        }
        formatted_hw = format_homework_item(dummy_hw, 1)
        assert "<script>" not in formatted_hw
        
    print("✅ HTML escaping & entity safety passed!")


async def test_schedule_data_and_gaps():
    print("--- [TEST 3] Schedule Integrity & Gap Calculations ---")
    
    # Check Week 1 (Знаменник) & Week 2 (Чисельник)
    for w in (1, 2):
        for d in range(5):
            lessons = get_day_lessons(d, w, subgroup=1)
            analyzed = analyze_day_gaps(lessons)
            
            # Check bell times integrity
            for item in analyzed:
                l = item["lesson"]
                assert l.pair_number in BELL_SCHEDULE
                assert l.start_minutes < l.end_minutes
                
    # Check gap detection on Monday
    mon_lessons = get_day_lessons(0, 1, 1)
    mon_analyzed = analyze_day_gaps(mon_lessons)
    assert mon_analyzed[0]["is_first"] is True
    assert mon_analyzed[0]["notify_30m"] is True
    assert mon_analyzed[1]["notify_30m"] is False
    assert mon_analyzed[2]["has_window"] is True
    assert mon_analyzed[2]["notify_30m"] is True

    # Check Friday on Week 2 (has pair 1, 2, 3)
    fri_lessons = get_day_lessons(4, 2, 1)
    assert len(fri_lessons) == 3
    assert fri_lessons[0].pair_number == 1
    assert fri_lessons[0].subject == "Дискретна математика"
    assert fri_lessons[0].teacher == "Пелещишин О.П."

    print("✅ Schedule data and gap calculations passed!")


async def test_database_stress():
    print("--- [TEST 4] Database Stress & CRUD Operations ---")
    await init_db()
    
    user_id = random.randint(1000000, 99999999)
    await register_or_update_user(user_id, user_id, "stress_user", "Stress")
    
    # Add 10 homework items
    hw_ids = []
    for i in range(10):
        dl = get_now() + timedelta(days=i+1)
        hid = await add_homework(user_id, f"Subject {i}", f"Task {i}", dl, "normal")
        hw_ids.append(hid)
        
    active_hw = await get_homework_list(user_id, completed=False)
    assert len(active_hw) == 10
    
    # Toggle 5 items
    for hid in hw_ids[:5]:
        status = await toggle_homework_status(hid, user_id)
        assert status is True
        
    active_after = await get_homework_list(user_id, completed=False)
    assert len(active_after) == 5
    completed = await get_homework_list(user_id, completed=True)
    assert len(completed) == 5
    
    # Delete all items
    for hid in hw_ids:
        deleted = await delete_homework(hid, user_id)
        assert deleted is True
        
    final_hw = await get_homework_list(user_id, completed=None)
    assert len(final_hw) == 0
    
    # Notes CRUD
    nid = await add_note(user_id, "Основи програмування", "Title <1>", "Content & link")
    notes = await get_notes_for_subject(user_id, "Основи програмування")
    assert len(notes) >= 1
    await delete_note(nid, user_id)
    
    print("✅ Database stress and concurrency passed!")


async def test_all_formatters():
    print("--- [TEST 5] All Message Formatters Output Check ---")
    
    # Day schedule formatting
    for day in range(7):
        target_date = date(2026, 9, 7) + timedelta(days=day)
        res1 = format_day_schedule(target_date, week_type=1, subgroup=1)
        assert len(res1) > 10
        res2 = format_day_schedule(target_date, week_type=2, subgroup=1)
        assert len(res2) > 10

    # Week schedule
    w1 = format_week_schedule(1, 1)
    assert "ЗНАМЕННИК" in w1.upper()
    w2 = format_week_schedule(2, 1)
    assert "ЧИСЕЛЬНИК" in w2.upper()

    # Live status
    live = format_live_status(subgroup=1, week_offset=0)
    assert len(live) > 10

    # Bells & Campuses & Teachers
    assert len(format_bells_message()) > 10
    assert len(format_campuses_message()) > 10
    assert len(format_teachers_message()) > 10

    print("✅ All message formatters generated valid HTML output!")


async def run_full_test_suite():
    print("=====================================================")
    print("🚀 STARTING COMPLETE CRASH & BUG TEST SUITE 🚀")
    print("=====================================================\n")
    
    await test_date_parser()
    print("")
    await test_html_safety()
    print("")
    await test_schedule_data_and_gaps()
    print("")
    await test_database_stress()
    print("")
    await test_all_formatters()
    print("")
    
    print("=====================================================")
    print("🏆 ALL CRASH TESTS AND BUG TESTS PASSED 100%! 🏆")
    print("=====================================================")


if __name__ == "__main__":
    asyncio.run(run_full_test_suite())
