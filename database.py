"""
طبقة قاعدة البيانات v2 — مهام + اجتماعات + اشتراكات Push
الملف النهائي: backend/database.py
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_PATH", "/data/tasks.db")


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'مفتوحة',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                title TEXT NOT NULL,
                attendees TEXT,
                location TEXT,
                meeting_date TEXT,
                meeting_time TEXT,
                duration_minutes INTEGER DEFAULT 60,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'قادم',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT UNIQUE NOT NULL,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                device_token TEXT,
                platform TEXT DEFAULT 'web',
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def insert_task(raw_text, title, category, priority, due_date):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tasks (raw_text, title, category, priority, due_date, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'مفتوحة', ?)""",
            (raw_text, title, category, priority, due_date, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def list_tasks(status=None):
    with get_conn() as conn:
        if status:
            rows = conn.execute("SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_task_status(task_id, status):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
        conn.commit()


def count_open_tasks_by_category():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) as c FROM tasks WHERE status='مفتوحة' GROUP BY category"
        ).fetchall()
        return {r["category"]: r["c"] for r in rows}


def insert_meeting(raw_text, title, attendees, location, meeting_date, meeting_time, duration_minutes, notes):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO meetings
               (raw_text, title, attendees, location, meeting_date, meeting_time, duration_minutes, notes, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'قادم', ?)""",
            (raw_text, title, attendees, location, meeting_date, meeting_time,
             duration_minutes, notes, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def list_meetings(status=None):
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM meetings WHERE status=? ORDER BY meeting_date ASC, meeting_time ASC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM meetings ORDER BY meeting_date ASC, meeting_time ASC"
            ).fetchall()
        return [dict(r) for r in rows]


def update_meeting_status(meeting_id, status):
    with get_conn() as conn:
        conn.execute("UPDATE meetings SET status=? WHERE id=?", (status, meeting_id))
        conn.commit()


def get_today_meetings():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM meetings WHERE meeting_date=? AND status='قادم' ORDER BY meeting_time ASC",
            (today,)
        ).fetchall()
        return [dict(r) for r in rows]


def save_push_subscription(endpoint, p256dh, auth, device_token=None, platform="web"):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO push_subscriptions (endpoint, p256dh, auth, device_token, platform, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (endpoint, p256dh, auth, device_token, platform, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_all_subscriptions():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM push_subscriptions").fetchall()
        return [dict(r) for r in rows]


def get_daily_report():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_conn() as conn:
        open_tasks = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE status='مفتوحة'"
        ).fetchone()["c"]
        done_today = conn.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE status='منجزة' AND created_at LIKE ?",
            (f"{today}%",)
        ).fetchone()["c"]
        meetings_today = conn.execute(
            "SELECT COUNT(*) as c FROM meetings WHERE meeting_date=?", (today,)
        ).fetchone()["c"]
        by_priority = conn.execute(
            "SELECT priority, COUNT(*) as c FROM tasks WHERE status='مفتوحة' GROUP BY priority"
        ).fetchall()

    return {
        "date": today,
        "open_tasks": open_tasks,
        "done_today": done_today,
        "meetings_today": meetings_today,
        "by_priority": {r["priority"]: r["c"] for r in by_priority},
    }
